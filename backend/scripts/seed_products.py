#!/usr/bin/env python3
"""
Product seeding script for WhatsApp Seller Bot.

Seeds the Supabase products table with 30 sample products across
Electronics, Clothing, and Home categories. Idempotent - skips
if products already exist.

Usage:
    python backend/scripts/seed_products.py
    
Exit Codes:
    0 - Success (products seeded or already exist)
    1 - Failure (connection error or insert failed)
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger
from supabase import create_client, Client

from backend.config.settings import settings


# Configure loguru for script output
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


# ============================================================================
# SAMPLE PRODUCTS DATA (30 products)
# ============================================================================

SAMPLE_PRODUCTS: List[Dict[str, Any]] = [
    # =========================================================================
    # ELECTRONICS (10 products)
    # =========================================================================
    {
        "name": "iPhone 15 Pro",
        "description": "Latest Apple flagship with A17 Pro chip and titanium design. Features 48MP camera and action button.",
        "price": float(Decimal("129999.00")),
        "category": "Electronics",
        "image_url": "https://picsum.photos/seed/iphone15/400",
        "stock": 25
    },
    {
        "name": "MacBook Air M3",
        "description": "Thin and light laptop with M3 chip. 13.6-inch Liquid Retina display with 8GB unified memory.",
        "price": float(Decimal("114900.00")),
        "category": "Electronics",
        "image_url": "https://picsum.photos/seed/macbookair/400",
        "stock": 15
    },
    {
        "name": "Samsung Galaxy S24 Ultra",
        "description": "Android flagship with S Pen and 200MP camera. 6.8-inch Dynamic AMOLED 2X display.",
        "price": float(Decimal("124999.00")),
        "category": "Electronics",
        "image_url": "https://picsum.photos/seed/galaxys24/400",
        "stock": 20
    },
    {
        "name": "Sony WH-1000XM5",
        "description": "Industry-leading noise canceling headphones. 30-hour battery life with quick charging.",
        "price": float(Decimal("29990.00")),
        "category": "Electronics",
        "image_url": "https://picsum.photos/seed/sonywh1000/400",
        "stock": 50
    },
    {
        "name": "Apple Watch Series 9",
        "description": "Advanced health and fitness tracking smartwatch. Always-on Retina display with GPS.",
        "price": float(Decimal("45900.00")),
        "category": "Electronics",
        "image_url": "https://picsum.photos/seed/applewatch9/400",
        "stock": 35
    },
    {
        "name": "iPad Air M2",
        "description": "Powerful tablet with M2 chip. 10.9-inch Liquid Retina display with Apple Pencil support.",
        "price": float(Decimal("59900.00")),
        "category": "Electronics",
        "image_url": "https://picsum.photos/seed/ipadair/400",
        "stock": 30
    },
    {
        "name": "Dell XPS 15",
        "description": "Premium Windows laptop with 15.6-inch 4K OLED display. Intel Core i7 13th gen processor.",
        "price": float(Decimal("145000.00")),
        "category": "Electronics",
        "image_url": "https://picsum.photos/seed/dellxps15/400",
        "stock": 12
    },
    {
        "name": "OnePlus 12",
        "description": "Flagship Android phone with Snapdragon 8 Gen 3. 120Hz AMOLED display and 100W charging.",
        "price": float(Decimal("64999.00")),
        "category": "Electronics",
        "image_url": "https://picsum.photos/seed/oneplus12/400",
        "stock": 40
    },
    {
        "name": "AirPods Pro 2",
        "description": "Active noise cancellation wireless earbuds. Adaptive audio with USB-C charging case.",
        "price": float(Decimal("24999.00")),
        "category": "Electronics",
        "image_url": "https://picsum.photos/seed/airpodspro2/400",
        "stock": 60
    },
    {
        "name": "Logitech MX Master 3S",
        "description": "Ergonomic wireless mouse with quiet clicks. 8K DPI sensor and customizable buttons.",
        "price": float(Decimal("8995.00")),
        "category": "Electronics",
        "image_url": "https://picsum.photos/seed/mxmaster3s/400",
        "stock": 45
    },
    
    # =========================================================================
    # CLOTHING (10 products)
    # =========================================================================
    {
        "name": "Levi's 511 Slim Fit Jeans",
        "description": "Classic slim fit jeans in dark blue denim. Comfortable stretch fabric for all-day wear.",
        "price": float(Decimal("3999.00")),
        "category": "Clothing",
        "image_url": "https://picsum.photos/seed/levis511/400",
        "stock": 100
    },
    {
        "name": "Nike Air Max 270",
        "description": "Iconic running shoes with visible Air unit. Breathable mesh upper and cushioned comfort.",
        "price": float(Decimal("12795.00")),
        "category": "Clothing",
        "image_url": "https://picsum.photos/seed/airmax270/400",
        "stock": 75
    },
    {
        "name": "Adidas Ultraboost 22",
        "description": "Premium running shoes with Boost cushioning. Primeknit upper for adaptive fit.",
        "price": float(Decimal("16999.00")),
        "category": "Clothing",
        "image_url": "https://picsum.photos/seed/ultraboost22/400",
        "stock": 55
    },
    {
        "name": "H&M Cotton T-Shirt Pack (3)",
        "description": "Basic crew neck t-shirts in black, white, grey. 100% cotton regular fit.",
        "price": float(Decimal("1499.00")),
        "category": "Clothing",
        "image_url": "https://picsum.photos/seed/hmtshirt/400",
        "stock": 200
    },
    {
        "name": "Zara Formal Shirt",
        "description": "Slim fit formal shirt in white. Easy-iron fabric perfect for office wear.",
        "price": float(Decimal("2990.00")),
        "category": "Clothing",
        "image_url": "https://picsum.photos/seed/zarashirt/400",
        "stock": 80
    },
    {
        "name": "Puma RS-X Sneakers",
        "description": "Retro-inspired chunky sneakers with bold colorblocking. Comfortable running system cushioning.",
        "price": float(Decimal("8999.00")),
        "category": "Clothing",
        "image_url": "https://picsum.photos/seed/pumarsx/400",
        "stock": 65
    },
    {
        "name": "Reebok Nano X3",
        "description": "Cross-training shoes designed for gym workouts. Durable and stable with Flexweave knit.",
        "price": float(Decimal("10499.00")),
        "category": "Clothing",
        "image_url": "https://picsum.photos/seed/reeboknano/400",
        "stock": 45
    },
    {
        "name": "Nike Dri-FIT Training Top",
        "description": "Moisture-wicking athletic shirt. Lightweight and breathable for intense workouts.",
        "price": float(Decimal("2495.00")),
        "category": "Clothing",
        "image_url": "https://picsum.photos/seed/nikedrifit/400",
        "stock": 120
    },
    {
        "name": "North Face ThermoBall Jacket",
        "description": "Insulated jacket for cold weather. Water-resistant shell with synthetic fill.",
        "price": float(Decimal("8500.00")),
        "category": "Clothing",
        "image_url": "https://picsum.photos/seed/northfacejacket/400",
        "stock": 30
    },
    {
        "name": "Allen Solly Chinos",
        "description": "Smart-casual trousers in beige. Slim fit with stretch for comfortable wear.",
        "price": float(Decimal("2799.00")),
        "category": "Clothing",
        "image_url": "https://picsum.photos/seed/allensollychinos/400",
        "stock": 90
    },
    
    # =========================================================================
    # HOME (10 products)
    # =========================================================================
    {
        "name": "Philips Air Fryer HD9252",
        "description": "4.1L capacity air fryer with rapid air technology. Digital touchscreen with 7 presets.",
        "price": float(Decimal("9995.00")),
        "category": "Home",
        "image_url": "https://picsum.photos/seed/philipsairfryer/400",
        "stock": 40
    },
    {
        "name": "Dyson V11 Absolute",
        "description": "Cordless vacuum cleaner with intelligent suction. 60-minute runtime and LCD screen.",
        "price": float(Decimal("49900.00")),
        "category": "Home",
        "image_url": "https://picsum.photos/seed/dysonv11/400",
        "stock": 18
    },
    {
        "name": "Amazon Echo Dot 5",
        "description": "Smart speaker with Alexa voice assistant. Improved audio and temperature sensor.",
        "price": float(Decimal("5499.00")),
        "category": "Home",
        "image_url": "https://picsum.photos/seed/echodot5/400",
        "stock": 100
    },
    {
        "name": "IKEA MICKE Desk",
        "description": "Compact study desk in white finish. Built-in cable management and drawer storage.",
        "price": float(Decimal("6999.00")),
        "category": "Home",
        "image_url": "https://picsum.photos/seed/ikeamicke/400",
        "stock": 25
    },
    {
        "name": "Decathlon Yoga Mat 5mm",
        "description": "Non-slip yoga mat with carrying strap. Eco-friendly material with cushioned support.",
        "price": float(Decimal("799.00")),
        "category": "Home",
        "image_url": "https://picsum.photos/seed/yogamat/400",
        "stock": 150
    },
    {
        "name": "Instant Pot Duo 6L",
        "description": "7-in-1 multi-cooker: pressure cooker, rice cooker, steamer, slow cooker, and more.",
        "price": float(Decimal("7995.00")),
        "category": "Home",
        "image_url": "https://picsum.photos/seed/instantpot/400",
        "stock": 35
    },
    {
        "name": "Wipro Smart LED Bulb Pack (4)",
        "description": "WiFi-enabled color-changing smart bulbs. Works with Alexa and Google Home.",
        "price": float(Decimal("1299.00")),
        "category": "Home",
        "image_url": "https://picsum.photos/seed/smartbulb/400",
        "stock": 200
    },
    {
        "name": "Milton Thermosteel Bottle Set (3)",
        "description": "Stainless steel vacuum insulated water bottles. Keeps drinks hot/cold for 24 hours.",
        "price": float(Decimal("899.00")),
        "category": "Home",
        "image_url": "https://picsum.photos/seed/miltonbottle/400",
        "stock": 180
    },
    {
        "name": "Urban Ladder Bookshelf",
        "description": "5-tier wooden bookshelf in walnut finish. Sturdy construction with modern design.",
        "price": float(Decimal("8500.00")),
        "category": "Home",
        "image_url": "https://picsum.photos/seed/bookshelf/400",
        "stock": 20
    },
    {
        "name": "Prestige Induction Cooktop",
        "description": "1800W induction stove with digital controls. Auto shut-off and overheat protection.",
        "price": float(Decimal("3495.00")),
        "category": "Home",
        "image_url": "https://picsum.photos/seed/inductioncooktop/400",
        "stock": 60
    },
]


async def get_product_count(supabase: Client) -> int:
    """
    Get current product count in database.
    
    Args:
        supabase: Supabase client instance
        
    Returns:
        Number of products in the database
        
    Raises:
        Exception: If query fails
    """
    try:
        result = supabase.table('products').select('id', count='exact').execute()
        return result.count if result.count else 0
    except Exception as e:
        logger.error(f"❌ Failed to count products: {e}")
        raise


async def seed_products(supabase: Client) -> bool:
    """
    Insert sample products if table is empty.
    
    This function is idempotent - it checks if products already exist
    before inserting. If products are found, it skips seeding.
    
    Args:
        supabase: Supabase client instance
        
    Returns:
        True if seeding succeeded or was skipped, False on failure
    """
    try:
        # Check existing product count
        count = await get_product_count(supabase)
        
        if count > 0:
            logger.info(f"✅ Products already exist ({count} found), skipping seed")
            return True
        
        # Seed products
        logger.info(f"📦 Seeding {len(SAMPLE_PRODUCTS)} products...")
        
        # Insert all products in a single batch
        result = supabase.table('products').insert(SAMPLE_PRODUCTS).execute()
        
        if not result.data:
            logger.error("❌ Insert returned no data")
            return False
        
        # Verify insert
        new_count = await get_product_count(supabase)
        logger.info(f"✅ Inserted {new_count} products successfully")
        
        # Log category breakdown
        categories = {}
        for product in SAMPLE_PRODUCTS:
            cat = product['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        for cat, count in categories.items():
            logger.info(f"   📁 {cat}: {count} products")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Seed failed: {e}")
        return False


async def main() -> None:
    """
    Main entry point for the seed script.
    
    Connects to Supabase, tests connection, and seeds products.
    Exits with code 0 on success, 1 on failure.
    """
    try:
        logger.info("🚀 WhatsApp Seller Bot - Product Seeder")
        logger.info("=" * 50)
        
        # Validate settings
        if not settings.supabase_url or not settings.supabase_service_key:
            logger.error("❌ Missing Supabase credentials in settings")
            logger.error("   Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
            sys.exit(1)
        
        # Connect to Supabase
        logger.info(f"🔌 Connecting to Supabase: {settings.supabase_url}")
        
        # Supabase SDK v2.x uses create_client without proxy argument
        from supabase import create_client as supabase_create_client
        supabase: Client = supabase_create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_key  # Use service_role for admin operations
        )
        
        # Test connection with a simple query
        try:
            supabase.table('products').select('id').limit(1).execute()
            logger.info("✅ Connected to Supabase successfully")
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            logger.error("   Make sure the 'products' table exists in Supabase")
            sys.exit(1)
        
        # Seed products
        logger.info("-" * 50)
        success = await seed_products(supabase)
        logger.info("-" * 50)
        
        if success:
            logger.info("✅ Seed script completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Seed script failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("⚠️ Seed interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
