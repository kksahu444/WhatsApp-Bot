"""
Async Cart Manager for WhatsApp AI Seller Bot.
All methods are async and use await for database calls.
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone
from loguru import logger

from backend.database.supabase_client import get_async_supabase_client
from backend.services.product_service import get_product_service


class CartManager:
    """Async service for cart operations."""

    def __init__(self):
        self.product_service = get_product_service()

    async def add_to_cart(
        self,
        user_phone: str,
        product_id: int,
        quantity: int = 1
    ) -> Dict:
        """
        Add product to cart (async). Upserts if exists.
        
        Returns:
            Dict: {"success": bool, "message": str, "data": Optional[dict]}
        """
        try:
            # Check stock
            if not await self.product_service.check_stock(product_id, quantity):
                return {
                    "success": False,
                    "message": "Product out of stock",
                    "data": None
                }
            
            client = await get_async_supabase_client()
            
            # Check if item exists using .maybe_single() for cleaner code
            existing_result = await client.table('carts')\
                .select('*')\
                .eq('user_phone', user_phone)\
                .eq('product_id', product_id)\
                .maybe_single()\
                .execute()
            
            if existing_result and existing_result.data:
                # Update quantity
                new_quantity = existing_result.data['quantity'] + quantity
                result = await client.table('carts')\
                    .update({
                        'quantity': new_quantity,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    })\
                    .eq('user_phone', user_phone)\
                    .eq('product_id', product_id)\
                    .execute()
                
                logger.info(f"✅ Updated cart: {user_phone} - product {product_id} qty: {new_quantity}")
                return {
                    "success": True,
                    "message": f"Updated quantity to {new_quantity}",
                    "data": result.data[0] if result.data else None
                }
            else:
                # Insert new item
                cart_item = {
                    "user_phone": user_phone,
                    "product_id": product_id,
                    "quantity": quantity
                }
                result = await client.table('carts').insert(cart_item).execute()
                
                logger.info(f"✅ Added to cart: {user_phone} - product {product_id}")
                return {
                    "success": True,
                    "message": "Added to cart",
                    "data": result.data[0] if result.data else None
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to add to cart: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }

    async def update_quantity(
        self,
        user_phone: str,
        product_id: int,
        quantity: int
    ) -> Dict:
        """
        Update cart item quantity (async).
        
        Args:
            user_phone: User phone number
            product_id: Product ID
            quantity: New quantity (if 0, removes item)
            
        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            if quantity <= 0:
                return await self.remove_from_cart(user_phone, product_id)
            
            # Check stock
            if not await self.product_service.check_stock(product_id, quantity):
                return {
                    "success": False,
                    "message": "Insufficient stock",
                    "data": None
                }
            
            client = await get_async_supabase_client()
            await client.table('carts')\
                .update({
                    'quantity': quantity,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })\
                .eq('user_phone', user_phone)\
                .eq('product_id', product_id)\
                .execute()
            
            logger.info(f"✅ Updated quantity: {user_phone} - product {product_id} → {quantity}")
            return {
                "success": True,
                "message": f"Quantity updated to {quantity}",
                "data": {"quantity": quantity}
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to update quantity: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }

    async def remove_from_cart(self, user_phone: str, product_id: int) -> Dict:
        """
        Remove product from cart (async).
        
        Returns:
            Dict: {"success": bool, "message": str, "data": None}
        """
        try:
            client = await get_async_supabase_client()
            await client.table('carts')\
                .delete()\
                .eq('user_phone', user_phone)\
                .eq('product_id', product_id)\
                .execute()
            
            logger.info(f"✅ Removed from cart: {user_phone} - product {product_id}")
            return {
                "success": True,
                "message": "Item removed from cart",
                "data": None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to remove from cart: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }

    async def get_cart(self, user_phone: str) -> List[Dict]:
        """
        Get user's cart with product details (async).
        
        Returns:
            List[Dict]: Cart items with product info and subtotals
        """
        try:
            client = await get_async_supabase_client()
            
            # Get cart items
            cart_result = await client.table('carts')\
                .select('*')\
                .eq('user_phone', user_phone)\
                .execute()
            
            if not cart_result.data:
                return []
            
            # Get product IDs
            product_ids = [item['product_id'] for item in cart_result.data]
            
            # Fetch product details
            products = await self.product_service.get_products_by_ids(product_ids)
            products_map = {p['id']: p for p in products}
            
            # Merge cart + products
            cart_with_details = []
            for item in cart_result.data:
                product = products_map.get(item['product_id'])
                if product:
                    cart_with_details.append({
                        **item,
                        "product": product,
                        "subtotal": float(product['price']) * item['quantity']
                    })
            
            logger.debug(f"✅ Fetched cart for {user_phone}: {len(cart_with_details)} items")
            return cart_with_details
            
        except Exception as e:
            logger.error(f"❌ Failed to get cart: {e}")
            return []

    async def get_cart_item(self, user_phone: str, product_id: int) -> Optional[Dict]:
        """Get single cart item with product details."""
        try:
            client = await get_async_supabase_client()
            result = await client.table('carts')\
                .select('*')\
                .eq('user_phone', user_phone)\
                .eq('product_id', product_id)\
                .execute()
            
            if not result.data:
                return None
            
            item_data = result.data[0]
            
            # Get product details
            product = await self.product_service.get_product_by_id(product_id)
            if product:
                return {
                    **item_data,
                    "product": product,
                    "subtotal": float(product['price']) * item_data['quantity']
                }
            return item_data
            
        except Exception as e:
            logger.error(f"❌ Failed to get cart item: {e}")
            return None

    async def calculate_total(self, user_phone: str) -> float:
        """Calculate cart total (async)."""
        cart = await self.get_cart(user_phone)
        total = sum(item['subtotal'] for item in cart)
        return float(total)

    async def clear_cart(self, user_phone: str) -> Dict:
        """
        Clear entire cart (async).
        
        Returns:
            Dict: {"success": bool, "message": str, "data": None}
        """
        try:
            client = await get_async_supabase_client()
            await client.table('carts')\
                .delete()\
                .eq('user_phone', user_phone)\
                .execute()
            
            logger.info(f"✅ Cleared cart for {user_phone}")
            return {
                "success": True,
                "message": "Cart cleared successfully",
                "data": None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to clear cart: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }

    async def get_cart_count(self, user_phone: str) -> int:
        """Get total item count in cart."""
        cart = await self.get_cart(user_phone)
        return sum(item['quantity'] for item in cart)

    async def get_cart_summary(self, user_phone: str) -> Dict:
        """
        Get cart summary with total and item count.
        
        Returns:
            Dict: {"items": List, "total": float, "item_count": int}
        """
        cart = await self.get_cart(user_phone)
        total = sum(item['subtotal'] for item in cart)
        item_count = sum(item['quantity'] for item in cart)
        
        return {
            "items": cart,
            "total": float(total),
            "item_count": item_count
        }


# Singleton
_cart_manager: Optional[CartManager] = None


def get_cart_manager() -> CartManager:
    """Get or create cart manager singleton."""
    global _cart_manager
    if _cart_manager is None:
        _cart_manager = CartManager()
    return _cart_manager
