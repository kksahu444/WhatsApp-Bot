"""
Order Tracking Handler for WhatsApp Bot.

Handles user queries about order status and delivery estimates.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Optional
from loguru import logger

from backend.database.supabase_client import get_async_supabase_client


# Order status display mapping
STATUS_DISPLAY = {
    "PENDING": "⏳ Pending Payment",
    "PENDING_PAYMENT": "⏳ Pending Payment",
    "VERIFICATION_PENDING": "🔍 Payment Verification",
    "PAYMENT_VERIFIED": "✅ Payment Verified",
    "CONFIRMED": "✅ Order Confirmed",
    "PROCESSING": "📦 Processing",
    "SHIPPED": "🚚 Shipped",
    "OUT_FOR_DELIVERY": "🛵 Out for Delivery",
    "DELIVERED": "✅ Delivered",
    "CANCELLED": "❌ Cancelled",
    "REFUNDED": "💰 Refunded",
}

# Delivery estimates by status (days from order)
DELIVERY_ESTIMATES = {
    "PENDING": (3, 7),
    "PENDING_PAYMENT": (3, 7),
    "VERIFICATION_PENDING": (3, 7),
    "PAYMENT_VERIFIED": (3, 6),
    "CONFIRMED": (3, 5),
    "PROCESSING": (2, 4),
    "SHIPPED": (1, 3),
    "OUT_FOR_DELIVERY": (0, 1),
    "DELIVERED": None,
    "CANCELLED": None,
    "REFUNDED": None,
}


def extract_order_id(message: str) -> Optional[str]:
    """
    Extract order ID from message.
    
    Formats supported:
    - ORD-20251205-ABC123
    - #ORD-20251205-ABC123
    - order ORD-20251205-ABC123
    
    Args:
        message: User's message text
        
    Returns:
        Order ID or None
    """
    # Pattern: ORD-YYYYMMDD-XXXXXX
    pattern = r'(ORD-\d{8}-[A-F0-9]{6})'
    match = re.search(pattern, message.upper())
    
    if match:
        return match.group(1)
    
    return None


async def get_order_by_id(order_id: str) -> Optional[Dict]:
    """
    Get order by ID from Supabase.
    
    Args:
        order_id: Order ID
        
    Returns:
        Order dict or None
    """
    try:
        client = await get_async_supabase_client()
        
        result = await client.table('orders')\
            .select('*, order_items(*)')\
            .eq('order_id', order_id)\
            .limit(1)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to get order {order_id}: {e}")
        return None


async def get_latest_order(user_phone: str) -> Optional[Dict]:
    """
    Get user's latest order.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        Order dict or None
    """
    try:
        client = await get_async_supabase_client()
        
        result = await client.table('orders')\
            .select('*, order_items(*)')\
            .eq('user_phone', user_phone)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to get latest order for {user_phone}: {e}")
        return None


async def get_all_orders(user_phone: str, limit: int = 5) -> list:
    """
    Get user's order history.
    
    Args:
        user_phone: User's phone number
        limit: Maximum orders to return
        
    Returns:
        List of orders
    """
    try:
        client = await get_async_supabase_client()
        
        result = await client.table('orders')\
            .select('order_id, status, total_amount, created_at')\
            .eq('user_phone', user_phone)\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data or []
        
    except Exception as e:
        logger.error(f"❌ Failed to get orders for {user_phone}: {e}")
        return []


def format_delivery_estimate(order: Dict) -> str:
    """
    Calculate and format delivery estimate.
    
    Args:
        order: Order dict
        
    Returns:
        Formatted delivery estimate string
    """
    status = order.get('status', 'PENDING').upper()
    
    # No estimate for completed/cancelled orders
    if DELIVERY_ESTIMATES.get(status) is None:
        if status == "DELIVERED":
            return "✅ Already Delivered"
        elif status == "CANCELLED":
            return "❌ Order Cancelled"
        elif status == "REFUNDED":
            return "💰 Refund Processed"
        return "N/A"
    
    # Calculate estimate from order date
    created_at = order.get('created_at', '')
    if created_at:
        try:
            # Parse ISO format
            if 'T' in created_at:
                order_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                order_date = datetime.strptime(created_at[:10], '%Y-%m-%d')
            
            min_days, max_days = DELIVERY_ESTIMATES[status]
            
            est_min = order_date + timedelta(days=min_days)
            est_max = order_date + timedelta(days=max_days)
            
            return f"📅 {est_min.strftime('%b %d')} - {est_max.strftime('%b %d, %Y')}"
            
        except Exception as e:
            logger.warning(f"Failed to parse order date: {e}")
    
    return "📅 3-7 business days"


def format_order_status(order: Dict) -> str:
    """
    Format order details for display.
    
    Args:
        order: Order dict
        
    Returns:
        Formatted order status message
    """
    order_id = order.get('order_id', 'Unknown')
    status = order.get('status', 'PENDING').upper()
    total = order.get('total_amount', 0)
    created_at = order.get('created_at', '')
    
    # Format date
    order_date = "Unknown"
    if created_at:
        try:
            if 'T' in created_at:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(created_at[:10], '%Y-%m-%d')
            order_date = dt.strftime('%b %d, %Y')
        except:
            order_date = created_at[:10]
    
    # Get display status
    status_display = STATUS_DISPLAY.get(status, f"📋 {status}")
    
    # Get delivery estimate
    delivery = format_delivery_estimate(order)
    
    # Format items
    items = order.get('order_items', [])
    items_text = ""
    if items:
        item_lines = []
        for item in items[:3]:  # Show max 3 items
            name = item.get('product_name', 'Item')
            qty = item.get('quantity', 1)
            item_lines.append(f"  • {name} x{qty}")
        items_text = "\n".join(item_lines)
        if len(items) > 3:
            items_text += f"\n  • +{len(items) - 3} more items"
    
    response = (
        f"📦 *Order Status*\n\n"
        f"🎫 Order: `{order_id}`\n"
        f"📊 Status: {status_display}\n"
        f"📅 Ordered: {order_date}\n"
        f"💰 Total: ₹{total:,.0f}\n"
    )
    
    if items_text:
        response += f"\n📋 *Items:*\n{items_text}\n"
    
    response += f"\n🚚 *Est. Delivery:*\n{delivery}"
    
    # Add next steps based on status
    if status in ["PENDING", "PENDING_PAYMENT"]:
        response += "\n\n💡 *Next Step:* Complete payment to process your order."
    elif status == "VERIFICATION_PENDING":
        response += "\n\n💡 *Next Step:* We're verifying your payment."
    elif status in ["SHIPPED", "OUT_FOR_DELIVERY"]:
        response += "\n\n💡 Your order is on its way! 🎉"
    
    return response


async def handle_track_order(user_phone: str, message: str) -> str:
    """
    Handle order tracking request.
    
    Args:
        user_phone: User's phone number
        message: User's message text
        
    Returns:
        Response message
    """
    logger.info(f"📦 Track order request from {user_phone}: {message[:50]}...")
    
    # Try to extract order ID from message
    order_id = extract_order_id(message)
    
    if order_id:
        # Get specific order
        order = await get_order_by_id(order_id)
        
        if order:
            # Verify order belongs to user (security)
            if order.get('user_phone') != user_phone:
                return (
                    "❌ Order not found.\n\n"
                    "Please check the order ID and try again."
                )
            
            return format_order_status(order)
        else:
            return (
                f"❌ Order `{order_id}` not found.\n\n"
                "Please check the order ID and try again.\n"
                "Format: ORD-YYYYMMDD-XXXXXX"
            )
    else:
        # No order ID provided - get latest order
        order = await get_latest_order(user_phone)
        
        if order:
            return format_order_status(order)
        else:
            return (
                "📦 You don't have any orders yet.\n\n"
                "Start shopping:\n"
                "• 'Show me phones'\n"
                "• 'Browse laptops'"
            )


async def handle_order_history(user_phone: str) -> str:
    """
    Show user's order history.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        Response message
    """
    logger.info(f"📋 Order history request from {user_phone}")
    
    orders = await get_all_orders(user_phone, limit=5)
    
    if not orders:
        return (
            "📋 You don't have any orders yet.\n\n"
            "Start shopping:\n"
            "• 'Show me phones'\n"
            "• 'Browse laptops'"
        )
    
    response = "📋 *Your Recent Orders*\n\n"
    
    for order in orders:
        order_id = order.get('order_id', 'Unknown')
        status = order.get('status', 'PENDING').upper()
        total = order.get('total_amount', 0)
        status_emoji = STATUS_DISPLAY.get(status, "📋")
        
        response += f"🎫 `{order_id}`\n"
        response += f"   {status_emoji}\n"
        response += f"   💰 ₹{total:,.0f}\n\n"
    
    response += "💡 Say 'track ORD-xxx' for details."
    
    return response


def is_tracking_request(message: str) -> bool:
    """
    Check if message is an order tracking request.
    
    Args:
        message: User's message text
        
    Returns:
        True if tracking request
    """
    message_lower = message.lower().strip()
    
    tracking_keywords = [
        "track",
        "tracking",
        "where is my order",
        "order status",
        "delivery status",
        "when will",
        "order update",
        "my order",
    ]
    
    # Check for order ID pattern
    if extract_order_id(message):
        return True
    
    for keyword in tracking_keywords:
        if keyword in message_lower:
            return True
    
    return False
