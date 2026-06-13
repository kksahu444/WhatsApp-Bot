import redis.asyncio as redis
from redis.asyncio import Redis
from typing import Optional
from loguru import logger
from backend.config.settings import settings

# Global Redis client
_redis_client: Optional[Redis] = None

async def get_redis_client() -> Redis:
    """Get or create Redis connection."""
    global _redis_client
    
    if _redis_client is None:
        try:
            _redis_client = await redis.from_url(
                settings.redis_connection_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50
            )
            # Test connection
            await _redis_client.ping()
            logger.info(f"✅ Redis connected: {settings.redis_host}:{settings.redis_port}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    return _redis_client

async def close_redis_client():
    """Close Redis connection gracefully."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis connection closed")
        _redis_client = None

class RedisService:
    """Redis operations wrapper."""
    
    def __init__(self):
        self.client: Optional[Redis] = None
    
    async def initialize(self):
        """Initialize Redis client."""
        self.client = await get_redis_client()
    
    async def set_with_expiry(self, key: str, value: str, ttl: int):
        """Set key with TTL."""
        if not self.client:
            await self.initialize()
        await self.client.setex(key, ttl, value)
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self.client:
            await self.initialize()
        return await self.client.get(key)
    
    async def delete(self, key: str):
        """Delete key."""
        if not self.client:
            await self.initialize()
        await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.client:
            await self.initialize()
        return await self.client.exists(key) > 0
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        if not self.client:
            await self.initialize()
        return await self.client.incrby(key, amount)
    
    async def set_hash(self, key: str, mapping: dict):
        """Set hash map."""
        if not self.client:
            await self.initialize()
        await self.client.hset(key, mapping=mapping)
    
    async def get_hash(self, key: str) -> dict:
        """Get hash map."""
        if not self.client:
            await self.initialize()
        return await self.client.hgetall(key)
    
    async def health_check(self) -> bool:
        """Check Redis health."""
        try:
            if not self.client:
                await self.initialize()
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

# Singleton instance
redis_service = RedisService()
