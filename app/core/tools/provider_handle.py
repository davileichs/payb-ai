"""
Provider handle tool for managing AI provider switching and settings.
"""

from typing import Dict, Any
from app.core.tools.base import BaseTool, ToolResult, register_tool
from app.core.chat_processor import get_chat_processor


class ProviderHandle(BaseTool):
    """
    A tool for managing AI providers and switching between them.
    """
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the provider handle tool."""
        try:
            action = kwargs.get("action", "status")
            provider = kwargs.get("provider")
            model = kwargs.get("model")
            
            chat_processor = get_chat_processor()
            
            if action == "switch":
                if not provider:
                    return ToolResult(
                        success=False,
                        error="Provider parameter is required for switch action",
                        metadata={"tool_name": "ProviderHandle"}
                    )
                
                result = await self._switch_provider(chat_processor, provider, model)
                return result
                
            elif action == "list":
                result = self._list_providers(chat_processor)
                return result
                
            elif action == "status":
                result = self._get_status(chat_processor)
                return result
                
            elif action == "test":
                result = await self._test_provider(chat_processor, provider)
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
    
    async def _switch_provider(self, chat_processor, provider: str, model: str = None) -> ToolResult:
        """Switch to a different AI provider."""
        try:
            # Validate provider
            if provider not in chat_processor.providers:
                return ToolResult(
                    success=False,
                    error=f"Provider '{provider}' not found. Available: {list(chat_processor.providers.keys())}",
                    metadata={"tool_name": "ProviderHandle"}
                )
            
            # Check if provider is available
            if not chat_processor.providers[provider].is_available():
                return ToolResult(
                    success=False,
                    error=f"Provider '{provider}' is not available. Check configuration and connectivity.",
                    metadata={"tool_name": "ProviderHandle"}
                )
            
            # Switch provider
            old_provider = chat_processor.current_provider
            chat_processor.current_provider = provider
            
            # Set model if specified
            if model and hasattr(chat_processor.providers[provider], 'model'):
                chat_processor.providers[provider].model = model
            
            return ToolResult(
                success=True,
                data={
                    "message": f"Successfully switched from {old_provider} to {provider}",
                    "previous_provider": old_provider,
                    "current_provider": provider,
                    "model": getattr(chat_processor.providers[provider], 'model', 'default')
                },
                metadata={"tool_name": "ProviderHandle"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to switch provider: {str(e)}",
                metadata={"tool_name": "ProviderHandle"}
            )
    
    def _list_providers(self, chat_processor) -> ToolResult:
        """List available AI providers and their status."""
        try:
            providers_info = {}
            for name, provider in chat_processor.providers.items():
                providers_info[name] = {
                    "available": provider.is_available(),
                    "model": getattr(provider, 'model', 'default'),
                    "current": name == chat_processor.current_provider
                }
            
            return ToolResult(
                success=True,
                data={
                    "providers": providers_info,
                    "current_provider": chat_processor.current_provider
                },
                metadata={"tool_name": "ProviderHandle"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to list providers: {str(e)}",
                metadata={"tool_name": "ProviderHandle"}
            )
    
    def _get_status(self, chat_processor) -> ToolResult:
        """Get current provider status."""
        try:
            current_provider = chat_processor.current_provider
            provider = chat_processor.providers[current_provider]
            
            return ToolResult(
                success=True,
                data={
                    "current_provider": current_provider,
                    "available": provider.is_available(),
                    "model": getattr(provider, 'model', 'default'),
                    "all_providers": list(chat_processor.providers.keys())
                },
                metadata={"tool_name": "ProviderHandle"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to get status: {str(e)}",
                metadata={"tool_name": "ProviderHandle"}
            )
    
    async def _test_provider(self, chat_processor, provider: str = None) -> ToolResult:
        """Test provider connectivity."""
        try:
            if provider:
                if provider not in chat_processor.providers:
                    return ToolResult(
                        success=False,
                        error=f"Provider '{provider}' not found",
                        metadata={"tool_name": "ProviderHandle"}
                    )
                providers_to_test = {provider: chat_processor.providers[provider]}
            else:
                providers_to_test = chat_processor.providers
            
            test_results = {}
            for name, provider_instance in providers_to_test.items():
                test_results[name] = {
                    "available": provider_instance.is_available(),
                    "model": getattr(provider_instance, 'model', 'default')
                }
            
            return ToolResult(
                success=True,
                data={
                    "test_results": test_results,
                    "message": "Provider connectivity test completed"
                },
                metadata={"tool_name": "ProviderHandle"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to test providers: {str(e)}",
                metadata={"tool_name": "ProviderHandle"}
            )


# Register the tool automatically
register_tool(ProviderHandle())
