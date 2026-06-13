from database.redis_client import redis_service
from backend.config.settings import get_settings
from loguru import logger
from typing import Optional
import json
import hashlib

settings = get_settings()

class IdempotencyService:
    """
    Idempotency service using Redis.
    Prevents duplicate operations (e.g., duplicate orders).
    """
    
    def __init__(self):
        self.ttl = settings.idempotency_ttl  # 24 hours
        self.prefix = "idemp"
    
    def _generate_key(self, operation: str, identifier: str) -> str:
        """Generate idempotency key."""
        return f"{self.prefix}:{operation}:{identifier}"
    
    def _hash_payload(self, payload: dict) -> str:
        """Hash payload for idempotency check."""
        payload_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_str.encode()).hexdigest()[:16]
    
    async def check_idempotency(
        self, 
        operation: str, 
        identifier: str,
        payload: Optional[dict] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check if operation already executed.
        
        Returns:
            (is_duplicate, existing_result)
        """
        # Generate key
        if payload:
            payload_hash = self._hash_payload(payload)
            key = self._generate_key(operation, f"{identifier}:{payload_hash}")
        else:
            key = self._generate_key(operation, identifier)
        
        try:
            # Check if key exists
            existing_result = await redis_service.get(key)
            
            if existing_result:
                logger.warning(f"Duplicate operation detected: {operation} for {identifier}")
                return True, existing_result
            
            return False, None
            
        except Exception as e:
            logger.error(f"Idempotency check error: {e}")
            # Fail open - allow operation if Redis is down
            return False, None
    
    async def store_result(
        self,
        operation: str,
        identifier: str,
        result: str,
        payload: Optional[dict] = None
    ):
        """Store operation result for idempotency."""
        # Generate key
        if payload:
            payload_hash = self._hash_payload(payload)
            key = self._generate_key(operation, f"{identifier}:{payload_hash}")
        else:
            key = self._generate_key(operation, identifier)
        
        try:
            await redis_service.set_with_expiry(key, result, self.ttl)
            logger.info(f"Stored idempotency key: {key}")
        except Exception as e:
            logger.error(f"Error storing idempotency result: {e}")
    
    async def delete_key(self, operation: str, identifier: str):
        """Delete idempotency key (for testing or manual intervention)."""
        key = self._generate_key(operation, identifier)
        try:
            await redis_service.delete(key)
            logger.info(f"Deleted idempotency key: {key}")
        except Exception as e:
            logger.error(f"Error deleting idempotency key: {e}")
    
    async def check_and_store(
        self,
        operation: str,
        identifier: str,
        result: str,
        payload: Optional[dict] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Atomic check and store.
        
        Returns:
            (is_duplicate, existing_result_or_new_result)
        """
        is_duplicate, existing_result = await self.check_idempotency(
            operation, identifier, payload
        )
        
        if is_duplicate:
            return True, existing_result
        
        # Store new result
        await self.store_result(operation, identifier, result, payload)
        return False, result

# Singleton instance
idempotency_service = IdempotencyService()


# Decorator for idempotent functions
def idempotent(operation: str):
    """
    Decorator to make functions idempotent.
    
    Usage:
        @idempotent("create_order")
        async def create_order(user_phone: str, items: list):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract identifier (assumes first arg is identifier)
            identifier = args[0] if args else kwargs.get('user_phone', 'unknown')
            payload = kwargs if kwargs else None
            
            # Check idempotency
            is_duplicate, existing_result = await idempotency_service.check_idempotency(
                operation, identifier, payload
            )
            
            if is_duplicate:
                logger.info(f"Returning cached result for {operation}:{identifier}")
                return existing_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store result
            await idempotency_service.store_result(
                operation, identifier, str(result), payload
            )
            
            return result
        
        return wrapper
    return decorator
