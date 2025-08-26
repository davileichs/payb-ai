"""
Main Slack bot class for handling Slack interactions.
"""

import logging
from typing import Dict, Any, Optional
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.signature import SignatureVerifier
from app.config import get_settings
from app.core.chat_processor import get_chat_processor
from app.core.conversation_manager import get_conversation_manager

logger = logging.getLogger(__name__)


class SlackBot:
    """Main Slack bot class for handling interactions."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncWebClient(token=self.settings.slack_bot_token)
        self.signature_verifier = SignatureVerifier(self.settings.slack_signing_secret)
        self.chat_processor = get_chat_processor()
        self.conversation_manager = get_conversation_manager()
    
    def verify_signature(self, body: str, headers: Dict[str, str]) -> bool:
        """Verify Slack request signature."""
        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")
        
        return self.signature_verifier.is_valid(body, timestamp, signature)
    
    async def handle_message_event(self, event: Dict[str, Any]) -> None:
        """Handle Slack message events."""
        try:
            # Ignore bot messages to prevent loops
            if event.get("bot_id"):
                return
            
            # Get message details
            channel = event.get("channel")
            user = event.get("user")
            text = event.get("text", "").strip()
            
            if not text or not channel or not user:
                return
            
            # Ignore messages that don't mention the bot (if configured)
            # For now, we'll respond to all messages in channels the bot is in
            
            logger.info(f"Processing message from {user} in {channel}: {text}")
            
            # Process message with AI using conversation manager
            result = await self.chat_processor.process_message(
                message=text,
                user_id=user,
                channel_id=channel
            )
            
            # Send response back to Slack
            await self.send_message(
                channel=channel,
                text=result["response"],
                thread_ts=event.get("ts")  # Reply in thread
            )
            
            logger.info(f"Sent response to {channel}: {result['response'][:100]}...")
            
        except Exception as e:
            logger.error(f"Error handling message event: {str(e)}")
            # Send error message to user
            try:
                await self.send_message(
                    channel=event.get("channel"),
                    text="Sorry, I encountered an error processing your message. Please try again.",
                    thread_ts=event.get("ts")
                )
            except:
                pass
    
    async def send_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send a message to a Slack channel."""
        try:
            response = await self.client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts,
                **kwargs
            )
            
            if not response["ok"]:
                logger.error(f"Failed to send message: {response.get('error')}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise
    
    async def handle_url_verification(self, challenge: str) -> str:
        """Handle Slack URL verification challenge."""
        return challenge
    
    def is_bot_message(self, event: Dict[str, Any]) -> bool:
        """Check if the message is from a bot."""
        return bool(event.get("bot_id") or event.get("subtype") == "bot_message")
    
    def get_conversation_key(self, channel: str, user: str) -> str:
        """Get the conversation key for a channel/user combination."""
        return f"{channel}:{user}"
    
    def clear_conversation(self, channel: str, user: str) -> None:
        """Clear conversation history for a specific channel/user."""
        self.conversation_manager.clear_conversation(user_id=user, channel_id=channel)
        logger.info(f"Cleared conversation for {channel}:{user}")


# Global Slack bot instance
slack_bot = SlackBot()


def get_slack_bot() -> SlackBot:
    """Get the global Slack bot instance."""
    return slack_bot
