from typing import List, Dict, Any, Optional
import openai
from app.config import get_settings
from app.core.providers.models import ChatCompletionResult, UsageInfo

class OpenAIProvider:
    
    def __init__(self):
        self.settings = get_settings()
        self.client = openai.OpenAI(api_key=self.settings.openai_api_key)
        self.model = self.settings.openai_model
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> ChatCompletionResult:
        """Generate chat completion using OpenAI API."""
        
        if not self.settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        # Prepare the request
        request_data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            request_data["max_tokens"] = max_tokens
        
        if tools:
            # Tools are already in the correct format from base tool system
            request_data["functions"] = tools
            if tool_choice:
                request_data["function_call"] = tool_choice
        
        try:
            response = self.client.chat.completions.create(**request_data)
            
            usage = UsageInfo(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
            
            result = ChatCompletionResult(
                content=response.choices[0].message.content or "",
                model=response.model,
                usage=usage
            )
            
            # Handle tool calls if present (let chat processor handle the format)
            if response.choices[0].message.function_call:
                result.tool_calls = [response.choices[0].message.function_call]
            elif response.choices[0].message.tool_calls:
                result.tool_calls = response.choices[0].message.tool_calls
            
            return result
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def is_available(self) -> bool:
        return bool(self.settings.openai_api_key)
