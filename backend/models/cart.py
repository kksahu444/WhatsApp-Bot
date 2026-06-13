"""
Cart Models
Pydantic models for shopping cart
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class CartItemBase(BaseModel):
    """Base cart item model."""
    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(..., ge=1, le=99, description="Item quantity")


class CartItemCreate(CartItemBase):
    """Model for adding item to cart."""
    pass


class CartItem(CartItemBase):
    """Full cart item with product details."""
    id: str = Field(..., description="Cart item ID")
    product_name: str = Field(..., description="Product name")
    product_price: float = Field(..., description="Unit price")
    product_image_url: Optional[str] = Field(None, description="Product image")
    subtotal: float = Field(..., description="Item subtotal")
    added_at: datetime = Field(..., description="When item was added")
    
    class Config:
        from_attributes = True


class Cart(BaseModel):
    """Shopping cart model."""
    id: str = Field(..., description="Cart ID")
    user_phone: str = Field(..., description="User phone number (hashed)")
    items: List[CartItem] = Field(default_factory=list, description="Cart items")
    total_items: int = Field(default=0, description="Total number of items")
    subtotal: float = Field(default=0.0, description="Cart subtotal")
    currency: str = Field(default="INR", description="Currency")
    created_at: datetime = Field(..., description="Cart creation time")
    updated_at: datetime = Field(..., description="Last update time")
    expires_at: Optional[datetime] = Field(None, description="Cart expiry time")
    
    class Config:
        from_attributes = True


class CartSummary(BaseModel):
    """Lightweight cart summary."""
    id: str
    total_items: int
    subtotal: float
    currency: str
    item_count: int = Field(..., description="Number of unique items")


class CartUpdateQuantity(BaseModel):
    """Model for updating item quantity."""
    product_id: str = Field(..., description="Product ID")
    quantity: int = Field(..., ge=0, le=99, description="New quantity (0 to remove)")


class CartClear(BaseModel):
    """Model for clearing cart."""
    confirm: bool = Field(..., description="Confirmation flag")
