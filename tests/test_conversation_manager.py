"""
Tests for conversation manager functionality.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from app.core.conversation_manager import ConversationManager, Conversation, Message
from app.config import get_settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.redis_host = None  # No Redis for testing
    settings.max_messages_per_conversation = 100
    return settings


@pytest.fixture
def conversation_manager(mock_settings):
    """Create a ConversationManager instance for testing."""
            with patch("app.core.conversation_manager.get_settings", return_value=mock_settings):
            with patch("app.core.conversation_manager.get_redis_storage"):
            manager = ConversationManager()
            return manager


class TestConversationManager:
    """Test cases for ConversationManager class."""
    
    def test_init(self, conversation_manager):
        """Test ConversationManager initialization."""
        assert conversation_manager.conversations == {}
        assert conversation_manager.max_messages_per_conversation == 100
    
    def test_generate_conversation_id(self, conversation_manager):
        """Test conversation ID generation."""
        user_id = "U123"
        channel_id = "C456"
        
        conversation_id = conversation_manager._generate_conversation_id(user_id, channel_id)
        
        assert user_id in conversation_id
        assert channel_id in conversation_id
        assert "_" in conversation_id
    
    def test_get_or_create_conversation_new(self, conversation_manager):
        """Test creating a new conversation."""
        user_id = "U123"
        channel_id = "C456"
        provider = "openai"
        model = "gpt-4"
        
        conversation = conversation_manager.get_or_create_conversation(
            user_id, channel_id, provider, model
        )
        
        assert conversation.user_id == user_id
        assert conversation.channel_id == channel_id
        assert conversation.provider == provider
        assert conversation.model == model
        assert conversation.messages == []
        
        # Check that it's stored
        key = f"{user_id}:{channel_id}"
        assert key in conversation_manager.conversations
    
    def test_get_or_create_conversation_existing(self, conversation_manager):
        """Test getting an existing conversation."""
        user_id = "U123"
        channel_id = "C456"
        provider = "openai"
        model = "gpt-4"
        
        # Create first conversation
        conversation1 = conversation_manager.get_or_create_conversation(
            user_id, channel_id, provider, model
        )
        
        # Get the same conversation
        conversation2 = conversation_manager.get_or_create_conversation(
            user_id, channel_id, provider, model
        )
        
        assert conversation1.id == conversation2.id
        assert len(conversation_manager.conversations) == 1
    
    def test_add_user_message(self, conversation_manager):
        """Test adding a user message."""
        user_id = "U123"
        channel_id = "C456"
        content = "Hello, AI!"
        
        conversation = conversation_manager.add_user_message(
            user_id, channel_id, content, "openai", "gpt-4"
        )
        
        assert len(conversation.messages) == 1
        assert conversation.messages[0].role == "user"
        assert conversation.messages[0].content == content
    
    def test_add_ai_response(self, conversation_manager):
        """Test adding an AI response."""
        user_id = "U123"
        channel_id = "C456"
        
        # First add a user message to create conversation
        conversation_manager.add_user_message(
            user_id, channel_id, "Hello", "openai", "gpt-4"
        )
        
        # Add AI response
        ai_content = "Hello! How can I help you?"
        result = conversation_manager.add_ai_response(
            user_id, channel_id, ai_content
        )
        
        assert result is not None
        assert len(result.messages) == 2
        assert result.messages[1].role == "assistant"
        assert result.messages[1].content == ai_content
    
    def test_get_conversation_context(self, conversation_manager):
        """Test getting conversation context for LLM."""
        user_id = "U123"
        channel_id = "C456"
        
        # Add some messages
        conversation_manager.add_user_message(
            user_id, channel_id, "Hello", "openai", "gpt-4"
        )
        conversation_manager.add_ai_response(
            user_id, channel_id, "Hi there!"
        )
        conversation_manager.add_user_message(
            user_id, channel_id, "How are you?", "openai", "gpt-4"
        )
        
        context = conversation_manager.get_conversation_context(user_id, channel_id)
        
        assert len(context) == 4  # 2 user + 2 assistant messages
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"
        assert context[2]["role"] == "user"
        assert context[3]["role"] == "assistant"
    
    def test_clear_conversation(self, conversation_manager):
        """Test clearing a conversation."""
        user_id = "U123"
        channel_id = "C456"
        
        # Create a conversation
        conversation_manager.add_user_message(
            user_id, channel_id, "Hello", "openai", "gpt-4"
        )
        
        # Clear it
        result = conversation_manager.clear_conversation(user_id, channel_id)
        
        assert result is True
        key = f"{user_id}:{channel_id}"
        assert key not in conversation_manager.conversations
    
    def test_clear_conversation_not_found(self, conversation_manager):
        """Test clearing a non-existent conversation."""
        result = conversation_manager.clear_conversation("U999", "C999")
        assert result is False
    
    def test_get_configuration(self, conversation_manager):
        """Test getting conversation configuration."""
        config = conversation_manager.get_configuration()
        
        assert "max_messages_per_conversation" in config
        assert "storage_type" in config
        assert "redis_configured" in config
        
        assert config["max_messages_per_conversation"] == 100
        assert config["storage_type"] == "in-memory"
        assert config["redis_configured"] is False
    
    def test_cleanup_conversations(self, conversation_manager):
        """Test conversation cleanup functionality."""
        # Create multiple conversations
        for i in range(15):
            user_id = f"U{i}"
            channel_id = f"C{i}"
            conversation_manager.add_user_message(
                user_id, channel_id, f"Message {i}", "openai", "gpt-4"
            )
        
        # Should have 15 conversations
        assert len(conversation_manager.conversations) == 15
        
        # Clean up to keep only 10 conversations
        cleaned_count = conversation_manager.cleanup_conversations(10)
        
        # Should have cleaned up 5 conversations
        assert cleaned_count == 5
        assert len(conversation_manager.conversations) == 10
        
        # Test cleanup when under limit
        cleaned_count = conversation_manager.cleanup_conversations(15)
        assert cleaned_count == 0
        assert len(conversation_manager.conversations) == 10


class TestConversation:
    """Test cases for Conversation class."""
    
    def test_conversation_init(self):
        """Test Conversation initialization."""
        conversation = Conversation(
            id="test_id",
            user_id="U123",
            channel_id="C456",
            provider="openai",
            model="gpt-4",
            messages=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert conversation.id == "test_id"
        assert conversation.user_id == "U123"
        assert conversation.channel_id == "C456"
        assert conversation.provider == "openai"
        assert conversation.model == "gpt-4"
    
    def test_add_message(self):
        """Test adding a message to conversation."""
        conversation = Conversation(
            id="test_id",
            user_id="U123",
            channel_id="C456",
            provider="openai",
            model="gpt-4",
            messages=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        conversation.add_message("user", "Hello")
        
        assert len(conversation.messages) == 1
        assert conversation.messages[0].role == "user"
        assert conversation.messages[0].content == "Hello"
    
    def test_get_llm_context(self):
        """Test getting LLM context from conversation."""
        conversation = Conversation(
            id="test_id",
            user_id="U123",
            channel_id="C456",
            provider="openai",
            model="gpt-4",
            messages=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Add messages
        conversation.add_message("user", "Hello")
        conversation.add_message("assistant", "Hi!")
        conversation.add_message("system", "System message")
        conversation.add_message("tool", "Tool result")
        
        context = conversation.get_llm_context()
        
        # Should only include user and assistant messages
        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"
        assert "system" not in [msg["role"] for msg in context]
        assert "tool" not in [msg["role"] for msg in context]


class TestMessage:
    """Test cases for Message class."""
    
    def test_message_init(self):
        """Test Message initialization."""
        timestamp = datetime.now(timezone.utc)
        message = Message(
            role="user",
            content="Hello",
            timestamp=timestamp,
            metadata={"user_id": "U123"}
        )
        
        assert message.role == "user"
        assert message.content == "Hello"
        assert message.timestamp == timestamp
        assert message.metadata["user_id"] == "U123"
    
    def test_message_to_dict(self):
        """Test Message to_dict conversion."""
        timestamp = datetime.now(timezone.utc)
        message = Message(
            role="user",
            content="Hello",
            timestamp=timestamp,
            metadata={"user_id": "U123"}
        )
        
        message_dict = message.to_dict()
        
        assert message_dict["role"] == "user"
        assert message_dict["content"] == "Hello"
        assert "timestamp" in message_dict
        assert message_dict["metadata"]["user_id"] == "U123"
