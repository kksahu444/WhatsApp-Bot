"""
Checkout Handlers for WhatsApp AI Seller Bot.

Handles:
- Starting checkout flow
- Processing checkout responses (name, address, confirmation)
- Order history
- Order tracking
"""

from loguru import logger

from backend.services.checkout_manager import get_checkout_manager, CheckoutState
from backend.services.cart_manager import get_cart_manager


async def handle_checkout(user_phone: str) -> str:
    """
    Start checkout flow.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        str: Response prompting for name
    """
    try:
        # Check if cart has items
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user_phone)
        
        if not cart:
            return (
                "🛒 Your cart is empty!\n\n"
                "Search for products first:\n"
                "• 'show me laptops'\n"
                "• 'phones under 50000'"
            )
        
        # Start checkout
        checkout_manager = get_checkout_manager()
        return await checkout_manager.start_checkout(user_phone)
        
    except Exception as e:
        logger.error(f"❌ Checkout start failed: {e}")
        return "❌ Checkout failed. Please try again."


async def handle_checkout_response(user_phone: str, message: str) -> str:
    """
    Handle responses during checkout flow.
    
    Routes to appropriate handler based on current state:
    - AWAITING_NAME → process_name
    - AWAITING_ADDRESS → process_address
    - AWAITING_CONFIRMATION → process_confirmation
    
    Args:
        user_phone: User's phone number
        message: User's message
        
    Returns:
        str: Response message
    """
    try:
        checkout_manager = get_checkout_manager()
        state = await checkout_manager.get_state(user_phone)
        
        if not state:
            return "Type 'checkout' to place an order."
        
        current_state = state.get("state")
        
        if current_state == CheckoutState.AWAITING_NAME.value:
            return await checkout_manager.process_name(user_phone, message)
            
        elif current_state == CheckoutState.AWAITING_ADDRESS.value:
            return await checkout_manager.process_address(user_phone, message)
            
        elif current_state == CheckoutState.AWAITING_CONFIRMATION.value:
            result = await checkout_manager.process_confirmation(user_phone, message)
            
            if result["success"]:
                order = result["order"]
                return (
                    "✅ *Order Placed Successfully!*\n\n"
                    f"🎫 Order ID: `{order['order_id']}`\n"
                    f"💰 Total: ₹{order['total_amount']:,.0f}\n"
                    f"📦 Status: {order['status'].title()}\n\n"
                    f"📱 Track your order:\n"
                    f"'track {order['order_id']}'\n\n"
                    "Thank you for shopping with us! 🙏"
                )
            else:
                return result["message"]
        
        return "Type 'checkout' to place an order."
        
    except Exception as e:
        logger.error(f"❌ Checkout response failed: {e}")
        return "❌ Something went wrong. Type 'checkout' to restart."


async def handle_order_history(user_phone: str) -> str:
    """
    Show user's order history.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        str: Formatted order history
    """
    try:
        from backend.services.order_service import get_order_service
        
        order_service = get_order_service()
        orders = await order_service.get_user_orders(user_phone, limit=5)
        
        if not orders:
            return (
                "📦 No orders yet!\n\n"
                "Start shopping:\n"
                "• 'show me laptops'\n"
                "• 'checkout' to place order"
            )
        
        response = "📦 *Your Orders*\n"
        response += "─" * 25 + "\n\n"
        
        for order in orders:
            status_emoji = {
                "pending": "🟡",
                "confirmed": "🟢",
                "shipped": "🚚",
                "delivered": "✅",
                "cancelled": "❌",
                "failed": "⚠️"
            }.get(order['status'], "📦")
            
            response += f"🎫 `{order['order_id']}`\n"
            response += f"   💰 ₹{order['total_amount']:,.0f}\n"
            response += f"   {status_emoji} {order['status'].title()}\n"
            response += f"   📅 {order['created_at'][:10]}\n\n"
        
        response += "─" * 25 + "\n"
        response += "Track order: 'track ORD-XXXXXXXX-XXXXXX'"
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Order history failed: {e}")
        return "❌ Failed to get order history."


async def handle_track_order(user_phone: str, order_id: str) -> str:
    """
    Track specific order.
    
    Args:
        user_phone: User's phone number
        order_id: Order ID to track
        
    Returns:
        str: Order details
    """
    try:
        from backend.services.order_service import get_order_service
        
        order_service = get_order_service()
        order = await order_service.get_order_by_id(order_id)
        
        if not order:
            return f"❌ Order `{order_id}` not found."
        
        # Verify user owns this order
        if order['user_phone'] != user_phone:
            return "❌ You don't have permission to view this order."
        
        # Build response
        status_emoji = {
            "pending": "🟡 Pending",
            "confirmed": "🟢 Confirmed",
            "shipped": "🚚 Shipped",
            "delivered": "✅ Delivered",
            "cancelled": "❌ Cancelled",
            "failed": "⚠️ Failed"
        }.get(order['status'], f"📦 {order['status'].title()}")
        
        response = f"📦 *Order {order['order_id']}*\n"
        response += "─" * 25 + "\n\n"
        response += f"📊 Status: {status_emoji}\n"
        response += f"💰 Total: ₹{order['total_amount']:,.0f}\n"
        response += f"📅 Date: {order['created_at'][:10]}\n\n"
        response += f"👤 {order['user_name']}\n"
        response += f"📍 {order['delivery_address']}\n\n"
        
        # List items
        items = order.get('items', [])
        if items:
            response += "*Items:*\n"
            for item in items:
                response += f"• {item['product_name']} ×{item['quantity']} = ₹{item['subtotal']:,.0f}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Track order failed: {e}")
        return "❌ Failed to track order."


async def handle_cancel_order(user_phone: str, order_id: str) -> str:
    """
    Cancel an order.
    
    Args:
        user_phone: User's phone number
        order_id: Order ID to cancel
        
    Returns:
        str: Cancellation result
    """
    try:
        from backend.services.order_service import get_order_service
        
        order_service = get_order_service()
        order = await order_service.get_order_by_id(order_id)
        
        if not order:
            return f"❌ Order `{order_id}` not found."
        
        if order['user_phone'] != user_phone:
            return "❌ You don't have permission to cancel this order."
        
        result = await order_service.cancel_order(order_id)
        
        if result["success"]:
            return f"✅ Order `{order_id}` has been cancelled.\n\nStock has been restored."
        else:
            return f"❌ {result['message']}"
            
    except Exception as e:
        logger.error(f"❌ Cancel order failed: {e}")
        return "❌ Failed to cancel order."
