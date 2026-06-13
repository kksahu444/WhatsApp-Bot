"""
WhatsApp Integration Module.

Components:
- client: Send messages via Meta Cloud API
- webhook: Handle incoming webhook payloads
- message_formatter: Format messages for WhatsApp
"""

from .client import get_whatsapp_client, WhatsAppClient
from .webhook import get_webhook_handler, WhatsAppWebhookHandler
from .message_formatter import get_message_formatter, WhatsAppMessageFormatter

__all__ = [
    "get_whatsapp_client",
    "WhatsAppClient",
    "get_webhook_handler", 
    "WhatsAppWebhookHandler",
    "get_message_formatter",
    "WhatsAppMessageFormatter",
]
