"""
Seed Data
Sample products for development and testing
"""

import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

SAMPLE_PRODUCTS: List[Dict[str, Any]] = [
    # Electronics
    {
        "name": "Wireless Bluetooth Earbuds Pro",
        "description": "Premium wireless earbuds with active noise cancellation, 30-hour battery life, and IPX5 water resistance. Features touch controls and seamless device switching.",
        "price": 2999.00,
        "currency": "INR",
        "category": "electronics",
        "subcategory": "audio",
        "brand": "TechSound",
        "sku": "TSE-001",
        "tags": ["wireless", "bluetooth", "earbuds", "anc", "noise cancellation"],
        "stock_quantity": 150,
        "is_active": True
    },
    {
        "name": "Smart Watch Series X",
        "description": "Advanced smartwatch with heart rate monitoring, GPS tracking, sleep analysis, and 50+ workout modes. 5-day battery life with always-on display.",
        "price": 8999.00,
        "currency": "INR",
        "category": "electronics",
        "subcategory": "wearables",
        "brand": "FitTech",
        "sku": "FTW-001",
        "tags": ["smartwatch", "fitness", "gps", "health", "heart rate"],
        "stock_quantity": 75,
        "is_active": True
    },
    {
        "name": "Portable Power Bank 20000mAh",
        "description": "High-capacity power bank with fast charging support. Features dual USB-A and USB-C ports. Can charge a smartphone 5 times.",
        "price": 1499.00,
        "currency": "INR",
        "category": "electronics",
        "subcategory": "accessories",
        "brand": "PowerMax",
        "sku": "PMB-001",
        "tags": ["power bank", "portable charger", "fast charging", "usb-c"],
        "stock_quantity": 200,
        "is_active": True
    },
    
    # Clothing
    {
        "name": "Premium Cotton T-Shirt",
        "description": "Ultra-soft 100% organic cotton t-shirt. Available in multiple colors. Breathable fabric perfect for everyday wear.",
        "price": 599.00,
        "currency": "INR",
        "category": "clothing",
        "subcategory": "t-shirts",
        "brand": "ComfortWear",
        "sku": "CWT-001",
        "tags": ["t-shirt", "cotton", "organic", "casual", "comfortable"],
        "stock_quantity": 500,
        "is_active": True
    },
    {
        "name": "Slim Fit Denim Jeans",
        "description": "Classic slim-fit jeans with stretch comfort technology. Made from premium denim with 5-pocket styling.",
        "price": 1299.00,
        "currency": "INR",
        "category": "clothing",
        "subcategory": "jeans",
        "brand": "DenimCraft",
        "sku": "DCJ-001",
        "tags": ["jeans", "denim", "slim fit", "stretch", "casual"],
        "stock_quantity": 300,
        "is_active": True
    },
    {
        "name": "Hooded Sweatshirt",
        "description": "Cozy fleece-lined hoodie with kangaroo pocket. Perfect for layering or lounging. Available in S, M, L, XL.",
        "price": 899.00,
        "currency": "INR",
        "category": "clothing",
        "subcategory": "hoodies",
        "brand": "ComfortWear",
        "sku": "CWH-001",
        "tags": ["hoodie", "sweatshirt", "fleece", "winter", "casual"],
        "stock_quantity": 250,
        "is_active": True
    },
    
    # Home
    {
        "name": "Stainless Steel Water Bottle",
        "description": "Double-wall vacuum insulated water bottle. Keeps drinks cold for 24 hours or hot for 12 hours. 750ml capacity.",
        "price": 699.00,
        "currency": "INR",
        "category": "home",
        "subcategory": "kitchen",
        "brand": "EcoBottle",
        "sku": "EBB-001",
        "tags": ["water bottle", "insulated", "stainless steel", "eco-friendly"],
        "stock_quantity": 400,
        "is_active": True
    },
    {
        "name": "Bamboo Cutting Board Set",
        "description": "Set of 3 premium bamboo cutting boards in different sizes. Antimicrobial and knife-friendly surface.",
        "price": 999.00,
        "currency": "INR",
        "category": "home",
        "subcategory": "kitchen",
        "brand": "EcoHome",
        "sku": "EHC-001",
        "tags": ["cutting board", "bamboo", "kitchen", "eco-friendly", "antimicrobial"],
        "stock_quantity": 150,
        "is_active": True
    },
    {
        "name": "LED Desk Lamp with Wireless Charger",
        "description": "Modern LED desk lamp with adjustable brightness and color temperature. Built-in 10W wireless charging pad.",
        "price": 1799.00,
        "currency": "INR",
        "category": "home",
        "subcategory": "lighting",
        "brand": "LumiTech",
        "sku": "LTL-001",
        "tags": ["desk lamp", "led", "wireless charger", "adjustable", "home office"],
        "stock_quantity": 100,
        "is_active": True
    },
    
    # Beauty
    {
        "name": "Vitamin C Serum",
        "description": "Brightening vitamin C serum with hyaluronic acid. Reduces dark spots and improves skin texture. 30ml bottle.",
        "price": 799.00,
        "currency": "INR",
        "category": "beauty",
        "subcategory": "skincare",
        "brand": "GlowUp",
        "sku": "GUS-001",
        "tags": ["serum", "vitamin c", "skincare", "brightening", "anti-aging"],
        "stock_quantity": 300,
        "is_active": True
    },
    
    # Sports
    {
        "name": "Yoga Mat Premium",
        "description": "Extra thick 6mm yoga mat with non-slip surface. Eco-friendly TPE material. Includes carrying strap.",
        "price": 1199.00,
        "currency": "INR",
        "category": "sports",
        "subcategory": "yoga",
        "brand": "ZenFit",
        "sku": "ZFY-001",
        "tags": ["yoga mat", "exercise", "fitness", "non-slip", "eco-friendly"],
        "stock_quantity": 200,
        "is_active": True
    },
    {
        "name": "Resistance Bands Set",
        "description": "Set of 5 resistance bands with different tension levels. Perfect for home workouts, physical therapy, and stretching.",
        "price": 499.00,
        "currency": "INR",
        "category": "sports",
        "subcategory": "fitness",
        "brand": "FlexFit",
        "sku": "FFR-001",
        "tags": ["resistance bands", "workout", "fitness", "home gym", "stretching"],
        "stock_quantity": 350,
        "is_active": True
    },
]


async def seed_products(supabase_client):
    """Seed products into Supabase."""
    logger.info(f"Seeding {len(SAMPLE_PRODUCTS)} products...")
    
    for product in SAMPLE_PRODUCTS:
        try:
            await supabase_client.create_product(product)
            logger.info(f"Created product: {product['name']}")
        except Exception as e:
            logger.warning(f"Failed to create product {product['name']}: {e}")
    
    logger.info("Product seeding complete!")


if __name__ == "__main__":
    import asyncio
    from database.supabase_client import get_supabase_client
    
    async def main():
        client = get_supabase_client()
        await seed_products(client)
    
    asyncio.run(main())
