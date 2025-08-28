import logging
from typing import Dict, Any, Optional
from slack_sdk.web.client import WebClient
from slack_sdk.signature import SignatureVerifier
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.config import get_settings
from app.core.chat_processor import get_chat_processor
from app.core.utils.conversation_manager import get_conversation_manager
from app.core.utils.provider_manager import get_provider_manager

logger = logging.getLogger(__name__)

class SlackBot:
    
    def __init__(self):
        self.settings = get_settings()
        self.client = WebClient(token=self.settings.slack_bot_token)
        self.signature_verifier = SignatureVerifier(self.settings.slack_signing_secret)
        self.chat_processor = get_chat_processor()
        self.conversation_manager = get_conversation_manager()
        self.provider_manager = get_provider_manager()
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    def verify_signature(self, body: str, headers: Dict[str, str]) -> bool:
        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")
        
        return self.signature_verifier.is_valid(body, timestamp, signature)
    
    async def handle_message_event(self, event: Dict[str, Any]) -> None:
        try:
            # Ignore bot messages to prevent loops
            if event.get("bot_id"):
                return
            
            channel = event.get("channel")
            user = event.get("user")
            text = event.get("text", "").strip()
            
            if not text or not channel or not user:
                return
            
            logger.info(f"Processing message from {user} in {channel}: {text}")
            
            # Check if this is a command
            if text.startswith('/'):
                await self.handle_command(channel, user, text, event.get("ts"))
            else:
                # Process regular message with AI
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
        try:
            # Run the synchronous call in a thread pool to avoid blocking
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.client.chat_postMessage(
                    channel=channel,
                    text=text,
                    thread_ts=thread_ts,
                    **kwargs
                )
            )
            
            if not response["ok"]:
                logger.error(f"Failed to send message: {response.get('error')}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise
    
    async def handle_url_verification(self, challenge: str) -> str:
        return challenge
    
    def is_bot_message(self, event: Dict[str, Any]) -> bool:
        return bool(event.get("bot_id") or event.get("subtype") == "bot_message")
    
    def get_conversation_key(self, channel: str, user: str) -> str:
        return f"{channel}:{user}"
    
    def clear_conversation(self, channel: str, user: str) -> None:
        self.conversation_manager.clear_conversation(user_id=user, channel_id=channel)
        logger.info(f"Cleared conversation for {channel}:{user}")
    
    async def handle_command(self, channel: str, user: str, text: str, thread_ts: Optional[str] = None) -> None:
        """Handle Slack commands starting with /"""
        try:
            parts = text.split()
            command = parts[0][1:]  # Remove the / prefix
            args = parts[1:] if len(parts) > 1 else []
            
            logger.info(f"Handling command '{command}' with args {args} from {user} in {channel}")
            
            if command == "provider":
                await self.handle_provider_command(channel, user, args, thread_ts)
            elif command == "agent":
                await self.handle_agent_command(channel, user, args, thread_ts)
            elif command == "clear":
                await self.handle_clear_command(channel, user, args, thread_ts)
            elif command == "status":
                await self.handle_status_command(channel, user, args, thread_ts)
            elif command == "help":
                await self.handle_help_command(channel, user, args, thread_ts)
            elif command == "reload":
                await self.handle_reload_command(channel, user, args, thread_ts)
            else:
                await self.send_message(
                    channel=channel,
                    text=f"Unknown command: `/{command}`. Use `/help` to see available commands.",
                    thread_ts=thread_ts
                )
                
        except Exception as e:
            logger.error(f"Error handling command: {str(e)}")
            await self.send_message(
                channel=channel,
                text="Sorry, I encountered an error processing your command. Please try again.",
                thread_ts=thread_ts
            )
    
    async def handle_provider_command(self, channel: str, user: str, args: list, thread_ts: Optional[str] = None) -> None:
        """Handle /provider command for switching AI providers"""
        if not args:
            # Show current provider and available options
            current_provider = self.provider_manager.get_channel_provider_name(channel)
            available_providers = self.provider_manager.get_available_providers()
            default_provider = self.provider_manager.get_default_provider_name()
            
            response = f"🤖 *Current Provider:* `{current_provider}`\n"
            response += f"📋 *Available Providers:* {', '.join([f'`{p}`' for p in available_providers])}\n"
            response += f"🔧 *Default Provider:* `{default_provider}`\n"
            response += f"💡 *Usage:* `/provider <provider_name> [model]` to switch"
            
            await self.send_message(channel=channel, text=response, thread_ts=thread_ts)
            return
        
        provider = args[0].lower()
        model = args[1] if len(args) > 1 else None
        
        if provider not in ["openai", "ollama"]:
            available_providers = self.provider_manager.get_available_providers()
            await self.send_message(
                channel=channel,
                text=f"❌ Invalid provider: `{provider}`. Available: {', '.join([f'`{p}`' for p in available_providers])}",
                thread_ts=thread_ts
            )
            return
        
        try:
            # Switch provider for this channel
            old_provider = self.provider_manager.get_channel_provider_name(channel)
            success = self.provider_manager.set_provider_for_channel(channel, provider)
            
            if success:
                # Update model if specified
                if model:
                    channel_provider = self.provider_manager.get_provider_for_channel(channel)
                    channel_provider.set_model(model)
                
                response = f"✅ *Provider switched successfully!*\n"
                response += f"🔄 *From:* `{old_provider}`\n"
                response += f"🔄 *To:* `{provider}`"
                if model:
                    response += f" (model: `{model}`)"
                response += f"\n📺 *Channel:* `{channel}`"
                
                await self.send_message(channel=channel, text=response, thread_ts=thread_ts)
                logger.info(f"Provider switched from {old_provider} to {provider} for channel {channel}")
            else:
                await self.send_message(
                    channel=channel,
                    text=f"❌ Failed to switch provider to `{provider}`",
                    thread_ts=thread_ts
                )
            
        except Exception as e:
            logger.error(f"Error switching provider: {str(e)}")
            await self.send_message(
                channel=channel,
                text=f"❌ Error switching provider: {str(e)}",
                thread_ts=thread_ts
            )
    
    async def handle_agent_command(self, channel: str, user: str, args: list, thread_ts: Optional[str] = None) -> None:
        """Handle /agent command for switching AI agents"""
        if not args:
            # Show current agent and available options
            from app.core.utils.agent_manager import get_agent_manager
            agent_manager = get_agent_manager()
            available_agents = agent_manager.get_available_agents()
            
            response = f"👤 *Available Agents:*\n"
            for agent_id in available_agents:
                agent_info = agent_manager.get_agent_info(agent_id)
                response += f"• `{agent_id}` - {agent_info.get('name', agent_id)}\n"
            response += f"💡 *Usage:* `/agent <agent_id>` to switch"
            
            await self.send_message(channel=channel, text=response, thread_ts=thread_ts)
            return
        
        agent_id = args[0].lower()
        
        try:
            from app.core.tools.base import tool_registry
            agent_tool = tool_registry.get_tool('AgentManagerTool')
            
            if not agent_tool:
                await self.send_message(
                    channel=channel,
                    text="❌ Agent management tool not available",
                    thread_ts=thread_ts
                )
                return
            
            # Switch agent
            result = await agent_tool.execute(
                action='switch',
                agent_id=agent_id,
                user_id=user,
                channel_id=channel
            )
            
            if result.success:
                agent_info = result.data
                response = f"✅ *Agent switched successfully!*\n"
                response += f"👤 *New Agent:* {agent_info['agent_name']}\n"
                response += f"📝 *Description:* {agent_info['description']}"
                
                await self.send_message(channel=channel, text=response, thread_ts=thread_ts)
                logger.info(f"Agent switched to {agent_id} for user {user} in channel {channel}")
            else:
                await self.send_message(
                    channel=channel,
                    text=f"❌ Error switching agent: {result.error}",
                    thread_ts=thread_ts
                )
                
        except Exception as e:
            logger.error(f"Error switching agent: {str(e)}")
            await self.send_message(
                channel=channel,
                text=f"❌ Error switching agent: {str(e)}",
                thread_ts=thread_ts
            )
    
    async def handle_clear_command(self, channel: str, user: str, args: list, thread_ts: Optional[str] = None) -> None:
        """Handle /clear command to clear conversation history"""
        try:
            self.clear_conversation(channel, user)
            await self.send_message(
                channel=channel,
                text="🧹 *Conversation cleared!* Your chat history has been reset.",
                thread_ts=thread_ts
            )
        except Exception as e:
            logger.error(f"Error clearing conversation: {str(e)}")
            await self.send_message(
                channel=channel,
                text="❌ Error clearing conversation. Please try again.",
                thread_ts=thread_ts
            )
    
    async def handle_status_command(self, channel: str, user: str, args: list, thread_ts: Optional[str] = None) -> None:
        """Handle /status command to show current system status"""
        try:
            # Get channel-specific provider info
            current_provider = self.provider_manager.get_channel_provider_name(channel)
            default_provider = self.provider_manager.get_default_provider_name()
            channel_provider = self.provider_manager.get_provider_for_channel(channel)
            provider_available = channel_provider.is_available()
            is_custom = channel in self.provider_manager.get_all_channel_providers()
            
            from app.core.utils.agent_manager import get_agent_manager
            agent_manager = get_agent_manager()
            current_agent = agent_manager.get_user_system_prompt(user, channel)
            
            response = f"📊 *System Status*\n"
            response += f"🤖 *Provider:* `{current_provider}` ({'✅ Available' if provider_available else '❌ Unavailable'})\n"
            response += f"🔧 *Default Provider:* `{default_provider}`\n"
            response += f"📺 *Channel:* `{channel}` {'(Custom)' if is_custom else '(Default)'}\n"
            response += f"👤 *Agent:* Using current agent configuration\n"
            response += f"💬 *Conversation:* Active"
            
            await self.send_message(channel=channel, text=response, thread_ts=thread_ts)
            
        except Exception as e:
            logger.error(f"Error getting status: {str(e)}")
            await self.send_message(
                channel=channel,
                text="❌ Error getting status. Please try again.",
                thread_ts=thread_ts
            )
    
    async def handle_help_command(self, channel: str, user: str, args: list, thread_ts: Optional[str] = None) -> None:
        """Handle /help command to show available commands"""
        response = f"🤖 *Available Commands:*\n\n"
        response += f"`/provider [provider_name]` - Switch AI provider (openai, ollama)\n"
        response += f"`/agent [agent_id]` - Switch AI agent\n"
        response += f"`/clear` - Clear conversation history\n"
        response += f"`/status` - Show current system status\n"
        response += f"`/reload [agents|config]` - Reload configuration files\n"
        response += f"`/help` - Show this help message\n\n"
        response += f"💡 *Example:* `/provider openai` or `/agent technical_support`"
        
        await self.send_message(channel=channel, text=response, thread_ts=thread_ts)
    
    async def handle_reload_command(self, channel: str, user: str, args: list, thread_ts: Optional[str] = None) -> None:
        """Handle /reload command to reload configuration files"""
        if not args:
            response = f"🔄 *Reload Commands:*\n\n"
            response += f"`/reload agents` - Reload agents.json file\n"
            response += f"`/reload config` - Show current config status\n\n"
            response += f"💡 *Note:* .env changes require container restart"
            
            await self.send_message(channel=channel, text=response, thread_ts=thread_ts)
            return
        
        reload_type = args[0].lower()
        
        try:
            if reload_type == "agents":
                from app.core.utils.agent_manager import get_agent_manager
                agent_manager = get_agent_manager()
                
                success = agent_manager.reload_agents_config()
                
                if success:
                    agents_count = len(agent_manager.agents_config.get("agents", {}))
                    response = f"✅ *Agents configuration reloaded!*\n"
                    response += f"📋 *Agents loaded:* {agents_count}\n"
                    response += f"🔄 *File:* agents.json"
                    
                    await self.send_message(channel=channel, text=response, thread_ts=thread_ts)
                    logger.info(f"Agents config reloaded by user {user} in channel {channel}")
                else:
                    await self.send_message(
                        channel=channel,
                        text="❌ Failed to reload agents configuration. Check the file format.",
                        thread_ts=thread_ts
                    )
                    
            elif reload_type == "config":
                from app.config import get_settings
                settings = get_settings()
                
                response = f"📊 *Current Configuration:*\n"
                response += f"🤖 *AI Provider:* `{settings.ai_provider}`\n"
                response += f"🧠 *OpenAI Model:* `{settings.openai_model}`\n"
                response += f"🦙 *Ollama Model:* `{settings.ollama_model}`\n"
                response += f"🌡️ *Temperature:* `{settings.ai_temperature}`\n"
                response += f"🐛 *Debug:* `{settings.debug}`\n\n"
                response += f"⚠️ *Note:* .env changes require container restart"
                
                await self.send_message(channel=channel, text=response, thread_ts=thread_ts)
                
            else:
                await self.send_message(
                    channel=channel,
                    text=f"❌ Unknown reload type: `{reload_type}`. Use `agents` or `config`",
                    thread_ts=thread_ts
                )
                
        except Exception as e:
            logger.error(f"Error reloading configuration: {str(e)}")
            await self.send_message(
                channel=channel,
                text=f"❌ Error reloading configuration: {str(e)}",
                thread_ts=thread_ts
            )

slack_bot = SlackBot()

def get_slack_bot() -> SlackBot:
    return slack_bot
