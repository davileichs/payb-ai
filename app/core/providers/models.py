"""
Unified models for AI provider responses.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class UsageInfo(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResult(BaseModel):
    """Standardized chat completion result from any AI provider."""
    content: str
    model: str
    usage: UsageInfo
    tool_calls: Optional[List[Any]] = None
    
    class Config:
        # Allow extra fields for provider-specific data
        extra = "allow"
