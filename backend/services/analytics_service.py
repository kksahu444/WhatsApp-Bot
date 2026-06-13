"""
Analytics Service
Metrics logging and tracking with non-blocking support.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from backend.config.settings import settings

logger = logging.getLogger(__name__)


# Event type constants for consistency
class EventType:
    MESSAGE_RECEIVED = "message"
    SEARCH_QUERY = "search"
    PRODUCT_VIEWED = "product_view"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    CART_VIEWED = "cart_view"
    CHECKOUT_START = "checkout_start"
    CHECKOUT_COMPLETE = "checkout"
    ORDER_PLACED = "order_placed"
    PAYMENT_RECEIVED = "payment"
    ABANDONED_CART_REMINDER = "abandoned_cart_reminder"
    SUPPORT_REQUESTED = "support_request"
    ERROR_OCCURRED = "error"


class AnalyticsService:
    """Service for logging and retrieving analytics."""
    
    def __init__(self, supabase_client, redis_client=None):
        self.db = supabase_client
        self.redis = redis_client
    
    async def log_event(
        self,
        event_type: str,
        user_phone_hash: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None
    ):
        """
        Log an analytics event.
        
        Args:
            event_type: Type of event (e.g., 'search', 'add_to_cart', 'order')
            user_phone_hash: Hashed phone number
            event_data: Additional event data
        """
        if not settings.ENABLE_ANALYTICS:
            return
        
        try:
            await self.db.log_analytics_event({
                "event_type": event_type,
                "user_phone_hash": user_phone_hash,
                "event_data": event_data or {}
            })
            
            # Update real-time counters in Redis
            if self.redis:
                today = datetime.utcnow().strftime("%Y-%m-%d")
                await self.redis.client.incr(f"analytics:{event_type}:{today}")
                await self.redis.client.expire(
                    f"analytics:{event_type}:{today}",
                    86400 * 30  # Keep 30 days
                )
            
        except Exception as e:
            logger.error(f"Failed to log analytics event: {e}")
    
    async def log_search(
        self,
        query: str,
        results_count: int,
        user_phone_hash: Optional[str] = None
    ):
        """Log a product search."""
        await self.log_event(
            "search",
            user_phone_hash,
            {"query": query, "results_count": results_count}
        )
    
    async def log_product_view(
        self,
        product_id: str,
        user_phone_hash: Optional[str] = None
    ):
        """Log a product view."""
        await self.log_event(
            "product_view",
            user_phone_hash,
            {"product_id": product_id}
        )
    
    async def log_add_to_cart(
        self,
        product_id: str,
        quantity: int,
        user_phone_hash: Optional[str] = None
    ):
        """Log an add to cart action."""
        await self.log_event(
            "add_to_cart",
            user_phone_hash,
            {"product_id": product_id, "quantity": quantity}
        )
    
    async def log_checkout(
        self,
        order_id: str,
        order_total: float,
        item_count: int,
        user_phone_hash: Optional[str] = None
    ):
        """Log a checkout/order."""
        await self.log_event(
            "checkout",
            user_phone_hash,
            {
                "order_id": order_id,
                "order_total": order_total,
                "item_count": item_count
            }
        )
    
    async def log_message(
        self,
        intent: str,
        user_phone_hash: Optional[str] = None
    ):
        """Log a message/conversation event."""
        await self.log_event(
            "message",
            user_phone_hash,
            {"intent": intent}
        )
    
    async def get_daily_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get daily statistics for the past N days.
        
        Args:
            days: Number of days to retrieve
        
        Returns:
            Dict with daily stats
        """
        stats = {
            "dates": [],
            "messages": [],
            "searches": [],
            "orders": [],
            "revenue": []
        }
        
        if not self.redis:
            return stats
        
        today = datetime.utcnow()
        
        for i in range(days):
            day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            stats["dates"].append(day)
            
            # Get counts from Redis
            messages = await self.redis.client.get(f"analytics:message:{day}")
            searches = await self.redis.client.get(f"analytics:search:{day}")
            orders = await self.redis.client.get(f"analytics:checkout:{day}")
            
            stats["messages"].append(int(messages) if messages else 0)
            stats["searches"].append(int(searches) if searches else 0)
            stats["orders"].append(int(orders) if orders else 0)
        
        # Reverse to chronological order
        for key in stats:
            stats[key].reverse()
        
        return stats
    
    async def get_top_searches(self, limit: int = 10) -> list:
        """Get top search queries."""
        # This would need to query the database
        # Simplified implementation
        response = self.db.client.table("analytics_events").select(
            "event_data"
        ).eq("event_type", "search").limit(1000).execute()
        
        if not response.data:
            return []
        
        # Count queries
        query_counts = {}
        for event in response.data:
            query = event.get("event_data", {}).get("query", "").lower()
            if query:
                query_counts[query] = query_counts.get(query, 0) + 1
        
        # Sort and return top
        sorted_queries = sorted(
            query_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {"query": q, "count": c}
            for q, c in sorted_queries[:limit]
        ]
    
    async def get_conversion_funnel(self) -> Dict[str, int]:
        """Get conversion funnel metrics."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        funnel = {
            "messages": 0,
            "searches": 0,
            "product_views": 0,
            "add_to_cart": 0,
            "checkout": 0
        }
        
        if self.redis:
            for event_type in funnel.keys():
                count = await self.redis.client.get(f"analytics:{event_type}:{today}")
                funnel[event_type] = int(count) if count else 0
        
        return funnel


# ==========================================
# Standalone Helper Functions
# Non-blocking analytics that work without service initialization
# ==========================================

_standalone_analytics: Optional[AnalyticsService] = None


async def _get_standalone_analytics() -> Optional[AnalyticsService]:
    """Get or create standalone analytics instance."""
    global _standalone_analytics
    if _standalone_analytics is None:
        try:
            from backend.database.supabase_client import get_async_supabase_client
            from backend.cache.redis_client import get_redis_client
            
            client = await get_async_supabase_client()
            redis = await get_redis_client()
            _standalone_analytics = AnalyticsService(client, redis)
        except Exception as e:
            logger.warning(f"⚠️ Failed to init standalone analytics: {e}")
            return None
    return _standalone_analytics


async def _log_event_standalone(
    user_phone: str,
    event_type: str,
    metadata: Dict[str, Any]
) -> bool:
    """Insert event into analytics (standalone helper)."""
    try:
        analytics = await _get_standalone_analytics()
        if analytics:
            await analytics.log_event(event_type, user_phone, metadata)
            return True
    except Exception as e:
        logger.warning(f"⚠️ Analytics log failed: {e}")
    return False


def log_event_fire_and_forget(
    user_phone: str,
    event_type: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an analytics event NON-BLOCKING (fire and forget).
    
    Use this from handlers when you don't want to wait for analytics.
    Creates an async task that runs in background.
    
    Args:
        user_phone: User's phone number
        event_type: Event type (use EventType constants)
        metadata: Optional additional data
        
    Usage:
        log_event_fire_and_forget(phone, EventType.ADD_TO_CART, {"product": "iPhone"})
    """
    if not settings.ENABLE_ANALYTICS:
        return
    
    metadata = metadata or {}
    
    try:
        asyncio.create_task(
            _log_event_standalone(user_phone, event_type, metadata)
        )
    except RuntimeError:
        # No event loop - skip silently
        logger.debug(f"📊 Analytics (deferred): {event_type}")


# Convenience functions for common events
def log_search_event(user_phone: str, query: str, results_count: int = 0):
    """Log search event (non-blocking)."""
    log_event_fire_and_forget(user_phone, EventType.SEARCH_QUERY, {
        "query": query[:100],
        "results_count": results_count
    })


def log_cart_event(user_phone: str, product_name: str, action: str = "add"):
    """Log cart event (non-blocking)."""
    event = EventType.ADD_TO_CART if action == "add" else EventType.REMOVE_FROM_CART
    log_event_fire_and_forget(user_phone, event, {
        "product_name": product_name[:50]
    })


def log_order_event(user_phone: str, order_id: str, total: float):
    """Log order placed event (non-blocking)."""
    log_event_fire_and_forget(user_phone, EventType.ORDER_PLACED, {
        "order_id": order_id,
        "total_amount": total
    })

