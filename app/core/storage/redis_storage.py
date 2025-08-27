import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.config import get_settings

logger = logging.getLogger(__name__)

class RedisConversationStorage:
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None
        self.prefix = "slack_bot:conversation:"
        self.ttl = None  # No expiration - conversations persist until manually deleted
        
    async def connect(self):
        try:
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
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    def _get_key(self, user_id: str, channel_id: str) -> str:
        return f"{self.prefix}channel:{channel_id}"
    
    async def save_conversation(self, conversation_data: Dict[str, Any]) -> bool:
        if not self.redis_client:
            return False
        
        try:
            key = self._get_key(conversation_data["user_id"], conversation_data["channel_id"])
            # Store conversation permanently (no expiration)
            await self.redis_client.set(key, json.dumps(conversation_data))
            return True
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            return False
    
    async def load_conversation(self, user_id: str, channel_id: str) -> Optional[Dict[str, Any]]:
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
        if not self.redis_client:
            return False
        
        try:
            key = self._get_key(user_id, channel_id)
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False
    
    async def get_conversation_count(self) -> int:
        if not self.redis_client:
            return 0
        
        try:
            keys = await self.redis_client.keys(f"{self.prefix}*")
            return len(keys)
        except Exception as e:
            logger.error(f"Failed to get conversation count: {e}")
            return 0
    
    async def get_all_conversation_keys(self) -> List[str]:
        if not self.redis_client:
            return []
        
        try:
            keys = await self.redis_client.keys(f"{self.prefix}*")
            return keys
        except Exception as e:
            logger.error(f"Failed to get conversation keys: {e}")
            return []
    
    async def cleanup_old_conversations(self, keep_count: int = None) -> int:
        if not self.redis_client:
            return 0
            
        if keep_count is None:
            logger.info("No cleanup requested - conversations persist indefinitely")
            return 0
        
        try:
            keys = await self.redis_client.keys(f"{self.prefix}*")
            if len(keys) <= keep_count:
                logger.info(f"Only {len(keys)} conversations exist, no cleanup needed")
                return 0
            
            key_times = []
            for key in keys:
                try:
                    data = await self.redis_client.get(key)
                    if data:
                        conversation = json.loads(data)
                        # Use the timestamp of the last message or current time as fallback
                        last_message_time = datetime.now().timestamp()
                        if conversation.get('messages'):
                            # If messages have timestamps, use the latest one
                            for msg in reversed(conversation['messages']):
                                if isinstance(msg, dict) and 'timestamp' in msg:
                                    last_message_time = msg['timestamp']
                                    break
                        
                        key_times.append((key, last_message_time))
                except Exception:
                    # If we can't read the conversation, mark it for deletion
                    key_times.append((key, 0))
            
            # Sort by timestamp (oldest first)
            key_times.sort(key=lambda x: x[1])
            
            to_delete = len(keys) - keep_count
            deleted_count = 0
            
            logger.info(f"Manual cleanup requested: deleting {to_delete} oldest conversations")
            for key, _ in key_times[:to_delete]:
                try:
                    await self.redis_client.delete(key)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete conversation {key}: {e}")
            
            logger.info(f"Manual cleanup completed: deleted {deleted_count} conversations")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old conversations: {e}")
            return 0
    
    async def cleanup_expired_conversations(self) -> int:
        return 0
    
    async def get_conversation_keys(self, pattern: str = None) -> List[str]:
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
    return redis_storage
