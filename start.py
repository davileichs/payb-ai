#!/usr/bin/env python3
"""
Startup script for the Slack Bot AI Chat application.
"""

import uvicorn
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    
    print(f"Starting Slack Bot AI Chat application...")
    print(f"Host: {settings.host}")
    print(f"Port: {settings.port}")
    print(f"Debug: {settings.debug}")
    print(f"AI Provider: {settings.ai_provider}")
    print(f"Log Level: {settings.log_level}")
    print("-" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
