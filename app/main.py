"""
Main FastAPI application for the Slack Bot AI Chat Webhook.
"""

import logging
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import get_settings
from app.api.slack_routes import router as slack_router
from app.api.ai_routes import router as ai_router
from app.core.conversation_manager import get_conversation_manager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Slack Bot AI Chat application...")
    settings = get_settings()
    logger.info(f"Configuration loaded: AI provider={settings.ai_provider}")
    
    # Initialize conversation manager
    conversation_manager = get_conversation_manager()
    await conversation_manager._load_conversations()
    logger.info("Conversation manager initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Slack Bot AI Chat application...")
    if hasattr(conversation_manager, 'redis_storage') and conversation_manager.redis_storage:
        await conversation_manager.redis_storage.disconnect()


# Create FastAPI app
app = FastAPI(
    title="Slack Bot AI Chat Webhook",
    description="A Slack bot webhook that integrates with AI chat services",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(slack_router)
app.include_router(ai_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Slack Bot AI Chat Webhook API",
        "version": "1.0.0",
        "endpoints": {
            "slack_webhook": "/slack",
            "ai_chat": "/api/ai/chat",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "slack-bot-ai-chat",
        "version": "1.0.0"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
