"""
Pytest Configuration and Fixtures
"""

import asyncio
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    mock.exists.return_value = 0
    return mock


@pytest.fixture
def mock_llm_handler():
    """Mock LLM handler."""
    mock = AsyncMock()
    mock.generate_response.return_value = "Test response"
    return mock


@pytest.fixture
def mock_search_engine():
    """Mock search engine."""
    mock = AsyncMock()
    mock.search.return_value = []
    return mock


@pytest.fixture
def sample_product():
    """Sample product data."""
    return {
        "id": "test-uuid-1",
        "sku": "SKU-001",
        "name": "Test Product",
        "description": "A test product description",
        "price": 150000,
        "category": "Electronics",
        "stock_quantity": 25,
        "image_url": "https://example.com/image.jpg",
        "is_active": True,
    }


@pytest.fixture
def sample_cart():
    """Sample cart data."""
    return {
        "id": "cart-uuid-1",
        "phone": "+6281234567890",
        "items": [
            {
                "product_id": "test-uuid-1",
                "quantity": 2,
                "price": 150000,
            }
        ],
    }


@pytest.fixture
def sample_order():
    """Sample order data."""
    return {
        "id": "order-uuid-1",
        "order_number": "ORD-20240115-A1B2",
        "phone": "+6281234567890",
        "status": "pending",
        "total_amount": 300000,
        "items": [
            {
                "product_id": "test-uuid-1",
                "product_name": "Test Product",
                "quantity": 2,
                "unit_price": 150000,
            }
        ],
    }


@pytest.fixture
def sample_message():
    """Sample WhatsApp message."""
    return {
        "phone": "+6281234567890",
        "message": "cari sepatu nike",
        "message_id": "msg-123",
        "timestamp": 1705312200,
    }
