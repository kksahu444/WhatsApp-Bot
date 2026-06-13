"""
Cart Handler for WhatsApp AI Seller Bot.
Handles cart operations: view, add, remove, clear, checkout.

CRITICAL FIXES APPLIED:
- Uses get_cart() + calculate_total() (not non-existent get_cart_summary())
- Accesses products[0] correctly after search
"""

from typing import Dict, List, Optional
from loguru import logger

from backend.services.cart_manager import get_cart_manager
from backend.services.product_service import get_product_service


async def handle_view_cart(user_phone: str) -> str:
    """
    Show user's cart with items and total.
    
    Uses get_cart() + calculate_total() from CartManager.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        str: Formatted cart display
    """
    try:
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user_phone)
        
        if not cart:
            return (
                "🛒 Your cart is empty!\n\n"
                "Start shopping by searching for products:\n"
                "• 'show me laptops'\n"
                "• 'phones under 50000'\n"
                "• 'browse electronics'"
            )
        
        # Calculate totals
        total_items = sum(item['quantity'] for item in cart)
        total_amount = await cart_manager.calculate_total(user_phone)
        
        # Build cart display
        response = f"🛒 *Your Cart* ({total_items} items)\n"
        response += "─" * 25 + "\n\n"
        
        for item in cart:
            product = item["product"]
            qty = item["quantity"]
            subtotal = item["subtotal"]
            
            response += f"📦 *{product['name']}*\n"
            response += f"   ₹{float(product['price']):,.0f} × {qty} = ₹{subtotal:,.0f}\n\n"
        
        response += "─" * 25 + "\n"
        response += f"💰 *Total: ₹{total_amount:,.0f}*\n\n"
        
        response += "📋 *Options:*\n"
        response += "• 'checkout' - Place order\n"
        response += "• 'remove [product]' - Remove item\n"
        response += "• 'clear cart' - Empty cart"
        
        logger.info(f"✅ Cart viewed: {user_phone} - {total_items} items, ₹{total_amount:,.0f}")
        return response
        
    except Exception as e:
        logger.error(f"❌ View cart failed: {e}")
        return "Sorry, couldn't load your cart. Please try again."


async def handle_add_to_cart(user_phone: str, message: str) -> str:
    """
    Add product to cart.
    
    CRITICAL FIX: Correctly accesses products[0] after search.
    
    Args:
        user_phone: User's phone number
        message: User's message containing product info
        
    Returns:
        str: Add result message
    """
    try:
        # Parse product name from message
        query = message.lower()
        remove_words = ["add", "to", "cart", "buy", "purchase", "want", "need", "get", "the", "a", "an"]
        for word in remove_words:
            query = query.replace(word, " ")
        query = " ".join(query.split()).strip()  # Clean up whitespace
        
        if not query:
            return (
                "Please specify a product to add.\n\n"
                "Examples:\n"
                "• 'add iPhone 15 Pro'\n"
                "• 'add MacBook Air'\n"
                "• 'add 1' (add product #1)"
            )
        
        product_service = get_product_service()
        product = None
        
        # Check if user provided product ID
        if query.isdigit():
            product = await product_service.get_product_by_id(int(query))
            if not product:
                return f"❌ Product ID #{query} not found."
        else:
            # Search for product by name
            products = await product_service.search_products(query, limit=1)
            
            if not products:
                return (
                    f"Sorry, couldn't find '{query}'.\n\n"
                    f"Try searching first: 'show me {query}'"
                )
            
            # ✅ CRITICAL FIX: Get first product from list
            product = products[0]
        
        # Check stock availability
        if product.get("stock", 0) <= 0:
            return f"❌ *{product['name']}* is currently out of stock."
        
        # Add to cart
        cart_manager = get_cart_manager()
        result = await cart_manager.add_to_cart(user_phone, product["id"], quantity=1)
        
        if result["success"]:
            # Get updated cart info
            total = await cart_manager.calculate_total(user_phone)
            count = await cart_manager.get_cart_count(user_phone)
            
            response = (
                f"✅ Added *{product['name']}* to cart!\n\n"
                f"💰 Price: ₹{float(product['price']):,.0f}\n"
                f"🛒 Cart: {count} items | Total: ₹{total:,.0f}\n"
            )
            
            # ==========================================
            # INTEGRATION: Product Recommendations
            # Show "You might also like" suggestions
            # ==========================================
            try:
                from backend.services.recommendation_service import format_recommendations_for_cart
                recommendations = await format_recommendations_for_cart(product['name'])
                if recommendations:
                    response += f"\n{recommendations}\n"
            except Exception as rec_error:
                # Recommendations are optional - don't fail the add
                logger.debug(f"Recommendations unavailable: {rec_error}")
            
            response += "\nType 'cart' to view or 'checkout' to order."
            
            # Log analytics (non-blocking)
            try:
                from backend.services.analytics_service import log_cart_event
                log_cart_event(user_phone, product['name'], action="add")
            except Exception:
                pass  # Analytics should never fail the main flow
            
            return response
        else:
            return f"❌ {result.get('message', 'Failed to add to cart')}"
        
    except Exception as e:
        logger.error(f"❌ Add to cart failed: {e}")
        return "Sorry, couldn't add to cart. Please try again."


