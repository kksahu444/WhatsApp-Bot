from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from backend.config.settings import get_settings
from backend.database.redis_client import redis_service
from loguru import logger
from typing import Optional

settings = get_settings()

def get_user_identifier(request: Request) -> str:
    """
    Extract user identifier from request.
    Priority: phone number > IP address
    """
    # Try to get phone from webhook payload
    if request.method == "POST":
        try:
            body = request.state.body if hasattr(request.state, 'body') else None
            if body and 'phone' in body:
                return f"user:{body['phone']}"
        except:
            pass
    
    # Fallback to IP address
    return f"ip:{get_remote_address(request)}"

# Initialize limiter with Redis backend
limiter = Limiter(
    key_func=get_user_identifier,
    storage_uri=settings.redis_connection_url,
    enabled=settings.rate_limit_enabled
)

class RateLimitMiddleware:
    """Custom rate limit middleware with Redis."""
    
    def __init__(self):
        self.rate_limit = settings.rate_limit_per_minute
        self.burst_limit = settings.rate_limit_burst
        self.window = 60  # 1 minute window
    
    async def check_rate_limit(self, user_id: str) -> tuple[bool, Optional[int]]:
        """
        Check if user exceeded rate limit.
        Returns: (is_allowed, retry_after_seconds)
        """
        key = f"rate_limit:{user_id}"
        
        try:
            # Get current count
            current = await redis_service.get(key)
            
            if current is None:
                # First request in window
                await redis_service.set_with_expiry(key, "1", self.window)
                return True, None
            
            count = int(current)
            
            # Check if limit exceeded
            if count >= self.rate_limit:
                # Get TTL for retry_after
                ttl = await redis_service.client.ttl(key)
                logger.warning(f"Rate limit exceeded for {user_id}: {count}/{self.rate_limit}")
                return False, ttl
            
            # Increment counter
            await redis_service.increment(key)
            return True, None
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fail open - allow request if Redis is down
            return True, None
    
    async def get_user_stats(self, user_id: str) -> dict:
        """Get rate limit stats for user."""
        key = f"rate_limit:{user_id}"
        
        try:
            count = await redis_service.get(key)
            ttl = await redis_service.client.ttl(key) if count else 0
            
            return {
                "requests_made": int(count) if count else 0,
                "limit": self.rate_limit,
                "remaining": max(0, self.rate_limit - int(count)) if count else self.rate_limit,
                "reset_in_seconds": ttl if ttl > 0 else self.window
            }
        except Exception as e:
            logger.error(f"Error getting rate limit stats: {e}")
            return {
                "requests_made": 0,
                "limit": self.rate_limit,
                "remaining": self.rate_limit,
                "reset_in_seconds": self.window
            }

# Global instance
rate_limiter = RateLimitMiddleware()

async def rate_limit_dependency(request: Request):
    """
    FastAPI dependency for rate limiting.
    Usage: @app.post("/webhook", dependencies=[Depends(rate_limit_dependency)])
    """
    user_id = get_user_identifier(request)
    is_allowed, retry_after = await rate_limiter.check_rate_limit(user_id)
    
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for {user_id}")
        raise RateLimitExceeded(f"Rate limit exceeded. Retry after {retry_after} seconds.")
    
    return True
