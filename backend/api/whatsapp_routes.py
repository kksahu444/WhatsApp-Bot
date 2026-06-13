"""
WhatsApp API Routes.
FastAPI endpoints for receiving/sending WhatsApp messages.

CRITICAL: Uses BackgroundTasks to process messages asynchronously.
Meta requires webhook response within 3 seconds or it will retry.

Features:
- Human support mode check (priority before AI processing)
- Global error handling with user-friendly messages
- Idempotency to prevent duplicate processing
"""

import os
from collections import deque
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from fastapi.responses import PlainTextResponse
from loguru import logger

from backend.whatsapp.webhook import get_webhook_handler
from backend.whatsapp.client import get_whatsapp_client
from backend.handlers.message_router import get_message_router
from backend.services.support_service import get_support_service
from backend.middleware.error_handler import (
    safe_execute_async, 
    get_user_friendly_message,
    categorize_error,
    DEFAULT_ERROR_MESSAGE
)


router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "your_secret_verify_token_123")


# Deque with maxlen for FIFO idempotency cache (auto-removes oldest when full)
_processed_messages = deque(maxlen=1000)


async def process_whatsapp_message(body: dict):
    """
    Background task to process WhatsApp message.
    
    This runs AFTER we return 200 OK to Meta, preventing timeout issues.
    LLM processing can take 5-15 seconds, which would fail the 3-second limit.
    """
    try:
        # Extract message
        handler = get_webhook_handler()
        message_data = handler.extract_message(body)
        
        if not message_data:
            # Might be a status update, not a message
            status_data = handler.extract_status_update(body)
            if status_data:
                logger.debug(f"📊 Status update: {status_data.get('status')} for {status_data.get('message_id')}")
            return
        
        from_number = message_data.get("from_number")
        message_text = message_data.get("message_text")
        message_id = message_data.get("message_id")
        
        # 1. Check idempotency (prevent duplicate processing)
        #    Meta can send the same message multiple times if our response is slow
        if not message_id:
            logger.warning("⚠️ Message has no ID, processing anyway")
        elif message_id in _processed_messages:
            logger.info(f"🔁 Duplicate message ignored: {message_id}")
            return
        
        # Add to cache (deque auto-removes oldest when > maxlen)
        if message_id:
            _processed_messages.append(message_id)
        
        logger.info(f"🔄 Processing message {message_id} from {from_number}")
        
        # 2. PRIORITY CHECK: Human Support Mode
        #    If user is in support mode, don't process with AI
        support_service = get_support_service()
        whatsapp_client = get_whatsapp_client()
        
        if await support_service.is_in_support_mode(from_number):
            # User is talking to human agent
            response = await support_service.handle_support_message(from_number, message_text)
            
            if response:
                # User requested to resume AI
                await whatsapp_client.send_text(from_number, response)
            else:
                # Still in support mode - log but don't reply
                logger.info(f"👨‍💻 Message from {from_number} forwarded to human agent (not processed)")
            return
        
        # 3. Check if user is requesting human support
        if support_service.is_support_request(message_text):
            await support_service.enable_support_mode(from_number)
            await whatsapp_client.send_text(
                from_number,
                support_service.get_support_enabled_message()
            )
            return
        
        # 4. Create inline background task handler for sheets logging
        #    We're already in a background task, so we handle additional tasks inline
        class InlineBackgroundTasks:
            """Execute tasks inline since we're already in background context."""
            def __init__(self):
                self._tasks = []
            
            def add_task(self, func, *args, **kwargs):
                self._tasks.append((func, args, kwargs))
            
            async def run_tasks(self):
                for func, args, kwargs in self._tasks:
                    try:
                        func(*args, **kwargs)  # Sync call for sheets logging
                    except Exception as e:
                        logger.error(f"❌ Inline task error: {e}")
        
        inline_tasks = InlineBackgroundTasks()
        
        # 5. Route to message handler (with timeout protection)
        message_router = get_message_router()
        response_data, success, error_msg = await safe_execute_async(
            message_router.route_message(from_number, message_text, inline_tasks),
            fallback={"success": False, "response": DEFAULT_ERROR_MESSAGE, "intent": "error"},
            operation_name="message_routing",
            timeout=15  # 15 seconds max for full processing
        )
        
        # 6. Run any queued tasks (e.g., Sheets logging)
        await inline_tasks.run_tasks()
        
        # 7. Send reply via WhatsApp
        if response_data.get("success", True):
            response_text = response_data.get("response", "")
            
            # Split long messages if needed
            if len(response_text) > 4000:
                from backend.whatsapp.message_formatter import get_message_formatter
                formatter = get_message_formatter()
                parts = formatter.split_message(response_text)
                
                for part in parts:
                    await whatsapp_client.send_text(from_number, part)
            else:
                await whatsapp_client.send_text(from_number, response_text)
        else:
            # Use error message from safe_execute or fallback
            error_response = error_msg or response_data.get("response", DEFAULT_ERROR_MESSAGE)
            await whatsapp_client.send_text(from_number, error_response)
        
        logger.info(f"✅ Processed message {message_id}")
        
    except Exception as e:
        # Global error handler - try to notify user
        category = categorize_error(e)
        error_message = get_user_friendly_message(category)
        
        logger.error(f"❌ Background processing error | Category: {category} | Error: {e}")
        
        # Try to send error message to user
        try:
            if from_number:
                whatsapp_client = get_whatsapp_client()
                await whatsapp_client.send_text(from_number, error_message)
        except Exception as send_error:
            logger.error(f"❌ Failed to send error message: {send_error}")


