import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict
from app.config import get_settings
from app.core.storage.redis_storage import get_redis_storage

logger = logging.getLogger(__name__)

@dataclass
class Message:
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content
        }

@dataclass
class Conversation:
    id: str
    user_id: str
    channel_id: str
    provider: str
    model: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "messages": [msg.to_dict() for msg in self.messages if msg.role != "tool"]
        }
    
    def get_llm_context(self, max_messages: int = 20) -> List[Dict[str, str]]:
        # Filter out system messages and tool messages for LLM context
        llm_messages = []
        for msg in self.messages[-max_messages:]:
            if msg.role in ['user', 'assistant']:
                llm_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        return llm_messages
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata
        )
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
    
    def get_message_count(self) -> int:
        return len(self.messages)

class ConversationManager:
    
    def __init__(self):
        self.settings = get_settings()
        self.conversations: Dict[str, Conversation] = {}
        
        self.max_messages_per_conversation = self.settings.max_messages_per_conversation
        
        # Initialize storage (Redis if available, otherwise in-memory)
        self.redis_storage = get_redis_storage()
        self.use_redis = hasattr(self.settings, 'redis_host') and self.settings.redis_host
        
        # Load existing conversations (synchronous initialization)
        self._load_conversations_sync()
    
    def _load_conversations_sync(self):
        if self.use_redis:
            try:
                # Try to connect to Redis synchronously
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Schedule async connection
                        loop.create_task(self._connect_redis())
                    else:
                        # Run in current loop
                        loop.run_until_complete(self._connect_redis())
                except RuntimeError:
                    self.use_redis = False
                    logger.info("Conversation manager initialized with in-memory storage (no event loop)")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis, falling back to in-memory: {e}")
                self.use_redis = False
        else:
            logger.info("Conversation manager initialized with in-memory storage")
    
    async def _connect_redis(self):
        try:
            await self.redis_storage.connect()
            logger.info("Conversation manager initialized with Redis storage")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, falling back to in-memory: {e}")
            self.use_redis = False
    
    async def _load_conversations(self):
        # This method is kept for compatibility but the actual loading is done in _load_conversations_sync
        pass
    
    async def _save_conversations(self):
        if self.use_redis:
            for conversation in self.conversations.values():
                await self.redis_storage.save_conversation(conversation.to_dict())
    
    def _save_conversations_sync(self):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, schedule the save
                loop.create_task(self._save_conversations())
            else:
                # If we're in a sync context, run the save
                loop.run_until_complete(self._save_conversations())
        except RuntimeError:
            # No event loop, skip saving
            pass
    
    def _generate_conversation_id(self, user_id: str, channel_id: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{user_id}_{channel_id}_{timestamp}"
    
    def get_or_create_conversation(
        self,
        user_id: str,
        channel_id: str,
        provider: str,
        model: str
    ) -> Conversation:
        """Get existing conversation or create a new one. Conversations are shared per channel."""
        # Use only channel_id as the key - all users in the same channel share conversation
        conversation_key = channel_id
        
        if conversation_key in self.conversations:
            conversation = self.conversations[conversation_key]
            return conversation
        
        conversation_id = self._generate_conversation_id("shared", channel_id)
        conversation = Conversation(
            id=conversation_id,
            user_id="shared",  # Indicates this is a shared channel conversation
            channel_id=channel_id,
            provider=provider,
            model=model,
            messages=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            metadata={"source": "slack", "type": "shared_channel"}
        )
        
        self.conversations[conversation_key] = conversation
        logger.info(f"Created new shared conversation {conversation_id} for channel {channel_id}")
        
        return conversation
    
    def add_user_message(
        self,
        user_id: str,
        channel_id: str,
        content: str,
        provider: str,
        model: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Add a user message to the shared channel conversation."""
        conversation = self.get_or_create_conversation(user_id, channel_id, provider, model)
        
        user_tagged_content = f"[{user_id}]: {content}"
        
        if metadata is None:
            metadata = {}
        metadata["sender_user_id"] = user_id
        
        conversation.add_message("user", user_tagged_content, metadata)
        
        # Check message limit
        if conversation.get_message_count() > self.max_messages_per_conversation:
            self._trim_conversation(conversation)
        
        self._save_conversations_sync()
        return conversation
    
    def add_ai_response(
        self,
        user_id: str,
        channel_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Conversation]:
        """Add an AI response to the shared channel conversation."""
        # Use channel_id as the key since conversations are shared per channel
        conversation_key = channel_id
        
        if conversation_key in self.conversations:
            conversation = self.conversations[conversation_key]
            conversation.add_message("assistant", content, metadata)
            
            # Check message limit
            if conversation.get_message_count() > self.max_messages_per_conversation:
                self._trim_conversation(conversation)
            
            self._save_conversations_sync()
            return conversation
        
        logger.warning(f"No shared conversation found for channel {channel_id}")
        return None
    
    def add_tool_result(
        self,
        user_id: str,
        channel_id: str,
        tool_name: str,
        tool_result: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Conversation]:
        """Add a tool execution result to the shared channel conversation."""
        # Use channel_id as the key since conversations are shared per channel
        conversation_key = channel_id
        
        if conversation_key in self.conversations:
            conversation = self.conversations[conversation_key]
            tool_content = f"Tool {tool_name} executed: {tool_result}"
            conversation.add_message("tool", tool_content, metadata)
            self._save_conversations_sync()
            return conversation
        
        return None
    
    def get_conversation_context(
        self,
        user_id: str,
        channel_id: str,
        max_messages: int = None
    ) -> List[Dict[str, str]]:
        """Get conversation context for LLM processing from shared channel conversation."""
        # Use channel_id as the key since conversations are shared per channel
        conversation_key = channel_id
        
        if conversation_key in self.conversations:
            conversation = self.conversations[conversation_key]
            # Use configured limit if max_messages not specified
            if max_messages is None:
                max_messages = self.max_messages_per_conversation
            return conversation.get_llm_context(max_messages)
        
        return []
    
    def clear_conversation(self, user_id: str, channel_id: str) -> bool:
        # Use channel_id as the key since conversations are shared per channel
        conversation_key = channel_id
        
        if conversation_key in self.conversations:
            del self.conversations[conversation_key]
            if self.use_redis:
                # Schedule async delete without awaiting (keep method sync)
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.redis_storage.delete_conversation("shared", channel_id))
                    else:
                        loop.run_until_complete(self.redis_storage.delete_conversation("shared", channel_id))
                except RuntimeError:
                    pass
            self._save_conversations_sync()
            logger.info(f"Cleared shared conversation for channel {channel_id}")
            return True
        
        return False
    
    def cleanup_conversations(self, max_conversations: int = None) -> int:
        if max_conversations is None:
            # No automatic cleanup - conversations persist indefinitely
            return 0
        
        if len(self.conversations) <= max_conversations:
            return 0
        
        sorted_conversations = sorted(
            self.conversations.items(),
            key=lambda x: x[1].updated_at
        )
        
        conversations_to_remove = sorted_conversations[:-max_conversations]
        removed_keys = [key for key, _ in conversations_to_remove]
        
        for key in removed_keys:
            del self.conversations[key]
        
        if removed_keys:
            logger.info(f"Cleaned up {len(removed_keys)} old conversations")
            self._save_conversations_sync()
        
        return len(removed_keys)
    
    def _trim_conversation(self, conversation: Conversation):
        if len(conversation.messages) > self.max_messages_per_conversation:
            # Keep system message if exists, then recent messages
            system_messages = [msg for msg in conversation.messages if msg.role == "system"]
            other_messages = [msg for msg in conversation.messages if msg.role != "system"]
            
            # Keep recent messages
            recent_messages = other_messages[-self.max_messages_per_conversation:]
            
            conversation.messages = system_messages + recent_messages
            logger.info(f"Trimmed conversation {conversation.id} to {len(conversation.messages)} messages")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        total_conversations = len(self.conversations)
        total_messages = sum(conv.get_message_count() for conv in self.conversations.values())
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "active_conversations": total_conversations,
            "max_messages_per_conversation": self.max_messages_per_conversation,
            "storage_type": "redis" if self.use_redis else "in-memory"
        }
    
    def get_configuration(self) -> Dict[str, Any]:
        return {
            "max_messages_per_conversation": self.settings.max_messages_per_conversation,
            "storage_type": "redis" if self.use_redis else "in-memory",
            "redis_configured": bool(self.settings.redis_host)
        }

conversation_manager = ConversationManager()

def get_conversation_manager() -> ConversationManager:
    return conversation_manager
