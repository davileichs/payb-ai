"""
Tests for AI chat functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.chat_processor import ChatProcessor
from app.core.tools.base import BaseTool, ToolResult, tool_registry


class MockTool(BaseTool):
    """Mock tool for testing."""
    
    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(
            success=True,
            data=f"Mock tool executed with: {kwargs}",
            metadata={"tool_name": "MockTool"}
        )


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.ai_provider = "openai"
    settings.openai_api_key = "test-key"
    settings.openai_model = "gpt-4"
    return settings


@pytest.fixture
def chat_processor(mock_settings):
    """Create a ChatProcessor instance for testing."""
    with pytest.MonkeyPatch().context() as m:
        m.setattr("app.config.get_settings", lambda: mock_settings)
        return ChatProcessor()


class TestChatProcessor:
    """Test cases for ChatProcessor class."""
    
    def test_init(self, chat_processor):
        """Test ChatProcessor initialization."""
        assert chat_processor.settings is not None
        assert "openai" in chat_processor.providers
        assert "ollama" in chat_processor.providers
    
    def test_prepare_messages(self, chat_processor):
        """Test message preparation."""
        message = "Hello, AI!"
        history = [{"role": "user", "content": "Previous message"}]
        
        messages = chat_processor._prepare_messages(message, history)
        
        assert len(messages) == 3  # system + history + current
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == message
    
    def test_get_available_providers(self, chat_processor):
        """Test getting available providers."""
        providers = chat_processor.get_available_providers()
        assert isinstance(providers, list)
        assert "openai" in providers


class TestToolRegistry:
    """Test cases for ToolRegistry class."""
    
    def test_register_tool(self):
        """Test tool registration."""
        tool = MockTool()
        tool_registry.register(tool)
        
        assert tool_registry.get_tool("MockTool") == tool
    
    def test_get_all_tools(self):
        """Test getting all tools."""
        # Clear existing tools
        tool_registry._tools.clear()
        
        tool1 = MockTool()
        tool2 = MockTool()
        tool_registry.register(tool1)
        tool_registry.register(tool2)
        
        all_tools = tool_registry.get_all_tools()
        assert len(all_tools) == 2
    
    def test_get_tool_schemas(self):
        """Test getting tool schemas."""
        # Clear existing tools
        tool_registry._tools.clear()
        
        tool = MockTool()
        tool_registry.register(tool)
        
        schemas = tool_registry.get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "MockTool"


@pytest.mark.asyncio
async def test_mock_tool_execution():
    """Test mock tool execution."""
    tool = MockTool()
    result = await tool.execute(test_param="value")
    
    assert result.success is True
    assert "test_param" in result.data
    assert result.metadata["tool_name"] == "MockTool"
