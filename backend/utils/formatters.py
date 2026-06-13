"""
Formatters
Message and data formatting utilities
"""

from typing import Optional, List, Dict, Any
from datetime import datetime


def format_price(amount: float, currency: str = "INR") -> str:
    """
    Format price with currency symbol.
    
    Args:
        amount: Price amount
        currency: Currency code
    
    Returns:
        Formatted price string
    """
    symbols = {
        "INR": "₹",
        "USD": "$",
        "EUR": "€",
        "GBP": "£"
    }
    
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def format_order_status(status: str) -> str:
    """
    Format order status with emoji.
    
    Args:
        status: Order status
    
    Returns:
        Formatted status with emoji
    """
    status_emojis = {
        "pending": "🕐 Pending",
        "confirmed": "✅ Confirmed",
        "processing": "⚙️ Processing",
        "shipped": "🚚 Shipped",
        "delivered": "📬 Delivered",
        "cancelled": "❌ Cancelled",
        "refunded": "💰 Refunded"
    }
    
    return status_emojis.get(status.lower(), f"❓ {status.title()}")


def format_date(dt: datetime, format_type: str = "short") -> str:
    """
    Format datetime for display.
    
    Args:
        dt: Datetime object
        format_type: 'short', 'long', or 'relative'
    
    Returns:
        Formatted date string
    """
    if format_type == "short":
        return dt.strftime("%d %b %Y")
    elif format_type == "long":
        return dt.strftime("%d %B %Y, %I:%M %p")
    elif format_type == "relative":
        return _relative_time(dt)
    else:
        return str(dt)


def _relative_time(dt: datetime) -> str:
    """Get relative time string."""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 30:
        return dt.strftime("%d %b %Y")
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def format_product_card(product: Dict[str, Any]) -> str:
    """
    Format product for WhatsApp display.
    
    Args:
        product: Product data
    
    Returns:
        Formatted product card
    """
    lines = [
        f"📦 *{product.get('name', 'Product')}*",
        f"💰 {format_price(product.get('price', 0))}",
    ]
    
    if product.get('brand'):
        lines.append(f"🏷️ {product['brand']}")
    
    desc = product.get('description', '')
    if desc:
        lines.append(f"\n{desc[:150]}{'...' if len(desc) > 150 else ''}")
    
    stock = product.get('stock_quantity', 0)
    if stock > 0:
        lines.append(f"\n✅ In Stock")
    else:
        lines.append(f"\n❌ Out of Stock")
    
    return "\n".join(lines)


def format_cart(cart: Dict[str, Any]) -> str:
    """
    Format cart for WhatsApp display.
    
    Args:
        cart: Cart data
    
    Returns:
        Formatted cart
    """
    if not cart.get('items'):
        return "🛒 Your cart is empty"
    
    lines = ["🛒 *Your Cart*\n"]
    
    for i, item in enumerate(cart['items'], 1):
        lines.append(
            f"{i}. {item['product_name']}\n"
            f"   {format_price(item['product_price'])} × {item['quantity']} = "
            f"{format_price(item['subtotal'])}"
        )
    
    lines.append("\n" + "─" * 20)
    lines.append(f"*Total:* {format_price(cart.get('subtotal', 0))}")
    lines.append(f"*Items:* {cart.get('total_items', 0)}")
    
    return "\n".join(lines)


def format_order_confirmation(order: Dict[str, Any]) -> str:
    """
    Format order confirmation message.
    
    Args:
        order: Order data
    
    Returns:
        Formatted confirmation
    """
    lines = [
        "🎉 *Order Confirmed!*\n",
        f"*Order #:* {order.get('order_number', 'N/A')}",
        f"*Status:* {format_order_status(order.get('status', 'pending'))}",
        "",
        "*Items:*"
    ]
    
    for item in order.get('items', []):
        lines.append(f"• {item['product_name']} × {item['quantity']}")
    
    lines.extend([
        "",
        "─" * 20,
        f"*Subtotal:* {format_price(order.get('subtotal', 0))}",
        f"*Shipping:* {format_price(order.get('shipping_fee', 0))}",
        f"*Tax:* {format_price(order.get('tax', 0))}",
        f"*Total:* {format_price(order.get('total', 0))}",
        "",
        f"*Payment:* {order.get('payment_method', 'COD').upper()}"
    ])
    
    if order.get('shipping_address'):
        addr = order['shipping_address']
        lines.extend([
            "",
            "*Delivery Address:*",
            addr.get('name', ''),
            addr.get('address_line1', ''),
            f"{addr.get('city', '')}, {addr.get('state', '')} - {addr.get('postal_code', '')}"
        ])
    
    return "\n".join(lines)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to max length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
