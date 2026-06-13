"""
Supabase Database Utility
=========================
Direct connection to Supabase for dashboard queries.
Separate from backend to ensure container isolation.
"""

import os
from typing import Optional, List, Dict, Any
from functools import lru_cache

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase_client() -> Client:
    """
    Get cached Supabase client.
    Uses Streamlit's cache_resource for connection pooling.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError(
            "Missing Supabase credentials. "
            "Set SUPABASE_URL and SUPABASE_KEY environment variables."
        )
    
    return create_client(url, key)


def fetch_conversations(
    limit: int = 50,
    phone_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch recent conversations from Supabase.
    
    Args:
        limit: Maximum number of rows to fetch
        phone_filter: Optional phone number to filter by
        
    Returns:
        List of conversation records
    """
    client = get_supabase_client()
    
    query = client.table("conversations").select("*")
    
    if phone_filter and phone_filter != "All":
        query = query.eq("user_phone", phone_filter)
    
    query = query.order("created_at", desc=True).limit(limit)
    
    response = query.execute()
    return response.data if response.data else []


def fetch_unique_phones() -> List[str]:
    """
    Fetch unique phone numbers from conversations.
    
    Returns:
        List of unique phone numbers
    """
    client = get_supabase_client()
    
    # Fetch distinct phone numbers
    response = client.table("conversations").select("user_phone").execute()
    
    if not response.data:
        return []
    
    # Extract unique phones
    phones = list(set(row["user_phone"] for row in response.data if row.get("user_phone")))
    phones.sort()
    
    return phones


def fetch_orders(
    limit: int = 100,
    status_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch orders from Supabase.
    
    Args:
        limit: Maximum number of rows to fetch
        status_filter: Optional status to filter by
        
    Returns:
        List of order records
    """
    client = get_supabase_client()
    
    query = client.table("orders").select("*")
    
    if status_filter and status_filter != "All":
        query = query.eq("status", status_filter)
    
    query = query.order("created_at", desc=True).limit(limit)
    
    response = query.execute()
    return response.data if response.data else []


def fetch_analytics_events(
    event_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Fetch analytics events from Supabase.
    
    Args:
        event_type: Optional event type to filter by
        limit: Maximum number of rows to fetch
        
    Returns:
        List of analytics event records
    """
    client = get_supabase_client()
    
    query = client.table("analytics_events").select("*")
    
    if event_type and event_type != "All":
        query = query.eq("event_type", event_type)
    
    query = query.order("created_at", desc=True).limit(limit)
    
    response = query.execute()
    return response.data if response.data else []


def get_dashboard_stats() -> Dict[str, Any]:
    """
    Get aggregated stats for dashboard overview.
    
    Returns:
        Dictionary with various stats
    """
    client = get_supabase_client()
    
    stats = {}
    
    try:
        # Total orders
        orders = client.table("orders").select("id", count="exact").execute()
        stats["total_orders"] = orders.count if orders.count else 0
        
        # Pending orders
        pending = client.table("orders").select("id", count="exact").eq("status", "pending").execute()
        stats["pending_orders"] = pending.count if pending.count else 0
        
        # Total conversations
        convos = client.table("conversations").select("id", count="exact").execute()
        stats["total_conversations"] = convos.count if convos.count else 0
        
        # Unique users (approximate)
        users = client.table("conversations").select("user_phone").execute()
        if users.data:
            stats["unique_users"] = len(set(row["user_phone"] for row in users.data))
        else:
            stats["unique_users"] = 0
            
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        stats = {
            "total_orders": 0,
            "pending_orders": 0,
            "total_conversations": 0,
            "unique_users": 0
        }
    
    return stats
