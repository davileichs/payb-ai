"""
Ollama provider for AI chat functionality.
"""

from typing import List, Dict, Any, Optional
import httpx
import json
from app.config import get_settings
from app.core.providers.models import ChatCompletionResult, UsageInfo


class OllamaProvider:
    """Ollama API provider for chat completion."""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url
        self.model = self.settings.ollama_model
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> ChatCompletionResult:
        """Generate chat completion using Ollama API."""
        
        # Convert system messages to assistant role for Ollama compatibility
        for msg in messages:
            if msg["role"] == "system":
                msg["role"] = "assistant"
        
        # Prepare the request
        request_data = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        if max_tokens:
            request_data["options"]["num_predict"] = max_tokens
        
        # Add tools if provided (modern Ollama supports native tool calling)
        if tools:
            request_data["tools"] = tools
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=request_data,
                    timeout=60.0
                )
                response.raise_for_status()
                
                result_data = response.json()
                
                # Create usage info
                usage = UsageInfo(
                    prompt_tokens=result_data.get("prompt_eval_count", 0),
                    completion_tokens=result_data.get("eval_count", 0),
                    total_tokens=result_data.get("prompt_eval_count", 0) + result_data.get("eval_count", 0)
                )
                
                # Create result with unified model
                result = ChatCompletionResult(
                    content=result_data.get("message", {}).get("content", ""),
                    model=result_data.get("model", self.model),
                    usage=usage
                )
                
                # Handle tool calls if present (modern Ollama format)
                if "tool_calls" in result_data.get("message", {}):
                    result.tool_calls = result_data["message"]["tool_calls"]
                
                return result
                
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Ollama provider is available."""
        return bool(self.base_url)
    
    async def health_check(self) -> bool:
        """Check if Ollama service is healthy."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                return response.status_code == 200
        except:
            return False
