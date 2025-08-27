import logging
from typing import Dict, Any
from app.slack.bot import get_slack_bot

logger = logging.getLogger(__name__)

class SlackEventHandler:
    
    def __init__(self):
        self.bot = get_slack_bot()
    
    async def handle_event(self, event: Dict[str, Any]) -> None:
        event_type = event.get("type")
        
        try:
            if event_type == "message":
                await self.handle_message_event(event)
            elif event_type == "app_mention":
                await self.handle_app_mention_event(event)
            elif event_type == "reaction_added":
                await self.handle_reaction_event(event)
            else:
                logger.info(f"Unhandled event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling event {event_type}: {str(e)}")
    
    async def handle_message_event(self, event: Dict[str, Any]) -> None:
        # Only handle messages in channels (not DMs for now)
        if event.get("channel_type") == "channel":
            await self.bot.handle_message_event(event)
    
    async def handle_app_mention_event(self, event: Dict[str, Any]) -> None:
        # This is triggered when someone mentions the bot
        await self.bot.handle_message_event(event)
    
    async def handle_reaction_event(self, event: Dict[str, Any]) -> None:
        # Could be used for feedback or other interactions
        logger.info(f"Reaction event: {event.get('reaction')} by {event.get('user')}")
    
    def is_valid_event(self, event: Dict[str, Any]) -> bool:
        required_fields = ["type"]
        return all(field in event for field in required_fields)

event_handler = SlackEventHandler()

def get_event_handler() -> SlackEventHandler:
    return event_handler
