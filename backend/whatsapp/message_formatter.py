"""
WhatsApp Message Formatter.
Formats bot responses for WhatsApp display.
"""

from typing import List, Dict


class WhatsAppMessageFormatter:
    """
    Format messages for WhatsApp.
    
    Handles:
    - Character limits (4096 chars)
    - Markdown conversion (bold, italic)
    - Link formatting
    - Message splitting
    """
    
    MAX_LENGTH = 4096
    
    @staticmethod
    def format_message(text: str) -> str:
        """
        Format message for WhatsApp.
        
        WhatsApp supports:
        - *bold*
        - _italic_
        - ~strikethrough~
        - ```code```
        - Monospace: `text`
        """
        # Ensure length limit
        if len(text) > WhatsAppMessageFormatter.MAX_LENGTH:
            text = text[:WhatsAppMessageFormatter.MAX_LENGTH - 50] + "\n\n...(message truncated)"
        
        return text
    
    @staticmethod
    def split_message(text: str, max_length: int = 4000) -> List[str]:
        """
        Split long message into multiple parts.
        
        Useful for order history or product lists.
        """
        if len(text) <= max_length:
            return [text]
        
        parts = []
        current = ""
        
        for line in text.split('\n'):
            if len(current) + len(line) + 1 <= max_length:
                current += line + '\n'
            else:
                if current:
                    parts.append(current.strip())
                current = line + '\n'
        
        if current:
            parts.append(current.strip())
        
        return parts
    
    @staticmethod
    def format_product_list(products: List[Dict]) -> str:
        """Format product list for WhatsApp."""
        if not products:
            return "No products found."
        
        message = "🛍️ *Available Products:*\n\n"
        
        for i, product in enumerate(products[:10], 1):  # Limit to 10
            name = product.get('name', 'Unknown')
            price = product.get('price', 0)
            stock = product.get('stock', 'N/A')
            
            message += f"{i}. *{name}*\n"
            message += f"   💰 ₹{price:,.0f}\n"
            message += f"   📦 Stock: {stock}\n\n"
        
        if len(products) > 10:
            message += f"\n_...and {len(products) - 10} more products_"
        
        return message
    
    @staticmethod
    def format_order_confirmation(order: Dict) -> str:
        """Format order confirmation message."""
        order_id = order.get('order_id', 'N/A')
        total = order.get('total_amount', 0)
        status = order.get('status', 'pending')
        
        message = "✅ *Order Placed Successfully!*\n\n"
        message += f"🎫 Order ID: `{order_id}`\n"
        message += f"💰 Total: ₹{total:,.0f}\n"
        message += f"📦 Status: {status.title()}\n\n"
        message += f"📱 Track your order:\n"
        message += f"'track {order_id}'\n\n"
        message += "Thank you for shopping with us! 🙏"
        
        return message
    
    @staticmethod
    def format_cart(cart_items: List[Dict], total: float) -> str:
        """Format shopping cart for WhatsApp."""
        if not cart_items:
            return "🛒 Your cart is empty!\n\nSearch for products to add."
        
        message = "🛒 *Your Shopping Cart*\n"
        message += "─" * 25 + "\n\n"
        
        for item in cart_items:
            name = item.get('product', {}).get('name', 'Unknown')
            qty = item.get('quantity', 1)
            subtotal = item.get('subtotal', 0)
            
            message += f"• *{name}*\n"
            message += f"  Qty: {qty} | ₹{subtotal:,.0f}\n\n"
        
        message += "─" * 25 + "\n"
        message += f"*Total: ₹{total:,.0f}*\n\n"
        message += "Type 'checkout' to place order"
        
        return message
    
    @staticmethod
    def format_error(error_message: str = None) -> str:
        """Format error message."""
        if error_message:
            return f"❌ {error_message}\n\nPlease try again or type 'help' for assistance."
        return "❌ Something went wrong. Please try again."
    
    @staticmethod
    def format_welcome() -> str:
        """Format welcome message."""
        return (
            "👋 *Welcome to ShopBot!*\n\n"
            "I can help you:\n"
            "🔍 Find products: 'show me laptops'\n"
            "🛒 Manage cart: 'add iPhone to cart'\n"
            "📦 Track orders: 'my orders'\n"
            "❓ Get help: 'help'\n\n"
            "What are you looking for today?"
        )


def get_message_formatter() -> WhatsAppMessageFormatter:
    """Get message formatter instance."""
    return WhatsAppMessageFormatter()
