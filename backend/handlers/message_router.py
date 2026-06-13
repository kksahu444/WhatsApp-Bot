"""
Message Router for WhatsApp AI Seller Bot.
Routes incoming messages to appropriate handlers based on intent classification.
"""

import re
from typing import Any, Dict, Optional, List
from loguru import logger

from backend.database.supabase_client import get_async_supabase_client


class MessageRouter:
    """Routes incoming messages to appropriate handlers."""

    def __init__(self):
        self.patterns = {
            "greeting": r"\b(hi|hello|hey|start|good morning|good evening|namaste)\b",
            "help": r"\b(help|support|how to|commands|what can you do)\b",
            "cart_view": r"\b(cart|view cart|my cart|show cart|check cart)\b",
            "cart_add": r"\b(add|add to cart|put in cart|buy this)\b",
            "cart_remove": r"\b(remove|delete|remove from cart|take out)\b",
            "cart_clear": r"\b(clear cart|empty cart|remove all)\b",
            "checkout": r"\b(checkout|place order|buy now|order|purchase)\b",
            "product_query": r"\b(show|find|search|looking for|want|need|recommend|browse)\b",
        }
        self.categories = ["electronics", "clothing", "home"]

    async def classify_intent(self, message: str) -> str:
        """
        Classify message intent using regex patterns.
        
        Args:
            message: User's message text
            
        Returns:
            str: Classified intent
        """
        message_lower = message.lower().strip()
        
        # Check patterns in order of specificity (more specific first)
        if re.search(self.patterns["greeting"], message_lower):
            return "greeting"
        if re.search(self.patterns["help"], message_lower):
            return "help"
        if re.search(self.patterns["cart_clear"], message_lower):
            return "cart_clear"
        
        # NEW: Order-related intents (check before checkout)
        if re.search(r"\b(orders|order history|my orders)\b", message_lower):
            return "order_history"
        if re.search(r"\b(track|tracking)\b", message_lower):
            return "track_order"
        if re.search(r"\b(cancel order|cancel my order)\b", message_lower):
            return "cancel_order"
        
        if re.search(self.patterns["checkout"], message_lower):
            return "checkout"
        # Check remove BEFORE view (remove contains "cart" keyword)
        if re.search(self.patterns["cart_remove"], message_lower):
            return "cart_remove"
        if re.search(self.patterns["cart_add"], message_lower):
            return "cart_add"
        if re.search(self.patterns["cart_view"], message_lower):
            return "cart_view"
        if re.search(self.patterns["product_query"], message_lower):
            return "product_query"
        
        # Check category names
        for category in self.categories:
            if category in message_lower:
                return "product_query"
        
        # Check price terms
        if any(word in message_lower for word in ["under", "below", "above", "price", "₹", "rs", "rupee"]):
            return "product_query"
        
        # Check product-related keywords
        product_keywords = ["phone", "laptop", "shirt", "shoes", "watch", "headphone", "jeans", "iphone", "macbook"]
        if any(kw in message_lower for kw in product_keywords):
            return "product_query"
        
        return "unknown"

    async def log_conversation(self, user_phone: str, role: str, message: str) -> None:
        """
        Log conversation to Supabase.
        
        Args:
            user_phone: User's phone number
            role: Message role ('user' or 'bot')
            message: Message content
        """
        try:
            client = await get_async_supabase_client()
            await client.table('conversations').insert({
                "user_phone": user_phone,
                "role": role,
                "message": message
            }).execute()
            logger.debug(f"✅ Logged: {role} - {message[:50]}...")
        except Exception as e:
            logger.warning(f"⚠️ Failed to log conversation: {e}")

    async def route_message(
        self, 
        user_phone: str, 
        message: str,
        background_tasks: Optional[Any] = None
    ) -> Dict:
        """
        Route message to appropriate handler and return response.
        
        Args:
            user_phone: User's phone number
            message: User's message text
            background_tasks: BackgroundTasks-like object for async operations (e.g., Sheets logging)
            
        Returns:
            Dict: {"intent": str, "response": str, "success": bool}
        """
        try:
            # Log user message
            await self.log_conversation(user_phone, "user", message)
            
            # CHECK PAYMENT CONFIRMATION FIRST
            from backend.handlers.payment_handler import is_payment_message, handle_payment_confirmation
            if is_payment_message(message):
                if background_tasks:
                    result = await handle_payment_confirmation(user_phone, message, background_tasks)
                    await self.log_conversation(user_phone, "bot", result["response"])
                    return {
                        "intent": result["intent"],
                        "response": result["response"],
                        "success": result["success"]
                    }
            
            # CHECK CHECKOUT STATE (user might be in multi-step flow)
            from backend.services.checkout_manager import get_checkout_manager
            checkout_manager = get_checkout_manager()
            checkout_state = await checkout_manager.get_state(user_phone)
            
            response_text = ""
            intent = ""
            
            if checkout_state:
                # User is in checkout flow - handle checkout response
                from backend.handlers.checkout_handler import handle_checkout_response
                response_text = await handle_checkout_response(user_phone, message)
                intent = "checkout_response"
            else:
                # Normal intent classification
                intent = await self.classify_intent(message)
                logger.info(f"🎯 Intent: {intent} | User: {user_phone} | Msg: {message[:50]}...")
                
                # Route to appropriate handler
                if intent == "greeting":
                    from backend.handlers.greeting_handler import handle_greeting
                    response_text = await handle_greeting(user_phone, message)
                    
                elif intent == "help":
                    from backend.handlers.greeting_handler import handle_help
                    response_text = await handle_help(user_phone)
                    
                elif intent == "cart_view":
                    from backend.handlers.cart_handler import handle_view_cart
                    response_text = await handle_view_cart(user_phone)
                    
                elif intent == "cart_add":
                    from backend.handlers.cart_handler import handle_add_to_cart
                    response_text = await handle_add_to_cart(user_phone, message)
                    
                elif intent == "cart_remove":
                    from backend.handlers.cart_handler import handle_remove_from_cart
                    response_text = await handle_remove_from_cart(user_phone, message)
                    
                elif intent == "cart_clear":
                    from backend.handlers.cart_handler import handle_clear_cart
                    response_text = await handle_clear_cart(user_phone)
                    
                elif intent == "checkout":
                    from backend.handlers.checkout_handler import handle_checkout
                    response_text = await handle_checkout(user_phone)
                    
                elif intent == "order_history":
                    from backend.handlers.tracking_handler import handle_order_history
                    response_text = await handle_order_history(user_phone)
                    
                elif intent == "track_order":
                    from backend.handlers.tracking_handler import handle_track_order
                    response_text = await handle_track_order(user_phone, message)
                    
                elif intent == "cancel_order":
                    # Extract order ID from message
                    match = re.search(r'(ORD-\d{8}-[A-F0-9]{6})', message, re.IGNORECASE)
                    if match:
                        order_id = match.group(1).upper()
                        from backend.handlers.checkout_handler import handle_cancel_order
                        response_text = await handle_cancel_order(user_phone, order_id)
                    else:
                        response_text = "Please provide order ID: 'cancel order ORD-20251205-A3F9B2'"
                    
                elif intent == "product_query":
                    from backend.handlers.product_handler import handle_product_query
                    response_text = await handle_product_query(user_phone, message)
                    
                else:
                    # Unknown intent - provide helpful guidance
                    response_text = (
                        "I'm not sure what you're looking for. Try:\n\n"
                        "🔍 'show me laptops'\n"
                        "🛒 'view cart'\n"
                        "📦 'checkout'\n"
                        "📋 'my orders'\n"
                        "💬 'help'"
                    )
            
            # Log bot response
            await self.log_conversation(user_phone, "bot", response_text)
            
            return {
                "intent": intent,
                "response": response_text,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ Routing failed: {e}")
            error_response = "Sorry, something went wrong. Please try again or type 'help'."
            await self.log_conversation(user_phone, "bot", error_response)
            return {
                "intent": "error",
                "response": error_response,
                "success": False
            }


# Singleton
_router: Optional[MessageRouter] = None


def get_message_router() -> MessageRouter:
    """Get or create message router singleton."""
    global _router
    if _router is None:
        _router = MessageRouter()
    return _router
