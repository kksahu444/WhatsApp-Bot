"""
WhatsApp Webhook Handler.
Processes incoming messages from Meta Cloud API.
"""

from typing import Dict, Optional
from loguru import logger


class WhatsAppWebhookHandler:
    """
    Handle incoming WhatsApp webhooks.
    
    Webhook structure: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components
    """
    
    def __init__(self):
        pass
    
    def extract_message(self, webhook_data: Dict) -> Optional[Dict]:
        """
        Extract message details from webhook payload.
        
        Returns:
            Dict with keys: from_number, message_text, message_type, timestamp, message_id
            or None if no valid message found
        """
        try:
            # Navigate webhook structure (lists, not dicts!)
            entries = webhook_data.get("entry", [])
            if not entries:
                logger.warning("⚠️ No entries in webhook")
                return None
            
            changes = entries[0].get("changes", [])
            if not changes:
                logger.warning("⚠️ No changes in webhook")
                return None
            
            value = changes[0].get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                # This could be a status update, not a message
                logger.debug("📊 Webhook has no messages (likely status update)")
                return None
            
            message = messages[0]
            
            # Extract details
            from_number = message.get("from")  # Phone number (without +)
            message_id = message.get("id")  # WAMID for idempotency
            message_type = message.get("type")  # text, image, document, etc.
            timestamp = message.get("timestamp")
            
            # Extract message content based on type
            message_text = ""
            
            if message_type == "text":
                message_text = message.get("text", {}).get("body", "")
            elif message_type == "image":
                caption = message.get("image", {}).get("caption", "")
                message_text = caption if caption else "[Image received]"
            elif message_type == "document":
                message_text = "[Document received]"
            elif message_type == "audio":
                message_text = "[Audio received]"
            elif message_type == "video":
                message_text = "[Video received]"
            elif message_type == "sticker":
                message_text = "[Sticker received]"
            elif message_type == "location":
                message_text = "[Location received]"
            elif message_type == "contacts":
                message_text = "[Contact received]"
            elif message_type == "interactive":
                # Button/list response
                interactive = message.get("interactive", {})
                interactive_type = interactive.get("type")
                if interactive_type == "button_reply":
                    message_text = interactive.get("button_reply", {}).get("title", "")
                elif interactive_type == "list_reply":
                    message_text = interactive.get("list_reply", {}).get("title", "")
                else:
                    message_text = "[Interactive message]"
            else:
                message_text = f"[{message_type} message]"
            
            result = {
                "from_number": f"+{from_number}",  # Add + prefix for E.164
                "message_text": message_text,
                "message_type": message_type,
                "timestamp": timestamp,
                "message_id": message_id,  # For idempotency
                "raw_message": message
            }
            
            logger.info(f"📨 Message from {result['from_number']}: {message_text[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to extract message: {e}")
            return None
    
    def extract_status_update(self, webhook_data: Dict) -> Optional[Dict]:
        """
        Extract message status update from webhook.
        
        Returns status info (delivered, read, failed) or None.
        """
        try:
            entries = webhook_data.get("entry", [])
            if not entries:
                return None
            
            changes = entries[0].get("changes", [])
            if not changes:
                return None
            
            value = changes[0].get("value", {})
            statuses = value.get("statuses", [])
            
            if not statuses:
                return None
            
            status = statuses[0]
            
            return {
                "message_id": status.get("id"),
                "status": status.get("status"),  # sent, delivered, read, failed
                "timestamp": status.get("timestamp"),
                "recipient_id": status.get("recipient_id"),
                "conversation_id": status.get("conversation", {}).get("id"),
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to extract status: {e}")
            return None
    
    def verify_webhook(self, mode: str, token: str, challenge: str, verify_token: str) -> Optional[str]:
        """
        Verify webhook during Meta setup.
        
        Returns challenge string if verification succeeds, None otherwise.
        """
        if mode == "subscribe" and token == verify_token:
            logger.info("✅ Webhook verified successfully")
            return challenge
        else:
            logger.error("❌ Webhook verification failed")
            return None


# Singleton
_webhook_handler: Optional[WhatsAppWebhookHandler] = None


def get_webhook_handler() -> WhatsAppWebhookHandler:
    """Get webhook handler singleton."""
    global _webhook_handler
    if _webhook_handler is None:
        _webhook_handler = WhatsAppWebhookHandler()
    return _webhook_handler
