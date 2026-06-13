"""
RAG Operations Utility
======================
Standalone embedding and ingestion logic for the dashboard.
IMPORTANT: This is intentionally separate from backend to ensure container isolation.

Uses:
- LanceDB for vector storage (shared volume with backend)
- Google Gemini for embeddings (models/embedding-001)
- pypdf for PDF parsing
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional, BinaryIO, Tuple
from pathlib import Path

import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

LANCEDB_PATH = os.getenv("LANCEDB_PATH", "/app/data/lancedb")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "models/embedding-001"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TABLE_NAME = "products"


# ============================================================================
# LAZY IMPORTS (avoid import errors if packages missing)
# ============================================================================

_lancedb = None
_genai = None
_pypdf = None


def _get_lancedb():
    """Lazy import lancedb."""
    global _lancedb
    if _lancedb is None:
        import lancedb
        _lancedb = lancedb
    return _lancedb


def _get_genai():
    """Lazy import google.generativeai."""
    global _genai
    if _genai is None:
        import google.generativeai as genai
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
        _genai = genai
    return _genai


def _get_pypdf():
    """Lazy import pypdf."""
    global _pypdf
    if _pypdf is None:
        from pypdf import PdfReader
        _pypdf = PdfReader
    return _pypdf


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

@st.cache_resource
def get_lancedb_connection():
    """
    Get cached LanceDB connection.
    Uses the shared volume path with backend.
    """
    lancedb = _get_lancedb()
    
    # Ensure directory exists
    Path(LANCEDB_PATH).mkdir(parents=True, exist_ok=True)
    
    db = lancedb.connect(LANCEDB_PATH)
    logger.info(f"Connected to LanceDB at {LANCEDB_PATH}")
    
    return db


def get_or_create_table(db, table_name: str = TABLE_NAME):
    """
    Get existing table or create a new one.
    
    Args:
        db: LanceDB connection
        table_name: Name of the table
        
    Returns:
        LanceDB table
    """
    existing_tables = db.table_names()
    
    if table_name in existing_tables:
        return db.open_table(table_name)
    else:
        # Create empty table with schema
        # Note: LanceDB requires at least one record to infer schema
        logger.warning(f"Table '{table_name}' does not exist. Will be created on first ingest.")
        return None


# ============================================================================
# EMBEDDING
# ============================================================================

def embed_text(text: str) -> List[float]:
    """
    Generate embedding for text using Gemini.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector as list of floats
    """
    genai = _get_genai()
    
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set. Cannot generate embeddings.")
    
    try:
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        raise


def embed_texts_batch(texts: List[str], batch_size: int = 20) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batches.
    
    Args:
        texts: List of texts to embed
        batch_size: Number of texts per batch
        
    Returns:
        List of embedding vectors
    """
    genai = _get_genai()
    
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set. Cannot generate embeddings.")
    
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        try:
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=batch,
                task_type="retrieval_document"
            )
            embeddings.extend(result['embedding'])
        except Exception as e:
            logger.error(f"Batch embedding error at index {i}: {e}")
            # Fall back to individual embedding
            for text in batch:
                try:
                    embeddings.append(embed_text(text))
                except Exception as inner_e:
                    logger.error(f"Individual embedding failed: {inner_e}")
                    # Use zero vector as fallback (not ideal but prevents crash)
                    embeddings.append([0.0] * 768)
    
    return embeddings


# ============================================================================
# TEXT PROCESSING
# ============================================================================

