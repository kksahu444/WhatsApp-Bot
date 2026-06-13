"""
Logging Middleware
Structured logging for all requests
"""

import logging
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.config.settings import settings
from backend.utils.security import redact_pii

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Start timer
        start_time = time.time()
        
        # Add request ID to state
        request.state.request_id = request_id
        
        # Log request
        self._log_request(request, request_id)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            self._log_response(request, response, request_id, duration_ms)
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._log_error(request, e, request_id, duration_ms)
            raise
    
    def _log_request(self, request: Request, request_id: str):
        """Log incoming request."""
        # Get safe headers (redact sensitive info)
        safe_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in ["authorization", "x-api-key", "cookie"]
        }
        
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "unknown")[:100]
        }
        
        if settings.DEBUG:
            log_data["headers"] = safe_headers
        
        logger.info(f"Request: {log_data}")
    
    def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        duration_ms: float
    ):
        """Log outgoing response."""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2)
        }
        
        # Log level based on status code
        if response.status_code >= 500:
            logger.error(f"Response: {log_data}")
        elif response.status_code >= 400:
            logger.warning(f"Response: {log_data}")
        else:
            logger.info(f"Response: {log_data}")
    
    def _log_error(
        self,
        request: Request,
        error: Exception,
        request_id: str,
        duration_ms: float
    ):
        """Log error response."""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "error": str(error),
            "error_type": type(error).__name__,
            "duration_ms": round(duration_ms, 2)
        }
        
        logger.error(f"Error: {log_data}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP, handling proxies."""
        # Check forwarded header
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")
