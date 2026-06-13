"""
Async Product Service for WhatsApp AI Seller Bot.
All methods are async and use await for database calls.
"""

from typing import List, Dict, Optional
from loguru import logger

from backend.database.supabase_client import get_async_supabase_client, get_async_supabase_admin_client


class ProductService:
    """Async service for product operations."""

    async def get_all_products(
        self,
        limit: int = 50,
        offset: int = 0,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> List[Dict]:
        """
        Fetch products with filters (async).
        
        Args:
            limit: Max products to return
            offset: Pagination offset
            category: Filter by category
            min_price: Minimum price
            max_price: Maximum price
            
        Returns:
            List[Dict]: Products
        """
        try:
            client = await get_async_supabase_client()
            query = client.table('products').select('*')
            
            # Apply filters
            if category:
                query = query.eq('category', category)
            if min_price is not None:
                query = query.gte('price', min_price)
            if max_price is not None:
                query = query.lte('price', max_price)
            
            # Only in-stock products
            query = query.gt('stock', 0)
            
            # Pagination
            query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
            
            result = await query.execute()
            logger.info(f"✅ Fetched {len(result.data)} products")
            return result.data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch products: {e}")
            return []

    async def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Get single product by ID (async)."""
        try:
            client = await get_async_supabase_client()
            result = await client.table('products')\
                .select('*')\
                .eq('id', product_id)\
                .maybe_single()\
                .execute()
            
            if result.data:
                logger.debug(f"✅ Fetched product: {result.data.get('name')}")
            return result.data
            
        except Exception as e:
            logger.warning(f"⚠️ Product {product_id} not found: {e}")
            return None

    async def get_products_by_ids(self, product_ids: List[int]) -> List[Dict]:
        """Get multiple products by IDs (for cart)."""
        if not product_ids:
            return []
            
        try:
            client = await get_async_supabase_client()
            result = await client.table('products')\
                .select('*')\
                .in_('id', product_ids)\
                .execute()
            
            logger.debug(f"✅ Fetched {len(result.data)} products by IDs")
            return result.data
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch products by IDs: {e}")
            return []

    async def search_products(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search products by text (async).
        Uses PostgreSQL ILIKE for case-insensitive search.
        """
        try:
            client = await get_async_supabase_client()
            result = await client.table('products')\
                .select('*')\
                .or_(f"name.ilike.%{query}%,description.ilike.%{query}%")\
                .gt('stock', 0)\
                .limit(limit)\
                .execute()
            
            logger.info(f"🔍 Search '{query}' returned {len(result.data)} results")
            return result.data
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []

    async def check_stock(self, product_id: int, required_quantity: int = 1) -> bool:
        """
        Check if product has sufficient stock.
        
        Args:
            product_id: Product ID
            required_quantity: Required quantity
            
        Returns:
            bool: True if stock available
        """
        try:
            client = await get_async_supabase_client()
            result = await client.table('products')\
                .select('stock')\
                .eq('id', product_id)\
                .execute()
            
            product_data = result.data[0] if result.data else None
            
            if not product_data:
                logger.warning(f"⚠️ Product {product_id} not found")
                return False
            
            current_stock = product_data.get('stock', 0)
            has_stock = current_stock >= required_quantity
            
            if not has_stock:
                logger.warning(
                    f"⚠️ Insufficient stock: product {product_id}, "
                    f"need {required_quantity}, have {current_stock}"
                )
            
            return has_stock
            
        except Exception as e:
            logger.error(f"❌ Stock check failed: {e}")
            return False

    async def update_stock(self, product_id: int, quantity_change: int) -> bool:
        """
        Update stock atomically via PostgreSQL function.
        
        Args:
            product_id: Product ID
            quantity_change: Change amount (negative = deduct, positive = restock)
            
        Returns:
            bool: Success status
        """
        try:
            client = await get_async_supabase_client()
            result = await client.rpc('update_stock_atomic', {
                'p_product_id': product_id,
                'p_quantity_change': quantity_change
            }).execute()
            
            if result.data is not None:
                logger.info(
                    f"✅ Stock updated: product {product_id}, "
                    f"change: {quantity_change:+d}, new stock: {result.data}"
                )
                return True
            return False
            
        except Exception as e:
            logger.error(f"❌ Stock update failed: {e}")
            return False

    async def get_categories(self) -> List[str]:
        """Get all unique product categories."""
        try:
            client = await get_async_supabase_client()
            result = await client.table('products')\
                .select('category')\
                .execute()
            
            categories = list(set(item['category'] for item in result.data if item.get('category')))
            logger.debug(f"✅ Fetched {len(categories)} categories")
            return sorted(categories)
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch categories: {e}")
            return []

    async def get_products_by_category(self, category: str, limit: int = 20) -> List[Dict]:
        """Get products in a specific category."""
        return await self.get_all_products(limit=limit, category=category)


# Singleton
_product_service: Optional[ProductService] = None


def get_product_service() -> ProductService:
    """Get or create product service singleton."""
    global _product_service
    if _product_service is None:
        _product_service = ProductService()
    return _product_service
