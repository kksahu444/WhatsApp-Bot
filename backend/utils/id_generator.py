"""
Order ID Generator.

Format: ORD-YYYYMMDD-XXXXXX
Example: ORD-20251205-A3F9B2
"""

import secrets
from datetime import datetime


def generate_order_id() -> str:
    """
    Generate unique order ID with date and random hex.
    
    Format: ORD-YYYYMMDD-XXXXXX
    - ORD: Order prefix
    - YYYYMMDD: Date part
    - XXXXXX: 6 random hex characters
    
    Returns:
        str: Unique order ID
    """
    date_part = datetime.utcnow().strftime("%Y%m%d")
    random_part = secrets.token_hex(3).upper()  # 6 hex chars
    return f"ORD-{date_part}-{random_part}"


def generate_idempotency_key(user_phone: str) -> str:
    """
    Generate idempotency key for order deduplication.
    
    Uses minute precision to allow retries but prevent duplicates.
    
    Args:
        user_phone: User's phone number
        
    Returns:
        str: Idempotency key
    """
    timestamp_key = datetime.utcnow().strftime("%Y%m%d%H%M")
    return f"{user_phone}:{timestamp_key}"
