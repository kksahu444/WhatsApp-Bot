"""
Validators
Input validation utilities
"""

import re
from typing import Optional, Tuple

import phonenumbers
from phonenumbers import NumberParseException


def validate_phone_number(
    phone: str,
    default_region: str = "IN"
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and normalize phone number.
    
    Args:
        phone: Phone number string
        default_region: Default region code
    
    Returns:
        Tuple of (is_valid, normalized_number, error_message)
    """
    try:
        # Clean the input
        phone = phone.strip()
        
        # Parse the number
        parsed = phonenumbers.parse(phone, default_region)
        
        # Check if valid
        if not phonenumbers.is_valid_number(parsed):
            return False, None, "Invalid phone number"
        
        # Format to E.164
        normalized = phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164
        )
        
        return True, normalized, None
        
    except NumberParseException as e:
        return False, None, f"Could not parse phone number: {e}"


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email address.
    
    Args:
        email: Email address
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not email:
        return False, "Email is required"
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, None


def validate_postal_code(
    postal_code: str,
    country: str = "IN"
) -> Tuple[bool, Optional[str]]:
    """
    Validate postal code.
    
    Args:
        postal_code: Postal code
        country: Country code
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    patterns = {
        "IN": r'^\d{6}$',  # India: 6 digits
        "US": r'^\d{5}(-\d{4})?$',  # US: 5 or 9 digits
        "UK": r'^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$',  # UK format
    }
    
    pattern = patterns.get(country, r'^\d{4,10}$')
    
    if not postal_code:
        return False, "Postal code is required"
    
    if not re.match(pattern, postal_code, re.IGNORECASE):
        return False, f"Invalid postal code format for {country}"
    
    return True, None


def validate_price(price: float) -> Tuple[bool, Optional[str]]:
    """
    Validate price value.
    
    Args:
        price: Price value
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if price is None:
        return False, "Price is required"
    
    if price < 0:
        return False, "Price cannot be negative"
    
    if price > 10000000:  # 1 crore limit
        return False, "Price exceeds maximum allowed value"
    
    return True, None


def validate_quantity(quantity: int) -> Tuple[bool, Optional[str]]:
    """
    Validate quantity value.
    
    Args:
        quantity: Quantity value
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if quantity is None:
        return False, "Quantity is required"
    
    if quantity < 1:
        return False, "Quantity must be at least 1"
    
    if quantity > 99:
        return False, "Maximum quantity is 99"
    
    return True, None


def sanitize_text(text: str, max_length: int = 1000) -> str:
    """
    Sanitize text input.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # Limit length
    text = text[:max_length]
    
    # Strip whitespace
    text = text.strip()
    
    return text


def validate_search_query(query: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate and sanitize search query.
    
    Args:
        query: Search query
    
    Returns:
        Tuple of (is_valid, sanitized_query, error_message)
    """
    if not query:
        return False, "", "Search query is required"
    
    # Sanitize
    query = sanitize_text(query, max_length=200)
    
    if len(query) < 2:
        return False, query, "Search query too short"
    
    # Remove special characters that might cause issues
    query = re.sub(r'[<>{}|\\^~\[\]`]', '', query)
    
    return True, query, None
