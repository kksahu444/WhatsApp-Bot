"""
Test script for async product and cart services.
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.product_service import get_product_service
from backend.services.cart_manager import get_cart_manager


async def test_services():
    """Test product and cart services."""
    print("=" * 50)
    print("🧪 Testing Async Services")
    print("=" * 50)
    
    # Test product service
    print("\n📦 Testing Product Service...")
    product_service = get_product_service()
    
    # Test get all products
    products = await product_service.get_all_products(limit=5)
    print(f"✅ Fetched {len(products)} products")
    
    if products:
        # Test get by ID
        product = await product_service.get_product_by_id(products[0]['id'])
        print(f"✅ Get by ID: {product['name'] if product else 'Not found'}")
        
        # Test search
        search_results = await product_service.search_products("phone", limit=3)
        print(f"✅ Search 'phone': {len(search_results)} results")
        
        # Test check stock
        has_stock = await product_service.check_stock(products[0]['id'], 1)
        print(f"✅ Stock check: {'Available' if has_stock else 'Out of stock'}")
        
        # Test categories
        categories = await product_service.get_categories()
        print(f"✅ Categories: {categories}")
    
    # Test cart manager
    print("\n🛒 Testing Cart Manager...")
    cart = get_cart_manager()
    test_phone = "+919999999999"
    
    if products:
        # Add to cart
        result = await cart.add_to_cart(test_phone, products[0]['id'], 2)
        print(f"✅ Add to cart: {result['message']} (success={result['success']})")
        
        # Get cart
        items = await cart.get_cart(test_phone)
        print(f"✅ Cart has {len(items)} item(s)")
        
        # Get count
        count = await cart.get_cart_count(test_phone)
        print(f"✅ Cart item count: {count}")
        
        # Calculate total
        total = await cart.calculate_total(test_phone)
        print(f"✅ Cart total: ₹{total:,.2f}")
        
        # Get summary
        summary = await cart.get_cart_summary(test_phone)
        print(f"✅ Cart summary: {summary['item_count']} items, ₹{summary['total']:,.2f}")
        
        # Update quantity
        update_result = await cart.update_quantity(test_phone, products[0]['id'], 3)
        print(f"✅ Update quantity: {update_result['message']} (success={update_result['success']})")
        
        # Clear cart (now returns Dict)
        clear_result = await cart.clear_cart(test_phone)
        print(f"✅ Clear cart: {clear_result['message']} (success={clear_result['success']})")
        
        # Verify cleared
        final_items = await cart.get_cart(test_phone)
        print(f"✅ Final cart count: {len(final_items)} items")
    
    print("\n" + "=" * 50)
    print("🎉 All tests completed!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_services())
