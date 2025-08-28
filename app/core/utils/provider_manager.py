import logging
from typing import Dict, Optional
from app.config import get_settings
from app.core.providers.base import BaseAIProvider
from app.core.providers.openai import OpenAIProvider
from app.core.providers.ollama import OllamaProvider

logger = logging.getLogger(__name__)

class ProviderManager:
    def __init__(self):
        self.settings = get_settings()
        self._default_provider = self.settings.ai_provider.lower()
        self._channel_providers: Dict[str, str] = {}
        self._provider_instances: Dict[str, BaseAIProvider] = {}
        
        # Initialize default provider instance
        self._initialize_provider(self._default_provider)
    
    def _initialize_provider(self, provider_name: str) -> BaseAIProvider:
        """Initialize a provider instance if not already created"""
        if provider_name not in self._provider_instances:
            if provider_name == "openai":
                self._provider_instances[provider_name] = OpenAIProvider()
            elif provider_name == "ollama":
                self._provider_instances[provider_name] = OllamaProvider()
            else:
                raise ValueError(f"Unknown provider: {provider_name}")
        
        return self._provider_instances[provider_name]
    
    def get_provider_for_channel(self, channel_id: str) -> BaseAIProvider:
        """Get the provider for a specific channel, falling back to default"""
        provider_name = self._channel_providers.get(channel_id, self._default_provider)
        return self._initialize_provider(provider_name)
    
    def set_provider_for_channel(self, channel_id: str, provider_name: str) -> bool:
        """Set the provider for a specific channel"""
        provider_name = provider_name.lower()
        
        if provider_name not in ["openai", "ollama"]:
            return False
        
        try:
            # Initialize the provider to ensure it's valid
            self._initialize_provider(provider_name)
            
            # Set the channel provider
            self._channel_providers[channel_id] = provider_name
            logger.info(f"Set provider '{provider_name}' for channel '{channel_id}'")
            return True
            
        except Exception as e:
            logger.error(f"Error setting provider '{provider_name}' for channel '{channel_id}': {e}")
            return False
    
    def get_channel_provider_name(self, channel_id: str) -> str:
        """Get the provider name for a specific channel"""
        return self._channel_providers.get(channel_id, self._default_provider)
    
    def get_default_provider_name(self) -> str:
        """Get the default provider name"""
        return self._default_provider
    
    def get_available_providers(self) -> list:
        """Get list of available providers"""
        return ["openai", "ollama"]
    
    def clear_channel_provider(self, channel_id: str) -> None:
        """Clear the provider for a specific channel (revert to default)"""
        if channel_id in self._channel_providers:
            del self._channel_providers[channel_id]
            logger.info(f"Cleared provider for channel '{channel_id}', reverting to default")
    
    def get_all_channel_providers(self) -> Dict[str, str]:
        """Get all channel-specific provider mappings"""
        return self._channel_providers.copy()

# Global instance
_provider_manager = None

def get_provider_manager() -> ProviderManager:
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager
