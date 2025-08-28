from typing import List, Dict, Any, Optional
import openai
import json
import logging
from app.config import get_settings
from app.core.providers.models import ChatCompletionResult, UsageInfo
from app.core.providers.base import BaseAIProvider
from app.core.tools.base import tool_registry

logger = logging.getLogger(__name__)

class OpenAIProvider(BaseAIProvider):
    
    def __init__(self):
        super().__init__()
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
        if not self.settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        request_data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            request_data["max_tokens"] = max_tokens
        
        if tools:
            request_data["tools"] = tools
            if tool_choice:
                request_data["tool_choice"] = tool_choice
        
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
            
            if response.choices[0].message.tool_calls:
                result.tool_calls = response.choices[0].message.tool_calls
            
            return result
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def is_available(self) -> bool:
        return bool(self.settings.openai_api_key)
    
    async def execute_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, Any]]:
        results = []
        
        for tool_call in tool_calls:
            try:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                tool_call_id = tool_call.id
                
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
                        logger.error(f"Error executing tool {tool_name}: {str(e)}")
                        continue
                else:
                    logger.warning(f"Tool {tool_name} not found, skipping")
                    continue
            except Exception as e:
                logger.error(f"Error processing tool call {tool_call}: {str(e)}")
                continue
        
        return results
