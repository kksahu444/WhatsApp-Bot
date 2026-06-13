#!/usr/bin/env python3
"""
Product Ingestion Script

Fetches products from Supabase and indexes them in LanceDB
for vector search capabilities.

Usage:
    python -m backend.scripts.ingest_products
    
    Or from project root:
    python backend/scripts/ingest_products.py
"""

import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Configure loguru for this script
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO",
    colorize=True
)


def main():
    """
    Main ingestion function.
    
    Fetches products from Supabase and indexes them in LanceDB
    with vector embeddings for semantic search.
    """
    logger.info("=" * 60)
    logger.info("Starting Product Ingestion")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    try:
        # Import search engine (this initializes embedding model and LanceDB)
        from backend.rag.search_engine import ProductSearchEngine
        
        logger.info("Initializing search engine...")
        engine = ProductSearchEngine()
        
        # Run ingestion
        logger.info("Starting ingestion from Supabase...")
        count = engine.ingest_from_supabase()
        
        elapsed = time.time() - start_time
        
        logger.info("=" * 60)
        logger.info(f"Ingestion Complete!")
        logger.info(f"   Products indexed: {count}")
        logger.info(f"   Time elapsed: {elapsed:.2f} seconds")
        logger.info("=" * 60)
        
        # Quick verification
        if count > 0:
            logger.info("Running test search...")
            results = engine.search("laptop", top_k=3)
            if results:
                logger.info(f"   Found {len(results)} results for 'laptop'")
                for i, r in enumerate(results, 1):
                    logger.info(f"   {i}. {r['name']} - Rs.{r['price']:.0f} (score: {r['score']:.3f})")
            else:
                logger.warning("   No results found for test query")
        
        return count
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
