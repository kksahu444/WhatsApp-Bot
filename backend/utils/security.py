"""
Security Utilities
Phone hashing, PII redaction, and security helpers
"""

import hashlib
import hmac
import re
import secrets
from typing import Optional

from backend.config.settings import get_settings


settings = get_settings()


# =============================================================================
# PHONE NUMBER HASHING
# =============================================================================

def hash_phone(phone: str) -> str:
    """
    Hash phone number for privacy-safe storage/logging.
    Uses HMAC-SHA256 with app secret key.
    """
    if not phone:
        return ""
    
    # Normalize phone number
    normalized = re.sub(r'\D', '', phone)
    
    # Use HMAC with secret key
    key = settings.jwt_secret_key.encode()
    message = normalized.encode()
    
    hashed = hmac.new(key, message, hashlib.sha256).hexdigest()
    
    # Return truncated hash
    return hashed[:16]


# Alias for backwards compatibility
hash_phone_number = hash_phone


def mask_phone(phone: str) -> str:
    """
    Mask phone number for display (show last 4 digits).
    Example: +6281234567890 → +62****7890
    """
    if not phone:
        return ""
    
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) < 4:
        return '*' * len(digits)
    
    # Keep country code + last 4 digits
    if phone.startswith('+'):
        if len(digits) > 6:
            return f"+{digits[:2]}****{digits[-4:]}"
        return f"+{digits[:2]}***{digits[-2:]}"
    
    return f"****{digits[-4:]}"


# =============================================================================
# PII REDACTION
# =============================================================================

def redact_pii(text: str) -> str:
    """
    Redact personally identifiable information from text.
    Useful for logging and analytics.
    """
    if not text:
        return text
    
    result = text
    
    # Redact phone numbers (various formats)
    # Indonesian format: 081234567890, +6281234567890
    result = re.sub(
        r'\+?62\s*\d{9,12}|\b0\d{9,12}\b',
        '[PHONE_REDACTED]',
        result
    )
    
    # Redact email addresses
    result = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL_REDACTED]',
        result
    )
    
    # Redact credit card numbers (basic pattern)
    result = re.sub(
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        '[CARD_REDACTED]',
        result
    )
    
    # Redact NIK (Indonesian ID number - 16 digits)
    result = re.sub(
        r'\b\d{16}\b',
        '[NIK_REDACTED]',
        result
    )
    
    # Redact addresses (basic patterns)
    # Jl./Jalan, RT/RW, Kec./Kelurahan, etc.
    result = re.sub(
        r'(?i)\b(jl\.?|jalan)\s+[^,\n]{5,50}',
        '[ADDRESS_REDACTED]',
        result
    )
    
    return result


def redact_for_logging(data: dict, sensitive_keys: list = None) -> dict:
    """
    Redact sensitive keys from a dictionary for safe logging.
    """
    if not data:
        return data
    
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'token', 'api_key', 'secret',
            'phone', 'email', 'address', 'nik', 'card',
            'credit_card', 'phone_number', 'auth'
        ]
    
    result = {}
    
    for key, value in data.items():
        lower_key = key.lower()
        
        # Check if key is sensitive
        is_sensitive = any(
            sensitive in lower_key 
            for sensitive in sensitive_keys
        )
        
        if is_sensitive:
            if isinstance(value, str):
                result[key] = '[REDACTED]'
            else:
                result[key] = '[REDACTED]'
        elif isinstance(value, dict):
            result[key] = redact_for_logging(value, sensitive_keys)
        elif isinstance(value, str):
            result[key] = redact_pii(value)
        else:
            result[key] = value
    
    return result


# =============================================================================
# WEBHOOK SECURITY
# =============================================================================

def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str = None
) -> bool:
    """
    Verify webhook signature from WhatsApp/Meta.
    Uses HMAC-SHA256.
    """
    if not signature:
        return False
    
    if secret is None:
        secret = settings.whatsapp_webhook_secret
    
    if not secret:
        # No secret configured - skip verification
        return True
    
    # Parse signature (format: sha256=<hash>)
    if '=' in signature:
        algo, received_hash = signature.split('=', 1)
    else:
        received_hash = signature
    
    # Calculate expected hash
    expected_hash = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison
    return hmac.compare_digest(expected_hash, received_hash)


def generate_webhook_secret() -> str:
    """Generate a secure random webhook secret."""
    return secrets.token_urlsafe(32)


# =============================================================================
# TOKEN UTILITIES
# =============================================================================

def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def generate_order_reference() -> str:
    """Generate a unique order reference number."""
    import time
    
    # Format: ORD-YYYYMMDD-XXXXX
    date_part = time.strftime('%Y%m%d')
    random_part = secrets.token_hex(4).upper()
    
    return f"ORD-{date_part}-{random_part}"


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return secrets.token_urlsafe(16)


# =============================================================================
# PASSWORD / API KEY HASHING
# =============================================================================

def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """Verify an API key against its hash."""
    provided_hash = hash_api_key(provided_key)
    return hmac.compare_digest(provided_hash, stored_hash)


# =============================================================================
# INPUT SANITIZATION
# =============================================================================

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input text.
    Removes control characters and limits length.
    """
    if not text:
        return ""
    
    # Remove control characters except newline and tab
    sanitized = ''.join(
        char for char in text 
        if char in '\n\t' or (ord(char) >= 32 and ord(char) != 127)
    )
    
    # Normalize whitespace
    sanitized = ' '.join(sanitized.split())
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()


def is_safe_filename(filename: str) -> bool:
    """Check if a filename is safe (no path traversal)."""
    if not filename:
        return False
    
    # Disallow path separators and special characters
    dangerous = ['..', '/', '\\', '\x00', ':', '*', '?', '"', '<', '>', '|']
    
    return not any(char in filename for char in dangerous)


# =============================================================================
# RATE LIMIT KEY GENERATION
# =============================================================================

def get_rate_limit_key(phone: str, action: str) -> str:
    """
    Generate a rate limit key for a phone/action combination.
    Uses hashed phone for privacy.
    """
    phone_hash = hash_phone(phone)
    return f"ratelimit:{action}:{phone_hash}"


def get_conversation_key(phone: str) -> str:
    """Generate a conversation cache key."""
    phone_hash = hash_phone(phone)
    return f"conversation:{phone_hash}"
