from typing import List, Dict, Any, Optional
import json
import logging
import os
import importlib
import inspect
from app.config import get_settings
from app.core.tools.base import tool_registry, ToolResult
from app.core.conversation_manager import get_conversation_manager
from app.core.agents import get_agent_manager

logger = logging.getLogger(__name__)

class ChatProcessor:
    
    def _discover_providers(self) -> Dict[str, Any]:
        """Dynamically discover and load all provider classes from the providers folder."""
        providers = {}
        providers_dir = os.path.join(os.path.dirname(__file__), "providers")
        
        # Get all Python files in the providers directory
        for filename in os.listdir(providers_dir):
            if filename.endswith('.py') and not filename.startswith('__') and filename != 'models.py':
                module_name = filename[:-3]  # Remove .py extension
                
                try:
                    # Import the module
                    module = importlib.import_module(f"app.core.providers.{module_name}")
                    
                    # Find provider classes (classes ending with 'Provider')
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if name.endswith('Provider') and hasattr(obj, 'chat_completion') and hasattr(obj, 'is_available'):
                            provider_name = name.lower().replace('provider', '')
                            try:
                                provider_instance = obj()
                                providers[provider_name] = provider_instance
                                logger.info(f"Discovered provider: {provider_name}")
                            except Exception as e:
                                logger.warning(f"Failed to initialize {provider_name} provider: {str(e)}")
                                
                except Exception as e:
                    logger.warning(f"Failed to load provider module {module_name}: {str(e)}")
        
        return providers
    
    def __init__(self):
        self.settings = get_settings()
        self.current_provider = self.settings.ai_provider
        
        # Dynamically discover and initialize providers
        self.providers = self._discover_providers()
        
        # Always initialize conversation and agent managers
        self.conversation_manager = get_conversation_manager()
        self.agent_manager = get_agent_manager()
        
        if not self.providers:
            logger.error("No providers available!")
            # Create a dummy provider entry to prevent complete failure
            self.providers["none"] = None
            self.current_provider = "none"
        else:
            # Validate provider availability
            if self.current_provider not in self.providers or not self.providers[self.current_provider].is_available():
                logger.warning(f"Configured provider {self.current_provider} is not available")
                # Try to find an available provider
                for name, provider in self.providers.items():
                    if provider and provider.is_available():
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
        
        # Check if we have any available providers
        if not self.providers or self.current_provider == "none" or not self.providers.get(self.current_provider):
            return {
                "response": "Sorry, no AI providers are currently available. Please check the configuration.",
                "provider": "none",
                "model": "none",
                "usage": {},
                "conversation_history": [],
                "error": "No providers available"
            }
        
        conversation = self.conversation_manager.add_user_message(
            user_id=user_id,
            channel_id=channel_id,
            content=message,
            provider=self.current_provider,
            model=self.providers[self.current_provider].model if hasattr(self.providers[self.current_provider], 'model') else "unknown"
        )
        
        llm_context = self.conversation_manager.get_conversation_context(
            user_id=user_id,
            channel_id=channel_id
        )
        
        # Prepare messages for AI
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
                    tools = [tool.get_schema() for tool in available_tools]
        
        try:
            provider = self.providers[self.current_provider]
            response = await provider.chat_completion(
                messages=messages,
                tools=tools,
                temperature=self.settings.ai_temperature
            )
            
            # Handle tool calls if present
            if hasattr(response, 'tool_calls') and response.tool_calls:
                tool_results = await self._execute_tools(response.tool_calls, self.current_provider)
                
                # Check for agent switches and provider switches
                for tool_result in tool_results:
                    # Handle agent switches
                    if tool_result.get("metadata", {}).get("agent_switch"):
                        new_agent_id = tool_result.get("metadata", {}).get("new_agent_id")
                        if new_agent_id:
                            self._update_conversation_agent(user_id, channel_id, new_agent_id)
                    
                    # Handle provider switches
                    if tool_result.get("metadata", {}).get("provider_switch"):
                        new_provider = tool_result.get("metadata", {}).get("new_provider")
                        new_model = tool_result.get("metadata", {}).get("new_model")
                        if new_provider and new_provider in self.providers:
                            # Validate provider is available
                            if self.providers[new_provider].is_available():
                                self.current_provider = new_provider
                                logger.info(f"Switched provider to {new_provider} for user {user_id} in channel {channel_id}")
                                
                                # Update model if specified
                                if new_model:
                                    if hasattr(self.providers[new_provider], 'model'):
                                        old_model = self.providers[new_provider].model
                                        self.providers[new_provider].model = new_model
                                        logger.info(f"Switched model from {old_model} to {new_model}")
                            else:
                                logger.warning(f"Provider {new_provider} is not available")
                
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
                                "name": tool_call.name if hasattr(tool_call, 'name') else tool_call.function.name,
                                "arguments": tool_call.arguments if hasattr(tool_call, 'arguments') else tool_call.function.arguments
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
                metadata={"provider": self.current_provider, "model": getattr(response, 'model', 'unknown')}
            )
            
            updated_context = self.conversation_manager.get_conversation_context(
                user_id=user_id,
                channel_id=channel_id
            )
            
            return {
                "response": response.content,
                "provider": self.current_provider,
                "model": getattr(response, 'model', 'unknown'),
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
                metadata={"error": str(e), "provider": self.current_provider}
            )
            
            return {
                "response": error_response,
                "provider": self.current_provider,
                "model": "unknown",
                "usage": {},
                "error": str(e),
                "conversation_history": self.conversation_manager.get_conversation_context(
                    user_id=user_id,
                    channel_id=channel_id
                )
            }
    
    async def _execute_tools(self, tool_calls: List[Any], provider_name: str) -> List[Dict[str, Any]]:
        results = []
        
        for tool_call in tool_calls:
            try:
                if provider_name == "openai":
                    # OpenAI format: FunctionCall objects
                    if hasattr(tool_call, 'name') and hasattr(tool_call, 'arguments'):
                        # Direct attributes (newer OpenAI format)
                        tool_name = tool_call.name
                        tool_args = json.loads(tool_call.arguments)
                        tool_call_id = getattr(tool_call, 'id', f"call_{len(results)}")
                    elif hasattr(tool_call, 'function'):
                        # Nested function attribute (older format)
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        tool_call_id = getattr(tool_call, 'id', f"call_{len(results)}")
                    else:
                        # Fallback to dictionary format
                        tool_name = tool_call["function"]["name"]
                        tool_args = json.loads(tool_call["function"]["arguments"])
                        tool_call_id = tool_call.get("id", f"call_{len(results)}")
                elif provider_name == "ollama":
                    # Ollama format: modern tool calling (similar to OpenAI)
                    if hasattr(tool_call, 'function'):
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        tool_call_id = getattr(tool_call, 'id', f"call_{len(results)}")
                    else:
                        tool_name = tool_call["function"]["name"]
                        tool_args = json.loads(tool_call["function"]["arguments"])
                        tool_call_id = tool_call.get("id", f"call_{len(results)}")
                else:
                    # Default format
                    tool_name = tool_call.get("function", {}).get("name", tool_call.get("name", ""))
                    tool_args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                    tool_call_id = tool_call.get("id", f"call_{len(results)}")
                
                tool = tool_registry.get_tool(tool_name)
                if tool:
                    try:
                        result = await tool.execute(**tool_args)
                        results.append({
                            "tool_call_id": tool_call_id,
                            "tool_name": tool_name,
                            "result": result.model_dump() if hasattr(result, 'model_dump') else result
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
                    "tool_call_id": getattr(tool_call, 'id', f"call_{len(results)}") if hasattr(tool_call, 'id') else f"call_{len(results)}",
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

# chat_processor = ChatProcessor()

def get_chat_processor() -> ChatProcessor:
    return ChatProcessor()
