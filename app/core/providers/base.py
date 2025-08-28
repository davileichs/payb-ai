from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.core.providers.models import ChatCompletionResult


class BaseAIProvider(ABC):
    
    def __init__(self):
        self.model = None
        self.settings = None
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> ChatCompletionResult:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    def get_model(self) -> str:
        return self.model or "unknown"
    
    def set_model(self, model: str) -> None:
        self.model = model
    
    async def health_check(self) -> bool:
        return self.is_available()
    
    def get_provider_name(self) -> str:
        return self.__class__.__name__.lower().replace('provider', '')
    
    @abstractmethod
    async def execute_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, Any]]:
        pass
