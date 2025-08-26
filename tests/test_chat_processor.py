"""
Tests for the ChatProcessor class.
Tests both mocked interactions and real OpenAI API calls.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from app.core.chat_processor import ChatProcessor
from app.core.providers.models import ChatCompletionResult, UsageInfo
from app.core.tools.base import ToolResult


class TestChatProcessor:
    """Test cases for ChatProcessor."""
    
    @pytest.fixture
    def chat_processor(self):
        """Create a ChatProcessor instance for testing."""
        return ChatProcessor()
    
    @pytest.fixture
    def mock_conversation(self):
        """Mock conversation data."""
        return {
            "user_id": "test_user_123",
            "channel_id": "test_channel_456",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"},
                {"role": "assistant", "content": "I'm doing well, thank you!"}
            ]
        }
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response."""
        return ChatCompletionResult(
            content="Hello! I'm here to help you with any questions.",
            model="gpt-4",
            usage=UsageInfo(
                prompt_tokens=50,
                completion_tokens=25,
                total_tokens=75
            )
        )
    
    @pytest.fixture
    def mock_tool_calls_response(self):
        """Mock OpenAI response with tool calls."""
        response = ChatCompletionResult(
            content="I'll check the weather for you.",
            model="gpt-4",
            usage=UsageInfo(
                prompt_tokens=60,
                completion_tokens=30,
                total_tokens=90
            )
        )
        response.tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "Weather",
                    "arguments": '{"location": "London", "units": "metric"}'
                }
            }
        ]
        return response
    
    def test_chat_processor_initialization(self, chat_processor):
        """Test ChatProcessor initialization."""
        assert chat_processor.settings is not None
        assert "openai" in chat_processor.providers
        assert "ollama" in chat_processor.providers
        assert chat_processor.conversation_manager is not None
        assert chat_processor.agent_manager is not None
    
    def test_provider_availability_check(self, chat_processor):
        """Test provider availability checking."""
        # Test OpenAI provider availability
        openai_available = chat_processor.providers["openai"].is_available()
        assert isinstance(openai_available, bool)
        
        # Test Ollama provider availability
        ollama_available = chat_processor.providers["ollama"].is_available()
        assert isinstance(ollama_available, bool)
    
    @pytest.mark.asyncio
    async def test_process_message_basic(self, chat_processor, mock_conversation):
        """Test basic message processing without tools."""
        # Mock the conversation manager
        with patch.object(chat_processor.conversation_manager, 'get_or_create_conversation') as mock_get_conv, \
             patch.object(chat_processor.conversation_manager, 'add_user_message') as mock_add_user, \
             patch.object(chat_processor.conversation_manager, 'add_ai_response') as mock_add_ai, \
             patch.object(chat_processor.conversation_manager, 'get_conversation_context') as mock_get_context:
            
            # Setup mocks
            mock_get_conv.return_value = Mock(id="conv_123")
            mock_get_context.return_value = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
            
            # Mock the provider response
            with patch.object(chat_processor.providers["openai"], 'chat_completion') as mock_chat:
                mock_chat.return_value = ChatCompletionResult(
                    content="Hello! How can I help you today?",
                    model="gpt-4",
                    usage=UsageInfo(
                        prompt_tokens=30,
                        completion_tokens=15,
                        total_tokens=45
                    )
                )
                
                # Process message
                result = await chat_processor.process_message(
                    message="Hello",
                    user_id="test_user",
                    channel_id="test_channel",
                    use_tools=False
                )
                
                # Verify result structure
                assert "response" in result
                assert "provider" in result
                assert "model" in result
                assert "usage" in result
                assert "conversation_history" in result
                assert "conversation_id" in result
                
                # Verify mocks were called
                mock_get_conv.assert_called_once()
                mock_add_user.assert_called_once()
                mock_add_ai.assert_called_once()
                mock_get_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_with_tools(self, chat_processor, mock_tool_calls_response):
        """Test message processing with tool calls."""
        with patch.object(chat_processor.conversation_manager, 'get_or_create_conversation') as mock_get_conv, \
             patch.object(chat_processor.conversation_manager, 'add_user_message') as mock_add_user, \
             patch.object(chat_processor.conversation_manager, 'add_tool_result') as mock_add_tool, \
             patch.object(chat_processor.conversation_manager, 'add_ai_response') as mock_add_ai, \
             patch.object(chat_processor.conversation_manager, 'get_conversation_context') as mock_get_context:
            
            # Setup mocks
            mock_get_conv.return_value = Mock(id="conv_123")
            mock_get_context.return_value = [
                {"role": "user", "content": "What's the weather like?"}
            ]
            
            # Mock the provider response with tool calls
            with patch.object(chat_processor.providers["openai"], 'chat_completion') as mock_chat:
                mock_chat.return_value = mock_tool_calls_response
                
                # Mock tool execution
                with patch.object(chat_processor, '_execute_tools') as mock_execute_tools:
                    mock_execute_tools.return_value = [
                        {
                            "tool_call_id": "call_123",
                            "tool_name": "Weather",
                            "result": {"temperature": "22°C", "condition": "Sunny"}
                        }
                    ]
                    
                    # Process message
                    result = await chat_processor.process_message(
                        message="What's the weather like?",
                        user_id="test_user",
                        channel_id="test_channel",
                        use_tools=True
                    )
                    
                    # Verify tool execution was called
                    mock_execute_tools.assert_called_once()
                    
                    # Verify tool result was added
                    mock_add_tool.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_tools_openai_format(self, chat_processor):
        """Test tool execution with OpenAI format."""
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "WeatherTool",
                    "arguments": '{"location": "Paris", "units": "metric"}'
                }
            }
        ]
        
        # Mock tool registry
        with patch('app.core.tools.base.tool_registry') as mock_registry:
            mock_tool = Mock()
            mock_tool.execute = AsyncMock(return_value=ToolResult(
                success=True,
                data={"temperature": "18°C", "condition": "Cloudy"}
            ))
            mock_registry.get_tool.return_value = mock_tool
            
            # Execute tools
            results = await chat_processor._execute_tools(tool_calls, "openai")
            
            # Verify results
            assert len(results) == 1
            assert results[0]["tool_call_id"] == "call_123"
            assert results[0]["tool_name"] == "WeatherTool"
            assert "temperature" in str(results[0]["result"])
    
    @pytest.mark.asyncio
    async def test_execute_tools_ollama_format(self, chat_processor):
        """Test tool execution with Ollama format."""
        tool_calls = [
            {
                "id": "call_456",
                "type": "function",
                "function": {
                    "name": "WeatherTool",
                    "arguments": '{"location": "Tokyo", "units": "metric"}'
                }
            }
        ]
        
        # Mock tool registry
        with patch('app.core.tools.base.tool_registry') as mock_registry:
            mock_tool = Mock()
            mock_tool.execute = AsyncMock(return_value=ToolResult(
                success=True,
                data={"temperature": "25°C", "condition": "Sunny"}
            ))
            mock_registry.get_tool.return_value = mock_tool
            
            # Execute tools
            results = await chat_processor._execute_tools(tool_calls, "ollama")
            
            # Verify results
            assert len(results) == 1
            assert results[0]["tool_call_id"] == "call_456"
            assert results[0]["tool_name"] == "WeatherTool"
            assert "temperature" in str(results[0]["result"])
    
    @pytest.mark.asyncio
    async def test_execute_tools_missing_tool(self, chat_processor):
        """Test tool execution when tool is not found."""
        tool_calls = [
            {
                "id": "call_789",
                "type": "function",
                "function": {
                    "name": "NonExistentTool",
                    "arguments": '{"param": "value"}'
                }
            }
        ]
        
        # Mock tool registry to return None (tool not found)
        with patch('app.core.tools.base.tool_registry') as mock_registry:
            mock_registry.get_tool.return_value = None
            
            # Execute tools
            results = await chat_processor._execute_tools(tool_calls, "openai")
            
            # Should return empty results when tool not found
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_execute_tools_tool_execution_error(self, chat_processor):
        """Test tool execution when tool execution fails."""
        tool_calls = [
            {
                "id": "call_999",
                "type": "function",
                "function": {
                    "name": "WeatherTool",
                    "arguments": '{"location": "Invalid"}'
                }
            }
        ]
        
        # Mock tool registry
        with patch('app.core.tools.base.tool_registry') as mock_registry:
            mock_tool = Mock()
            mock_tool.execute = AsyncMock(side_effect=Exception("Tool execution failed"))
            mock_registry.get_tool.return_value = mock_tool
            
            # Execute tools
            results = await chat_processor._execute_tools(tool_calls, "openai")
            
            # Should return empty results when tool execution fails
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_real_openai_integration(self, chat_processor):
        """Test real OpenAI API integration (requires API key)."""
        # Skip if no OpenAI API key
        if not chat_processor.providers["openai"].is_available():
            pytest.skip("OpenAI API key not configured")
        
        # Test basic message processing with real API
        result = await chat_processor.process_message(
            message="Hello, can you tell me a short joke?",
            user_id="test_user_real",
            channel_id="test_channel_real",
            use_tools=False
        )
        
        # Verify result structure
        assert "response" in result
        assert "provider" in result
        assert result["provider"] == "openai"
        assert "model" in result
        assert "usage" in result
        assert "conversation_history" in result
        
        # Verify response contains some content
        assert len(result["response"]) > 0
        
        # Verify usage information
        assert "prompt_tokens" in result["usage"]
        assert "completion_tokens" in result["usage"]
        assert "total_tokens" in result["usage"]
        
        print(f"Real OpenAI test - Response: {result['response'][:100]}...")
        print(f"Model: {result['model']}")
        print(f"Usage: {result['usage']}")
    
    @pytest.mark.asyncio
    async def test_real_openai_with_tools(self, chat_processor):
        """Test real OpenAI API integration with tools (requires API key)."""
        # Skip if no OpenAI API key
        if not chat_processor.providers["openai"].is_available():
            pytest.skip("OpenAI API key not configured")
        
        # Test message processing with tools enabled
        result = await chat_processor.process_message(
            message="What's the weather like in London?",
            user_id="test_user_tools",
            channel_id="test_channel_tools",
            use_tools=True
        )
        
        # Verify result structure
        assert "response" in result
        assert "provider" in result
        assert result["provider"] == "openai"
        
        # The response should either use tools or provide a direct answer
        assert len(result["response"]) > 0
        
        print(f"Real OpenAI with tools test - Response: {result['response'][:100]}...")
        print(f"Model: {result['model']}")
        print(f"Usage: {result['usage']}")
    
    def test_error_handling(self, chat_processor):
        """Test error handling in chat processor."""
        # Test with invalid provider
        chat_processor.current_provider = "invalid_provider"
        
        # Should handle gracefully
        assert chat_processor.current_provider == "invalid_provider"
    
    @pytest.mark.asyncio
    async def test_conversation_context_management(self, chat_processor):
        """Test conversation context management."""
        with patch.object(chat_processor.conversation_manager, 'get_or_create_conversation') as mock_get_conv, \
             patch.object(chat_processor.conversation_manager, 'add_user_message') as mock_add_user, \
             patch.object(chat_processor.conversation_manager, 'get_conversation_context') as mock_get_context:
            
            # Setup mocks
            mock_get_conv.return_value = Mock(id="conv_context_test")
            mock_get_context.return_value = [
                {"role": "user", "content": "Context message 1"},
                {"role": "assistant", "content": "Context response 1"},
                {"role": "user", "content": "Context message 2"}
            ]
            
            # Mock provider response
            with patch.object(chat_processor.providers["openai"], 'chat_completion') as mock_chat:
                mock_chat.return_value = ChatCompletionResult(
                    content="I remember our conversation context.",
                    model="gpt-4",
                    usage=UsageInfo(
                        prompt_tokens=40,
                        completion_tokens=20,
                        total_tokens=60
                    )
                )
                
                # Process message
                result = await chat_processor.process_message(
                    message="Do you remember what we talked about?",
                    user_id="context_user",
                    channel_id="context_channel",
                    use_tools=False
                )
                
                # Verify context was retrieved
                mock_get_context.assert_called_once()
                
                # Verify conversation history is included
                assert "conversation_history" in result
                assert len(result["conversation_history"]) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
