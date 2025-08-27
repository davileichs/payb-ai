from typing import Dict, Any
from app.core.tools.base import BaseTool, ToolResult, register_tool

class ProviderHandle(BaseTool):
    
    async def execute(self, **kwargs) -> ToolResult:
        try:
            action = kwargs.get("action", "status")
            provider = kwargs.get("provider")
            model = kwargs.get("model")
            
            if action == "switch":
                if not provider:
                    return ToolResult(
                        success=False,
                        error="Provider parameter is required for switch action",
                        metadata={"tool_name": "ProviderHandle"}
                    )
                
                result = await self._switch_provider(provider, model)
                return result
                
            elif action == "list":
                result = self._list_providers()
                return result
                
            elif action == "status":
                result = self._get_status()
                return result
                
            elif action == "test":
                result = await self._test_provider(provider)
                return result
                
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action: {action}",
                    metadata={"tool_name": "ProviderHandle"}
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool_name": "ProviderHandle"}
            )
    
    async def _switch_provider(self, provider: str, model: str = None) -> ToolResult:
        try:
            # Return proper metadata for the chat processor to handle the switch
            return ToolResult(
                success=True,
                data={
                    "message": f"Provider switched to {provider}" + (f" with model {model}" if model else ""),
                    "action": "switch_provider",
                    "provider": provider,
                    "model": model,
                    "status": "success"
                },
                metadata={
                    "tool_name": "ProviderHandle", 
                    "action": "switch_provider",
                    "provider_switch": True,
                    "new_provider": provider,
                    "new_model": model
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool_name": "ProviderHandle"}
            )
    
    def _list_providers(self) -> ToolResult:
        try:
            # Import here to avoid circular imports
            from app.core.chat_processor import get_chat_processor
            
            chat_processor = get_chat_processor()
            providers_info = {}
            
            for name, provider in chat_processor.providers.items():
                if provider is not None:
                    providers_info[name] = {
                        "name": name.title(),
                        "description": f"{name.title()} AI provider",
                        "status": "Available" if provider.is_available() else "Unavailable",
                        "is_current": name == chat_processor.current_provider
                    }
            
            return ToolResult(
                success=True,
                data={
                    "providers": providers_info,
                    "current_provider": chat_processor.current_provider,
                    "message": "Available AI providers and their capabilities"
                },
                metadata={"tool_name": "ProviderHandle"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool_name": "ProviderHandle"}
            )
    
    def _get_status(self) -> ToolResult:
        try:
            # Import here to avoid circular imports
            from app.core.chat_processor import get_chat_processor
            
            chat_processor = get_chat_processor()
            available_providers = [name for name, provider in chat_processor.providers.items() 
                                 if provider is not None and provider.is_available()]
            
            status_info = {
                "message": "Provider status information",
                "current_provider": chat_processor.current_provider,
                "available_providers": available_providers,
                "total_providers": len(chat_processor.providers),
                "status": "healthy" if available_providers else "no providers available"
            }
            
            return ToolResult(
                success=True,
                data=status_info,
                metadata={"tool_name": "ProviderHandle"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool_name": "ProviderHandle"}
            )
    
    async def _test_provider(self, provider: str = None) -> ToolResult:
        try:
            if provider:
                # Test specific provider
                test_result = {
                    "provider": provider,
                    "status": "Test requested",
                    "note": f"Provider testing for {provider} has been requested"
                }
            else:
                # Test all providers
                test_result = {
                    "providers": ["openai", "ollama"],
                    "status": "Test requested for all providers",
                    "note": "Provider testing has been requested for all available providers"
                }
            
            return ToolResult(
                success=True,
                data=test_result,
                metadata={"tool_name": "ProviderHandle", "action": "test_provider"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool_name": "ProviderHandle"}
            )

# Register the tool automatically
register_tool(ProviderHandle())
