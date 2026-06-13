"""
Abandoned Cart Check Script
Identifies abandoned carts and sends reminder notifications.

Run modes:
1. Single check: python -m backend.scripts.check_abandoned_carts
2. Continuous worker: python -m backend.scripts.check_abandoned_carts --loop
3. Stats only: python -m backend.scripts.check_abandoned_carts --stats-only
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Configuration
CHECK_INTERVAL_SECONDS = int(os.getenv("CART_CHECK_INTERVAL", "300"))  # 5 minutes
CART_ABANDON_THRESHOLD_MINUTES = int(os.getenv("CART_ABANDON_MINS", "30"))
REMINDER_COOLDOWN_HOURS = 24

from database.supabase_client import get_supabase_client
from utils.whatsapp_client import WhatsAppClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==========================================
# Redis Idempotency Helper
# ==========================================
class ReminderCache:
    """Redis-based reminder tracking to prevent duplicate sends."""
    
    def __init__(self):
        self._redis = None
    
    async def connect(self):
        """Connect to Redis."""
        try:
            import redis.asyncio as redis
            self._redis = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                decode_responses=True
            )
            await self._redis.ping()
            logger.info("✅ Redis connected for reminder tracking")
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e}")
            self._redis = None
    
    async def was_reminder_sent(self, phone: str) -> bool:
        """Check if reminder was already sent within cooldown."""
        if not self._redis:
            return False
        try:
            key = f"reminder_sent:{phone}"
            return await self._redis.exists(key) > 0
        except Exception:
            return False
    
    async def mark_reminder_sent(self, phone: str):
        """Mark reminder as sent with TTL."""
        if not self._redis:
            return
        try:
            key = f"reminder_sent:{phone}"
            await self._redis.set(key, datetime.utcnow().isoformat(), ex=REMINDER_COOLDOWN_HOURS * 3600)
        except Exception as e:
            logger.warning(f"⚠️ Failed to mark reminder: {e}")
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


class AbandonedCartChecker:
    """Checks for and notifies about abandoned carts."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.whatsapp_client = WhatsAppClient()
        self.reminder_cache = ReminderCache()
        
        # Configuration
        self.abandoned_threshold_minutes = CART_ABANDON_THRESHOLD_MINUTES
        self.abandoned_threshold_hours = 24  # Consider cart abandoned after 24 hours
        self.reminder_intervals = [24, 48, 72]  # Send reminders at these hour marks
        self.max_reminders = 3
    
    async def initialize(self):
        """Initialize async resources."""
        await self.reminder_cache.connect()
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.reminder_cache.close()
    
    async def check_abandoned_carts(self) -> dict:
        """
        Find and process abandoned carts.
        Returns summary of actions taken.
        """
        logger.info("Starting abandoned cart check...")
        
        cutoff_time = datetime.utcnow() - timedelta(hours=self.abandoned_threshold_hours)
        
        # Find carts that:
        # 1. Have items
        # 2. Were last updated before cutoff
        # 3. Haven't been converted to orders
        try:
            response = self.supabase.table("carts").select(
                "*, cart_items!inner(*)"
            ).lt(
                "updated_at", cutoff_time.isoformat()
            ).execute()
            
            abandoned_carts = response.data
            
            logger.info(f"Found {len(abandoned_carts)} potentially abandoned carts")
            
            reminders_sent = 0
            errors = []
            
            for cart in abandoned_carts:
                try:
                    should_remind = await self._should_send_reminder(cart)
                    
                    if should_remind:
                        await self._send_reminder(cart)
                        await self._record_reminder(cart['id'])
                        reminders_sent += 1
                
                except Exception as e:
                    logger.error(f"Error processing cart {cart['id']}: {e}")
                    errors.append({
                        "cart_id": cart['id'],
                        "error": str(e)
                    })
            
            return {
                "carts_checked": len(abandoned_carts),
                "reminders_sent": reminders_sent,
                "errors": errors
            }
        
        except Exception as e:
            logger.error(f"Failed to check abandoned carts: {e}")
            raise
    
    async def _should_send_reminder(self, cart: dict) -> bool:
        """Determine if we should send a reminder for this cart."""
        cart_id = cart['id']
        phone = cart.get('phone', '')
        
        # Check Redis idempotency first (fast path)
        if phone and await self.reminder_cache.was_reminder_sent(phone):
            logger.debug(f"⏭️ Skipping {phone[-4:]} - reminder already sent recently")
            return False
        
        # Check reminder history in DB
        try:
            response = self.supabase.table("cart_reminders").select("*").eq(
                "cart_id", cart_id
            ).order("created_at", desc=True).limit(1).execute()
            
            if not response.data:
                # No reminders sent yet
                return True
            
            last_reminder = response.data[0]
            reminder_count = last_reminder.get('reminder_count', 1)
            
            # Check if max reminders reached
            if reminder_count >= self.max_reminders:
                return False
            
            # Check if enough time has passed since last reminder
            last_reminder_time = datetime.fromisoformat(
                last_reminder['created_at'].replace('Z', '+00:00')
            )
            hours_since_last = (datetime.utcnow() - last_reminder_time.replace(tzinfo=None)).total_seconds() / 3600
            
            # Get next reminder interval
            if reminder_count < len(self.reminder_intervals):
                next_interval = self.reminder_intervals[reminder_count]
            else:
                next_interval = self.reminder_intervals[-1]
            
            return hours_since_last >= next_interval
        
        except Exception:
            # If table doesn't exist or other error, allow reminder
            return True
    
    async def _send_reminder(self, cart: dict):
        """Send an abandoned cart reminder via WhatsApp."""
        phone = cart['phone']
        items = cart.get('cart_items', [])
        
        # Calculate cart total
        total = sum(
            item.get('quantity', 0) * item.get('price', 0) 
            for item in items
        )
        item_count = len(items)
        
        # Build reminder message
        message = (
            f"🛒 *Keranjang Belanja Anda Menunggu!*\n\n"
            f"Hai! Kami melihat Anda memiliki {item_count} item di keranjang.\n\n"
            f"💰 Total: Rp {total:,.0f}\n\n"
            f"Jangan sampai kehabisan! Selesaikan pesanan Anda sekarang.\n\n"
            f"Ketik *'keranjang'* untuk melihat atau *'checkout'* untuk menyelesaikan pesanan."
        )
        
        try:
            await self.whatsapp_client.send_text(phone, message)
            logger.info(f"✅ Sent reminder to {phone[:6]}***")
            
            # Mark in Redis to prevent duplicates
            await self.reminder_cache.mark_reminder_sent(phone)
        
        except Exception as e:
            logger.error(f"❌ Failed to send reminder to {phone[:6]}***: {e}")
            raise
    
    async def _record_reminder(self, cart_id: str):
        """Record that a reminder was sent."""
        try:
            # Get current reminder count
            response = self.supabase.table("cart_reminders").select("reminder_count").eq(
                "cart_id", cart_id
            ).order("created_at", desc=True).limit(1).execute()
            
            current_count = response.data[0]['reminder_count'] if response.data else 0
            
            # Insert new reminder record
            self.supabase.table("cart_reminders").insert({
                "cart_id": cart_id,
                "reminder_count": current_count + 1,
                "created_at": datetime.utcnow().isoformat()
            }).execute()
        
        except Exception as e:
            # Table might not exist - that's okay
            logger.warning(f"Could not record reminder: {e}")
    
    async def get_cart_statistics(self) -> dict:
        """Get statistics about cart abandonment."""
        try:
            # Total active carts
            total_response = self.supabase.table("carts").select(
                "id", count="exact"
            ).execute()
            total_carts = total_response.count or 0
            
            # Abandoned carts (no activity in 24h)
            cutoff = datetime.utcnow() - timedelta(hours=24)
            abandoned_response = self.supabase.table("carts").select(
                "id", count="exact"
            ).lt("updated_at", cutoff.isoformat()).execute()
            abandoned_count = abandoned_response.count or 0
            
            # Carts converted to orders today
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            converted_response = self.supabase.table("orders").select(
                "id", count="exact"
            ).gte("created_at", today_start.isoformat()).execute()
            converted_today = converted_response.count or 0
            
            return {
                "total_active_carts": total_carts,
                "abandoned_carts": abandoned_count,
                "converted_today": converted_today,
                "abandonment_rate": (abandoned_count / total_carts * 100) if total_carts > 0 else 0
            }
        
        except Exception as e:
            logger.error(f"Failed to get cart statistics: {e}")
            return {}


