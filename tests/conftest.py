import pytest
import asyncio
from unittest.mock import Mock

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.slack_bot_token = "xoxb-test-token"
    settings.slack_signing_secret = "test-signing-secret"
    settings.slack_app_token = "xapp-test-token"
    settings.jwt_secret_key = "test-secret-key"
    settings.ai_provider = "openai"
    settings.openai_api_key = "test-openai-key"
    settings.openai_model = "gpt-4o-mini"
    settings.ai_temperature = 0.7
    settings.host = "0.0.0.0"
    settings.port = 8000
    settings.debug = False
    settings.max_messages_per_conversation = 100
    settings.log_level = "INFO"
    settings.redis_host = None
    return settings
