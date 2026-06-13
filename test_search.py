#!/usr/bin/env python3
"""Quick test script for search engine."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.rag.search_engine import get_search_engine

def main():
    print("Loading search engine...")
    engine = get_search_engine()
    
    # Test 1: Search for smartphones
    print("\n" + "="*50)
    print("Test 1: Search for 'smartphones'")
    print("="*50)
    results = engine.search('smartphones', top_k=3)
    print("\nTop Phones:")
    for i, r in enumerate(results):
        print(f"  {i+1}. {r['name']} - Rs.{r['price']:,.0f}")
    
    # Test 2: Search with price filter
    print("\n" + "="*50)
    print("Test 2: Search for 'shoes' with max_price=15000")
    print("="*50)
    results = engine.search('shoes', top_k=5, max_price=15000)
    print("\nAffordable Shoes:")
    for i, r in enumerate(results):
        print(f"  {i+1}. {r['name']} - Rs.{r['price']:,.0f}")
    
    # Test 3: Category filter
    print("\n" + "="*50)
    print("Test 3: Search 'for home' with category='Home'")
    print("="*50)
    results = engine.search('for home', top_k=3, category='Home')
    print("\nHome Products:")
    for i, r in enumerate(results):
        print(f"  {i+1}. {r['name']} - Rs.{r['price']:,.0f}")
    
    # Test 4: Get categories
    print("\n" + "="*50)
    print("Test 4: Get all categories")
    print("="*50)
    categories = engine.get_categories()
    print(f"\nCategories: {categories}")
    
    # Test 5: Product count
    print("\n" + "="*50)
    print(f"Total products indexed: {engine.get_product_count()}")
    print("="*50)
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    main()
