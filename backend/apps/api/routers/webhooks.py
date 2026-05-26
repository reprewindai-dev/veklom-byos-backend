"""Webhook endpoints for external integrations."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/resend")
async def resend_webhook(request: Request):
    """
    Handle Resend email delivery webhooks.
    
    This endpoint receives webhook events from Resend such as:
    - Email delivery status
    - Bounces
    - Complaints
    - Opens/Clicks
    
    Reference: https://resend.com/docs/api-reference/webhooks
    """
    try:
        # Verify webhook signature if RESEND_WEBHOOK_SECRET is set
        # For now, we'll just log the event
        payload = await request.json()
        logger.info(f"Resend webhook received: {payload}")
        
        # Process the webhook event
        event_type = payload.get("type")
        event_data = payload.get("data", {})
        
        if event_type == "email.delivered":
            logger.info(f"Email delivered: {event_data.get('email_id')}")
        elif event_type == "email.bounced":
            logger.warning(f"Email bounced: {event_data.get('email_id')}, reason: {event_data.get('reason')}")
        elif event_type == "email.complained":
            logger.warning(f"Email complained: {event_data.get('email_id')}")
        elif event_type == "email.opened":
            logger.info(f"Email opened: {event_data.get('email_id')}")
        elif event_type == "email.clicked":
            logger.info(f"Email clicked: {event_data.get('email_id')}")
        
        return JSONResponse(content={"received": True}, status_code=200)
        
    except Exception as e:
        logger.error(f"Error processing Resend webhook: {str(e)}")
        return JSONResponse(content={"error": "Webhook processing failed"}, status_code=500)
