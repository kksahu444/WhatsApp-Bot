"""
Supabase client singleton module.

Provides both sync and async Supabase clients for database operations.
Uses the Supabase Python SDK with connection pooling and health checks.

IMPORTANT: Use `await get_async_supabase_client()` for async operations.
"""

from typing import Optional

from loguru import logger
from supabase import create_client, Client
from supabase._async.client import AsyncClient, create_client as acreate_client

from backend.config.settings import settings


# Global singleton instances
_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None
_async_supabase_client: Optional[AsyncClient] = None
_async_supabase_admin_client: Optional[AsyncClient] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client singleton using anon key.
    
    This client uses the anon (public) key and respects Row Level Security (RLS).
    Use this for user-facing operations where RLS should be enforced.
    
    Returns:
        Client: Supabase client instance with anon key
        
    Raises:
        Exception: If connection fails
    """
    global _supabase_client
    
    if _supabase_client is None:
        try:
            _supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_key
            )
            logger.info(f"✅ Supabase client initialized: {settings.supabase_url}")
        except Exception as e:
            logger.error(f"❌ Failed to create Supabase client: {e}")
            raise
    
    return _supabase_client


def get_supabase_admin_client() -> Client:
    """
    Get or create Supabase admin client singleton using service_role key.
    
    This client uses the service_role key and bypasses Row Level Security (RLS).
    Use this for admin operations like seeding data or background jobs.
    
    Returns:
        Client: Supabase client instance with service_role key
        
    Raises:
        Exception: If connection fails
    """
    global _supabase_admin_client
    
    if _supabase_admin_client is None:
        try:
            _supabase_admin_client = create_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
            logger.info(f"✅ Supabase admin client initialized: {settings.supabase_url}")
        except Exception as e:
            logger.error(f"❌ Failed to create Supabase admin client: {e}")
            raise
    
    return _supabase_admin_client


async def get_async_supabase_client() -> AsyncClient:
    """
    Get or create async Supabase client singleton using anon key.
    
    This is the PREFERRED client for async FastAPI operations.
    Uses the anon (public) key and respects Row Level Security (RLS).
    
    Returns:
        AsyncClient: Async Supabase client instance
        
    Raises:
        Exception: If connection fails
        
    Usage:
        client = await get_async_supabase_client()
        result = await client.table('products').select('*').execute()
    """
    global _async_supabase_client
    
    if _async_supabase_client is None:
        try:
            _async_supabase_client = await acreate_client(
                settings.supabase_url,
                settings.supabase_key
            )
            logger.info(f"✅ Async Supabase client initialized: {settings.supabase_url}")
        except Exception as e:
            logger.error(f"❌ Failed to create async Supabase client: {e}")
            raise
    
    return _async_supabase_client


async def get_async_supabase_admin_client() -> AsyncClient:
    """
    Get or create async Supabase admin client singleton using service_role key.
    
    This client uses the service_role key and bypasses Row Level Security (RLS).
    Use this for admin operations that need to run async.
    
    Returns:
        AsyncClient: Async Supabase admin client instance
    """
    global _async_supabase_admin_client
    
    if _async_supabase_admin_client is None:
        try:
            _async_supabase_admin_client = await acreate_client(
                settings.supabase_url,
                settings.supabase_service_key
            )
            logger.info(f"✅ Async Supabase admin client initialized: {settings.supabase_url}")
        except Exception as e:
            logger.error(f"❌ Failed to create async Supabase admin client: {e}")
            raise
    
    return _async_supabase_admin_client


def health_check() -> bool:
    """
    Check if Supabase connection is healthy.
    
    Performs a simple query to verify database connectivity.
    
    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        client = get_supabase_client()
        # Simple query to test connection
        result = client.table('products').select('id').limit(1).execute()
        logger.debug("✅ Supabase health check passed")
        return True
    except Exception as e:
        logger.error(f"❌ Supabase health check failed: {e}")
        return False


def close_connection() -> None:
    """
    Close Supabase client connections.
    
    Resets the global singleton instances. Useful for testing
    or when gracefully shutting down the application.
    """
    global _supabase_client, _supabase_admin_client, _async_supabase_client, _async_supabase_admin_client
    
    _supabase_client = None
    _supabase_admin_client = None
    _async_supabase_client = None
    _async_supabase_admin_client = None
    logger.info("🔌 Supabase connections closed")


# Alias for backward compatibility and cleaner imports
get_supabase_client_async = get_async_supabase_client


