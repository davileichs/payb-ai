"""
Redis-based storage for conversation persistence.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.config import get_settings

logger = logging.getLogger(__name__)


class RedisConversationStorage:
    """Redis-based storage for conversation persistence."""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None
        self.prefix = "slack_bot:conversation:"
        self.ttl = 86400  # 24 hours in seconds
        
    async def connect(self):
        """Connect to Redis."""
        try:
            # In production, you'd get Redis config from settings
            self.redis_client = redis.Redis(
                host=self.settings.redis_host if hasattr(self.settings, 'redis_host') else 'localhost',
                port=self.settings.redis_port if hasattr(self.settings, 'redis_port') else 6379,
                db=0,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    def _get_key(self, user_id: str, channel_id: str) -> str:
        """Get Redis key for conversation."""
        return f"{self.prefix}{user_id}:{channel_id}"
    
    async def save_conversation(self, conversation_data: Dict[str, Any]) -> bool:
        """Save conversation to Redis (minimal payload: user_id, channel_id, messages[role,content])."""
        if not self.redis_client:
            return False
        
        try:
            key = self._get_key(conversation_data["user_id"], conversation_data["channel_id"])
            # Only store minimal fields; assume conversation_data already minimal
            await self.redis_client.setex(key, self.ttl, json.dumps(conversation_data))
            return True
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            return False
    
    async def load_conversation(self, user_id: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """Load conversation from Redis."""
        if not self.redis_client:
            return None
        
        try:
            key = self._get_key(user_id, channel_id)
            data = await self.redis_client.get(key)
            if data:
                conversation = json.loads(data)
                return conversation
            return None
        except Exception as e:
            logger.error(f"Failed to load conversation: {e}")
            return None
    
    async def delete_conversation(self, user_id: str, channel_id: str) -> bool:
        """Delete conversation from Redis."""
        if not self.redis_client:
            return False
        
        try:
            key = self._get_key(user_id, channel_id)
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False
    
    async def cleanup_expired_conversations(self) -> int:
        """Clean up expired conversations (Redis handles this automatically with TTL)."""
        # Redis automatically expires keys based on TTL
        # This method is mainly for monitoring/logging
        return 0
    
    async def get_conversation_keys(self, pattern: str = None) -> List[str]:
        """Get all conversation keys matching a pattern."""
        if not self.redis_client:
            return []
        
        try:
            if pattern is None:
                pattern = f"{self.prefix}*"
            keys = await self.redis_client.keys(pattern)
            return [key.replace(self.prefix, "") for key in keys]
        except Exception as e:
            logger.error(f"Failed to get conversation keys: {e}")
            return []
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        if not self.redis_client:
            return {"status": "disconnected"}
        
        try:
            keys = await self.get_conversation_keys()
            return {
                "status": "connected",
                "total_conversations": len(keys),
                "ttl_seconds": self.ttl,
                "prefix": self.prefix
            }
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {"status": "error", "error": str(e)}


# Global Redis storage instance
redis_storage = RedisConversationStorage()


def get_redis_storage() -> RedisConversationStorage:
    """Get the global Redis storage instance."""
    return redis_storage