def extract_text_from_pdf(file_obj: BinaryIO) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        file_obj: File-like object containing PDF
        
    Returns:
        Extracted text as string
    """
    PdfReader = _get_pypdf()
    
    try:
        reader = PdfReader(file_obj)
        text_parts = []
        
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
        
        full_text = "\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} characters from {len(reader.pages)} pages")
        
        return full_text
        
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise


def extract_text_from_txt(file_obj: BinaryIO) -> str:
    """
    Extract text from a TXT file.
    
    Args:
        file_obj: File-like object containing text
        
    Returns:
        Text content as string
    """
    try:
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
        return content
    except Exception as e:
        logger.error(f"TXT extraction error: {e}")
        raise


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    # Clean text
    text = re.sub(r'\s+', ' ', text).strip()
    
    if not text:
        return []
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence ending within last 100 chars
            last_period = text.rfind('.', end - 100, end)
            last_newline = text.rfind('\n', end - 100, end)
            break_point = max(last_period, last_newline)
            
            if break_point > start:
                end = break_point + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start with overlap
        start = end - overlap if end < len(text) else len(text)
    
    return chunks


# ============================================================================
# INGESTION
# ============================================================================

def ingest_document(
    file_obj: BinaryIO,
    filename: str,
    source_type: str = "document",
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[bool, int, str]:
    """
    Ingest a document into the RAG knowledge base.
    
    Args:
        file_obj: File-like object containing the document
        filename: Original filename
        source_type: Type of source (document, product_catalog, faq, etc.)
        metadata: Additional metadata to store with chunks
        
    Returns:
        Tuple of (success, num_chunks, message)
    """
    logger.info(f"Starting ingestion for: {filename}")
    
    # Determine file type and extract text
    file_ext = Path(filename).suffix.lower()
    
    try:
        if file_ext == '.pdf':
            text = extract_text_from_pdf(file_obj)
        elif file_ext in ['.txt', '.text']:
            text = extract_text_from_txt(file_obj)
        else:
            return False, 0, f"Unsupported file type: {file_ext}"
    except Exception as e:
        return False, 0, f"Failed to extract text: {str(e)}"
    
    # Check if any text was extracted
    if not text or len(text.strip()) < 10:
        logger.warning(f"No text extracted from {filename}. Skipping ingestion.")
        return False, 0, "No text could be extracted from the document. The file may be empty, scanned (image-only), or corrupted."
    
    # Chunk the text
    chunks = chunk_text(text)
    
    if not chunks:
        logger.warning(f"No chunks created from {filename}. Text may be too short.")
        return False, 0, "Document produced no valid chunks after processing."
    
    logger.info(f"Created {len(chunks)} chunks from {filename}")
    
    # Generate embeddings
    try:
        embeddings = embed_texts_batch(chunks)
    except Exception as e:
        return False, 0, f"Failed to generate embeddings: {str(e)}"
    
    # Prepare records for LanceDB
    records = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        record = {
            "text": chunk,
            "vector": embedding,
            "source": filename,
            "source_type": source_type,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        
        # Add custom metadata
        if metadata:
            record.update(metadata)
        
        records.append(record)
    
    # Add to LanceDB
    try:
        db = get_lancedb_connection()
        existing_tables = db.table_names()
        
        if TABLE_NAME in existing_tables:
            table = db.open_table(TABLE_NAME)
            table.add(records)
            logger.info(f"Added {len(records)} records to existing table '{TABLE_NAME}'")
        else:
            # Create new table
            table = db.create_table(TABLE_NAME, records)
            logger.info(f"Created new table '{TABLE_NAME}' with {len(records)} records")
        
        return True, len(chunks), f"Successfully indexed {len(chunks)} chunks from {filename}"
        
    except Exception as e:
        logger.error(f"LanceDB insertion error: {e}")
        return False, 0, f"Failed to store in database: {str(e)}"


def get_knowledge_base_stats() -> Dict[str, Any]:
    """
    Get statistics about the knowledge base.
    
    Returns:
        Dictionary with stats (total_records, sources, etc.)
    """
    try:
        db = get_lancedb_connection()
        existing_tables = db.table_names()
        
        stats = {
            "tables": existing_tables,
            "total_records": 0,
            "sources": [],
        }
        
        if TABLE_NAME in existing_tables:
            table = db.open_table(TABLE_NAME)
            
            # Get record count
            df = table.to_pandas()
            stats["total_records"] = len(df)
            
            # Get unique sources
            if "source" in df.columns:
                stats["sources"] = df["source"].unique().tolist()
            
            # Get source types
            if "source_type" in df.columns:
                stats["source_types"] = df["source_type"].value_counts().to_dict()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting KB stats: {e}")
        return {
            "tables": [],
            "total_records": 0,
            "sources": [],
            "error": str(e)
        }


def search_knowledge_base(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search the knowledge base.
    
    Args:
        query: Search query
        limit: Maximum results to return
        
    Returns:
        List of matching records with scores
    """
    try:
        db = get_lancedb_connection()
        
        if TABLE_NAME not in db.table_names():
            return []
        
        # Generate query embedding
        query_embedding = embed_text(query)
        
        # Search
        table = db.open_table(TABLE_NAME)
        results = table.search(query_embedding).limit(limit).to_list()
        
        return results
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []
