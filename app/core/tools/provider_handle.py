"""
Provider handle tool for managing AI provider switching and settings.
"""

from typing import Dict, Any
from app.core.tools.base import BaseTool, ToolResult, register_tool


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
        """Switch to a different AI provider."""
        try:
            # This tool will be called by the chat processor, so we can't directly switch
            # Instead, return instructions for the user
            return ToolResult(
                success=True,
                data={
                    "message": f"Provider switch requested to {provider}",
                    "action": "switch_provider",
                    "provider": provider,
                    "model": model,
                    "note": "Provider switching is handled by the chat processor. This request has been logged."
                },
                metadata={"tool_name": "ProviderHandle", "action": "switch_provider"}
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"tool_name": "ProviderHandle"}
            )
    
    def _list_providers(self) -> ToolResult:
        """List available AI providers."""
        try:
            providers_info = {
                "openai": {
                    "name": "OpenAI",
                    "description": "OpenAI GPT models via API",
                    "models": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
                    "status": "Available with API key"
                },
                "ollama": {
                    "name": "Ollama",
                    "description": "Local AI models via Ollama",
                    "models": ["llama2", "mistral", "codellama", "neural-chat"],
                    "status": "Available locally"
                }
            }
            
            return ToolResult(
                success=True,
                data={
                    "providers": providers_info,
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
        """Get current provider status."""
        try:
            # Return general status information
            status_info = {
                "message": "Provider status information",
                "note": "Detailed status is available through the chat processor",
                "available_providers": ["openai", "ollama"],
                "current_provider": "Determined by chat processor configuration"
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
        """Test a specific provider or all providers."""
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
