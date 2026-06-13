"""
Product Models
Pydantic models for product data
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ProductCategory(str, Enum):
    """Product categories."""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    HOME = "home"
    BEAUTY = "beauty"
    SPORTS = "sports"
    BOOKS = "books"
    OTHER = "other"


class ProductBase(BaseModel):
    """Base product model."""
    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    description: str = Field(..., min_length=1, max_length=2000, description="Product description")
    price: float = Field(..., gt=0, description="Product price")
    currency: str = Field(default="INR", description="Currency code")
    category: ProductCategory = Field(..., description="Product category")
    subcategory: Optional[str] = Field(None, max_length=100, description="Product subcategory")
    brand: Optional[str] = Field(None, max_length=100, description="Brand name")
    sku: Optional[str] = Field(None, max_length=50, description="Stock keeping unit")
    image_url: Optional[str] = Field(None, description="Product image URL")
    tags: List[str] = Field(default_factory=list, description="Product tags for search")


class ProductCreate(ProductBase):
    """Model for creating a new product."""
    stock_quantity: int = Field(default=0, ge=0, description="Available stock")
    is_active: bool = Field(default=True, description="Product is available for sale")


class ProductUpdate(BaseModel):
    """Model for updating a product."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    price: Optional[float] = Field(None, gt=0)
    category: Optional[ProductCategory] = None
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    tags: Optional[List[str]] = None
    stock_quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class Product(ProductBase):
    """Full product model with database fields."""
    id: str = Field(..., description="Product ID")
    stock_quantity: int = Field(default=0, description="Available stock")
    is_active: bool = Field(default=True, description="Product is available")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class ProductSearch(BaseModel):
    """Model for product search queries."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    category: Optional[ProductCategory] = Field(None, description="Filter by category")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    limit: int = Field(default=10, ge=1, le=50, description="Max results to return")


class ProductSearchResult(BaseModel):
    """Model for search results."""
    product: Product
    score: float = Field(..., description="Relevance score")
    snippet: Optional[str] = Field(None, description="Matching text snippet")
