"""
Support Service for Human Handoff.

Enables seamless transition between AI and human support agents.
Uses Redis to track user support mode state.
"""

from typing import Optional
from loguru import logger

from backend.config.settings import settings


# Redis key prefix for support mode
SUPPORT_MODE_KEY = "user_mode:{phone}"
SUPPORT_MODE_VALUE = "human"

# Keywords that trigger human handoff
SUPPORT_KEYWORDS = [
    "support",
    "human",
    "agent",
    "help me",
    "talk to human",
    "talk to agent",
    "real person",
    "customer service",
    "complaint",
    "speak to someone",
]

# Keywords that resume AI mode
RESUME_KEYWORDS = [
    "resume ai",
    "resume bot",
    "back to ai",
    "back to bot",
    "exit support",
    "done",
]


class SupportService:
    """
    Manages human support handoff for WhatsApp users.
    
    When a user requests human support:
    1. Set Redis key to "human" mode
    2. Bot stops processing their messages
    3. Human agent can respond via dashboard/WhatsApp Business
    4. User types "RESUME AI" to go back to bot
    """
    
    def __init__(self):
        self._redis = None
    
    async def _get_redis(self):
        """Get Redis client (lazy initialization)."""
        if self._redis is None:
            try:
                from backend.cache.redis_client import get_redis_client
                self._redis = await get_redis_client()
            except Exception as e:
                logger.error(f"❌ Failed to get Redis client: {e}")
                return None
        return self._redis
    
    def _get_key(self, phone: str) -> str:
        """Get Redis key for user's support mode."""
        return SUPPORT_MODE_KEY.format(phone=phone)
    
    async def is_in_support_mode(self, user_phone: str) -> bool:
        """
        Check if user is in human support mode.
        
        Args:
            user_phone: User's phone number
            
        Returns:
            True if user is in human support mode
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return False
            
            key = self._get_key(user_phone)
            value = await redis.get(key)
            
            is_support = value == SUPPORT_MODE_VALUE if value else False
            if is_support:
                logger.debug(f"👨‍💻 User {user_phone} is in support mode")
            
            return is_support
            
        except Exception as e:
            logger.error(f"❌ Failed to check support mode: {e}")
            return False
    
    async def enable_support_mode(self, user_phone: str) -> bool:
        """
        Enable human support mode for a user.
        
        Args:
            user_phone: User's phone number
            
        Returns:
            True if successfully enabled
        """
        try:
            redis = await self._get_redis()
            if not redis:
                logger.error("❌ Redis not available for support mode")
                return False
            
            key = self._get_key(user_phone)
            # No expiry - stays until manually disabled
            await redis.set(key, SUPPORT_MODE_VALUE)
            
            logger.info(f"👨‍💻 Support mode ENABLED for {user_phone}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to enable support mode: {e}")
            return False
    
    async def disable_support_mode(self, user_phone: str) -> bool:
        """
        Disable human support mode for a user (resume AI).
        
        Args:
            user_phone: User's phone number
            
        Returns:
            True if successfully disabled
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return False
            
            key = self._get_key(user_phone)
            await redis.delete(key)
            
            logger.info(f"🤖 Support mode DISABLED for {user_phone} - AI resumed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to disable support mode: {e}")
            return False
    
    async def toggle_support_mode(self, user_phone: str, enable: bool) -> bool:
        """
        Toggle support mode for a user.
        
        Args:
            user_phone: User's phone number
            enable: True to enable, False to disable
            
        Returns:
            True if operation succeeded
        """
        if enable:
            return await self.enable_support_mode(user_phone)
        else:
            return await self.disable_support_mode(user_phone)
    
    def is_support_request(self, message: str) -> bool:
        """
        Check if message is a request for human support.
        
        Args:
            message: User's message text
            
        Returns:
            True if user is requesting human support
        """
        message_lower = message.lower().strip()
        
        for keyword in SUPPORT_KEYWORDS:
            if keyword in message_lower:
                return True
        
        return False
    
    def is_resume_request(self, message: str) -> bool:
        """
        Check if message is a request to resume AI mode.
        
        Args:
            message: User's message text
            
        Returns:
            True if user wants to resume AI
        """
        message_lower = message.lower().strip()
        
        for keyword in RESUME_KEYWORDS:
            if keyword in message_lower:
                return True
        
        return False
    
    async def handle_support_message(self, user_phone: str, message: str) -> Optional[str]:
        """
        Handle message from user in support mode.
        
        This is called when a user is in human support mode.
        Checks if they want to resume AI, otherwise logs the message.
        
        Args:
            user_phone: User's phone number
            message: User's message text
            
        Returns:
            Response if AI should reply, None if human agent should handle
        """
        # Check if user wants to resume AI
        if self.is_resume_request(message):
            await self.disable_support_mode(user_phone)
            return (
                "🤖 *AI Mode Resumed*\n\n"
                "I'm back! How can I help you?\n\n"
                "Try:\n"
                "• 'Show me phones'\n"
                "• 'View cart'\n"
                "• 'Track order'"
            )
        
        # User is talking to human agent - don't process
        logger.info(f"👨‍💻 Human support message from {user_phone}: {message[:50]}...")
        return None
    
    def get_support_enabled_message(self) -> str:
        """Get message to send when support mode is enabled."""
        return (
            "👨‍💻 *Connected to Human Support*\n\n"
            "An agent will respond shortly.\n"
            "AI is now paused for your conversation.\n\n"
            "💡 Type *'RESUME AI'* when you're done to return to the bot."
        )
    
    def get_already_in_support_message(self) -> str:
        """Get message when user is already in support mode."""
        return (
            "👨‍💻 You're already connected to human support.\n\n"
            "Please wait for an agent to respond.\n"
            "Type *'RESUME AI'* to return to the bot."
        )


# Singleton
_support_service: Optional[SupportService] = None


def get_support_service() -> SupportService:
    """Get or create support service singleton."""
    global _support_service
    if _support_service is None:
        _support_service = SupportService()
    return _support_service
