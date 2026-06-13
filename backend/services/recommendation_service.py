"""
Product Recommendation Service.

Uses Vector Search (LanceDB) to find similar products for cross-selling.
"People who viewed X also liked Y, Z..."
"""

from typing import List, Dict, Optional
from loguru import logger


class RecommendationService:
    """
    Product recommendation engine using semantic similarity.
    
    Reuses the existing LanceDB search engine for memory efficiency.
    """
    
    def __init__(self):
        self._search_engine = None
    
    async def _get_search_engine(self):
        """Lazy-load search engine singleton."""
        if self._search_engine is None:
            try:
                from backend.rag.search_engine import get_search_engine
                self._search_engine = get_search_engine()
            except Exception as e:
                logger.error(f"❌ Failed to get search engine: {e}")
                return None
        return self._search_engine
    
    def _normalize_name(self, name: str) -> str:
        """Normalize product name for comparison."""
        return name.lower().strip()
    
    def _is_same_product(self, name1: str, name2: str) -> bool:
        """
        Check if two product names refer to the same product.
        Uses fuzzy matching to handle variations.
        """
        n1 = self._normalize_name(name1)
        n2 = self._normalize_name(name2)
        
        # Exact match
        if n1 == n2:
            return True
        
        # One contains the other (for short names)
        if len(n1) > 5 and len(n2) > 5:
            if n1 in n2 or n2 in n1:
                return True
        
        # Word overlap check (for longer names)
        words1 = set(n1.split())
        words2 = set(n2.split())
        
        if len(words1) >= 2 and len(words2) >= 2:
            overlap = len(words1 & words2)
            min_words = min(len(words1), len(words2))
            if overlap >= min_words * 0.7:  # 70% word overlap
                return True
        
        return False
    
    async def get_similar_products(
        self,
        product_name: str,
        limit: int = 3,
        exclude_same: bool = True
    ) -> List[Dict]:
        """
        Find products similar to the given product.
        
        Uses semantic search to find related items.
        
        Args:
            product_name: Name of the product to find similar items for
            limit: Maximum number of recommendations
            exclude_same: Whether to exclude the input product itself
            
        Returns:
            List of similar product dicts with keys: name, price, category
        """
        try:
            search_engine = await self._get_search_engine()
            if not search_engine:
                return []
            
            # Search for similar products (get extra to filter later)
            search_limit = limit + 3 if exclude_same else limit
            results = await search_engine.search(product_name, limit=search_limit)
            
            if not results:
                return []
            
            recommendations = []
            
            for product in results:
                # Get product name (handle different dict structures)
                name = product.get('name') or product.get('product_name', '')
                
                # Skip if same product
                if exclude_same and self._is_same_product(product_name, name):
                    continue
                
                recommendations.append({
                    'name': name,
                    'price': product.get('price', 0),
                    'category': product.get('category', ''),
                    'product_id': product.get('id') or product.get('product_id', '')
                })
                
                if len(recommendations) >= limit:
                    break
            
            logger.debug(f"🎯 Recommendations for '{product_name}': {len(recommendations)} items")
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Recommendation error: {e}")
            return []
    
    async def get_cart_recommendations(
        self,
        cart_items: List[Dict],
        limit: int = 3
    ) -> List[Dict]:
        """
        Get recommendations based on entire cart contents.
        
        Args:
            cart_items: List of cart items with 'product_name' key
            limit: Maximum recommendations to return
            
        Returns:
            List of recommended products
        """
        try:
            if not cart_items:
                return []
            
            # Get names of items in cart
            cart_names = [
                item.get('product_name', '') 
                for item in cart_items 
                if item.get('product_name')
            ]
            
            if not cart_names:
                return []
            
            all_recommendations = []
            seen_names = set(self._normalize_name(n) for n in cart_names)
            
            # Get recommendations for each cart item
            for name in cart_names[:2]:  # Only check first 2 items for speed
                recs = await self.get_similar_products(name, limit=2)
                
                for rec in recs:
                    rec_name = self._normalize_name(rec['name'])
                    if rec_name not in seen_names:
                        all_recommendations.append(rec)
                        seen_names.add(rec_name)
            
            return all_recommendations[:limit]
            
        except Exception as e:
            logger.error(f"❌ Cart recommendations error: {e}")
            return []
    
    def format_recommendations(self, recommendations: List[Dict]) -> str:
        """
        Format recommendations for WhatsApp display.
        
        Args:
            recommendations: List of product recommendations
            
        Returns:
            Formatted string for WhatsApp message
        """
        if not recommendations:
            return ""
        
        lines = ["💡 *You might also like:*"]
        
        for i, rec in enumerate(recommendations[:3], 1):
            name = rec.get('name', 'Product')[:30]
            price = rec.get('price', 0)
            lines.append(f"{i}. {name} - ₹{price:,.0f}")
        
        lines.append("\n_Say 'add [item name]' to add to cart_")
        
        return "\n".join(lines)


# Singleton
_recommendation_service: Optional[RecommendationService] = None


def get_recommendation_service() -> RecommendationService:
    """Get or create recommendation service singleton."""
    global _recommendation_service
    if _recommendation_service is None:
        _recommendation_service = RecommendationService()
    return _recommendation_service


async def get_similar_products(product_name: str, limit: int = 3) -> List[Dict]:
    """
    Convenience function to get similar products.
    
    Usage:
        recs = await get_similar_products("iPhone 15")
    """
    service = get_recommendation_service()
    return await service.get_similar_products(product_name, limit)


async def format_recommendations_for_cart(product_name: str) -> str:
    """
    Get formatted recommendations for cart addition.
    
    Usage:
        rec_text = await format_recommendations_for_cart("iPhone 15")
        response = f"Added to cart! {rec_text}"
    """
    service = get_recommendation_service()
    recs = await service.get_similar_products(product_name, limit=3)
    return service.format_recommendations(recs)
