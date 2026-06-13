"""
Payment Handler for WhatsApp Bot.

Handles manual UPI payment confirmations.
Updates order status and logs to Google Sheets.
"""

import re
from typing import Dict, Optional
from fastapi import BackgroundTasks
from loguru import logger

from backend.database.supabase_client import get_async_supabase_client
from backend.services.sheets_service import get_sheets_service


# Keywords that indicate payment confirmation
PAYMENT_KEYWORDS = [
    'paid',
    'payment done',
    'payment sent',
    'money sent',
    'transferred',
    'screenshot',
    'ss sent',
    'sent payment',
    'done payment',
    'upi done',
    'gpay done',
    'paytm done',
    'phonepe done',
    'bhim done',
]


def is_payment_message(message: str) -> bool:
    """
    Check if message indicates payment confirmation.
    
    Args:
        message: User's message text
        
    Returns:
        bool: True if message is about payment
    """
    message_lower = message.lower().strip()
    
    for keyword in PAYMENT_KEYWORDS:
        if keyword in message_lower:
            return True
    
    # Also check for patterns like "paid ₹500" or "sent 1000"
    payment_pattern = r'(paid|sent|transferred)\s*[₹rs.]?\s*\d+'
    if re.search(payment_pattern, message_lower):
        return True
    
    return False


async def get_pending_order(user_phone: str) -> Optional[Dict]:
    """
    Get the latest pending order for a user.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        Order dict or None
    """
    try:
        client = await get_async_supabase_client()
        
        # Find latest pending order
        result = await client.table('orders')\
            .select('*, order_items(*)')\
            .eq('user_phone', user_phone)\
            .in_('status', ['pending', 'PENDING', 'PENDING_PAYMENT'])\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to get pending order: {e}")
        return None


async def update_order_status(order_id: str, new_status: str) -> bool:
    """
    Update order status in Supabase.
    
    Args:
        order_id: Order ID
        new_status: New status value
        
    Returns:
        bool: Success status
    """
    try:
        client = await get_async_supabase_client()
        
        result = await client.table('orders')\
            .update({'status': new_status})\
            .eq('order_id', order_id)\
            .execute()
        
        if result.data:
            logger.info(f"✅ Order {order_id} status updated to {new_status}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Failed to update order status: {e}")
        return False


def log_order_to_sheets(order_data: Dict) -> None:
    """
    Background task to log order to Google Sheets.
    
    This function is designed to run in FastAPI BackgroundTasks.
    It swallows all exceptions to prevent affecting the main response.
    
    Args:
        order_data: Order data dict
    """
    try:
        sheets = get_sheets_service()
        sheets.log_order(order_data)
    except Exception as e:
        # Swallow exception - don't affect main flow
        logger.error(f"❌ Background sheets logging failed: {e}")


async def handle_payment_confirmation(
    user_phone: str,
    message: str,
    background_tasks: BackgroundTasks
) -> Dict:
    """
    Handle payment confirmation message.
    
    Args:
        user_phone: User's phone number
        message: User's message text
        background_tasks: FastAPI BackgroundTasks for async operations
        
    Returns:
        Dict with keys: success, response, intent
    """
    try:
        logger.info(f"💰 Payment confirmation from {user_phone}: {message[:50]}...")
        
        # Get pending order
        order = await get_pending_order(user_phone)
        
        if not order:
            return {
                "success": True,
                "response": (
                    "❌ No pending order found.\n\n"
                    "Please place an order first:\n"
                    "• Browse products: 'show me phones'\n"
                    "• Add to cart: 'add iPhone to cart'\n"
                    "• Checkout: 'checkout'"
                ),
                "intent": "payment_no_order"
            }
        
        order_id = order.get('order_id', 'Unknown')
        total_amount = order.get('total_amount', 0)
        
        # Update status to VERIFICATION_PENDING
        success = await update_order_status(order_id, 'VERIFICATION_PENDING')
        
        if not success:
            return {
                "success": False,
                "response": (
                    "❌ Something went wrong updating your order.\n"
                    "Please try again or contact support."
                ),
                "intent": "payment_error"
            }
        
        # Prepare order data for Sheets
        order_data = {
            'order_id': order_id,
            'user_phone': user_phone,
            'user_name': order.get('user_name', 'N/A'),
            'items': order.get('order_items', []),
            'total_amount': total_amount,
            'status': 'VERIFICATION_PENDING',
            'created_at': order.get('created_at', '')
        }
        
        # CRITICAL: Add to background tasks - do NOT await
        background_tasks.add_task(log_order_to_sheets, order_data)
        
        logger.info(f"✅ Payment confirmation processed: {order_id}")
        
        return {
            "success": True,
            "response": (
                f"✅ *Payment Marked!*\n\n"
                f"🎫 Order: `{order_id}`\n"
                f"💰 Amount: ₹{total_amount:,.0f}\n"
                f"📦 Status: Verification Pending\n\n"
                f"We're verifying your payment.\n"
                f"You'll receive a confirmation shortly! 🙏"
            ),
            "intent": "payment_confirmed"
        }
        
    except Exception as e:
        logger.error(f"❌ Payment confirmation failed: {e}")
        return {
            "success": False,
            "response": (
                "❌ Something went wrong.\n"
                "Please try again or contact support."
            ),
            "intent": "payment_error"
        }


async def handle_payment_inquiry(user_phone: str) -> Dict:
    """
    Handle payment status inquiry.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        Dict with response
    """
    try:
        order = await get_pending_order(user_phone)
        
        if not order:
            return {
                "success": True,
                "response": (
                    "📦 You have no pending orders.\n\n"
                    "Start shopping:\n"
                    "• 'show me laptops'\n"
                    "• 'checkout' to place order"
                ),
                "intent": "payment_inquiry"
            }
        
        order_id = order.get('order_id', 'Unknown')
        total_amount = order.get('total_amount', 0)
        status = order.get('status', 'PENDING')
        
        # UPI payment info (customize with your UPI ID)
        upi_id = "your-upi@paytm"  # Replace with actual UPI ID
        
        return {
            "success": True,
            "response": (
                f"💳 *Payment Details*\n\n"
                f"🎫 Order: `{order_id}`\n"
                f"💰 Amount: ₹{total_amount:,.0f}\n"
                f"📊 Status: {status}\n\n"
                f"*Pay via UPI:*\n"
                f"📱 UPI ID: `{upi_id}`\n\n"
                f"After payment, send 'payment done' or share screenshot."
            ),
            "intent": "payment_inquiry"
        }
        
    except Exception as e:
        logger.error(f"❌ Payment inquiry failed: {e}")
        return {
            "success": False,
            "response": "❌ Failed to get payment info. Please try again.",
            "intent": "payment_error"
        }
