"""
Main AI chat processor that coordinates between AI providers and tools.
"""

from typing import List, Dict, Any, Optional
import json
import logging
from app.config import get_settings
from app.core.providers.openai import OpenAIProvider
from app.core.providers.ollama import OllamaProvider
from app.core.tools.base import tool_registry, ToolResult
from app.core.conversation_manager import get_conversation_manager
from app.core.agents import get_agent_manager

logger = logging.getLogger(__name__)


class ChatProcessor:
    """Main chat processor that handles AI interactions and tool execution."""
    
    def __init__(self):
        self.settings = get_settings()
        self.providers = {
            "openai": OpenAIProvider(),
            "ollama": OllamaProvider()
        }
        self.current_provider = self.settings.ai_provider
        self.conversation_manager = get_conversation_manager()
        self.agent_manager = get_agent_manager()
        
        # Validate provider availability
        if not self.providers[self.current_provider].is_available():
            logger.warning(f"Configured provider {self.current_provider} is not available")
            # Try to find an available provider
            for name, provider in self.providers.items():
                if provider.is_available():
                    self.current_provider = name
                    logger.info(f"Switched to provider: {name}")
                    break
    
    async def process_message(
        self,
        message: str,
        user_id: str,
        channel_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        use_tools: bool = True
    ) -> Dict[str, Any]:
        """Process a user message and generate an AI response."""
        
        # Get or create conversation from conversation manager
        conversation = self.conversation_manager.add_user_message(
            user_id=user_id,
            channel_id=channel_id,
            content=message,
            provider=self.current_provider,
            model=self.providers[self.current_provider].model if hasattr(self.providers[self.current_provider], 'model') else "unknown"
        )
        
        # Get conversation context for LLM
        llm_context = self.conversation_manager.get_conversation_context(
            user_id=user_id,
            channel_id=channel_id
        )
        
        # Prepare messages for AI
        messages = self._prepare_messages(message, llm_context, user_id, channel_id)
        
        # Get available tools if requested
        tools = None
        if use_tools:
            # Get all available tools for the AI to choose from
            available_tools = tool_registry.get_all_tools()
            
            if available_tools:
                tools = [tool.get_schema() for tool in available_tools]
        
        try:
            # Get AI response
            provider = self.providers[self.current_provider]
            response = await provider.chat_completion(
                messages=messages,
                tools=tools,
                temperature=self.settings.ai_temperature
            )
            
            # Handle tool calls if present
            if "tool_calls" in response and response["tool_calls"]:
                tool_results = await self._execute_tools(response["tool_calls"], self.current_provider)
                
                # Check for agent switches and update storage
                for tool_result in tool_results:
                    if tool_result.get("metadata", {}).get("agent_switch"):
                        new_agent_id = tool_result.get("metadata", {}).get("new_agent_id")
                        if new_agent_id:
                            self._update_conversation_agent(user_id, channel_id, new_agent_id)
                
                # Add tool results to conversation
                for tool_result in tool_results:
                    self.conversation_manager.add_tool_result(
                        user_id=user_id,
                        channel_id=channel_id,
                        tool_name=tool_result["tool_name"],
                        tool_result=json.dumps(tool_result["result"]),
                        metadata={"tool_call_id": tool_result["tool_call_id"]}
                    )
                
                # Add tool results to messages for final response
                messages.append({
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": response.tool_calls
                })
                
                # Add tool results
                for tool_result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_result["tool_call_id"],
                        "content": json.dumps(tool_result["result"])
                    })
                
                # Get final response from AI
                final_response = await provider.chat_completion(
                    messages=messages,
                    temperature=self.settings.ai_temperature
                )
                
                response = final_response
            
            # Add AI response to conversation
            self.conversation_manager.add_ai_response(
                user_id=user_id,
                channel_id=channel_id,
                content=response.content,
                metadata={"provider": self.current_provider, "model": response.model}
            )
            
            # Get updated context for return
            updated_context = self.conversation_manager.get_conversation_context(
                user_id=user_id,
                channel_id=channel_id
            )
            
            return {
                "response": response.content,
                "provider": self.current_provider,
                "model": response.model,
                "usage": response.usage.dict() if response.usage else {},
                "conversation_history": updated_context,
                "conversation_id": conversation.id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            error_response = f"Sorry, I encountered an error: {str(e)}"
            
            # Add error response to conversation
            self.conversation_manager.add_ai_response(
                user_id=user_id,
                channel_id=channel_id,
                content=error_response,
                metadata={"error": str(e), "provider": self.current_provider}
            )
            
            return {
                "response": error_response,
                "provider": self.current_provider,
                "error": str(e),
                "conversation_history": self.conversation_manager.get_conversation_context(
                    user_id=user_id,
                    channel_id=channel_id
                )
            }
    
    async def _execute_tools(self, tool_calls: List[Dict[str, Any]], provider_name: str) -> List[Dict[str, Any]]:
        """Execute the requested tools and return results."""
        results = []
        
        for tool_call in tool_calls:
            try:
                if provider_name == "openai":
                    # OpenAI format: function calling
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                elif provider_name == "ollama":
                    # Ollama format: modern tool calling (similar to OpenAI)
                    tool_name = tool_call["function"]["name"]
                    tool_args = tool_call["function"]["arguments"]
                else:
                    # Default format
                    tool_name = tool_call.get("function", {}).get("name", tool_call.get("name", ""))
                    tool_args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                
                tool = tool_registry.get_tool(tool_name)
                if tool:
                    try:
                        result = await tool.execute(**tool_args)
                        results.append({
                            "tool_call_id": tool_call.get("id", f"call_{len(results)}"),
                            "tool_name": tool_name,
                            "result": result.dict() if hasattr(result, 'dict') else result
                        })
                    except Exception as e:
                        # Skip tools that fail with exceptions - just log the error
                        logger.error(f"Error executing tool {tool_name} from {provider_name}: {str(e)}")
                        continue
                else:
                    # Skip non-existent tools - just log a warning
                    logger.warning(f"Tool {tool_name} not found from {provider_name}, skipping")
                    continue
            except Exception as e:
                logger.error(f"Error processing tool call {tool_call}: {str(e)}")
                results.append({
                    "tool_call_id": tool_call.get("id", f"call_{len(results)}"),
                    "tool_name": "unknown",
                    "result": {"success": False, "error": f"Tool call parsing error: {str(e)}"}
                })
        
        return results
    
    def _prepare_messages(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        user_id: str,
        channel_id: str
    ) -> List[Dict[str, str]]:
        """Prepare messages for AI processing."""
        messages = []
        
        # Get agent system prompt
        system_message = self.agent_manager.get_user_system_prompt(user_id, channel_id)
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        # Add conversation history (limit to configured max messages to avoid token limits)
        for msg in conversation_history[-self.settings.max_messages_per_conversation:]:
            messages.append(msg)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        return messages
    
    def _update_conversation_agent(self, user_id: str, channel_id: str, agent_id: str):
        """Update the current agent in the agent manager tool for the given user and channel."""
        try:
            # Get the global agent manager tool instance
            from app.core.tools.agent_manager import get_agent_manager_tool
            agent_tool = get_agent_manager_tool()
            
            # Update the user's agent preference
            key = f"{user_id}:{channel_id}"
            agent_tool._user_agents[key] = agent_id
            
            logger.info(f"Updated agent to {agent_id} for user {user_id} in channel {channel_id}")
        except Exception as e:
            logger.error(f"Failed to update conversation agent: {str(e)}")
    
    
# Global chat processor instance
chat_processor = ChatProcessor()


def get_chat_processor() -> ChatProcessor:
    """Get the global chat processor instance."""
    return chat_processor
