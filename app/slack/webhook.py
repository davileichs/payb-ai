"""
Slack webhook endpoint for receiving and processing Slack events.
"""

import logging
from typing import Dict, Any
from fastapi import Request, HTTPException, status
from app.slack.bot import get_slack_bot
from app.slack.events import get_event_handler

logger = logging.getLogger(__name__)


class SlackWebhook:
    """Handles Slack webhook requests."""
    
    def __init__(self):
        self.bot = get_slack_bot()
        self.event_handler = get_event_handler()
    
    async def handle_webhook(self, request: Request) -> Dict[str, Any]:
        """Handle incoming Slack webhook requests."""
        try:
            # Get request body and headers
            body = await request.body()
            body_str = body.decode("utf-8")
            headers = dict(request.headers)
            
            # Verify Slack signature
            if not self.bot.verify_signature(body_str, headers):
                logger.warning("Invalid Slack signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid signature"
                )
            
            # Parse the request
            form_data = await request.form()
            payload = form_data.get("payload")
            
            if not payload:
                # Handle URL verification challenge
                challenge = form_data.get("challenge")
                if challenge:
                    logger.info("Handling URL verification challenge")
                    return {"challenge": challenge}
                
                # Handle regular event
                event_type = form_data.get("type")
                if event_type == "url_verification":
                    challenge = form_data.get("challenge")
                    if challenge:
                        return {"challenge": challenge}
                
                # Handle event subscription
                event_data = form_data.get("event")
                if event_data:
                    await self._process_event(event_data)
                    return {"status": "ok"}
                
                logger.warning("No valid payload found in webhook")
                return {"status": "ok"}
            
            # Handle interactive components (buttons, menus, etc.)
            if payload:
                # For now, just acknowledge interactive components
                logger.info("Received interactive component payload")
                return {"status": "ok"}
            
            return {"status": "ok"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def _process_event(self, event_data: str) -> None:
        """Process a Slack event."""
        try:
            # Parse event data
            if isinstance(event_data, str):
                import json
                event = json.loads(event_data)
            else:
                event = event_data
            
            # Validate event
            if not self.event_handler.is_valid_event(event):
                logger.warning(f"Invalid event data: {event}")
                return
            
            # Handle the event
            await self.event_handler.handle_event(event)
            
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")


# Global webhook handler instance
webhook_handler = SlackWebhook()


def get_webhook_handler() -> SlackWebhook:
    """Get the global webhook handler instance."""
    return webhook_handler
