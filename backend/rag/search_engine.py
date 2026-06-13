"""
Product Search Engine using LanceDB for hybrid search.

Combines semantic vector search with full-text search (BM25)
for accurate product retrieval based on natural language queries.
"""

import os
from typing import List, Dict, Optional, Any
from pathlib import Path

import lancedb
from loguru import logger

from backend.config.settings import settings
from backend.rag.embeddings import (
    generate_embedding,
    generate_embeddings_batch,
    get_embedding_dimension,
)


# Table name for products
PRODUCTS_TABLE = "products"


class ProductSearchEngine:
    """
    Hybrid search engine for products using LanceDB.
    
    Combines semantic vector search with keyword (BM25) search
    for accurate product retrieval based on natural language queries.
    
    Attributes:
        db_path: Path to LanceDB storage directory
        db: LanceDB connection instance
        table: Products table reference
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize search engine.
        
        Args:
            db_path: Path to LanceDB storage (default: from settings)
        """
        self.db_path = db_path or settings.lancedb_path
        self.db: Optional[lancedb.DBConnection] = None
        self.table = None
        self.table_name = PRODUCTS_TABLE
        
        self._initialize_db()
    
    def _initialize_db(self) -> None:
        """Initialize LanceDB connection and open table if exists."""
        try:
            # Create directory if it doesn't exist
            db_dir = Path(self.db_path)
            db_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"🔌 Connecting to LanceDB: {self.db_path}")
            self.db = lancedb.connect(self.db_path)
            
            # Check if table exists
            existing_tables = self.db.table_names()
            if self.table_name in existing_tables:
                self.table = self.db.open_table(self.table_name)
                count = len(self.table)
                logger.info(f"✅ Opened existing table: {self.table_name} ({count} products)")
            else:
                logger.warning(f"⚠️ Table '{self.table_name}' not found. Run ingestion script first.")
                self.table = None
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize LanceDB: {e}")
            raise
    
    def ingest_from_supabase(self) -> int:
        """
        Fetch products from Supabase, generate embeddings, store in LanceDB.
        
        This method:
        1. Fetches all products from Supabase
        2. Generates embeddings for each product (name + description + category)
        3. Stores products with embeddings in LanceDB
        4. Creates full-text search index
        
        Returns:
            int: Number of products ingested
            
        Raises:
            RuntimeError: If ingestion fails
        """
        try:
            # Import here to avoid circular imports
            from backend.database.supabase_client import get_supabase_client
            
            # Fetch all products from Supabase
            logger.info("📥 Fetching products from Supabase...")
            supabase = get_supabase_client()
            result = supabase.table('products').select('*').execute()
            products = result.data
            
            if not products:
                logger.warning("⚠️ No products found in Supabase")
                return 0
            
            logger.info(f"✅ Fetched {len(products)} products from Supabase")
            
            # Generate embeddings for all products
            logger.info("🧠 Generating embeddings...")
            texts = []
            for p in products:
                text_parts = [
                    p.get('name', ''),
                    p.get('description', ''),
                    p.get('category', '')
                ]
                combined_text = ' '.join(filter(None, text_parts))
                texts.append(combined_text)
            
            embeddings = generate_embeddings_batch(texts, show_progress=True)
            
            # Prepare data for LanceDB
            logger.info("📦 Preparing data for LanceDB...")
            lance_data = []
            for product, embedding in zip(products, embeddings):
                lance_data.append({
                    "id": product['id'],
                    "name": product.get('name', ''),
                    "description": product.get('description', ''),
                    "price": float(product.get('price', 0)),
                    "category": product.get('category', ''),
                    "image_url": product.get('image_url', ''),
                    "stock": product.get('stock', 0),
                    "vector": embedding
                })
            
            # Create or overwrite table
            logger.info(f"💾 Storing {len(lance_data)} products in LanceDB...")
            
            # Drop existing table if it exists
            if self.table_name in self.db.table_names():
                self.db.drop_table(self.table_name)
                logger.info(f"🗑️ Dropped existing table: {self.table_name}")
            
            # Create new table with data
            self.table = self.db.create_table(
                self.table_name,
                data=lance_data,
            )
            
            # Create full-text search index
            logger.info("🔍 Creating full-text search index...")
            try:
                self.table.create_fts_index(
                    ["name", "description", "category"],
                    replace=True
                )
                logger.info("✅ FTS index created successfully")
            except Exception as fts_error:
                logger.warning(f"⚠️ FTS index creation failed (optional): {fts_error}")
            
            logger.info(f"✅ Ingestion complete: {len(lance_data)} products indexed")
            return len(lance_data)
            
        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}")
            raise RuntimeError(f"Product ingestion failed: {e}")
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        category: Optional[str] = None,
        in_stock_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: Vector similarity + optional filters.
        
        Args:
            query: Search query (natural language)
            top_k: Number of results to return (default: 5)
            min_price: Minimum price filter (optional)
            max_price: Maximum price filter (optional)
            category: Category filter (optional, case-insensitive)
            in_stock_only: Only return products in stock
            
        Returns:
            List[Dict]: Top-k products with similarity scores
        """
        if not self.table:
            logger.error("❌ Table not initialized. Run ingestion first.")
            return []
        
        if not query or not query.strip():
            logger.warning("⚠️ Empty search query")
            return []
        
        try:
            # Generate query embedding
            query_embedding = generate_embedding(query)
            
            # Start vector search
            search_builder = self.table.search(query_embedding)
            
            # Build filter conditions
            filters = []
            
            if min_price is not None:
                filters.append(f"price >= {min_price}")
            
            if max_price is not None:
                filters.append(f"price <= {max_price}")
            
            if category:
                filters.append(f"category = '{category}'")
            
            if in_stock_only:
                filters.append("stock > 0")
            
            # Apply filters
            if filters:
                filter_str = " AND ".join(filters)
                search_builder = search_builder.where(filter_str)
            
            # Execute search
            results = search_builder.limit(top_k).to_list()
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.get('id'),
                    "name": result.get('name', ''),
                    "description": result.get('description', ''),
                    "price": result.get('price', 0),
                    "category": result.get('category', ''),
                    "image_url": result.get('image_url', ''),
                    "stock": result.get('stock', 0),
                    "score": 1.0 - result.get('_distance', 0.0)
                })
            
            logger.info(f"🔍 Search '{query[:50]}' returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def search_by_category(
        self,
        category: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get products by category.
        
        Args:
            category: Category name
            top_k: Maximum products to return
            
        Returns:
            List[Dict]: Products in the category
        """
        if not self.table:
            return []
        
        try:
            results = self.table.search().where(
                f"category = '{category}'"
            ).limit(top_k).to_list()
            
            return [
                {
                    "id": r.get('id'),
                    "name": r.get('name', ''),
                    "description": r.get('description', ''),
                    "price": r.get('price', 0),
                    "category": r.get('category', ''),
                    "image_url": r.get('image_url', ''),
                    "stock": r.get('stock', 0),
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"❌ Category search failed: {e}")
            return []
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single product by ID.
        
        Args:
            product_id: Product ID
            
        Returns:
            Product dict or None if not found
        """
        if not self.table:
            return None
        
        try:
            results = self.table.search().where(
                f"id = {product_id}"
            ).limit(1).to_list()
            
            if results:
                r = results[0]
                return {
                    "id": r.get('id'),
                    "name": r.get('name', ''),
                    "description": r.get('description', ''),
                    "price": r.get('price', 0),
                    "category": r.get('category', ''),
                    "image_url": r.get('image_url', ''),
                    "stock": r.get('stock', 0),
                }
            return None
        except Exception as e:
            logger.error(f"❌ Get product by ID failed: {e}")
            return None
    
    def get_similar_products(
        self,
        product_id: int,
        top_k: int = 5,
        exclude_same: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find products similar to a given product.
        
        Args:
            product_id: Reference product ID
            top_k: Number of similar products to return
            exclude_same: Exclude the reference product from results
            
        Returns:
            List of similar products
        """
        if not self.table:
            return []
        
        try:
            # Get the product's embedding
            results = self.table.search().where(
                f"id = {product_id}"
            ).limit(1).to_list()
            
            if not results:
                logger.warning(f"⚠️ Product {product_id} not found")
                return []
            
            product_embedding = results[0].get('vector')
            if not product_embedding:
                return []
            
            # Search for similar products
            limit = top_k + 1 if exclude_same else top_k
            similar = self.table.search(product_embedding).limit(limit).to_list()
            
            # Format and filter results
            formatted = []
            for r in similar:
                if exclude_same and r.get('id') == product_id:
                    continue
                formatted.append({
                    "id": r.get('id'),
                    "name": r.get('name', ''),
                    "description": r.get('description', ''),
                    "price": r.get('price', 0),
                    "category": r.get('category', ''),
                    "image_url": r.get('image_url', ''),
                    "stock": r.get('stock', 0),
                    "score": 1.0 - r.get('_distance', 0.0)
                })
                if len(formatted) >= top_k:
                    break
            
            return formatted
            
        except Exception as e:
            logger.error(f"❌ Similar products search failed: {e}")
            return []
    
    def get_product_count(self) -> int:
        """
        Get total number of indexed products.
        
        Returns:
            int: Number of products in the index
        """
        if not self.table:
            return 0
        try:
            return len(self.table)
        except Exception:
            return 0
    
    def get_categories(self) -> List[str]:
        """
        Get list of all product categories.
        
        Returns:
            List[str]: Unique category names
        """
        if not self.table:
            return []
        
        try:
            results = self.table.to_pandas()
            categories = results['category'].unique().tolist()
            return sorted([c for c in categories if c])
        except Exception as e:
            logger.error(f"❌ Failed to get categories: {e}")
            return []
    
    def health_check(self) -> bool:
        """
        Check if search engine is healthy.
        
        Returns:
            bool: True if healthy
        """
        try:
            if not self.db or not self.table:
                return False
            count = self.get_product_count()
            return count > 0
        except Exception:
            return False


# Singleton instance
_search_engine: Optional[ProductSearchEngine] = None


def get_search_engine() -> ProductSearchEngine:
    """
    Get or create search engine singleton.
    
    Returns:
        ProductSearchEngine: Search engine instance
    """
    global _search_engine
    if _search_engine is None:
        _search_engine = ProductSearchEngine()
    return _search_engine


def reset_search_engine() -> None:
    """Reset the search engine singleton (useful for testing)."""
    global _search_engine
    _search_engine = None
