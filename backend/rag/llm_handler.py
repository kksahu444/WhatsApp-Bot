"""
LLM Handler - Async Gemini Integration

Provides async interface to Google Gemini 1.5 Flash for product recommendations.
Includes token counting, cost tracking, retry logic, and safety filter handling.
"""

import asyncio
from typing import List, Dict, Optional, Any

import google.generativeai as genai
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from backend.config.settings import settings


class GeminiAssistant:
    """
    Async Gemini LLM handler for product recommendations.
    
    Uses Gemini 1.5 Flash with search context injection.
    All public methods are async for FastAPI compatibility.
    
    Attributes:
        model: Gemini GenerativeModel instance
        model_name: Name of the Gemini model
        max_tokens: Maximum tokens per request (cost control)
        temperature: Response creativity (0.0-1.0)
    """
    
    # Gemini 1.5 Flash pricing (December 2024)
    # Input: $0.075 per 1M tokens, Output: $0.30 per 1M tokens
    INPUT_COST_PER_TOKEN = 0.075 / 1_000_000
    OUTPUT_COST_PER_TOKEN = 0.30 / 1_000_000
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Gemini API key (default: from settings)
        """
        self.api_key = api_key or getattr(settings, 'gemini_api_key', None)
        self.model_name = getattr(settings, 'gemini_model', 'gemini-2.0-flash')
        self.max_tokens = getattr(settings, 'gemini_token_limit_per_request', 4000)
        self.temperature = getattr(settings, 'gemini_temperature', 0.7)
        self.max_output_tokens = getattr(settings, 'gemini_max_tokens', 1024)
        
        self.model = None
        
        if not self.api_key:
            logger.warning("Gemini API key missing - fallback mode enabled")
        else:
            try:
                genai.configure(api_key=self.api_key)
                # Use models/ prefix for newer API versions
                model_path = self.model_name
                if not model_path.startswith("models/"):
                    model_path = f"models/{model_path}"
                self.model = genai.GenerativeModel(
                    model_path,
                    generation_config={
                        "temperature": self.temperature,
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": self.max_output_tokens,
                    }
                )
                logger.info(f"Gemini initialized: {model_path}")
            except Exception as e:
                logger.error(f"Gemini init failed: {e}")
                self.model = None
    
    def _build_prompt(self, user_query: str, products: List[Dict]) -> str:
        """
        Build seller persona prompt with product context.
        
        Args:
            user_query: User's search query
            products: Relevant products from LanceDB search
            
        Returns:
            Formatted prompt string
        """
        system_prompt = """You are a friendly shopping assistant for an Indian e-commerce platform.

Your role:
- Recommend products based on the customer's query
- Highlight key features and prices in Indian Rupees (Rs.)
- Compare options if multiple products match
- Be conversational but concise (2-3 sentences per product)
- Use emojis sparingly (1-2 per response)
- Always show prices with commas (e.g., Rs.1,29,999)

Customer asked: "{query}"

Available products:
{products}

