"""
Order Manager
Order processing with idempotency support
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from models.order import Order, OrderCreate, OrderItem, OrderStatus, OrderSummary
from utils.security import hash_phone_number
from .idempotency import IdempotencyService

logger = logging.getLogger(__name__)


class OrderManager:
    """Manage order operations with idempotency."""
    
    def __init__(self, supabase_client, redis_client=None):
        self.db = supabase_client
        self.redis = redis_client
        self.idempotency = IdempotencyService(redis_client) if redis_client else None
    
    def _generate_order_number(self) -> str:
        """Generate human-readable order number."""
        import random
        import string
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ORD-{timestamp}-{random_part}"
    
    async def create_order(
        self,
        order_data: OrderCreate,
        phone_number: str,
        idempotency_key: Optional[str] = None
    ) -> Order:
        """
        Create a new order from cart.
        
        Args:
            order_data: Order creation data
            phone_number: User's phone number
            idempotency_key: Key for idempotent operation
        
        Returns:
            Created order
        """
        phone_hash = hash_phone_number(phone_number)
        
        # Check idempotency
        if self.idempotency and idempotency_key:
            existing = await self.idempotency.check_and_get(idempotency_key)
            if existing:
                logger.info(f"Returning cached order for key: {idempotency_key}")
                return Order(**existing)
        
        # Get cart
        cart_data = await self.db.get_cart(phone_hash)
        if not cart_data or not cart_data.get("cart_items"):
            raise ValueError("Cart is empty")
        
        # Build order items
        items = []
        subtotal = 0.0
        
        for cart_item in cart_data["cart_items"]:
            product = cart_item["products"]
            quantity = cart_item["quantity"]
            unit_price = float(product["price"])
            item_subtotal = unit_price * quantity
            
            items.append({
                "product_id": cart_item["product_id"],
                "product_name": product["name"],
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": item_subtotal
            })
            subtotal += item_subtotal
        
        # Calculate totals
        shipping_fee = self._calculate_shipping(subtotal)
        tax = self._calculate_tax(subtotal)
        total = subtotal + shipping_fee + tax
        
        # Create order
        order_number = self._generate_order_number()
        order_record = {
            "order_number": order_number,
            "user_phone_hash": phone_hash,
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "tax": tax,
            "total": round(total, 2),
            "status": OrderStatus.PENDING.value,
            "payment_method": order_data.payment_method.value,
            "shipping_address": order_data.shipping_address.dict(),
            "notes": order_data.notes,
            "idempotency_key": idempotency_key
        }
        
        # Save to database
        created_order = await self.db.create_order(order_record)
        
        # Save order items
        for item in items:
            item["order_id"] = created_order["id"]
            await self.db.client.table("order_items").insert(item).execute()
        
        # Clear cart
        await self.db.clear_cart(cart_data["id"])
        
        # Build response
        order = Order(
            id=created_order["id"],
            order_number=order_number,
            user_phone=phone_hash,
            items=[OrderItem(**item) for item in items],
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            tax=tax,
            total=round(total, 2),
            status=OrderStatus.PENDING,
            payment_status=order_data.payment_method.value,
            payment_method=order_data.payment_method,
            shipping_address=order_data.shipping_address,
            created_at=created_order["created_at"],
            updated_at=created_order["updated_at"],
            notes=order_data.notes
        )
        
        # Cache for idempotency
        if self.idempotency and idempotency_key:
            await self.idempotency.store_result(idempotency_key, order.dict())
        
        logger.info(f"Created order: {order_number}")
        return order
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        order_data = await self.db.get_order(order_id)
        if not order_data:
            return None
        return self._build_order(order_data)
    
    async def get_order_by_number(
        self,
        order_number: str,
        phone_number: str
    ) -> Optional[Order]:
        """Get order by order number for a specific user."""
        phone_hash = hash_phone_number(phone_number)
        
        response = self.db.client.table("orders").select(
            "*, order_items(*)"
        ).eq("order_number", order_number).eq(
            "user_phone_hash", phone_hash
        ).single().execute()
        
        if not response.data:
            return None
        
        return self._build_order(response.data)
    
    async def get_user_orders(
        self,
        phone_number: str,
        limit: int = 10
    ) -> List[OrderSummary]:
        """Get user's order history."""
        phone_hash = hash_phone_number(phone_number)
        orders = await self.db.get_orders_by_user(phone_hash, limit)
        
        return [
            OrderSummary(
                id=o["id"],
                order_number=o["order_number"],
                status=OrderStatus(o["status"]),
                total=o["total"],
                currency=o.get("currency", "INR"),
                item_count=len(o.get("order_items", [])),
                created_at=o["created_at"]
            )
            for o in orders
        ]
    
    async def update_status(
        self,
        order_id: str,
        status: OrderStatus,
        notes: Optional[str] = None,
        tracking_number: Optional[str] = None
    ) -> Optional[Order]:
        """Update order status."""
        update_data = {"status": status.value}
        
        if notes:
            update_data["admin_notes"] = notes
        if tracking_number:
            update_data["tracking_number"] = tracking_number
        
        # Set timestamp based on status
        if status == OrderStatus.CONFIRMED:
            update_data["confirmed_at"] = datetime.utcnow().isoformat()
        elif status == OrderStatus.SHIPPED:
            update_data["shipped_at"] = datetime.utcnow().isoformat()
        elif status == OrderStatus.DELIVERED:
            update_data["delivered_at"] = datetime.utcnow().isoformat()
        
        await self.db.client.table("orders").update(update_data).eq(
            "id", order_id
        ).execute()
        
        return await self.get_order(order_id)
    
    def _calculate_shipping(self, subtotal: float) -> float:
        """Calculate shipping fee."""
        if subtotal >= 500:  # Free shipping over ₹500
            return 0.0
        return 50.0
    
    def _calculate_tax(self, subtotal: float) -> float:
        """Calculate tax (GST)."""
        # Simplified - 18% GST
        return round(subtotal * 0.18, 2)
    
    def _build_order(self, order_data: Dict[str, Any]) -> Order:
        """Build Order object from database data."""
        items = [
            OrderItem(
                product_id=item["product_id"],
                product_name=item["product_name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                subtotal=item["subtotal"]
            )
            for item in order_data.get("order_items", [])
        ]
        
        from models.order import Address, PaymentMethod
        
        return Order(
            id=order_data["id"],
            order_number=order_data["order_number"],
            user_phone=order_data["user_phone_hash"],
            items=items,
            subtotal=order_data["subtotal"],
            shipping_fee=order_data.get("shipping_fee", 0),
            tax=order_data.get("tax", 0),
            total=order_data["total"],
            currency=order_data.get("currency", "INR"),
            status=OrderStatus(order_data["status"]),
            payment_status=order_data.get("payment_status", "pending"),
            payment_method=PaymentMethod(order_data["payment_method"]),
            shipping_address=Address(**order_data["shipping_address"]),
            created_at=order_data["created_at"],
            updated_at=order_data["updated_at"],
            confirmed_at=order_data.get("confirmed_at"),
            shipped_at=order_data.get("shipped_at"),
            delivered_at=order_data.get("delivered_at"),
            notes=order_data.get("notes"),
            admin_notes=order_data.get("admin_notes"),
            tracking_number=order_data.get("tracking_number"),
            tracking_url=order_data.get("tracking_url")
        )
