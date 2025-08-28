from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.auth.middleware import auth_scheme, get_current_user
from app.core.chat_processor import get_chat_processor
from app.core.tools.base import tool_registry
from app.core.utils.provider_manager import get_provider_manager

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

class ProviderSwitchRequest(BaseModel):
    channel_id: str
    provider: str
    model: Optional[str] = None

class ProviderResponse(BaseModel):
    success: bool
    message: str
    current_provider: str
    available_providers: List[str]

class ProviderStatusResponse(BaseModel):
    channel_id: str
    current_provider: str
    default_provider: str
    available_providers: List[str]
    is_custom: bool

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

@router.post("/provider/switch", response_model=ProviderResponse)
async def switch_provider(
    request: ProviderSwitchRequest,
    _: dict = Depends(auth_scheme)
):
    """Switch the AI provider for a specific channel"""
    try:
        provider_manager = get_provider_manager()
        
        success = provider_manager.set_provider_for_channel(
            channel_id=request.channel_id,
            provider_name=request.provider
        )
        
        if success:
            # Update model if specified
            if request.model:
                provider = provider_manager.get_provider_for_channel(request.channel_id)
                provider.set_model(request.model)
            
            current_provider = provider_manager.get_channel_provider_name(request.channel_id)
            available_providers = provider_manager.get_available_providers()
            
            return ProviderResponse(
                success=True,
                message=f"Provider switched to {request.provider} for channel {request.channel_id}",
                current_provider=current_provider,
                available_providers=available_providers
            )
        else:
            available_providers = provider_manager.get_available_providers()
            return ProviderResponse(
                success=False,
                message=f"Invalid provider: {request.provider}",
                current_provider=provider_manager.get_channel_provider_name(request.channel_id),
                available_providers=available_providers
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error switching provider: {str(e)}"
        )

@router.get("/provider/status/{channel_id}", response_model=ProviderStatusResponse)
async def get_provider_status(
    channel_id: str,
    _: dict = Depends(auth_scheme)
):
    """Get the current provider status for a specific channel"""
    try:
        provider_manager = get_provider_manager()
        
        current_provider = provider_manager.get_channel_provider_name(channel_id)
        default_provider = provider_manager.get_default_provider_name()
        available_providers = provider_manager.get_available_providers()
        is_custom = channel_id in provider_manager.get_all_channel_providers()
        
        return ProviderStatusResponse(
            channel_id=channel_id,
            current_provider=current_provider,
            default_provider=default_provider,
            available_providers=available_providers,
            is_custom=is_custom
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting provider status: {str(e)}"
        )

@router.delete("/provider/reset/{channel_id}", response_model=ProviderResponse)
async def reset_provider(
    channel_id: str,
    _: dict = Depends(auth_scheme)
):
    """Reset the provider for a specific channel to default"""
    try:
        provider_manager = get_provider_manager()
        
        provider_manager.clear_channel_provider(channel_id)
        current_provider = provider_manager.get_channel_provider_name(channel_id)
        available_providers = provider_manager.get_available_providers()
        
        return ProviderResponse(
            success=True,
            message=f"Provider reset to default for channel {channel_id}",
            current_provider=current_provider,
            available_providers=available_providers
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting provider: {str(e)}"
        )

@router.get("/providers", response_model=Dict[str, Any])
async def get_available_providers(
    _: dict = Depends(auth_scheme)
):
    """Get all available providers and current channel mappings"""
    try:
        provider_manager = get_provider_manager()
        
        return {
            "available_providers": provider_manager.get_available_providers(),
            "default_provider": provider_manager.get_default_provider_name(),
            "channel_providers": provider_manager.get_all_channel_providers()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting providers: {str(e)}"
        )

@router.post("/reload/agents")
async def reload_agents_config(
    _: dict = Depends(auth_scheme)
):
    """Reload agents configuration from agents.json file"""
    try:
        from app.core.utils.agent_manager import get_agent_manager
        agent_manager = get_agent_manager()
        
        success = agent_manager.reload_agents_config()
        
        if success:
            return {
                "success": True,
                "message": "Agents configuration reloaded successfully",
                "agents_count": len(agent_manager.agents_config.get("agents", {}))
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reload agents configuration"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reloading agents config: {str(e)}"
        )

@router.post("/reload/config")
async def reload_application_config(
    _: dict = Depends(auth_scheme)
):
    """Reload application configuration from .env file"""
    try:
        # Note: Pydantic settings are typically loaded once at startup
        # For .env changes, a restart is usually required
        # But we can provide a status endpoint to check current config
        from app.config import get_settings
        settings = get_settings()
        
        return {
            "success": True,
            "message": "Configuration status retrieved (restart required for .env changes)",
            "current_config": {
                "ai_provider": settings.ai_provider,
                "openai_model": settings.openai_model,
                "ollama_model": settings.ollama_model,
                "ai_temperature": settings.ai_temperature,
                "debug": settings.debug
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting config status: {str(e)}"
        )