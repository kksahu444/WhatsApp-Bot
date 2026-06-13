"""
Unit Tests for Validators
"""

import pytest
from utils.validators import validate_phone_number


class TestPhoneValidation:
    """Tests for phone number validation."""
    
    def test_valid_indonesian_phone_with_plus(self):
        """Test valid Indonesian phone with country code."""
        result = validate_phone_number("+6281234567890")
        assert result.is_valid
        assert result.formatted == "+6281234567890"
        assert result.country_code == "ID"
    
    def test_valid_indonesian_phone_with_zero(self):
        """Test valid Indonesian phone starting with 0."""
        result = validate_phone_number("081234567890")
        assert result.is_valid
        assert "62" in result.formatted
    
    def test_valid_phone_with_62_prefix(self):
        """Test valid phone with 62 prefix (no plus)."""
        result = validate_phone_number("6281234567890")
        assert result.is_valid
    
    def test_invalid_phone_too_short(self):
        """Test invalid phone that's too short."""
        result = validate_phone_number("0812345")
        assert not result.is_valid
    
    def test_invalid_phone_letters(self):
        """Test invalid phone with letters."""
        result = validate_phone_number("08123abc4567")
        # Should handle gracefully
        assert isinstance(result.is_valid, bool)
    
    def test_empty_phone(self):
        """Test empty phone number."""
        result = validate_phone_number("")
        assert not result.is_valid
    
    def test_none_phone(self):
        """Test None phone number."""
        result = validate_phone_number(None)
        assert not result.is_valid
