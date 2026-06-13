"""
API Client Utility
Handles communication with the backend API
"""

import httpx
import os
from typing import Optional, Dict, Any
import streamlit as st


class APIClient:
    """HTTP client for backend API."""
    
    def __init__(self):
        self.base_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        self.api_key = os.getenv('BACKEND_API_KEY', '')
        self.timeout = 30.0
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            'Content-Type': 'application/json',
        }
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers(),
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make POST request."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers(),
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make PUT request."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.put(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers(),
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
    
    # Synchronous versions for Streamlit
    def get_sync(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make synchronous GET request."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers(),
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    def post_sync(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make synchronous POST request."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers(),
                json=data
            )
            response.raise_for_status()
            return response.json()


@st.cache_resource
def get_api_client() -> APIClient:
    """Get cached API client instance."""
    return APIClient()