async def handle_remove_from_cart(user_phone: str, message: str) -> str:
    """
    Remove product from cart.
    
    Args:
        user_phone: User's phone number
        message: User's message containing product to remove
        
    Returns:
        str: Remove result message
    """
    try:
        # Parse product name from message
        query = message.lower()
        remove_words = ["remove", "delete", "from", "cart", "take", "out", "the", "a", "an"]
        for word in remove_words:
            query = query.replace(word, " ")
        query = " ".join(query.split()).strip()
        
        if not query:
            return (
                "Please specify a product to remove.\n\n"
                "Example: 'remove iPhone 15 Pro'\n\n"
                "Type 'cart' to see your items."
            )
        
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user_phone)
        
        if not cart:
            return "🛒 Your cart is empty!"
        
        # Find matching product in cart
        product_to_remove = None
        for item in cart:
            product_name = item["product"]["name"].lower()
            if query.lower() in product_name or product_name in query.lower():
                product_to_remove = item
                break
        
        if not product_to_remove:
            # Show cart items to help user
            items_list = ", ".join([item["product"]["name"] for item in cart])
            return (
                f"'{query}' not found in your cart.\n\n"
                f"Your cart items: {items_list}\n\n"
                "Type 'cart' to view details."
            )
        
        # Remove from cart
        result = await cart_manager.remove_from_cart(
            user_phone,
            product_to_remove["product_id"]
        )
        
        if result.get("success", False):
            return (
                f"✅ Removed *{product_to_remove['product']['name']}* from cart.\n\n"
                "Type 'cart' to view updated cart."
            )
        else:
            return f"❌ {result.get('message', 'Failed to remove item')}"
        
    except Exception as e:
        logger.error(f"❌ Remove from cart failed: {e}")
        return "Sorry, couldn't remove item. Please try again."


async def handle_clear_cart(user_phone: str) -> str:
    """
    Clear all items from cart.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        str: Clear result message
    """
    try:
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user_phone)
        
        if not cart:
            return "🛒 Your cart is already empty!"
        
        result = await cart_manager.clear_cart(user_phone)
        
        if result.get("success", False):
            return (
                "🗑️ Cart cleared successfully!\n\n"
                "Start fresh by searching for products:\n"
                "• 'show me laptops'\n"
                "• 'phones under 50000'"
            )
        else:
            return f"❌ {result.get('message', 'Failed to clear cart')}"
        
    except Exception as e:
        logger.error(f"❌ Clear cart failed: {e}")
        return "Sorry, couldn't clear cart. Please try again."


# Note: handle_checkout moved to checkout_handler.py for multi-step flow


async def handle_update_quantity(user_phone: str, product_id: int, quantity: int) -> str:
    """
    Update quantity of a cart item.
    
    Args:
        user_phone: User's phone number
        product_id: Product ID to update
        quantity: New quantity
        
    Returns:
        str: Update result message
    """
    try:
        cart_manager = get_cart_manager()
        result = await cart_manager.update_quantity(user_phone, product_id, quantity)
        
        if result.get("success", False):
            if quantity == 0:
                return "✅ Item removed from cart."
            return f"✅ Quantity updated to {quantity}."
        else:
            return f"❌ {result.get('message', 'Failed to update quantity')}"
        
    except Exception as e:
        logger.error(f"❌ Update quantity failed: {e}")
        return "Sorry, couldn't update quantity. Please try again."
