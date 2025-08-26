"""
Slack webhook API routes.
"""

from fastapi import APIRouter, Request, HTTPException, status
from app.slack.webhook import get_webhook_handler

router = APIRouter(prefix="/slack", tags=["slack"])


@router.post("/")
async def slack_webhook(request: Request):
    """Slack webhook endpoint for receiving events."""
    webhook_handler = get_webhook_handler()
    return await webhook_handler.handle_webhook(request)


@router.get("/")
async def slack_webhook_get():
    """Handle GET requests to Slack webhook (for verification)."""
    return {"message": "Slack webhook endpoint is active"}


@router.post("/events")
async def slack_events(request: Request):
    """Alternative endpoint for Slack events."""
    webhook_handler = get_webhook_handler()
    return await webhook_handler.handle_webhook(request)
