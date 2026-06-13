#!/usr/bin/env python3
"""
Test script for LLM Handler and Cost Tracker.

Tests:
1. Gemini initialization
2. Token counting
3. Recommendation generation
4. Cost logging to Supabase
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
    level="INFO"
)


async def test_llm():
    """Test the LLM handler."""
    print("\n" + "=" * 60)
    print("Testing LLM Handler")
    print("=" * 60)
    
    from backend.rag.llm_handler import get_gemini_assistant
    from backend.rag.search_engine import get_search_engine
    
    # Get search engine and assistant
    search_engine = get_search_engine()
    assistant = get_gemini_assistant()
    
    print(f"\nModel: {assistant.model_name}")
    print(f"API Key configured: {'Yes' if assistant.api_key else 'No'}")
    print(f"Model initialized: {'Yes' if assistant.model else 'No'}")
    
    # Test 1: Health check
    print("\n--- Test 1: Health Check ---")
    is_healthy = await assistant.health_check()
    print(f"Health check: {'PASS' if is_healthy else 'FAIL (fallback mode)'}")
    
    # Test 2: Search for products
    print("\n--- Test 2: Search for 'smartphone under 70000' ---")
    products = search_engine.search("smartphone under 70000", top_k=3)
    print(f"Found {len(products)} products:")
    for p in products:
        print(f"  - {p['name']} - Rs.{p['price']:,.0f}")
    
    # Test 3: Generate recommendation
    print("\n--- Test 3: Generate Recommendation ---")
    result = await assistant.generate_recommendation(
        user_query="I want a good smartphone under 70000",
        products=products,
        user_phone="+919876543210"
    )
    
    print(f"\nTokens used: {result['tokens_used']}")
    print(f"Cost: ${result['cost_usd']:.6f} (Rs.{result['cost_usd'] * 83:.4f})")
    print(f"Products shown: {result['products_count']}")
    print(f"\nResponse:\n{'-' * 40}")
    print(result['response'])
    print("-" * 40)
    
    return result


async def test_cost_tracker():
    """Test the cost tracker."""
    print("\n" + "=" * 60)
    print("Testing Cost Tracker")
    print("=" * 60)
    
    from backend.rag.cost_tracker import (
        log_llm_cost,
        get_daily_cost_summary,
        check_budget_exceeded
    )
    
    # Test 1: Log a test cost
    print("\n--- Test 1: Log LLM Cost ---")
    success = await log_llm_cost(
        user_phone="+919876543210",
        model="gemini-1.5-flash",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.000023
    )
    print(f"Cost logged: {'SUCCESS' if success else 'FAILED'}")
    
    # Test 2: Get daily summary
    print("\n--- Test 2: Daily Cost Summary ---")
    daily = await get_daily_cost_summary()
    print(f"Date: {daily.get('date')}")
    print(f"Total calls: {daily.get('total_calls')}")
    print(f"Total tokens: {daily.get('total_tokens')}")
    print(f"Total cost: ${daily.get('total_cost_usd', 0):.6f} (Rs.{daily.get('total_cost_inr', 0):.2f})")
    
    # Test 3: Budget check
    print("\n--- Test 3: Budget Check ---")
    budget = await check_budget_exceeded(
        daily_budget_usd=1.0,
        monthly_budget_usd=25.0
    )
    print(f"Daily exceeded: {budget.get('daily_exceeded')}")
    print(f"Monthly exceeded: {budget.get('monthly_exceeded')}")
    print(f"Daily remaining: ${budget.get('daily_remaining_usd', 0):.4f}")
    print(f"Monthly remaining: ${budget.get('monthly_remaining_usd', 0):.2f}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("LLM Handler & Cost Tracker Test Suite")
    print("=" * 60)
    
    try:
        # Test LLM
        await test_llm()
        
        # Test cost tracker
        await test_cost_tracker()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
