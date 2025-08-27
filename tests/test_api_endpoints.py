import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

class TestAPIEndpoints:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_chat_processor(self):
        processor = Mock()
        processor.process_message = AsyncMock(return_value={
            "response": "Hello! How can I help you?",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "usage": {"prompt_tokens": 10, "completion_tokens": 8},
            "conversation_history": [
                {"role": "user", "content": "[testuser]: Hello"},
                {"role": "assistant", "content": "Hello! How can I help you?"}
            ]
        })
        return processor

    @pytest.fixture  
    def mock_tool_registry(self):
        registry = Mock()
        registry.get_all_tools.return_value = ["conversation_manager", "weather"]
        return registry

    def test_root_endpoint(self, client):
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Slack Bot AI Chat Webhook API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data

    def test_health_endpoint(self, client):
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "slack-bot-ai-chat"
        assert data["version"] == "1.0.0"

    @patch('app.api.ai_routes.get_chat_processor')
    @patch('app.core.tools.base.tool_registry')
    def test_ai_health_endpoint(self, mock_tool_registry, mock_get_processor, client, mock_chat_processor):
        mock_get_processor.return_value = mock_chat_processor
        mock_tool_registry.get_all_tools.return_value = ["conversation_manager", "weather"]
        
        response = client.get("/api/ai/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["tools_count"] == 2

    def test_chat_endpoint_without_auth(self, client):
        response = client.post("/api/ai/chat", json={
            "message": "Hello",
            "user_id": "testuser",
            "channel_id": "testchannel"
        })
        
        assert response.status_code == 401

    @patch('app.api.ai_routes.get_chat_processor')
    @patch('app.auth.middleware.get_settings')
    def test_chat_endpoint_with_valid_auth(self, mock_settings, mock_get_processor, client, mock_chat_processor):
        mock_settings.return_value.jwt_secret_key = "test-secret-key"
        mock_get_processor.return_value = mock_chat_processor
        
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "Hello",
                "user_id": "testuser", 
                "channel_id": "testchannel",
                "use_tools": True
            },
            headers={"Authorization": "Bearer test-secret-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Hello! How can I help you?"
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4o-mini"
        assert len(data["conversation_history"]) == 2

    @patch('app.api.ai_routes.get_chat_processor')
    @patch('app.auth.middleware.get_settings')
    def test_chat_endpoint_with_invalid_auth(self, mock_settings, mock_get_processor, client, mock_chat_processor):
        mock_settings.return_value.jwt_secret_key = "test-secret-key"
        mock_get_processor.return_value = mock_chat_processor
        
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "Hello",
                "user_id": "testuser",
                "channel_id": "testchannel"
            },
            headers={"Authorization": "Bearer wrong-key"}
        )
        
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]

    @patch('app.api.ai_routes.get_chat_processor')
    @patch('app.auth.middleware.get_settings')
    def test_chat_endpoint_processing_error(self, mock_settings, mock_get_processor, client):
        mock_settings.return_value.jwt_secret_key = "test-secret-key"
        
        processor = Mock()
        processor.process_message = AsyncMock(side_effect=Exception("Processing failed"))
        mock_get_processor.return_value = processor
        
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "Hello",
                "user_id": "testuser",
                "channel_id": "testchannel"
            },
            headers={"Authorization": "Bearer test-secret-key"}
        )
        
        assert response.status_code == 500
        assert "Error processing chat" in response.json()["detail"]

    @patch('app.api.ai_routes.get_chat_processor')
    @patch('app.auth.middleware.get_settings')
    def test_chat_endpoint_minimal_payload(self, mock_settings, mock_get_processor, client, mock_chat_processor):
        mock_settings.return_value.jwt_secret_key = "test-secret-key"
        mock_get_processor.return_value = mock_chat_processor
        
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "Hi",
                "user_id": "user1",
                "channel_id": "general"
            },
            headers={"Authorization": "Bearer test-secret-key"}
        )
        
        assert response.status_code == 200
        
        # Verify the processor was called with correct parameters
        mock_chat_processor.process_message.assert_called_once()
        call_args = mock_chat_processor.process_message.call_args
        assert call_args[1]["message"] == "Hi"
        assert call_args[1]["user_id"] == "user1"
        assert call_args[1]["channel_id"] == "general"
        assert call_args[1]["use_tools"] is True  # Default value
