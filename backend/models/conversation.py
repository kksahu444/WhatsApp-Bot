"""
Conversation Models
Pydantic models for conversation tracking
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class Intent(str, Enum):
    """Message intent classification."""
    GREETING = "greeting"
    PRODUCT_SEARCH = "product_search"
    PRODUCT_INFO = "product_info"
    ADD_TO_CART = "add_to_cart"
    VIEW_CART = "view_cart"
    UPDATE_CART = "update_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    CHECKOUT = "checkout"
    ORDER_STATUS = "order_status"
    HELP = "help"
    SUPPORT = "support"
    COMPLAINT = "complaint"
    UNKNOWN = "unknown"


class MessageRole(str, Enum):
    """Message sender role."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """Chat message model."""
    id: str = Field(..., description="Message ID")
    role: MessageRole = Field(..., description="Sender role")
    content: str = Field(..., description="Message content")
    intent: Optional[Intent] = Field(None, description="Detected intent")
    timestamp: datetime = Field(..., description="Message timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        from_attributes = True


class Conversation(BaseModel):
    """Conversation thread model."""
    id: str = Field(..., description="Conversation ID")
    user_phone: str = Field(..., description="User phone (hashed)")
    messages: List[Message] = Field(default_factory=list, description="Message history")
    
    # Context
    current_intent: Optional[Intent] = Field(None, description="Current conversation intent")
    context: Dict[str, Any] = Field(default_factory=dict, description="Conversation context")
    
    # State
    is_active: bool = Field(default=True, description="Conversation is active")
    needs_human: bool = Field(default=False, description="Needs human support")
    
    # Timestamps
    created_at: datetime = Field(..., description="Conversation start")
    updated_at: datetime = Field(..., description="Last activity")
    
    class Config:
        from_attributes = True


class ConversationContext(BaseModel):
    """Context passed between message handlers."""
    conversation_id: str
    user_phone: str
    current_cart_id: Optional[str] = None
    last_intent: Optional[Intent] = None
    last_product_id: Optional[str] = None
    last_search_results: List[str] = Field(default_factory=list)
    pending_action: Optional[str] = None
    
    class Config:
        from_attributes = True


class IntentClassification(BaseModel):
    """Intent classification result."""
    intent: Intent
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    
    # Entities can include:
    # - product_name: str
    # - product_id: str
    # - quantity: int
    # - order_number: str
    # - action: str (add, remove, update)
