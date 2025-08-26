"""
Tests for Ollama provider functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from app.core.providers.ollama import OllamaProvider


class TestOllamaProvider:
    """Test cases for OllamaProvider class."""
    
    def test_init(self):
        """Test OllamaProvider initialization."""
        with patch('app.config.get_settings') as mock_get_settings:
            mock_settings.return_value.ollama_base_url = "http://localhost:11434"
            mock_settings.return_value.ollama_model = "llama2"
            
            provider = OllamaProvider()
            assert provider.base_url == "http://localhost:11434"
            assert provider.model == "llama2"
    
    @pytest.mark.asyncio
    async def test_system_message_conversion(self):
        """Test that system messages are converted to assistant messages."""
        with patch('app.config.get_settings') as mock_get_settings:
            mock_settings.return_value.ollama_base_url = "http://localhost:11434"
            mock_settings.return_value.ollama_model = "llama2"
            
            provider = OllamaProvider()
            
            # Test messages with system role
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"}
            ]
            
            # Mock the HTTP response
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "message": {"content": "Hello! How can I help you?"},
                "model": "llama2",
                "prompt_eval_count": 10,
                "eval_count": 5
            }
            mock_response.raise_for_status.return_value = None
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = None
                mock_client_instance.post.return_value = mock_response
                mock_client.return_value = mock_client_instance
                
                result = await provider.chat_completion(messages)
                
                # Verify the request was made with converted messages
                call_args = mock_client_instance.post.call_args
                request_data = call_args[1]['json']
                
                # Check that system message was converted to assistant
                assert len(request_data['messages']) == 2
                assert request_data['messages'][0]['role'] == 'assistant'
                assert request_data['messages'][0]['content'] == 'You are a helpful assistant.'
                assert request_data['messages'][1]['role'] == 'user'
                
                # Verify the response
                assert result['content'] == "Hello! How can I help you?"
                assert result['model'] == "llama2"
    
    @pytest.mark.asyncio
    async def test_multiple_system_messages_converted(self):
        """Test that multiple system messages are converted to assistant messages."""
        with patch('app.config.get_settings') as mock_get_settings:
            mock_settings.return_value.ollama_base_url = "http://localhost:11434"
            mock_settings.return_value.ollama_model = "llama2"
            
            provider = OllamaProvider()
            
            # Test messages with multiple system roles
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "system", "content": "Be concise in your responses."},
                {"role": "user", "content": "Hello!"}
            ]
            
            # Mock the HTTP response
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "message": {"content": "Hello! How can I help you?"},
                "model": "llama2",
                "prompt_eval_count": 10,
                "eval_count": 5
            }
            mock_response.raise_for_status.return_value = None
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = None
                mock_client_instance.post.return_value = mock_response
                mock_client.return_value = mock_client_instance
                
                result = await provider.chat_completion(messages)
                
                # Verify the request was made with converted messages
                call_args = mock_client_instance.post.call_args
                request_data = call_args[1]['json']
                
                # Check that multiple system messages were converted to assistant
                assert len(request_data['messages']) == 3
                assert request_data['messages'][0]['role'] == 'assistant'
                assert request_data['messages'][0]['content'] == 'You are a helpful assistant.'
                assert request_data['messages'][1]['role'] == 'assistant'
                assert request_data['messages'][1]['content'] == 'Be concise in your responses.'
                assert request_data['messages'][2]['role'] == 'user'
    
    def test_is_available(self):
        """Test is_available method."""
        with patch('app.config.get_settings') as mock_get_settings:
            # Test with base_url set
            mock_get_settings.return_value.ollama_base_url = "http://localhost:11434"
            provider = OllamaProvider()
            assert provider.is_available() is True
            
            # Test without base_url
            mock_get_settings.return_value.ollama_base_url = ""
            provider = OllamaProvider()
            assert provider.is_available() is False
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health_check method."""
        with patch('app.config.get_settings') as mock_get_settings:
            mock_settings.return_value.ollama_base_url = "http://localhost:11434"
            mock_settings.return_value.ollama_model = "llama2"
            
            provider = OllamaProvider()
            
            # Test successful health check
            with patch('httpx.AsyncClient') as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = None
                mock_client_instance.get.return_value.status_code = 200
                
                mock_client.return_value = mock_client_instance
                
                result = await provider.health_check()
                assert result is True
            
            # Test failed health check
            with patch('httpx.AsyncClient') as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.__aenter__.return_value = mock_client_instance
                mock_client_instance.__aexit__.return_value = None
                mock_client_instance.get.side_effect = Exception("Connection failed")
                
                mock_client.return_value = mock_client_instance
                
                result = await provider.health_check()
                assert result is False
