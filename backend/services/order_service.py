"""
Order Service - Core order management.

Features:
- Idempotency protection (prevents duplicate orders)
- Atomic stock deduction with rollback
- Order history and tracking
"""

from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from backend.database.supabase_client import get_async_supabase_client
from backend.services.product_service import get_product_service
from backend.services.cart_manager import get_cart_manager
from backend.utils.id_generator import generate_order_id


class OrderService:
    """Order management with idempotency and atomic stock updates."""

    async def create_order(
        self,
        user_phone: str,
        user_name: str,
        delivery_address: str,
        cart_items: List[Dict]
    ) -> Dict:
        """
        Create order with full validation.
        
        Args:
            user_phone: User's phone number
            user_name: Customer name
            delivery_address: Delivery address
            cart_items: Cart items with product details
            
        Returns:
            Dict with keys: success, order (if success), message
        """
        try:
            # Generate idempotency key (minute precision)
            timestamp_key = datetime.utcnow().strftime("%Y%m%d%H%M")
            idempotency_key = f"{user_phone}:{timestamp_key}"
            
            client = await get_async_supabase_client()
            
            # Check idempotency - prevent duplicate orders
            existing_result = await client.table('orders')\
                .select('*')\
                .eq('idempotency_key', idempotency_key)\
                .execute()
            
            existing_data = existing_result.data[0] if existing_result.data else None
            
            if existing_data:
                # Check if previous order failed
                if existing_data.get('status') == 'failed':
                    logger.warning(f"⚠️ Previous attempt failed, allowing retry")
                    # Continue to create new order
                else:
                    logger.info(f"✅ Idempotent return: {existing_data['order_id']}")
                    return {
                        "success": True,
                        "order": existing_data,
                        "message": "Order already created"
                    }
            
            # Validate cart
            if not cart_items:
                return {"success": False, "message": "❌ Cart is empty"}
            
            # Calculate total
            total_amount = sum(item['subtotal'] for item in cart_items)
            
            # Check stock for ALL items first
            product_service = get_product_service()
            for item in cart_items:
                has_stock = await product_service.check_stock(
                    item['product_id'],
                    item['quantity']
                )
                if not has_stock:
                    return {
                        "success": False,
                        "message": f"❌ Insufficient stock: {item['product']['name']}"
                    }
            
            # Generate order ID
            order_id = generate_order_id()
            
            # Create order record
            order_data = {
                "order_id": order_id,
                "user_phone": user_phone,
                "user_name": user_name,
                "delivery_address": delivery_address,
                "total_amount": float(total_amount),
                "status": "pending",
                "idempotency_key": idempotency_key
            }
            
            order_result = await client.table('orders').insert(order_data).execute()
            
            if not order_result.data:
                return {"success": False, "message": "❌ Failed to create order"}
            
            # ✅ CRITICAL FIX: Extract first item from list
            order = (
                order_result.data[0] if isinstance(order_result.data, list) 
                else order_result.data
            )
            
            # Create order items
            order_items = []
            for item in cart_items:
                order_items.append({
                    "order_id": order_id,
                    "product_id": item['product_id'],
                    "product_name": item['product']['name'],
                    "quantity": item['quantity'],
                    "price": float(item['product']['price']),
                    "subtotal": float(item['subtotal'])
                })
            
            items_result = await client.table('order_items').insert(order_items).execute()
            
            # Validate order items created
            if not items_result.data:
                await client.table('orders')\
                    .update({'status': 'failed'})\
                    .eq('order_id', order_id)\
                    .execute()
                return {"success": False, "message": "❌ Failed to create order items"}
            
            # Deduct stock atomically with rollback support
            deducted_items = []
            for item in cart_items:
                success = await product_service.update_stock(
                    item['product_id'],
                    -item['quantity']  # Negative = deduct
                )
                
                if success:
                    deducted_items.append(item)
                else:
                    # ROLLBACK: Restore stock for all deducted items
                    logger.error(f"❌ Stock deduction failed: {item['product_id']}")
                    for deducted in deducted_items:
                        await product_service.update_stock(
                            deducted['product_id'],
                            deducted['quantity']  # Positive = restore
                        )
                    
                    # Mark order as failed
                    await client.table('orders')\
                        .update({'status': 'failed'})\
                        .eq('order_id', order_id)\
                        .execute()
                    
                    return {
                        "success": False,
                        "message": f"❌ Stock deduction failed for {item['product']['name']}"
                    }
            
            # Clear cart after successful order
            cart_manager = get_cart_manager()
            await cart_manager.clear_cart(user_phone)
            
            logger.info(f"✅ Order created: {order_id} for {user_phone}")
            
            return {
                "success": True,
                "order": order,
                "order_items": items_result.data,
                "message": f"Order placed! ID: {order_id}"
            }
            
        except Exception as e:
            logger.error(f"❌ Order creation failed: {e}")
            return {
                "success": False,
                "message": f"❌ Order failed: {str(e)}"
            }

    async def get_order_by_id(self, order_id: str) -> Optional[Dict]:
        """
        Get order with items.
        
        Args:
            order_id: Order ID (e.g., ORD-20251205-A3F9B2)
            
        Returns:
            Order dict with items, or None
        """
        try:
            client = await get_async_supabase_client()
            
            # Get order
            order_result = await client.table('orders')\
                .select('*')\
                .eq('order_id', order_id)\
                .maybe_single()\
                .execute()
            
            if not order_result.data:
                return None
            
            order = order_result.data
            
            # Get order items
            items_result = await client.table('order_items')\
                .select('*')\
                .eq('order_id', order_id)\
                .execute()
            
            order['items'] = items_result.data
            
            return order
            
        except Exception as e:
            logger.error(f"❌ Get order failed: {e}")
            return None

    async def get_user_orders(self, user_phone: str, limit: int = 10) -> List[Dict]:
        """
        Get user's order history.
        
        Args:
            user_phone: User's phone number
            limit: Max orders to return
            
        Returns:
            List of orders (most recent first)
        """
        try:
            client = await get_async_supabase_client()
            
            result = await client.table('orders')\
                .select('*')\
                .eq('user_phone', user_phone)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"❌ Get orders failed: {e}")
            return []

    async def update_order_status(self, order_id: str, new_status: str) -> bool:
        """
        Update order status.
        
        Args:
            order_id: Order ID
            new_status: New status (pending, confirmed, shipped, delivered, cancelled)
            
        Returns:
            bool: Success status
        """
        try:
            client = await get_async_supabase_client()
            
            await client.table('orders')\
                .update({'status': new_status})\
                .eq('order_id', order_id)\
                .execute()
            
            logger.info(f"✅ Order {order_id} → {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Status update failed: {e}")
            return False

    async def cancel_order(self, order_id: str) -> Dict:
        """
        Cancel order and restore stock.
        
        Args:
            order_id: Order ID
            
        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            # Get order with items
            order = await self.get_order_by_id(order_id)
            
            if not order:
                return {"success": False, "message": "Order not found"}
            
            if order['status'] in ['cancelled', 'delivered']:
                return {"success": False, "message": f"Cannot cancel {order['status']} order"}
            
            # Restore stock for each item
            product_service = get_product_service()
            for item in order.get('items', []):
                await product_service.update_stock(
                    item['product_id'],
                    item['quantity']  # Positive = restore
                )
            
            # Update status
            await self.update_order_status(order_id, 'cancelled')
            
            logger.info(f"✅ Order cancelled: {order_id}")
            return {"success": True, "message": "Order cancelled successfully"}
            
        except Exception as e:
            logger.error(f"❌ Cancel order failed: {e}")
            return {"success": False, "message": str(e)}


# Singleton
_order_service: Optional[OrderService] = None


def get_order_service() -> OrderService:
    """Get order service singleton."""
    global _order_service
    if _order_service is None:
        _order_service = OrderService()
    return _order_service
