"""
Unit Tests for Formatters
"""

import pytest
from datetime import datetime
from utils.formatters import (
    format_price,
    format_date,
    format_order_status,
    format_cart_summary,
    format_product_card,
)


class TestFormatPrice:
    """Tests for price formatting."""
    
    def test_format_price_basic(self):
        """Test basic price formatting."""
        result = format_price(150000)
        assert "150" in result
        assert "Rp" in result
    
    def test_format_price_with_thousands(self):
        """Test price with thousand separators."""
        result = format_price(1500000)
        assert "1.500.000" in result or "1,500,000" in result
    
    def test_format_price_zero(self):
        """Test zero price."""
        result = format_price(0)
        assert "0" in result
    
    def test_format_price_decimal(self):
        """Test price with decimals."""
        result = format_price(150000.50)
        assert "150" in result


class TestFormatDate:
    """Tests for date formatting."""
    
    def test_format_date_datetime(self):
        """Test datetime formatting."""
        dt = datetime(2024, 1, 15, 14, 30)
        result = format_date(dt)
        assert "15" in result
        assert "2024" in result or "Jan" in result
    
    def test_format_date_string(self):
        """Test string date formatting."""
        result = format_date("2024-01-15T14:30:00")
        assert "15" in result


class TestFormatOrderStatus:
    """Tests for order status formatting."""
    
    def test_format_status_pending(self):
        """Test pending status."""
        result = format_order_status("pending")
        assert "Menunggu" in result or "pending" in result.lower()
    
    def test_format_status_confirmed(self):
        """Test confirmed status."""
        result = format_order_status("confirmed")
        assert "Dikonfirmasi" in result or "confirmed" in result.lower()
    
    def test_format_status_unknown(self):
        """Test unknown status."""
        result = format_order_status("unknown_status")
        assert "unknown" in result.lower()


class TestFormatCartSummary:
    """Tests for cart summary formatting."""
    
    def test_format_cart_with_items(self):
        """Test cart with items."""
        items = [
            {"name": "Product A", "quantity": 2, "price": 100000},
            {"name": "Product B", "quantity": 1, "price": 150000},
        ]
        result = format_cart_summary(items, 350000)
        assert "Product A" in result
        assert "Product B" in result
        assert "350" in result
    
    def test_format_empty_cart(self):
        """Test empty cart."""
        result = format_cart_summary([], 0)
        assert "kosong" in result.lower() or "empty" in result.lower()


class TestFormatProductCard:
    """Tests for product card formatting."""
    
    def test_format_product_card(self):
        """Test product card formatting."""
        product = {
            "name": "Premium Headphones",
            "price": 350000,
            "description": "High quality headphones",
            "stock_quantity": 10,
        }
        result = format_product_card(product)
        assert "Premium Headphones" in result
        assert "350" in result
