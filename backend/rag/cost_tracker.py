"""
Cost Tracker - Async LLM Usage Logging

Logs LLM token usage and costs to Supabase llm_costs table.
Provides async functions for cost tracking and analytics.
"""

import asyncio
from datetime import datetime, date
from typing import Optional
from calendar import monthrange

from loguru import logger

from backend.database.supabase_client import get_supabase_client


async def log_llm_cost(
    user_phone: Optional[str],
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float
) -> bool:
    """
    Log LLM usage to llm_costs table (async).
    
    Args:
        user_phone: User identifier (can be None)
        model: Model name (e.g., "gemini-1.5-flash")
        input_tokens: Input token count
        output_tokens: Output token count
        cost_usd: Estimated cost in USD
        
    Returns:
        True if logged successfully, False otherwise
    """
    try:
        # Get sync client and wrap in thread
        client = get_supabase_client()
        
        data = {
            "user_phone": user_phone or "anonymous",
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost": float(cost_usd),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Run sync Supabase call in thread pool
        result = await asyncio.to_thread(
            lambda: client.table("llm_costs").insert(data).execute()
        )
        
        logger.debug(
            f"Logged: {input_tokens + output_tokens} tokens, ${cost_usd:.6f}"
        )
        return True
        
    except Exception as e:
        logger.warning(f"Cost logging failed: {e}")
        return False


async def get_daily_cost_summary(target_date: Optional[date] = None) -> dict:
    """
    Get cost summary for a specific date (async).
    
    Args:
        target_date: Date to query (default: today)
        
    Returns:
        Dict with daily stats: {
            "date": "2024-12-04",
            "total_calls": 150,
            "total_tokens": 45000,
            "total_cost_usd": 0.0234,
            "total_cost_inr": 1.95,
            "avg_tokens_per_call": 300
        }
    """
    try:
        if target_date is None:
            target_date = datetime.utcnow().date()
        
        date_str = target_date.isoformat()
        client = get_supabase_client()
        
        # Run sync Supabase call in thread pool
        result = await asyncio.to_thread(
            lambda: client.table("llm_costs")
                .select("*")
                .gte("timestamp", f"{date_str}T00:00:00Z")
                .lte("timestamp", f"{date_str}T23:59:59Z")
                .execute()
        )
        
        records = result.data
        
        if not records:
            return {
                "date": date_str,
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "total_cost_inr": 0.0,
                "avg_tokens_per_call": 0
            }
        
        total_tokens = sum(r["total_tokens"] for r in records)
        total_cost_usd = sum(float(r["estimated_cost"]) for r in records)
        total_calls = len(records)
        
        return {
            "date": date_str,
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost_usd, 6),
            "total_cost_inr": round(total_cost_usd * 83, 2),
            "avg_tokens_per_call": round(total_tokens / total_calls) if total_calls > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to get daily summary: {e}")
        return {
            "date": target_date.isoformat() if target_date else "unknown",
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "total_cost_inr": 0.0,
            "avg_tokens_per_call": 0,
            "error": str(e)
        }


async def get_monthly_cost_summary(year: int, month: int) -> dict:
    """
    Get cost summary for entire month (async).
    
    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)
        
    Returns:
        Dict with monthly stats: {
            "year": 2024,
            "month": 12,
            "total_calls": 4500,
            "total_tokens": 1350000,
            "total_cost_usd": 0.70,
            "total_cost_inr": 58.10
        }
    """
    try:
        days_in_month = monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{days_in_month}"
        
        client = get_supabase_client()
        
        # Run sync Supabase call in thread pool
        result = await asyncio.to_thread(
            lambda: client.table("llm_costs")
                .select("*")
                .gte("timestamp", f"{start_date}T00:00:00Z")
                .lte("timestamp", f"{end_date}T23:59:59Z")
                .execute()
        )
        
        records = result.data
        
        if not records:
            return {
                "year": year,
                "month": month,
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "total_cost_inr": 0.0
            }
        
        total_tokens = sum(r["total_tokens"] for r in records)
        total_cost_usd = sum(float(r["estimated_cost"]) for r in records)
        
        return {
            "year": year,
            "month": month,
            "total_calls": len(records),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost_usd, 2),
            "total_cost_inr": round(total_cost_usd * 83, 2)
        }
        
    except Exception as e:
        logger.error(f"Monthly summary failed: {e}")
        return {
            "year": year,
            "month": month,
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "total_cost_inr": 0.0,
            "error": str(e)
        }


async def get_user_usage(user_phone: str, limit: int = 100) -> dict:
    """
    Get usage history for a specific user (async).
    
    Args:
        user_phone: User phone number
        limit: Maximum records to return
        
    Returns:
        Dict with user stats and recent usage
    """
    try:
        client = get_supabase_client()
        
        # Run sync Supabase call in thread pool
        result = await asyncio.to_thread(
            lambda: client.table("llm_costs")
                .select("*")
                .eq("user_phone", user_phone)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
        )
        
        records = result.data
        
        if not records:
            return {
                "user_phone": user_phone,
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "recent_usage": []
            }
        
        total_tokens = sum(r["total_tokens"] for r in records)
        total_cost_usd = sum(float(r["estimated_cost"]) for r in records)
        
        return {
            "user_phone": user_phone,
            "total_calls": len(records),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost_usd, 6),
            "recent_usage": records[:10]
        }
        
    except Exception as e:
        logger.error(f"User usage query failed: {e}")
        return {
            "user_phone": user_phone,
            "total_calls": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "recent_usage": [],
            "error": str(e)
        }


async def check_budget_exceeded(
    daily_budget_usd: float = 1.0,
    monthly_budget_usd: float = 25.0
) -> dict:
    """
    Check if budget limits have been exceeded (async).
    
    Args:
        daily_budget_usd: Daily budget in USD
        monthly_budget_usd: Monthly budget in USD
        
    Returns:
        Dict with budget status: {
            "daily_exceeded": False,
            "monthly_exceeded": False,
            "daily_usage_usd": 0.05,
            "monthly_usage_usd": 1.20,
            "daily_remaining_usd": 0.95,
            "monthly_remaining_usd": 23.80
        }
    """
    try:
        today = datetime.utcnow()
        
        # Get daily usage
        daily_summary = await get_daily_cost_summary(today.date())
        daily_usage = daily_summary.get("total_cost_usd", 0.0)
        
        # Get monthly usage
        monthly_summary = await get_monthly_cost_summary(today.year, today.month)
        monthly_usage = monthly_summary.get("total_cost_usd", 0.0)
        
        return {
            "daily_exceeded": daily_usage >= daily_budget_usd,
            "monthly_exceeded": monthly_usage >= monthly_budget_usd,
            "daily_usage_usd": daily_usage,
            "monthly_usage_usd": monthly_usage,
            "daily_remaining_usd": max(0, daily_budget_usd - daily_usage),
            "monthly_remaining_usd": max(0, monthly_budget_usd - monthly_usage),
            "daily_budget_usd": daily_budget_usd,
            "monthly_budget_usd": monthly_budget_usd
        }
        
    except Exception as e:
        logger.error(f"Budget check failed: {e}")
        return {
            "daily_exceeded": False,
            "monthly_exceeded": False,
            "error": str(e)
        }
