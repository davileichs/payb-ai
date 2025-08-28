from typing import List, Dict, Any, Optional
import json
import logging
from app.config import get_settings
from app.core.tools.base import tool_registry, ToolResult
from app.core.utils.conversation_manager import get_conversation_manager
from app.core.utils.agent_manager import get_agent_manager
from app.core.utils.provider_manager import get_provider_manager
from app.core.providers.base import BaseAIProvider

logger = logging.getLogger(__name__)

class ChatProcessor:
    
    def __init__(self):
        self.settings = get_settings()
        self.provider_manager = get_provider_manager()
        self.conversation_manager = get_conversation_manager()
        self.agent_manager = get_agent_manager()
        
        # Test default provider availability
        default_provider = self.provider_manager.get_provider_for_channel("default")
        if not default_provider.is_available():
            logger.error(f"Default provider {self.settings.ai_provider} is not available")
            raise RuntimeError(f"Default provider {self.settings.ai_provider} is not available")
    
    def _get_provider_for_channel(self, channel_id: str) -> BaseAIProvider:
        """Get the appropriate provider for a specific channel"""
        return self.provider_manager.get_provider_for_channel(channel_id)
    
    async def process_message(
        self,
        message: str,
        user_id: str,
        channel_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        use_tools: bool = True
    ) -> Dict[str, Any]:
        # Get the provider for this specific channel
        provider = self._get_provider_for_channel(channel_id)
        current_provider_name = self.provider_manager.get_channel_provider_name(channel_id)
        
        if not provider.is_available():
            return {
                "response": "Sorry, the AI provider is not currently available. Please check the configuration.",
                "provider": current_provider_name,
                "model": "none",
                "usage": {},
                "conversation_history": [],
                "error": "Provider not available"
            }
        
        conversation = self.conversation_manager.add_user_message(
            user_id=user_id,
            channel_id=channel_id,
            content=message,
            provider=current_provider_name,
            model=provider.get_model()
        )
        
        llm_context = self.conversation_manager.get_conversation_context(
            user_id=user_id,
            channel_id=channel_id
        )
        
        messages = self._prepare_messages(message, llm_context, user_id, channel_id)
        
        tools = None
        if use_tools:
            tool_names = self.agent_manager.get_user_tools(user_id, channel_id)
            
            if tool_names:
                available_tools = []
                for tool_name in tool_names:
                    tool = tool_registry.get_tool(tool_name)
                    if tool:
                        available_tools.append(tool)
                
                if available_tools:
                    tools = []
                    for tool in available_tools:
                        schema = tool.get_schema()
                        tools.append({
                            "type": "function",
                            "function": {
                                "name": schema["name"],
                                "description": schema["description"],
                                "parameters": schema["parameters"]
                            }
                        })
        
        try:
            response = await provider.chat_completion(
                messages=messages,
                tools=tools,
                temperature=self.settings.ai_temperature
            )
            
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_results = await provider.execute_tool_calls(response.tool_calls)
                
                for tool_result in tool_results:
                    if tool_result.get("metadata", {}).get("agent_switch"):
                        new_agent_id = tool_result.get("metadata", {}).get("new_agent_id")
                        if new_agent_id:
                            self._update_conversation_agent(user_id, channel_id, new_agent_id)
                
                for tool_result in tool_results:
                    self.conversation_manager.add_tool_result(
                        user_id=user_id,
                        channel_id=channel_id,
                        tool_name=tool_result["tool_name"],
                        tool_result=json.dumps(tool_result["result"]),
                        metadata={"tool_call_id": tool_result["tool_call_id"]}
                    )
                
                messages.append({
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id if hasattr(tool_call, 'id') else f"call_{i}",
                            "type": "function",
                            "function": {
                                "name": tool_call.name if hasattr(tool_call, 'name') else (tool_call.function.name if hasattr(tool_call, 'function') else tool_call.get('function', {}).get('name', f"tool_{i}")),
                                "arguments": tool_call.arguments if hasattr(tool_call, 'arguments') else (tool_call.function.arguments if hasattr(tool_call, 'function') else tool_call.get('function', {}).get('arguments', '{}'))
                            }
                        }
                        for i, tool_call in enumerate(response.tool_calls)
                    ]
                })
                
                for tool_result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_result["tool_call_id"],
                        "content": json.dumps(tool_result["result"])
                    })
                
                final_response = await provider.chat_completion(
                    messages=messages,
                    temperature=self.settings.ai_temperature
                )
                
                response = final_response
            
            self.conversation_manager.add_ai_response(
                user_id=user_id,
                channel_id=channel_id,
                content=response.content,
                metadata={"provider": current_provider_name, "model": response.model}
            )
            
            updated_context = self.conversation_manager.get_conversation_context(
                user_id=user_id,
                channel_id=channel_id
            )
            
            return {
                "response": response.content,
                "provider": current_provider_name,
                "model": response.model,
                "usage": response.usage.model_dump() if response.usage else {},
                "conversation_history": updated_context,
                "conversation_id": conversation.id
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            error_response = f"Sorry, I encountered an error: {str(e)}"
            
            self.conversation_manager.add_ai_response(
                user_id=user_id,
                channel_id=channel_id,
                content=error_response,
                metadata={"error": str(e), "provider": current_provider_name}
            )
            
            return {
                "response": error_response,
                "provider": current_provider_name,
                "model": "unknown",
                "usage": {},
                "error": str(e),
                "conversation_history": self.conversation_manager.get_conversation_context(
                    user_id=user_id,
                    channel_id=channel_id
                )
            }
    

    
    def _prepare_messages(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        user_id: str,
        channel_id: str
    ) -> List[Dict[str, str]]:
        messages = []
        
        system_message = self.agent_manager.get_user_system_prompt(user_id, channel_id)
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        for msg in conversation_history[-self.settings.max_messages_per_conversation:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": message})
        
        return messages
    
    def _update_conversation_agent(self, user_id: str, channel_id: str, agent_id: str):
        try:
            from app.core.tools.agent_manager import get_agent_manager_tool
            agent_tool = get_agent_manager_tool()
            
            key = f"{user_id}:{channel_id}"
            agent_tool._user_agents[key] = agent_id
            
            logger.info(f"Updated agent to {agent_id} for user {user_id} in channel {channel_id}")
        except Exception as e:
            logger.error(f"Failed to update conversation agent: {str(e)}")

# Global chat processor instance to maintain state across requests
_chat_processor_instance = None

def get_chat_processor() -> ChatProcessor:
    global _chat_processor_instance
    if _chat_processor_instance is None:
        _chat_processor_instance = ChatProcessor()
    return _chat_processor_instance
