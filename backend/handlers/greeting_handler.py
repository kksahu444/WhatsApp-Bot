"""
Greeting Handler for WhatsApp AI Seller Bot.
Handles greetings, help requests, and onboarding.
"""

from typing import Optional
from loguru import logger


async def handle_greeting(user_phone: str, message: str) -> str:
    """
    Handle greeting messages.
    
    Args:
        user_phone: User's phone number
        message: User's greeting message
        
    Returns:
        str: Welcome message
    """
    logger.info(f"👋 Greeting from {user_phone}: {message[:30]}...")
    
    return (
        "👋 *Welcome to our store!*\n\n"
        "I'm your AI shopping assistant. I can help you:\n\n"
        "🔍 *Find Products*\n"
        "   'show me laptops'\n"
        "   'phones under 50000'\n\n"
        "🛒 *Manage Cart*\n"
        "   'add [product]' - Add to cart\n"
        "   'cart' - View your cart\n"
        "   'checkout' - Place order\n\n"
        "📦 *Categories*\n"
        "   📱 Electronics | 👕 Clothing | 🏠 Home\n\n"
        "What are you looking for today?"
    )


async def handle_help(user_phone: str) -> str:
    """
    Show help message with all available commands.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        str: Help guide message
    """
    logger.info(f"❓ Help requested: {user_phone}")
    
    return (
        "📖 *Help Guide*\n\n"
        "*Search Products:*\n"
        "- 'show me laptops'\n"
        "- 'phones under 50000'\n"
        "- 'red shoes'\n\n"
        "*Cart Management:*\n"
        "- 'cart' or 'view cart'\n"
        "- 'add [product name]'\n"
        "- 'remove [product name]'\n"
        "- 'clear cart'\n\n"
        "*Orders:*\n"
        "- 'checkout' - Place order\n"
        "- 'track order [ID]' - Track delivery\n\n"
        "*Categories:*\n"
        "📱 Electronics • 👕 Clothing • 🏠 Home\n\n"
        "Just type naturally and I'll understand! 😊"
    )


async def handle_unknown(user_phone: str, message: str) -> str:
    """
    Handle unknown/unrecognized messages.
    
    Args:
        user_phone: User's phone number
        message: User's message
        
    Returns:
        str: Guidance message
    """
    logger.debug(f"❔ Unknown intent from {user_phone}: {message[:30]}...")
    
    return (
        "I'm not sure what you're looking for.\n\n"
        "Try one of these:\n"
        "🔍 'show me laptops'\n"
        "💰 'phones under 50000'\n"
        "🛒 'view cart'\n"
        "❓ 'help'\n\n"
        "Or just tell me what you need! 😊"
    )


async def handle_thank_you(user_phone: str) -> str:
    """
    Handle thank you messages.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        str: Thank you response
    """
    logger.info(f"🙏 Thank you from {user_phone}")
    
    return (
        "You're welcome! 😊\n\n"
        "Feel free to ask if you need anything else.\n"
        "Happy shopping! 🛍️"
    )


async def handle_goodbye(user_phone: str) -> str:
    """
    Handle goodbye messages.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        str: Goodbye response
    """
    logger.info(f"👋 Goodbye from {user_phone}")
    
    return (
        "Goodbye! 👋\n\n"
        "Thanks for visiting. Come back anytime!\n"
        "Your cart will be saved for next time. 🛒"
    )