Provide a natural recommendation. If multiple products match, compare them briefly. If no products match well, suggest alternatives or ask clarifying questions."""

        # Format products (max 5)
        product_text = ""
        for i, p in enumerate(products[:5], 1):
            product_text += f"\n{i}. **{p.get('name', 'Unknown')}**\n"
            product_text += f"   Price: Rs.{float(p.get('price', 0)):,.0f}\n"
            product_text += f"   Category: {p.get('category', 'N/A')}\n"
            product_text += f"   Description: {p.get('description', 'No description')}\n"
            stock = p.get('stock', 0)
            if stock < 5 and stock > 0:
                product_text += f"   Low stock: {stock} left\n"
            elif stock == 0:
                product_text += f"   Out of stock\n"
        
        if not product_text:
            product_text = "No products available matching this query."
        
        return system_prompt.format(query=user_query, products=product_text)
    
    async def _count_tokens_async(self, text: str) -> int:
        """
        Count tokens using Gemini's built-in counter.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Token count (int)
        """
        if not self.model:
            # Fallback: rough estimate (4 chars per token)
            return len(text) // 4
        
        try:
            # Run blocking Gemini call in thread pool
            result = await asyncio.to_thread(
                self.model.count_tokens, text
            )
            return result.total_tokens
        except Exception as e:
            logger.warning(f"Token counting failed: {e}, using estimate")
            return len(text) // 4
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    async def _call_gemini_async(self, prompt: str) -> str:
        """
        Call Gemini API with async retry logic.
        
        Args:
            prompt: Formatted prompt
            
        Returns:
            Generated response text
            
        Raises:
            Exception: After 3 failed retries or safety block
        """
        if not self.model:
            raise RuntimeError("Gemini model not initialized")
        
        try:
            # Run blocking Gemini call in thread pool
            response = await asyncio.to_thread(
                self.model.generate_content, prompt
            )
            
            # Check for safety filter blocks
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.finish_reason.name == "SAFETY":
                    logger.warning("Gemini response blocked by safety filters")
                    raise ValueError("Response blocked by safety filters")
            
            # Check if response has text
            if not response.text:
                logger.warning("Gemini returned empty response")
                raise ValueError("Empty response from Gemini")
            
            return response.text
            
        except ValueError:
            # Re-raise safety/empty response errors
            raise
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    async def generate_recommendation(
        self,
        user_query: str,
        products: List[Dict],
        user_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate async product recommendation using Gemini.
        
        Args:
            user_query: User's natural language query
            products: Relevant products from search (List[Dict])
            user_phone: User identifier for cost tracking
            
        Returns:
            Dict with keys:
                - response (str): Generated recommendation
                - tokens_used (int): Total tokens consumed
                - cost_usd (float): Estimated cost in USD
                - products_count (int): Number of products shown
        """
        # Fallback if no model
        if not self.model:
            return await self._fallback_response(user_query, products)
        
        try:
            # Build prompt
            prompt = self._build_prompt(user_query, products)
            
            # Count input tokens
            input_tokens = await self._count_tokens_async(prompt)
            
            # Check token limit - truncate products if needed
            if input_tokens > self.max_tokens:
                logger.warning(f"Prompt too long ({input_tokens} tokens), truncating")
                products = products[:3]
                prompt = self._build_prompt(user_query, products)
                input_tokens = await self._count_tokens_async(prompt)
            
            logger.info(f"Calling Gemini (input: {input_tokens} tokens)")
            
            # Call Gemini with retry
            response_text = await self._call_gemini_async(prompt)
            
            # Count output tokens
            output_tokens = await self._count_tokens_async(response_text)
            total_tokens = input_tokens + output_tokens
            
            # Calculate cost
            cost_usd = (
                (input_tokens * self.INPUT_COST_PER_TOKEN) +
                (output_tokens * self.OUTPUT_COST_PER_TOKEN)
            )
            
            logger.info(f"Generated: {output_tokens} tokens, ${cost_usd:.6f}")
            
            # Log usage asynchronously (don't block on failure)
            try:
                from backend.rag.cost_tracker import log_llm_cost
                await log_llm_cost(
                    user_phone=user_phone,
                    model=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd
                )
            except Exception as e:
                logger.warning(f"Cost tracking failed: {e}")
            
            return {
                "response": response_text,
                "tokens_used": total_tokens,
                "cost_usd": cost_usd,
                "products_count": len(products)
            }
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return await self._fallback_response(user_query, products)
    
    async def _fallback_response(
        self,
        user_query: str,
        products: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate simple response without LLM.
        
        Used when Gemini is unavailable or fails.
        
        Args:
            user_query: User's query
            products: Search results
            
        Returns:
            Fallback response dict
        """
        if not products:
            response = (
                f"Sorry, I couldn't find products matching '{user_query}'. "
                f"Try searching for Electronics, Clothing, or Home items!"
            )
        else:
            response = f"Found {len(products)} products for '{user_query}':\n\n"
            for i, p in enumerate(products[:5], 1):
                name = p.get('name', 'Unknown')
                price = float(p.get('price', 0))
                response += f"{i}. {name} - Rs.{price:,.0f}\n"
            response += "\nType 'cart' to view your cart!"
        
        return {
            "response": response,
            "tokens_used": 0,
            "cost_usd": 0.0,
            "products_count": len(products)
        }
    
    async def health_check(self) -> bool:
        """
        Check if Gemini is available.
        
        Returns:
            True if model is initialized and responsive
        """
        if not self.model:
            return False
        
        try:
            # Simple test call
            tokens = await self._count_tokens_async("test")
            return tokens > 0
        except Exception:
            return False


# Singleton instance
_assistant: Optional[GeminiAssistant] = None


def get_gemini_assistant() -> GeminiAssistant:
    """
    Get or create GeminiAssistant singleton.
    
    Returns:
        GeminiAssistant: Singleton instance
    """
    global _assistant
    if _assistant is None:
        _assistant = GeminiAssistant()
    return _assistant


def reset_gemini_assistant() -> None:
    """Reset the singleton (useful for testing)."""
    global _assistant
    _assistant = None
