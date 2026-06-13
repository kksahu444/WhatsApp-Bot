"""
Test Day 7 - Complete checkout flow.

Tests:
1. Add product to cart
2. Start checkout
3. Provide name
4. Provide address
5. Confirm order
6. View order history
"""

import asyncio
from loguru import logger


async def test_complete_flow():
    """Test complete checkout flow."""
    print("=" * 60)
    print("🧪 Testing Day 7 - Order Management & Checkout")
    print("=" * 60)
    
    from backend.handlers.message_router import get_message_router
    router = get_message_router()
    phone = "+919999999999"
    
    # Test 1: Add to cart
    print("\n📝 Test 1: Add to cart")
    result = await router.route_message(phone, "add iPhone 15 Pro")
    print(f"   Intent: {result['intent']}")
    print(f"   Response: {result['response'][:100]}...")
    
    # Test 2: Start checkout
    print("\n📝 Test 2: Start checkout")
    result = await router.route_message(phone, "checkout")
    print(f"   Intent: {result['intent']}")
    print(f"   Response: {result['response']}")
    
    # Test 3: Provide name
    print("\n📝 Test 3: Provide name")
    result = await router.route_message(phone, "Krishnkant Sahu")
    print(f"   Intent: {result['intent']}")
    print(f"   Response: {result['response']}")
    
    # Test 4: Provide address
    print("\n📝 Test 4: Provide address")
    result = await router.route_message(phone, "New Delhi, India 110001")
    print(f"   Intent: {result['intent']}")
    print(f"   Response: {result['response']}")
    
    # Test 5: Confirm order
    print("\n📝 Test 5: Confirm order")
    result = await router.route_message(phone, "YES")
    print(f"   Intent: {result['intent']}")
    print(f"   Response: {result['response']}")
    
    # Test 6: View order history
    print("\n📝 Test 6: View order history")
    result = await router.route_message(phone, "my orders")
    print(f"   Intent: {result['intent']}")
    print(f"   Response: {result['response']}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED!")
    print("=" * 60)


async def test_intent_classification():
    """Test new intent patterns."""
    print("\n🧪 Testing Intent Classification")
    print("-" * 40)
    
    from backend.handlers.message_router import get_message_router
    router = get_message_router()
    
    test_cases = [
        ("checkout", "checkout"),
        ("place order", "checkout"),
        ("my orders", "order_history"),
        ("order history", "order_history"),
        ("track ORD-20251205-A3F9B2", "track_order"),
        ("cancel order ORD-20251205-A3F9B2", "cancel_order"),
    ]
    
    all_passed = True
    for message, expected in test_cases:
        intent = await router.classify_intent(message)
        status = "✅" if intent == expected else "❌"
        if intent != expected:
            all_passed = False
        print(f"   {status} '{message}' → {intent} (expected: {expected})")
    
    if all_passed:
        print("\n✅ All intent tests passed!")
    else:
        print("\n⚠️ Some intent tests failed!")


if __name__ == "__main__":
    asyncio.run(test_intent_classification())
    asyncio.run(test_complete_flow())
