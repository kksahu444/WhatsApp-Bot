"""
Webhook Models
Pydantic models for webhook payloads
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    """WhatsApp message types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACT = "contact"
    BUTTON = "button"
    LIST = "list"
    INTERACTIVE = "interactive"


class WhatsAppMessage(BaseModel):
    """Incoming WhatsApp message."""
    message_id: str = Field(..., description="WhatsApp message ID")
    from_number: str = Field(..., description="Sender phone number")
    to_number: Optional[str] = Field(None, description="Recipient phone number")
    timestamp: datetime = Field(..., description="Message timestamp")
    type: MessageType = Field(..., description="Message type")
    
    # Content based on type
    text: Optional[str] = Field(None, description="Text content")
    caption: Optional[str] = Field(None, description="Media caption")
    media_url: Optional[str] = Field(None, description="Media URL")
    media_mime_type: Optional[str] = Field(None, description="Media MIME type")
    
    # Interactive message data
    button_id: Optional[str] = Field(None, description="Button ID if interactive")
    button_text: Optional[str] = Field(None, description="Button text")
    list_id: Optional[str] = Field(None, description="List selection ID")
    list_title: Optional[str] = Field(None, description="List selection title")
    
    # Location data
    latitude: Optional[float] = Field(None, description="Location latitude")
    longitude: Optional[float] = Field(None, description="Location longitude")
    location_name: Optional[str] = Field(None, description="Location name")
    
    # Metadata
    context: Optional[Dict[str, Any]] = Field(None, description="Message context")
    
    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    """Webhook payload from WhatsApp bot."""
    type: str = Field(..., description="Payload type: message, status, etc.")
    message: Optional[WhatsAppMessage] = Field(None, description="Message data")
    
    # Status update fields
    status: Optional[str] = Field(None, description="Message status")
    status_message_id: Optional[str] = Field(None, description="ID of message with status")
    
    # Error fields
    error_code: Optional[int] = Field(None, description="Error code if any")
    error_message: Optional[str] = Field(None, description="Error message")
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Payload timestamp")
    source: str = Field(default="wwebjs", description="Source: wwebjs or meta")
    
    class Config:
        from_attributes = True


class WebhookResponse(BaseModel):
    """Response to send back via webhook."""
    success: bool = Field(..., description="Processing success")
    reply: Optional[str] = Field(None, description="Text reply to send")
    reply_type: str = Field(default="text", description="Reply type")
    
    # Interactive elements
    buttons: Optional[List[Dict[str, str]]] = Field(None, description="Button options")
    list_sections: Optional[List[Dict[str, Any]]] = Field(None, description="List sections")
    
    # Media
    media_url: Optional[str] = Field(None, description="Media to send")
    media_type: Optional[str] = Field(None, description="Media type")
    caption: Optional[str] = Field(None, description="Media caption")
    
    # Metadata
    action: Optional[str] = Field(None, description="Action taken")
    intent: Optional[str] = Field(None, description="Detected intent")
    
    class Config:
        from_attributes = True


class ButtonOption(BaseModel):
    """Interactive button option."""
    id: str = Field(..., max_length=256, description="Button ID")
    title: str = Field(..., max_length=20, description="Button title")


class ListSection(BaseModel):
    """Interactive list section."""
    title: str = Field(..., max_length=24, description="Section title")
    rows: List[Dict[str, str]] = Field(..., description="Section rows")


class ListRow(BaseModel):
    """Interactive list row."""
    id: str = Field(..., max_length=200, description="Row ID")
    title: str = Field(..., max_length=24, description="Row title")
    description: Optional[str] = Field(None, max_length=72, description="Row description")
