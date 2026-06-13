"""
Checkout Manager - Multi-step conversation state.

Uses Redis to maintain checkout state across messages:
1. AWAITING_NAME → User provides name
2. AWAITING_ADDRESS → User provides address
3. AWAITING_CONFIRMATION → User confirms order

State expires after 5 minutes of inactivity.
"""

from typing import Optional, Dict
from enum import Enum
from loguru import logger
import json


class CheckoutState(Enum):
    """Checkout flow states."""
    IDLE = "idle"
    AWAITING_NAME = "awaiting_name"
    AWAITING_ADDRESS = "awaiting_address"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


class CheckoutManager:
    """Manage multi-step checkout state using Redis."""

    def __init__(self):
        self.state_ttl = 300  # 5 minutes timeout

    async def _get_redis(self):
        """Get Redis client."""
        from backend.database.redis_client import get_redis_client
        return await get_redis_client()

    def _get_key(self, user_phone: str) -> str:
        """Get Redis key for user's checkout state."""
        return f"checkout:{user_phone}"

    async def get_state(self, user_phone: str) -> Optional[Dict]:
        """
        Get current checkout state for user.
        
        Args:
            user_phone: User's phone number
            
        Returns:
            Dict with 'state' and 'data', or None if no active checkout
        """
        try:
            redis = await self._get_redis()
            key = self._get_key(user_phone)
            data = await redis.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"❌ Get checkout state failed: {e}")
            return None

    async def set_state(
        self,
        user_phone: str,
        state: CheckoutState,
        data: Dict = None
    ):
        """
        Set checkout state with TTL.
        
        Args:
            user_phone: User's phone number
            state: Current checkout state
            data: Associated data (name, address, etc.)
        """
        try:
            redis = await self._get_redis()
            key = self._get_key(user_phone)
            
            state_data = {
                "state": state.value,
                "data": data or {}
            }
            
            await redis.set(key, json.dumps(state_data), ex=self.state_ttl)
            logger.debug(f"✅ Checkout state set: {user_phone} → {state.value}")
            
        except Exception as e:
            logger.error(f"❌ Set checkout state failed: {e}")

    async def clear_state(self, user_phone: str):
        """Clear checkout state (on completion or cancel)."""
        try:
            redis = await self._get_redis()
            await redis.delete(self._get_key(user_phone))
            logger.debug(f"✅ Checkout state cleared: {user_phone}")
            
        except Exception as e:
            logger.error(f"❌ Clear checkout state failed: {e}")

    async def start_checkout(self, user_phone: str) -> str:
        """
        Start checkout flow.
        
        Args:
            user_phone: User's phone number
            
        Returns:
            str: Prompt for user's name
        """
        await self.set_state(user_phone, CheckoutState.AWAITING_NAME)
        
        return (
            "🛒 *Let's complete your order!*\n\n"
            "Please provide your *full name*:"
        )

    async def process_name(self, user_phone: str, name: str) -> str:
        """
        Process name input and move to address step.
        
        Args:
            user_phone: User's phone number
            name: User's name
            
        Returns:
            str: Response (address prompt or error)
        """
        # Validate name
        name = name.strip()
        if len(name) < 2:
            return "❌ Name must be at least 2 characters. Please try again:"
        
        if len(name) > 100:
            return "❌ Name is too long. Please use a shorter name:"
        
        # Save name and move to address step
        state = await self.get_state(user_phone) or {"data": {}}
        state["data"]["name"] = name
        
        await self.set_state(user_phone, CheckoutState.AWAITING_ADDRESS, state["data"])
        
        return (
            f"✅ Name: *{name}*\n\n"
            "📍 Please provide your *delivery address*:\n"
            "(Include street, city, state, and PIN code)"
        )

    async def process_address(self, user_phone: str, address: str) -> str:
        """
        Process address input and show confirmation.
        
        Args:
            user_phone: User's phone number
            address: Delivery address
            
        Returns:
            str: Confirmation prompt or error
        """
        # Validate address
        address = address.strip()
        if len(address) < 10:
            return "❌ Address must be at least 10 characters. Please provide a complete address:"
        
        if len(address) > 500:
            return "❌ Address is too long. Please shorten it:"
        
        # Get current state
        state = await self.get_state(user_phone)
        if not state or "name" not in state.get("data", {}):
            await self.clear_state(user_phone)
            return "❌ Session expired. Type 'checkout' to restart."
        
        # Save address and move to confirmation
        state["data"]["address"] = address
        await self.set_state(user_phone, CheckoutState.AWAITING_CONFIRMATION, state["data"])
        
        # Get cart summary
        from backend.services.cart_manager import get_cart_manager
        cart_manager = get_cart_manager()
        
        total = await cart_manager.calculate_total(user_phone)
        count = await cart_manager.get_cart_count(user_phone)
        
        return (
            "📋 *Order Confirmation*\n\n"
            f"👤 Name: {state['data']['name']}\n"
            f"📍 Address: {address}\n"
            f"🛒 Items: {count}\n"
            f"💰 Total: ₹{total:,.0f}\n\n"
            "Reply *YES* to confirm or *NO* to cancel."
        )

    async def process_confirmation(self, user_phone: str, confirmation: str) -> Dict:
        """
        Process order confirmation.
        
        Args:
            user_phone: User's phone number
            confirmation: User's response (yes/no)
            
        Returns:
            Dict: {"success": bool, "order": dict (if success), "message": str}
        """
        # Check state
        state = await self.get_state(user_phone)
        if not state or state.get("state") != CheckoutState.AWAITING_CONFIRMATION.value:
            await self.clear_state(user_phone)
            return {
                "success": False,
                "message": "❌ Session expired. Type 'checkout' to restart."
            }
        
        # Check confirmation
        confirmation_lower = confirmation.lower().strip()
        if confirmation_lower not in ["yes", "y", "confirm", "ok", "proceed"]:
            await self.clear_state(user_phone)
            return {
                "success": False,
                "message": "❌ Order cancelled. Your cart items are saved."
            }
        
        # Get cart
        from backend.services.cart_manager import get_cart_manager
        cart_manager = get_cart_manager()
        cart = await cart_manager.get_cart(user_phone)
        
        if not cart:
            await self.clear_state(user_phone)
            return {"success": False, "message": "❌ Cart is empty"}
        
        # Create order
        from backend.services.order_service import get_order_service
        order_service = get_order_service()
        
        result = await order_service.create_order(
            user_phone=user_phone,
            user_name=state["data"]["name"],
            delivery_address=state["data"]["address"],
            cart_items=cart
        )
        
        # Clear checkout state
        await self.clear_state(user_phone)
        
        return result


# Singleton
_checkout_manager: Optional[CheckoutManager] = None


def get_checkout_manager() -> CheckoutManager:
    """Get checkout manager singleton."""
    global _checkout_manager
    if _checkout_manager is None:
        _checkout_manager = CheckoutManager()
    return _checkout_manager
