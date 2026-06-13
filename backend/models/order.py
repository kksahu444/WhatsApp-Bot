"""
Order Models
Pydantic models for order processing
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
    """Order status values."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment methods."""
    COD = "cod"  # Cash on delivery
    UPI = "upi"
    CARD = "card"
    WALLET = "wallet"


class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Address(BaseModel):
    """Delivery address model."""
    name: str = Field(..., min_length=1, max_length=100, description="Recipient name")
    phone: str = Field(..., description="Contact phone")
    address_line1: str = Field(..., min_length=1, max_length=200, description="Address line 1")
    address_line2: Optional[str] = Field(None, max_length=200, description="Address line 2")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    state: str = Field(..., min_length=1, max_length=100, description="State")
    postal_code: str = Field(..., min_length=1, max_length=20, description="Postal code")
    country: str = Field(default="India", description="Country")


class OrderItem(BaseModel):
    """Order item model."""
    product_id: str = Field(..., description="Product ID")
    product_name: str = Field(..., description="Product name at time of order")
    quantity: int = Field(..., ge=1, description="Quantity ordered")
    unit_price: float = Field(..., gt=0, description="Unit price at time of order")
    subtotal: float = Field(..., description="Item subtotal")
    
    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    """Model for creating an order."""
    cart_id: str = Field(..., description="Cart ID to convert to order")
    shipping_address: Address = Field(..., description="Delivery address")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    notes: Optional[str] = Field(None, max_length=500, description="Order notes")


class Order(BaseModel):
    """Full order model."""
    id: str = Field(..., description="Order ID")
    order_number: str = Field(..., description="Human-readable order number")
    user_phone: str = Field(..., description="User phone (hashed)")
    items: List[OrderItem] = Field(..., description="Order items")
    
    # Pricing
    subtotal: float = Field(..., description="Items subtotal")
    shipping_fee: float = Field(default=0.0, description="Shipping fee")
    tax: float = Field(default=0.0, description="Tax amount")
    discount: float = Field(default=0.0, description="Discount amount")
    total: float = Field(..., description="Order total")
    currency: str = Field(default="INR", description="Currency")
    
    # Status
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Order status")
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING, description="Payment status")
    payment_method: PaymentMethod = Field(..., description="Payment method")
    
    # Address
    shipping_address: Address = Field(..., description="Shipping address")
    
    # Timestamps
    created_at: datetime = Field(..., description="Order creation time")
    updated_at: datetime = Field(..., description="Last update time")
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation time")
    shipped_at: Optional[datetime] = Field(None, description="Shipping time")
    delivered_at: Optional[datetime] = Field(None, description="Delivery time")
    
    # Notes
    notes: Optional[str] = Field(None, description="Customer notes")
    admin_notes: Optional[str] = Field(None, description="Admin notes")
    
    # Tracking
    tracking_number: Optional[str] = Field(None, description="Shipment tracking")
    tracking_url: Optional[str] = Field(None, description="Tracking URL")
    
    class Config:
        from_attributes = True


class OrderSummary(BaseModel):
    """Lightweight order summary."""
    id: str
    order_number: str
    status: OrderStatus
    total: float
    currency: str
    item_count: int
    created_at: datetime


class OrderStatusUpdate(BaseModel):
    """Model for updating order status."""
    status: OrderStatus = Field(..., description="New status")
    notes: Optional[str] = Field(None, max_length=500, description="Status update notes")
    tracking_number: Optional[str] = Field(None, description="Tracking number")
    tracking_url: Optional[str] = Field(None, description="Tracking URL")