class SupabaseService:
    """
    Service class providing common database operations.
    
    Wraps the Supabase client with convenience methods for
    common CRUD operations used throughout the application.
    
    Attributes:
        client: Supabase client instance (anon key)
        admin_client: Supabase admin client instance (service_role key)
    """
    
    def __init__(self, use_admin: bool = False) -> None:
        """
        Initialize SupabaseService.
        
        Args:
            use_admin: If True, use service_role key (bypasses RLS).
                      If False, use anon key (respects RLS).
        """
        self.client = get_supabase_admin_client() if use_admin else get_supabase_client()
        self._use_admin = use_admin
    
    async def get_products(
        self,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[dict]:
        """
        Fetch products with optional category filter.
        
        Args:
            category: Filter by category name (optional)
            limit: Maximum number of products to return
            offset: Number of products to skip (for pagination)
            
        Returns:
            List of product dictionaries
        """
        try:
            query = self.client.table('products').select('*')
            
            if category:
                query = query.eq('category', category)
            
            result = query.range(offset, offset + limit - 1).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"❌ Failed to fetch products: {e}")
            return []
    
    async def get_product_by_id(self, product_id: int) -> Optional[dict]:
        """
        Fetch a single product by ID.
        
        Args:
            product_id: The product ID to fetch
            
        Returns:
            Product dictionary or None if not found
        """
        try:
            result = self.client.table('products').select('*').eq('id', product_id).single().execute()
            return result.data
        except Exception as e:
            logger.error(f"❌ Failed to fetch product {product_id}: {e}")
            return None
    
    async def search_products(self, query: str, limit: int = 10) -> list[dict]:
        """
        Search products by name or description.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching product dictionaries
        """
        try:
            # Use ilike for case-insensitive search
            result = self.client.table('products').select('*').or_(
                f"name.ilike.%{query}%,description.ilike.%{query}%"
            ).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"❌ Failed to search products: {e}")
            return []
    
    async def get_cart(self, user_phone: str) -> list[dict]:
        """
        Get cart items for a user.
        
        Args:
            user_phone: User's phone number
            
        Returns:
            List of cart item dictionaries with product details
        """
        try:
            result = self.client.table('carts').select(
                '*, products(*)'
            ).eq('user_phone', user_phone).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"❌ Failed to fetch cart for {user_phone}: {e}")
            return []
    
    async def add_to_cart(
        self,
        user_phone: str,
        product_id: int,
        quantity: int = 1
    ) -> Optional[dict]:
        """
        Add item to cart or update quantity if exists.
        
        Args:
            user_phone: User's phone number
            product_id: Product ID to add
            quantity: Quantity to add
            
        Returns:
            Cart item dictionary or None on failure
        """
        try:
            # Check if item already in cart
            existing = self.client.table('carts').select('*').eq(
                'user_phone', user_phone
            ).eq('product_id', product_id).execute()
            
            if existing.data:
                # Update quantity
                new_qty = existing.data[0]['quantity'] + quantity
                result = self.client.table('carts').update(
                    {'quantity': new_qty}
                ).eq('user_phone', user_phone).eq('product_id', product_id).execute()
            else:
                # Insert new item
                result = self.client.table('carts').insert({
                    'user_phone': user_phone,
                    'product_id': product_id,
                    'quantity': quantity
                }).execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"❌ Failed to add to cart: {e}")
            return None
    
    async def clear_cart(self, user_phone: str) -> bool:
        """
        Clear all items from user's cart.
        
        Args:
            user_phone: User's phone number
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.table('carts').delete().eq('user_phone', user_phone).execute()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to clear cart for {user_phone}: {e}")
            return False
    
    async def create_order(
        self,
        user_phone: str,
        items_json: list[dict],
        total_amount: float,
        user_name: str,
        address: str
    ) -> Optional[dict]:
        """
        Create a new order.
        
        Args:
            user_phone: User's phone number
            items_json: List of order items with product details
            total_amount: Total order amount
            user_name: Customer name
            address: Delivery address
            
        Returns:
            Order dictionary or None on failure
        """
        try:
            result = self.client.table('orders').insert({
                'user_phone': user_phone,
                'items_json': items_json,
                'total_amount': total_amount,
                'status': 'pending',
                'user_name': user_name,
                'address': address
            }).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"❌ Failed to create order: {e}")
            return None
    
    async def save_conversation(
        self,
        user_phone: str,
        role: str,
        message: str
    ) -> Optional[dict]:
        """
        Save a conversation message.
        
        Args:
            user_phone: User's phone number
            role: Message role ('user' or 'assistant')
            message: Message content
            
        Returns:
            Conversation record or None on failure
        """
        try:
            result = self.client.table('conversations').insert({
                'user_phone': user_phone,
                'role': role,
                'message': message
            }).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"❌ Failed to save conversation: {e}")
            return None
    
    async def get_conversation_history(
        self,
        user_phone: str,
        limit: int = 20
    ) -> list[dict]:
        """
        Get recent conversation history for a user.
        
        Args:
            user_phone: User's phone number
            limit: Maximum number of messages to return
            
        Returns:
            List of conversation messages ordered by timestamp
        """
        try:
            result = self.client.table('conversations').select('*').eq(
                'user_phone', user_phone
            ).order('timestamp', desc=True).limit(limit).execute()
            # Return in chronological order
            return list(reversed(result.data or []))
        except Exception as e:
            logger.error(f"❌ Failed to fetch conversation history: {e}")
            return []


# Convenience export - creates client on import
# supabase = get_supabase_client()

