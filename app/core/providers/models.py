from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResult(BaseModel):
    content: str
    model: str
    usage: UsageInfo
    tool_calls: Optional[List[Any]] = None
    
    class Config:
        # Allow extra fields for provider-specific data
        extra = "allow"
