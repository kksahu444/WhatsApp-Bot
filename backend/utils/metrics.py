"""
Prometheus Metrics
Application metrics for monitoring
"""

import logging
from typing import Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST
)
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# =============================================================================
# METRICS DEFINITIONS
# =============================================================================

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Business metrics
MESSAGES_PROCESSED = Counter(
    "messages_processed_total",
    "Total messages processed",
    ["intent", "status"]
)

ORDERS_CREATED = Counter(
    "orders_created_total",
    "Total orders created",
    ["payment_method", "status"]
)

CART_OPERATIONS = Counter(
    "cart_operations_total",
    "Cart operations",
    ["operation"]  # add, remove, clear
)

PRODUCT_SEARCHES = Counter(
    "product_searches_total",
    "Product searches",
    ["has_results"]
)

# System metrics
ACTIVE_CONVERSATIONS = Gauge(
    "active_conversations",
    "Currently active conversations"
)

LLM_TOKENS_USED = Counter(
    "llm_tokens_used_total",
    "LLM tokens consumed",
    ["type"]  # input, output
)

LLM_REQUESTS = Counter(
    "llm_requests_total",
    "LLM API requests",
    ["model", "status"]
)

CACHE_HITS = Counter(
    "cache_hits_total",
    "Cache hits",
    ["cache_type"]
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Cache misses",
    ["cache_type"]
)


# =============================================================================
# METRICS MIDDLEWARE
# =============================================================================

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Collect metrics for each request."""
        import time
        
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Start timer
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Get endpoint (normalize path parameters)
        endpoint = self._normalize_path(request.url.path)
        
        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path to reduce cardinality."""
        import re
        
        # Replace UUIDs with placeholder
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path
        )
        
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def record_message_processed(intent: str, success: bool):
    """Record a processed message."""
    MESSAGES_PROCESSED.labels(
        intent=intent,
        status="success" if success else "error"
    ).inc()


def record_order_created(payment_method: str, success: bool):
    """Record an order creation."""
    ORDERS_CREATED.labels(
        payment_method=payment_method,
        status="success" if success else "error"
    ).inc()


def record_cart_operation(operation: str):
    """Record a cart operation."""
    CART_OPERATIONS.labels(operation=operation).inc()


def record_search(has_results: bool):
    """Record a product search."""
    PRODUCT_SEARCHES.labels(
        has_results="yes" if has_results else "no"
    ).inc()


def record_llm_usage(input_tokens: int, output_tokens: int, model: str, success: bool):
    """Record LLM token usage."""
    LLM_TOKENS_USED.labels(type="input").inc(input_tokens)
    LLM_TOKENS_USED.labels(type="output").inc(output_tokens)
    LLM_REQUESTS.labels(
        model=model,
        status="success" if success else "error"
    ).inc()


def record_cache(cache_type: str, hit: bool):
    """Record cache hit/miss."""
    if hit:
        CACHE_HITS.labels(cache_type=cache_type).inc()
    else:
        CACHE_MISSES.labels(cache_type=cache_type).inc()


# =============================================================================
# SETUP
# =============================================================================

def setup_metrics(app: FastAPI):
    """Configure metrics for the application."""
    
    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    # Add metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    logger.info("Prometheus metrics configured at /metrics")
