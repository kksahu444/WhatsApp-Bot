"""
Product Handler for WhatsApp AI Seller Bot.
Handles product search queries and recommendations.

HYBRID APPROACH:
1. LanceDB semantic search → get ranked product IDs (relevance)
2. Supabase fetch → get fresh stock/prices (accuracy)
3. Preserve LanceDB relevance order
4. Filter out-of-stock products
5. Gemini generates AI response
"""

import re
from typing import Dict, List, Optional
from loguru import logger

from backend.rag.search_engine import get_search_engine
from backend.services.product_service import get_product_service
from backend.rag.llm_handler import get_gemini_assistant


async def handle_product_query(user_phone: str, query: str) -> str:
    """
    Handle product search using HYBRID APPROACH:
    1. LanceDB semantic search (relevance ranking)
    2. Supabase fresh data (accurate stock/price)
    3. Preserve relevance order
    4. Filter out-of-stock
    5. Gemini AI response
    
    Args:
        user_phone: User's phone number
        query: Search query text
        
    Returns:
        str: Formatted product response
    """
    try:
        logger.info(f"🔍 Product query from {user_phone}: {query}")
        
        # Extract filters from query
        filters = extract_filters(query)
        logger.debug(f"📋 Extracted filters: {filters}")
        
        # STEP 1: LanceDB semantic search (SYNC - no await!)
        search_engine = get_search_engine()
        lancedb_results = search_engine.search(
            query=query,
            top_k=10,  # Get extra in case some are out of stock
            min_price=filters.get("min_price"),
            max_price=filters.get("max_price"),
            category=filters.get("category")
        )
        
        if not lancedb_results:
            return (
                f"Sorry, I couldn't find products matching '{query}'.\n\n"
                "Try searching for:\n"
                "📱 Electronics (phones, laptops, headphones)\n"
                "👕 Clothing (jeans, shoes, jackets)\n"
                "🏠 Home (furniture, appliances)"
            )
        
        # STEP 2: Fetch fresh data from Supabase
        product_ids = [p["id"] for p in lancedb_results]
        product_service = get_product_service()
        fresh_products = await product_service.get_products_by_ids(product_ids)
        
        # STEP 3: Preserve relevance order + filter out-of-stock
        products_map = {p["id"]: p for p in fresh_products}
        
        in_stock_products = []
        for lance_result in lancedb_results:
            product_id = lance_result["id"]
            if product_id in products_map:
                product = products_map[product_id]
                if product.get("stock", 0) > 0:
                    in_stock_products.append(product)
            if len(in_stock_products) >= 5:
                break
        
        if not in_stock_products:
            return (
                f"Sorry, products matching '{query}' are currently out of stock.\n\n"
                "Try browsing other categories:\n"
                "📱 Electronics • 👕 Clothing • 🏠 Home"
            )
        
        # STEP 4: Generate AI response with fresh data
        try:
            assistant = get_gemini_assistant()
            result = await assistant.generate_recommendation(
                user_query=query, 
                products=in_stock_products, 
                user_phone=user_phone
            )
            
            response = result.get("response", "")
            
            if response:
                response += "\n\n💬 To add a product, type: 'add [product name]'"
                logger.info(f"✅ Query handled: {len(in_stock_products)} products shown")
                return response
        except Exception as llm_error:
            logger.warning(f"⚠️ LLM failed, using fallback: {llm_error}")
        
        # Fallback: Format products manually
        response = format_products_fallback(in_stock_products, query)
        logger.info(f"✅ Query handled with fallback: {len(in_stock_products)} products")
        return response
        
    except Exception as e:
        logger.error(f"❌ Product query failed: {e}")
        return "Sorry, I encountered an error while searching. Please try again."


