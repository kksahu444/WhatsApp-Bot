"""
Error Handler
Global error handling middleware with LLM timeout and user-friendly messages.
"""

import asyncio
import functools
import logging
import traceback
from typing import Callable, Any, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger as loguru_logger

from backend.config.settings import settings

logger = logging.getLogger(__name__)


# ============================================
# Configuration
# ============================================
LLM_TIMEOUT_SECONDS = 10
DEFAULT_ERROR_MESSAGE = "⚠️ System is currently experiencing heavy load. Please try again in 2 minutes."
REDIS_ERROR_MESSAGE = "⚠️ Service temporarily unavailable. Please try again shortly."
LLM_TIMEOUT_MESSAGE = "⚠️ I'm thinking too hard! Please try a simpler question."


# ============================================
# Error Categories
# ============================================
class ErrorCategory:
    """Categorize errors for appropriate responses."""
    REDIS = "redis"
    DATABASE = "database"
    LLM_TIMEOUT = "llm_timeout"
    LLM_ERROR = "llm_error"
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


def categorize_error(error: Exception) -> str:
    """Categorize an exception for appropriate handling."""
    error_type = type(error).__name__
    error_msg = str(error).lower()
    
    if "redis" in error_type.lower() or "redis" in error_msg:
        return ErrorCategory.REDIS
    if "supabase" in error_type.lower() or "postgres" in error_msg:
        return ErrorCategory.DATABASE
    if isinstance(error, asyncio.TimeoutError) or "timeout" in error_msg:
        return ErrorCategory.LLM_TIMEOUT
    if "gemini" in error_msg or "generative" in error_msg:
        return ErrorCategory.LLM_ERROR
    if "rate" in error_msg and "limit" in error_msg:
        return ErrorCategory.RATE_LIMIT
    if "validation" in error_type.lower():
        return ErrorCategory.VALIDATION
    
    return ErrorCategory.UNKNOWN


def get_user_friendly_message(category: str) -> str:
    """Get user-friendly error message based on category."""
    messages = {
        ErrorCategory.REDIS: REDIS_ERROR_MESSAGE,
        ErrorCategory.DATABASE: "⚠️ Database temporarily unavailable. Please try again.",
        ErrorCategory.LLM_TIMEOUT: LLM_TIMEOUT_MESSAGE,
        ErrorCategory.LLM_ERROR: "⚠️ AI service is busy. Please try again.",
        ErrorCategory.RATE_LIMIT: "⚠️ Too many requests. Please wait a moment.",
        ErrorCategory.VALIDATION: "❌ Invalid input. Please check your message.",
        ErrorCategory.UNKNOWN: DEFAULT_ERROR_MESSAGE,
    }
    return messages.get(category, DEFAULT_ERROR_MESSAGE)


# ============================================
# Async Timeout Wrapper
# ============================================
async def with_timeout(coro, timeout: float = LLM_TIMEOUT_SECONDS) -> Any:
    """Execute a coroutine with a timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        loguru_logger.warning(f"⏰ Operation timed out after {timeout}s")
        raise


# ============================================
# Handler Decorator (NEW)
# ============================================
def safe_handler(fallback_response: Optional[str] = None, timeout: Optional[float] = None):
    """
    Decorator for safe handler execution with error catching.
    
    Usage:
        @safe_handler(fallback_response="Sorry, error occurred", timeout=10)
        async def my_handler(phone, message):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                if timeout:
                    return await with_timeout(func(*args, **kwargs), timeout=timeout)
                return await func(*args, **kwargs)
            except asyncio.TimeoutError:
                loguru_logger.error(f"⏰ Handler {func.__name__} timed out")
                return fallback_response or LLM_TIMEOUT_MESSAGE
            except Exception as e:
                category = categorize_error(e)
                loguru_logger.error(
                    f"❌ Handler {func.__name__} failed | "
                    f"Category: {category} | Error: {type(e).__name__}: {e}"
                )
                return fallback_response or get_user_friendly_message(category)
        return wrapper
    return decorator


# ============================================
# Safe Execute Async (NEW)
# ============================================
async def safe_execute_async(
    coro,
    fallback: Any = None,
    operation_name: str = "operation",
    timeout: float = LLM_TIMEOUT_SECONDS
) -> tuple:
    """
    Safely execute a coroutine with timeout and error handling.
    Returns: (result, success, error_message)
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        return (result, True, None)
    except asyncio.TimeoutError:
        loguru_logger.warning(f"⏰ {operation_name} timed out after {timeout}s")
        return (fallback, False, LLM_TIMEOUT_MESSAGE)
    except Exception as e:
        category = categorize_error(e)
        loguru_logger.error(f"❌ {operation_name} failed: {type(e).__name__}: {e}")
        return (fallback, False, get_user_friendly_message(category))


def setup_error_handlers(app: FastAPI):
    """Configure global error handlers."""
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException
    ) -> Response:
        """Handle HTTP exceptions."""
        logger.warning(
            f"HTTP {exc.status_code} at {request.url.path}: {exc.detail}"
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
    ) -> Response:
        """Handle validation errors."""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(f"Validation error at {request.url.path}: {errors}")
        
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "details": errors
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(
        request: Request,
        exc: ValueError
    ) -> Response:
        """Handle value errors."""
        logger.warning(f"Value error at {request.url.path}: {exc}")
        
        return JSONResponse(
            status_code=400,
            content={
                "error": str(exc),
                "type": "value_error"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception
    ) -> Response:
        """Handle all other exceptions."""
        # Log full traceback
        logger.exception(f"Unhandled exception at {request.url.path}")
        
        # In debug mode, include traceback
        if settings.DEBUG:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": str(exc),
                    "traceback": traceback.format_exc()
                }
            )
        
        # In production, hide details
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later."
            }
        )


class ErrorContext:
    """Context manager for error handling with custom messages."""
    
    def __init__(self, operation: str, raise_http: bool = True):
        self.operation = operation
        self.raise_http = raise_http
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            logger.error(f"Error in {self.operation}: {exc_val}")
            
            if self.raise_http:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=500,
                    detail=f"Error in {self.operation}"
                )
        
        return False  # Don't suppress the exception


def safe_execute(func: Callable, default=None, log_error: bool = True):
    """
    Execute a function safely, returning default on error.
    
    Usage:
        result = safe_execute(lambda: risky_operation(), default=[])
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"Safe execute error: {e}")
        return default