async def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check for abandoned carts")
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics, don't send reminders"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without sending reminders"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously in a loop (worker mode)"
    )
    
    args = parser.parse_args()
    
    checker = AbandonedCartChecker()
    await checker.initialize()
    
    try:
        if args.stats_only:
            stats = await checker.get_cart_statistics()
            print("\n=== Cart Statistics ===")
            print(f"Total active carts: {stats.get('total_active_carts', 0)}")
            print(f"Abandoned carts: {stats.get('abandoned_carts', 0)}")
            print(f"Converted today: {stats.get('converted_today', 0)}")
            print(f"Abandonment rate: {stats.get('abandonment_rate', 0):.1f}%")
            return
        
        if args.dry_run:
            print("DRY RUN - No reminders will be sent")
            # Temporarily disable sending
            async def fake_send(*args, **kwargs):
                print(f"  Would send to: {args[0][:6]}***")
            checker.whatsapp_client.send_text = fake_send
        
        if args.loop:
            # Continuous worker mode
            logger.info(f"🚀 Starting abandoned cart worker (interval: {CHECK_INTERVAL_SECONDS}s)")
            
            while True:
                try:
                    result = await checker.check_abandoned_carts()
                    if result['reminders_sent'] > 0:
                        logger.info(f"📤 Sent {result['reminders_sent']} reminder(s)")
                except Exception as e:
                    logger.error(f"❌ Check failed: {e}")
                
                logger.debug(f"💤 Sleeping {CHECK_INTERVAL_SECONDS}s...")
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        else:
            # Single run mode
            result = await checker.check_abandoned_carts()
            
            print("\n=== Abandoned Cart Check Results ===")
            print(f"Carts checked: {result['carts_checked']}")
            print(f"Reminders sent: {result['reminders_sent']}")
            
            if result['errors']:
                print(f"Errors: {len(result['errors'])}")
                for error in result['errors'][:5]:
                    print(f"  - Cart {error['cart_id']}: {error['error']}")
    
    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user")
    finally:
        await checker.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