def extract_filters(query: str) -> Dict:
    """
    Extract price and category filters from query text.
    
    Args:
        query: Search query text
        
    Returns:
        Dict: Extracted filters {category, min_price, max_price}
    """
    filters = {}
    query_lower = query.lower()
    
    # Category keywords mapping
    categories = {
        "Electronics": ["electronics", "phone", "laptop", "headphone", "watch", "tablet", "camera", "speaker", "earbuds", "macbook", "iphone", "samsung", "tech"],
        "Clothing": ["clothing", "clothes", "jeans", "shirt", "shoes", "jacket", "dress", "t-shirt", "tshirt", "pants", "sneakers"],
        "Home": ["home", "furniture", "appliance", "kitchen", "decor", "sofa", "chair", "table", "lamp"]
    }
    
    for category, keywords in categories.items():
        if any(kw in query_lower for kw in keywords):
            filters["category"] = category
            break
    
    # Extract max price: "under 5000", "below ₹50000", "less than 10000"
    under_match = re.search(
        r'(under|below|less than|max|maximum|upto|up to|cheaper than)\s*[₹rs.]?\s*(\d+)',
        query_lower
    )
    if under_match:
        filters["max_price"] = float(under_match.group(2))
    
    # Extract min price: "above 1000", "over ₹5000", "more than 10000"
    above_match = re.search(
        r'(above|more than|over|min|minimum|starting|from)\s*[₹rs.]?\s*(\d+)',
        query_lower
    )
    if above_match:
        filters["min_price"] = float(above_match.group(2))
    
    # Extract price range: "between 1000 and 5000", "1000-5000"
    range_match = re.search(r'(\d+)\s*[-to]+\s*(\d+)', query_lower)
    if range_match:
        filters["min_price"] = float(range_match.group(1))
        filters["max_price"] = float(range_match.group(2))
    
    logger.debug(f"🎯 Filters: {filters}")
    return filters


def format_products_fallback(products: List[Dict], query: str) -> str:
    """
    Format products as text response (fallback when LLM fails).
    
    Args:
        products: List of product dictionaries
        query: Original search query
        
    Returns:
        str: Formatted product list
    """
    response = f"🔍 *Results for '{query}'*\n"
    response += "─" * 25 + "\n\n"
    
    for i, product in enumerate(products, 1):
        name = product.get('name', 'Unknown')
        price = float(product.get('price', 0))
        stock = product.get('stock', 0)
        
        response += f"*{i}. {name}*\n"
        response += f"   💰 ₹{price:,.0f}\n"
        
        # Add brief description if available
        desc = product.get('description', '')
        if desc:
            desc_text = desc[:80] + "..." if len(desc) > 80 else desc
            response += f"   📝 {desc_text}\n"
        
        if stock <= 5:
            response += f"   ⚠️ Only {stock} left!\n"
        
        response += "\n"
    
    response += "─" * 25 + "\n"
    response += "💬 To add a product, type: 'add [product name]'"
    
    return response


async def handle_product_details(user_phone: str, product_id: int) -> str:
    """
    Show detailed product information.
    
    Args:
        user_phone: User's phone number
        product_id: Product ID to show
        
    Returns:
        str: Formatted product details
    """
    try:
        from backend.services.product_service import get_product_service
        
        product_service = get_product_service()
        product = await product_service.get_product_by_id(product_id)
        
        if not product:
            return f"Product #{product_id} not found."
        
        price = float(product.get('price', 0))
        stock = product.get('stock', 0)
        stock_status = f"✅ {stock} in stock" if stock > 0 else "❌ Out of Stock"
        
        response = f"📦 *{product['name']}*\n\n"
        response += f"💰 Price: ₹{price:,.0f}\n"
        response += f"📊 {stock_status}\n"
        response += f"🏷️ Category: {product.get('category', 'N/A')}\n\n"
        
        if product.get('description'):
            response += f"📝 {product['description']}\n\n"
        
        if stock > 0:
            response += f"Type 'add {product['name']}' to add to cart."
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Product details failed: {e}")
        return "Sorry, couldn't load product details."
