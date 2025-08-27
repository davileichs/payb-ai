from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.auth.middleware import auth_scheme, get_current_user
from app.core.chat_processor import get_chat_processor
from app.core.tools.base import tool_registry

router = APIRouter(prefix="/api/ai", tags=["ai"])

class ChatRequest(BaseModel):
    message: str
    user_id: str
    channel_id: str
    use_tools: bool = True
    temperature: Optional[float] = None

class ChatResponse(BaseModel):
    response: str
    provider: str
    model: str
    usage: Dict[str, Any]
    conversation_history: List[Dict[str, str]]

class HealthResponse(BaseModel):
    status: str
    tools_count: int

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    _: dict = Depends(auth_scheme)
):
    try:
        chat_processor = get_chat_processor()
        
        result = await chat_processor.process_message(
            message=request.message,
            user_id=request.user_id,
            channel_id=request.channel_id,
            use_tools=request.use_tools
        )
        
        return ChatResponse(
            response=result["response"],
            provider=result["provider"],
            model=result["model"],
            usage=result.get("usage", {}),
            conversation_history=result["conversation_history"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )

@router.get("/health", response_model=HealthResponse)
async def ai_health_check():
    chat_processor = get_chat_processor()
    
    return HealthResponse(
        status="healthy",
        tools_count=len(tool_registry.get_all_tools())
    )