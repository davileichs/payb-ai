"""
Tests for Slack bot functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.slack.bot import SlackBot
from app.config import get_settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.slack_bot_token = "xoxb-test-token"
    settings.slack_signing_secret = "test-secret"
    return settings


@pytest.fixture
def slack_bot(mock_settings):
    """Create a SlackBot instance for testing."""
    with pytest.MonkeyPatch().context() as m:
        m.setattr("app.config.get_settings", lambda: mock_settings)
        return SlackBot()


class TestSlackBot:
    """Test cases for SlackBot class."""
    
    def test_init(self, slack_bot):
        """Test SlackBot initialization."""
        assert slack_bot.settings is not None
        assert slack_bot.conversations == {}
    
    def test_verify_signature_valid(self, slack_bot):
        """Test signature verification with valid signature."""
        # This is a simplified test - in real scenarios you'd need proper signature generation
        body = "test-body"
        headers = {
            "x-slack-request-timestamp": "1234567890",
            "x-slack-signature": "v0=test-signature"
        }
        
        # Mock the signature verifier
        slack_bot.signature_verifier.is_valid = MagicMock(return_value=True)
        
        result = slack_bot.verify_signature(body, headers)
        assert result is True
    
    def test_get_conversation_key(self, slack_bot):
        """Test conversation key generation."""
        key = slack_bot.get_conversation_key("C123", "U456")
        assert key == "C123:U456"
    
    def test_clear_conversation(self, slack_bot):
        """Test conversation clearing."""
        # Add a conversation
        slack_bot.conversations["C123:U456"] = [{"role": "user", "content": "test"}]
        
        # Clear it
        slack_bot.clear_conversation("C123", "U456")
        
        assert "C123:U456" not in slack_bot.conversations


@pytest.mark.asyncio
async def test_handle_url_verification(slack_bot):
    """Test URL verification challenge handling."""
    challenge = "test-challenge"
    result = await slack_bot.handle_url_verification(challenge)
    assert result == challenge