@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    """
    Webhook verification endpoint.
    
    Meta calls this GET endpoint when you set up the webhook.
    Must return the challenge string if token matches.
    
    Setup:
    1. Go to Meta Developer Portal → Your App → WhatsApp → Configuration
    2. Click "Edit" on Webhook
    3. Enter your callback URL: https://your-domain.com/whatsapp/webhook
    4. Enter verify token (same as WHATSAPP_VERIFY_TOKEN env var)
    5. Click "Verify and Save"
    """
    handler = get_webhook_handler()
    result = handler.verify_webhook(mode, token, challenge, VERIFY_TOKEN)
    
    if result:
        return PlainTextResponse(content=result, status_code=200)
    else:
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """
    Receive incoming WhatsApp messages.
    
    CRITICAL: Returns 200 OK immediately (within 3 seconds) to prevent Meta timeout.
    Actual message processing happens in background task.
    
    Webhook payload structure:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "919999999999",
                        "id": "wamid.xxx",
                        "type": "text",
                        "text": {"body": "hello"},
                        "timestamp": "1234567890"
                    }]
                }
            }]
        }]
    }
    """
    try:
        # Get webhook payload
        body = await request.json()
        logger.debug(f"📥 Webhook received: {body.get('object', 'unknown')}")
        
        # Validate it's from WhatsApp
        if body.get("object") != "whatsapp_business_account":
            logger.warning(f"⚠️ Unexpected webhook object: {body.get('object')}")
            return {"status": "ignored"}
        
        # Add processing to background tasks
        # This allows us to return 200 immediately while processing continues
        background_tasks.add_task(process_whatsapp_message, body)
        
        # Return 200 OK immediately (Meta requires response within 3 seconds)
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"❌ Webhook receive error: {e}")
        # Still return 200 to prevent Meta retries on our errors
        return {"status": "error"}


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "whatsapp-webhook",
        "verify_token_set": bool(os.getenv("WHATSAPP_VERIFY_TOKEN")),
        "credentials_set": bool(os.getenv("WHATSAPP_ACCESS_TOKEN") and os.getenv("WHATSAPP_PHONE_NUMBER_ID"))
    }
