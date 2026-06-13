"""
Unit Tests for Security Utilities
"""

import pytest
from utils.security import (
    hash_phone,
    mask_phone,
    redact_pii,
    sanitize_input,
    generate_order_reference,
    verify_webhook_signature,
)


class TestHashPhone:
    """Tests for phone hashing."""
    
    def test_hash_phone_consistent(self):
        """Test that same phone produces same hash."""
        phone = "+6281234567890"
        hash1 = hash_phone(phone)
        hash2 = hash_phone(phone)
        assert hash1 == hash2
    
    def test_hash_phone_different(self):
        """Test that different phones produce different hashes."""
        hash1 = hash_phone("+6281234567890")
        hash2 = hash_phone("+6281234567891")
        assert hash1 != hash2
    
    def test_hash_phone_empty(self):
        """Test empty phone."""
        result = hash_phone("")
        assert result == ""


class TestMaskPhone:
    """Tests for phone masking."""
    
    def test_mask_phone_indonesian(self):
        """Test Indonesian phone masking."""
        result = mask_phone("+6281234567890")
        assert "****" in result
        assert "7890" in result
    
    def test_mask_phone_without_plus(self):
        """Test phone without plus sign."""
        result = mask_phone("081234567890")
        assert "****" in result
    
    def test_mask_phone_empty(self):
        """Test empty phone."""
        result = mask_phone("")
        assert result == ""


class TestRedactPII:
    """Tests for PII redaction."""
    
    def test_redact_phone_number(self):
        """Test phone number redaction."""
        text = "Call me at 081234567890 please"
        result = redact_pii(text)
        assert "081234567890" not in result
        assert "PHONE_REDACTED" in result
    
    def test_redact_email(self):
        """Test email redaction."""
        text = "Email me at test@example.com"
        result = redact_pii(text)
        assert "test@example.com" not in result
        assert "EMAIL_REDACTED" in result
    
    def test_redact_nothing(self):
        """Test text without PII."""
        text = "Hello, how are you?"
        result = redact_pii(text)
        assert result == text


class TestSanitizeInput:
    """Tests for input sanitization."""
    
    def test_sanitize_normal_text(self):
        """Test normal text."""
        text = "Hello World"
        result = sanitize_input(text)
        assert result == "Hello World"
    
    def test_sanitize_with_control_chars(self):
        """Test text with control characters."""
        text = "Hello\x00World"
        result = sanitize_input(text)
        assert "\x00" not in result
    
    def test_sanitize_max_length(self):
        """Test max length truncation."""
        text = "a" * 2000
        result = sanitize_input(text, max_length=1000)
        assert len(result) == 1000


class TestGenerateOrderReference:
    """Tests for order reference generation."""
    
    def test_order_reference_format(self):
        """Test order reference format."""
        ref = generate_order_reference()
        assert ref.startswith("ORD-")
        assert len(ref) == 21  # ORD-YYYYMMDD-XXXXXXXX
    
    def test_order_reference_unique(self):
        """Test that references are unique."""
        ref1 = generate_order_reference()
        ref2 = generate_order_reference()
        assert ref1 != ref2
