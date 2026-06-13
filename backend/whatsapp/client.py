"""
WhatsApp Business API Client.
Handles sending messages via Meta Cloud API.
"""

import os
import httpx
from typing import Optional
from loguru import logger


class WhatsAppClient:
    """
    WhatsApp Business API client for Meta Cloud API.
    
    Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
    """
    
    def __init__(self):
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"
        
        if not self.phone_number_id or not self.access_token:
            logger.warning("⚠️ WhatsApp credentials not configured")
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone to Meta format (digits only, no +).
        
        E.164: +919999999999 → 919999999999
        """
        return ''.join(filter(str.isdigit, phone))
    
    async def send_text(self, to: str, message: str) -> bool:
        """
        Send text message to WhatsApp user.
        
        Args:
            to: Recipient phone number (format: +919999999999)
            message: Text message to send
            
        Returns:
            bool: True if sent successfully
        """
        try:
            url = f"{self.base_url}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self._normalize_phone(to),
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": message
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                
                # Accept any 2xx status code (200, 201, etc.)
                if 200 <= response.status_code < 300:
                    logger.info(f"✅ Message sent to {to}")
                    return True
                else:
                    logger.error(f"❌ Failed to send message: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ WhatsApp send error: {e}")
            return False
    
    async def send_image(self, to: str, image_url: str, caption: str = "") -> bool:
        """Send image message."""
        try:
            url = f"{self.base_url}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": self._normalize_phone(to),
                "type": "image",
                "image": {
                    "link": image_url,
                    "caption": caption
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                return 200 <= response.status_code < 300
                
        except Exception as e:
            logger.error(f"❌ Image send error: {e}")
            return False
    
    async def send_template(self, to: str, template_name: str, language: str = "en") -> bool:
        """Send approved message template."""
        try:
            url = f"{self.base_url}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": self._normalize_phone(to),
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language}
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                return 200 <= response.status_code < 300
                
        except Exception as e:
            logger.error(f"❌ Template send error: {e}")
            return False


# Singleton
_whatsapp_client: Optional[WhatsAppClient] = None


def get_whatsapp_client() -> WhatsAppClient:
    """Get WhatsApp client singleton."""
    global _whatsapp_client
    if _whatsapp_client is None:
        _whatsapp_client = WhatsAppClient()
    return _whatsapp_client
