from typing import List, Dict, Any, Optional
import httpx
import json
import logging
from app.config import get_settings
from app.core.providers.models import ChatCompletionResult, UsageInfo
from app.core.providers.base import BaseAIProvider
from app.core.tools.base import tool_registry

logger = logging.getLogger(__name__)

class OllamaProvider(BaseAIProvider):
    
    def __init__(self):
        super().__init__()
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
        for msg in messages:
            if msg["role"] == "system":
                msg["role"] = "assistant"
        
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
                
                usage = UsageInfo(
                    prompt_tokens=result_data.get("prompt_eval_count", 0),
                    completion_tokens=result_data.get("eval_count", 0),
                    total_tokens=result_data.get("prompt_eval_count", 0) + result_data.get("eval_count", 0)
                )
                
                message_content = result_data.get("message", {}).get("content", "")
                
                # Check if the content contains tool call JSON (Ollama sometimes includes this in content)
                tool_calls = None
                if "tool_calls" in result_data.get("message", {}):
                    tool_calls = result_data["message"]["tool_calls"]
                elif "tool_calls" in message_content:
                    # Try to extract tool calls from content if Ollama includes them there
                    try:
                        import re
                        tool_call_match = re.search(r'"tool_calls":\s*\[.*?\]', message_content, re.DOTALL)
                        if tool_call_match:
                            tool_calls = json.loads(f"{{{tool_call_match.group()}}}")["tool_calls"]
                            # Remove tool calls from content to avoid duplication
                            message_content = re.sub(r'"tool_calls":\s*\[.*?\],?\s*', '', message_content, flags=re.DOTALL)
                    except:
                        pass
                
                result = ChatCompletionResult(
                    content=message_content,
                    model=result_data.get("model", self.model),
                    usage=usage
                )
                
                if tool_calls:
                    result.tool_calls = tool_calls
                
                return result
                
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")
    
    def is_available(self) -> bool:
        return bool(self.base_url)
    
    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                return response.status_code == 200
        except:
            return False
    
    async def execute_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, Any]]:
        results = []
        
        for tool_call in tool_calls:
            try:
                # Handle different tool call formats
                if hasattr(tool_call, 'function'):
                    # OpenAI format
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_call_id = tool_call.id
                elif isinstance(tool_call, dict):
                    # Dictionary format (Ollama might return this)
                    tool_name = tool_call.get('function', {}).get('name')
                    tool_args = json.loads(tool_call.get('function', {}).get('arguments', '{}'))
                    tool_call_id = tool_call.get('id', f"call_{len(results)}")
                else:
                    # Try to access attributes directly
                    tool_name = getattr(tool_call, 'name', None)
                    tool_args = json.loads(getattr(tool_call, 'arguments', '{}'))
                    tool_call_id = getattr(tool_call, 'id', f"call_{len(results)}")
                
                if not tool_name:
                    logger.error(f"Could not extract tool name from tool call: {tool_call}")
                    continue
                
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
