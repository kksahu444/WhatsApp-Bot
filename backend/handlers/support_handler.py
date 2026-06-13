"""
Support Handler
Handle human handoff and support requests
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request

from models.webhook import WebhookResponse
from utils.security import hash_phone_number

logger = logging.getLogger(__name__)

router = APIRouter()


async def handle_support_request(
    user_phone: str,
    message: str,
    request: Request
) -> WebhookResponse:
    """
    Handle support/human handoff request.
    
    Args:
        user_phone: User's phone number
        message: User's message
        request: FastAPI request
    
    Returns:
        Response about support
    """
    try:
        phone_hash = hash_phone_number(user_phone)
        
        # Create support ticket
        ticket = await _create_support_ticket(
            phone_hash, message, request
        )
        
        response_text = "🙋 *Support Request*\n\n"
        response_text += f"Ticket #: {ticket['ticket_number']}\n\n"
        response_text += "A support agent will contact you shortly.\n"
        response_text += "Our support hours: 9 AM - 9 PM IST\n\n"
        response_text += "In the meantime, you can:\n"
        response_text += "• Type 'help' for self-service options\n"
        response_text += "• Check order status with 'order status'\n"
        response_text += "• Continue shopping"
        
        return WebhookResponse(
            success=True,
            reply=response_text,
            action="support_ticket_created",
            intent="support"
        )
        
    except Exception as e:
        logger.exception(f"Support request error: {e}")
        return WebhookResponse(
            success=True,
            reply="Our support team is currently busy.\n"
                  "Please try again later or email krishnkantsahu102@gmail.com",
            action="support_unavailable"
        )


async def _create_support_ticket(
    phone_hash: str,
    message: str,
    request: Request
) -> dict:
    """Create a support ticket in database."""
    import uuid
    from datetime import datetime
    
    ticket_number = f"TKT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    ticket_data = {
        "user_phone_hash": phone_hash,
        "status": "open",
        "priority": _determine_priority(message),
        "subject": message[:200] if message else "Support request",
    }
    
    try:
        response = request.app.state.supabase.client.table(
            "support_tickets"
        ).insert(ticket_data).execute()
        
        ticket = response.data[0] if response.data else {"id": "unknown"}
        ticket["ticket_number"] = ticket_number
        
        # Notify support team (could send to Slack, email, etc.)
        await _notify_support_team(ticket, request)
        
        return ticket
        
    except Exception as e:
        logger.error(f"Failed to create support ticket: {e}")
        return {"id": "unknown", "ticket_number": ticket_number}


def _determine_priority(message: str) -> str:
    """Determine ticket priority based on message content."""
    message_lower = message.lower()
    
    urgent_keywords = ["urgent", "emergency", "immediately", "asap", "refund"]
    high_keywords = ["complaint", "broken", "wrong", "missing", "damaged"]
    
    if any(word in message_lower for word in urgent_keywords):
        return "urgent"
    elif any(word in message_lower for word in high_keywords):
        return "high"
    else:
        return "normal"


async def _notify_support_team(ticket: dict, request: Request):
    """Notify support team of new ticket."""
    # In production, this could:
    # - Send Slack notification
    # - Send email
    # - Update dashboard in real-time
    logger.info(f"New support ticket: {ticket.get('ticket_number')}")


# REST API endpoints for support dashboard
@router.get("/tickets")
async def list_tickets(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50
):
    """List support tickets."""
    query = request.app.state.supabase.client.table("support_tickets").select("*")
    
    if status:
        query = query.eq("status", status)
    
    response = query.order("created_at", desc=True).limit(limit).execute()
    
    return {"tickets": response.data}


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, request: Request):
    """Get ticket details."""
    response = request.app.state.supabase.client.table(
        "support_tickets"
    ).select("*").eq("id", ticket_id).single().execute()
    
    return response.data


@router.patch("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    request: Request,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None
):
    """Update ticket status."""
    update_data = {}
    
    if status:
        update_data["status"] = status
        if status == "resolved":
            from datetime import datetime
            update_data["resolved_at"] = datetime.utcnow().isoformat()
    
    if assigned_to:
        update_data["assigned_to"] = assigned_to
        if "status" not in update_data:
            update_data["status"] = "in_progress"
    
    if not update_data:
        return {"error": "No updates provided"}
    
    response = request.app.state.supabase.client.table(
        "support_tickets"
    ).update(update_data).eq("id", ticket_id).execute()
    
    return response.data[0] if response.data else None


@router.get("/queue")
async def get_support_queue(request: Request):
    """Get support queue statistics."""
    supabase = request.app.state.supabase.client
    
    # Get counts by status
    open_count = len(supabase.table("support_tickets").select(
        "id"
    ).eq("status", "open").execute().data)
    
    in_progress = len(supabase.table("support_tickets").select(
        "id"
    ).eq("status", "in_progress").execute().data)
    
    urgent = len(supabase.table("support_tickets").select(
        "id"
    ).eq("priority", "urgent").neq("status", "resolved").execute().data)
    
    return {
        "open": open_count,
        "in_progress": in_progress,
        "urgent": urgent,
        "total_pending": open_count + in_progress
    }
