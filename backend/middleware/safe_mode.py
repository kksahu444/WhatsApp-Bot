"""
Safe Mode Middleware
Kill switch to disable LLM responses
"""

import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class SafeModeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle safe mode (kill switch).
    When enabled, bypasses LLM and returns fallback responses.
    """
    
    # Endpoints that should bypass safe mode checks
    BYPASS_PATHS = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/products",  # Product listing should still work
        "/api/v1/support",   # Support should still work
    ]
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Check safe mode and process request."""
        # Check if safe mode is enabled
        safe_mode = await self._check_safe_mode(request)
        
        # Add to request state
        request.state.safe_mode = safe_mode
        
        # Bypass for certain paths
        if self._should_bypass(request.url.path):
            return await call_next(request)
        
        # If safe mode and it's a message/webhook endpoint
        if safe_mode and self._is_message_endpoint(request.url.path):
            logger.warning(f"Safe mode active - limiting response for {request.url.path}")
            # Still process but LLM handlers will check safe_mode flag
        
        return await call_next(request)
    
    async def _check_safe_mode(self, request: Request) -> bool:
        """Check if safe mode is enabled."""
        # Check environment setting
        if settings.SAFE_MODE:
            return True
        
        # Check Redis for dynamic toggle
        try:
            if hasattr(request.app.state, 'redis') and request.app.state.redis:
                redis_flag = await request.app.state.redis.get("safe_mode")
                if redis_flag and redis_flag.lower() == "true":
                    return True
        except Exception as e:
            logger.error(f"Error checking safe mode in Redis: {e}")
        
        return False
    
    def _should_bypass(self, path: str) -> bool:
        """Check if path should bypass safe mode."""
        for bypass_path in self.BYPASS_PATHS:
            if path.startswith(bypass_path):
                return True
        return False
    
    def _is_message_endpoint(self, path: str) -> bool:
        """Check if endpoint handles messages."""
        message_paths = [
            "/webhook",
            "/api/v1/message",
            "/api/v1/chat"
        ]
        for msg_path in message_paths:
            if msg_path in path:
                return True
        return False


async def enable_safe_mode(request: Request):
    """Enable safe mode via Redis."""
    try:
        if hasattr(request.app.state, 'redis') and request.app.state.redis:
            await request.app.state.redis.set("safe_mode", "true")
            logger.warning("Safe mode ENABLED")
            return True
    except Exception as e:
        logger.error(f"Failed to enable safe mode: {e}")
    return False


async def disable_safe_mode(request: Request):
    """Disable safe mode via Redis."""
    try:
        if hasattr(request.app.state, 'redis') and request.app.state.redis:
            await request.app.state.redis.delete("safe_mode")
            logger.info("Safe mode DISABLED")
            return True
    except Exception as e:
        logger.error(f"Failed to disable safe mode: {e}")
    return False


async def get_safe_mode_status(request: Request) -> dict:
    """Get current safe mode status."""
    env_setting = settings.SAFE_MODE
    redis_setting = False
    
    try:
        if hasattr(request.app.state, 'redis') and request.app.state.redis:
            redis_flag = await request.app.state.redis.get("safe_mode")
            redis_setting = redis_flag and redis_flag.lower() == "true"
    except Exception:
        pass
    
    return {
        "safe_mode_active": env_setting or redis_setting,
        "env_setting": env_setting,
        "redis_setting": redis_setting
    }
