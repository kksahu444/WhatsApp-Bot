"""
Embeddings module for generating text embeddings using SentenceTransformers.

Uses the all-MiniLM-L6-v2 model which produces 384-dimensional vectors.
Optimized for semantic similarity and search applications.
"""

from typing import List, Optional, Union
import numpy as np
from loguru import logger

# Lazy import to avoid slow startup
SentenceTransformer = None

# Global model instance (singleton)
_model = None


def _load_sentence_transformer():
    """Lazy load SentenceTransformer to avoid import overhead."""
    global SentenceTransformer
    if SentenceTransformer is None:
        from sentence_transformers import SentenceTransformer as ST
        SentenceTransformer = ST


def get_embedding_model():
    """
    Get or load SentenceTransformer model singleton.
    
    Uses all-MiniLM-L6-v2 which is:
    - Fast (80ms per sentence on CPU)
    - Lightweight (80MB model size)
    - Good quality (384-dimensional embeddings)
    
    Returns:
        SentenceTransformer: Embedding model instance
        
    Raises:
        RuntimeError: If model fails to load
    """
    global _model
    
    if _model is None:
        try:
            _load_sentence_transformer()
            logger.info("📥 Loading embedding model: all-MiniLM-L6-v2...")
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise RuntimeError(f"Failed to load embedding model: {e}")
    
    return _model


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector from text.
    
    Args:
        text: Input text to embed (will be truncated if > 512 tokens)
        
    Returns:
        List[float]: 384-dimensional embedding vector
        
    Raises:
        ValueError: If text is empty
        RuntimeError: If embedding generation fails
    """
    if not text or not text.strip():
        raise ValueError("Cannot generate embedding for empty text")
    
    model = get_embedding_model()
    
    # Truncate long text to approximately 512 tokens
    words = text.split()
    if len(words) > 512:
        text = ' '.join(words[:512])
        logger.warning(f"⚠️ Text truncated from {len(words)} to 512 words")
    
    try:
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"❌ Failed to generate embedding: {e}")
        raise RuntimeError(f"Embedding generation failed: {e}")


def generate_embeddings_batch(
    texts: List[str],
    show_progress: bool = True,
    batch_size: int = 32
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts (faster than one-by-one).
    
    Uses batched encoding for efficiency. Much faster than calling
    generate_embedding() in a loop for large datasets.
    
    Args:
        texts: List of input texts to embed
        show_progress: Whether to show progress bar
        batch_size: Number of texts to process at once
        
    Returns:
        List[List[float]]: List of 384-dimensional embedding vectors
        
    Raises:
        ValueError: If texts list is empty
        RuntimeError: If embedding generation fails
    """
    if not texts:
        raise ValueError("Cannot generate embeddings for empty text list")
    
    model = get_embedding_model()
    
    # Truncate long texts
    processed_texts = []
    truncated_count = 0
    
    for text in texts:
        if not text or not text.strip():
            processed_texts.append("")
            continue
            
        words = text.split()
        if len(words) > 512:
            text = ' '.join(words[:512])
            truncated_count += 1
        processed_texts.append(text)
    
    if truncated_count > 0:
        logger.warning(f"⚠️ Truncated {truncated_count} texts to 512 words")
    
    try:
        logger.info(f"🧠 Generating embeddings for {len(processed_texts)} texts...")
        embeddings = model.encode(
            processed_texts,
            convert_to_numpy=True,
            show_progress_bar=show_progress,
            batch_size=batch_size
        )
        logger.info(f"✅ Generated {len(embeddings)} embeddings")
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"❌ Failed to generate batch embeddings: {e}")
        raise RuntimeError(f"Batch embedding generation failed: {e}")


def get_embedding_dimension() -> int:
    """
    Get embedding vector dimension.
    
    Returns:
        int: 384 for all-MiniLM-L6-v2 model
    """
    return 384


def compute_similarity(
    embedding1: List[float],
    embedding2: List[float]
) -> float:
    """
    Compute cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        float: Cosine similarity score (0.0 to 1.0)
    """
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def preload_model() -> None:
    """
    Preload the embedding model.
    
    Call this during application startup to avoid
    cold start latency on first embedding request.
    """
    logger.info("🔄 Preloading embedding model...")
    get_embedding_model()
    logger.info("✅ Embedding model preloaded")
