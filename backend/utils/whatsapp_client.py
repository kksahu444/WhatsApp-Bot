"""
WhatsApp Client
Send messages via WhatsApp (through Node.js bot or Meta API)
"""

import logging
from typing import Optional, List, Dict, Any

import httpx

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """Client for sending WhatsApp messages."""
    
    def __init__(self):
        self.transport = settings.WHATSAPP_TRANSPORT
        self.bot_url = "http://localhost:3000"  # Node.js bot URL
        self.meta_token = settings.META_WHATSAPP_TOKEN
        self.phone_number_id = settings.META_PHONE_NUMBER_ID
        
    async def send_message(
        self,
        to: str,
        message: str,
        message_type: str = "text"
    ) -> bool:
        """
        Send a text message.
        
        Args:
            to: Recipient phone number
            message: Message text
            message_type: Type of message
        
        Returns:
            True if sent successfully
        """
        if self.transport == "meta":
            return await self._send_meta(to, message)
        else:
            return await self._send_wwebjs(to, message)
    
    async def send_buttons(
        self,
        to: str,
        body: str,
        buttons: List[Dict[str, str]]
    ) -> bool:
        """
        Send interactive buttons message.
        
        Args:
            to: Recipient phone number
            body: Message body
            buttons: List of button options [{"id": "...", "title": "..."}]
        
        Returns:
            True if sent successfully
        """
        if self.transport == "meta":
            return await self._send_meta_buttons(to, body, buttons)
        else:
            # wwebjs doesn't support buttons in the same way
            # Fall back to numbered list
            button_text = "\n".join(
                f"{i+1}. {btn['title']}" 
                for i, btn in enumerate(buttons)
            )
            return await self._send_wwebjs(to, f"{body}\n\n{button_text}")
    
    async def send_list(
        self,
        to: str,
        body: str,
        button_text: str,
        sections: List[Dict[str, Any]]
    ) -> bool:
        """
        Send interactive list message.
        
        Args:
            to: Recipient phone number
            body: Message body
            button_text: Text for the list button
            sections: List sections with rows
        
        Returns:
            True if sent successfully
        """
        if self.transport == "meta":
            return await self._send_meta_list(to, body, button_text, sections)
        else:
            # Fall back to text list
            text = body + "\n"
            for section in sections:
                text += f"\n*{section.get('title', '')}*\n"
                for row in section.get("rows", []):
                    text += f"• {row['title']}\n"
            return await self._send_wwebjs(to, text)
    
    async def send_image(
        self,
        to: str,
        image_url: str,
        caption: Optional[str] = None
    ) -> bool:
        """
        Send an image message.
        
        Args:
            to: Recipient phone number
            image_url: URL of the image
            caption: Optional caption
        
        Returns:
            True if sent successfully
        """
        if self.transport == "meta":
            return await self._send_meta_media(to, "image", image_url, caption)
        else:
            return await self._send_wwebjs_media(to, "image", image_url, caption)
    
    # =========================================================================
    # WWEBJS TRANSPORT
    # =========================================================================
    
    async def _send_wwebjs(self, to: str, message: str) -> bool:
        """Send via whatsapp-web.js bot."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.bot_url}/send",
                    json={
                        "to": to,
                        "message": message
                    },
                    timeout=30.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send via wwebjs: {e}")
            return False
    
    async def _send_wwebjs_media(
        self,
        to: str,
        media_type: str,
        url: str,
        caption: Optional[str]
    ) -> bool:
        """Send media via wwebjs."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.bot_url}/send-media",
                    json={
                        "to": to,
                        "type": media_type,
                        "url": url,
                        "caption": caption
                    },
                    timeout=60.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send media via wwebjs: {e}")
            return False
    
    # =========================================================================
    # META CLOUD API TRANSPORT
    # =========================================================================
    
    async def _send_meta(self, to: str, message: str) -> bool:
        """Send via Meta Cloud API."""
        if not self.meta_token or not self.phone_number_id:
            logger.error("Meta API credentials not configured")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages",
                    headers={
                        "Authorization": f"Bearer {self.meta_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "text",
                        "text": {"body": message}
                    },
                    timeout=30.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send via Meta API: {e}")
            return False
    
    async def _send_meta_buttons(
        self,
        to: str,
        body: str,
        buttons: List[Dict[str, str]]
    ) -> bool:
        """Send buttons via Meta API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages",
                    headers={
                        "Authorization": f"Bearer {self.meta_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "interactive",
                        "interactive": {
                            "type": "button",
                            "body": {"text": body},
                            "action": {
                                "buttons": [
                                    {
                                        "type": "reply",
                                        "reply": {
                                            "id": btn["id"],
                                            "title": btn["title"][:20]
                                        }
                                    }
                                    for btn in buttons[:3]  # Max 3 buttons
                                ]
                            }
                        }
                    },
                    timeout=30.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send buttons via Meta API: {e}")
            return False
    
    async def _send_meta_list(
        self,
        to: str,
        body: str,
        button_text: str,
        sections: List[Dict[str, Any]]
    ) -> bool:
        """Send list via Meta API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages",
                    headers={
                        "Authorization": f"Bearer {self.meta_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "interactive",
                        "interactive": {
                            "type": "list",
                            "body": {"text": body},
                            "action": {
                                "button": button_text[:20],
                                "sections": sections[:10]  # Max 10 sections
                            }
                        }
                    },
                    timeout=30.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send list via Meta API: {e}")
            return False
    
    async def _send_meta_media(
        self,
        to: str,
        media_type: str,
        url: str,
        caption: Optional[str]
    ) -> bool:
        """Send media via Meta API."""
        try:
            media_obj = {"link": url}
            if caption:
                media_obj["caption"] = caption
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages",
                    headers={
                        "Authorization": f"Bearer {self.meta_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": media_type,
                        media_type: media_obj
                    },
                    timeout=60.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send media via Meta API: {e}")
            return False
