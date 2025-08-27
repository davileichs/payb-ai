import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from app.slack.bot import SlackBot

class TestSlackBot:
    @pytest.fixture
    def mock_settings(self):
        settings = Mock()
        settings.slack_bot_token = "xoxb-test-token"
        settings.slack_signing_secret = "test-signing-secret"
        return settings

    @pytest.fixture
    def mock_chat_processor(self):
        processor = Mock()
        processor.process_message = AsyncMock(return_value={
            "response": "Hello! How can I help you?",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "conversation_history": []
        })
        return processor

    @pytest.fixture
    def mock_conversation_manager(self):
        manager = Mock()
        return manager

    @pytest.fixture
    def slack_bot(self, mock_settings, mock_chat_processor, mock_conversation_manager):
        with patch('app.slack.bot.get_settings', return_value=mock_settings):
            with patch('app.slack.bot.get_chat_processor', return_value=mock_chat_processor):
                with patch('app.slack.bot.get_conversation_manager', return_value=mock_conversation_manager):
                    with patch('app.slack.bot.WebClient') as mock_client:
                        with patch('app.slack.bot.SignatureVerifier'):
                            bot = SlackBot()
                            bot.client = mock_client
                            return bot

    def test_slack_bot_initialization(self, slack_bot):
        assert slack_bot is not None
        assert hasattr(slack_bot, 'client')
        assert hasattr(slack_bot, 'signature_verifier')
        assert hasattr(slack_bot, 'chat_processor')
        assert hasattr(slack_bot, 'conversation_manager')
        assert hasattr(slack_bot, 'executor')

    def test_verify_signature_valid(self, slack_bot):
        slack_bot.signature_verifier.is_valid = Mock(return_value=True)
        
        headers = {
            "x-slack-request-timestamp": "1234567890",
            "x-slack-signature": "v0=test-signature"
        }
        
        result = slack_bot.verify_signature("test-body", headers)
        
        assert result is True
        slack_bot.signature_verifier.is_valid.assert_called_once_with(
            "test-body", "1234567890", "v0=test-signature"
        )

    def test_verify_signature_invalid(self, slack_bot):
        slack_bot.signature_verifier.is_valid = Mock(return_value=False)
        
        headers = {
            "x-slack-request-timestamp": "1234567890", 
            "x-slack-signature": "v0=invalid-signature"
        }
        
        result = slack_bot.verify_signature("test-body", headers)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_message_event_success(self, slack_bot):
        event = {
            "type": "message",
            "text": "Hello bot",
            "user": "U123456789",
            "channel": "C123456789",
            "ts": "1234567890.123"
        }
        
        slack_bot.send_message = AsyncMock()
        
        await slack_bot.handle_message_event(event)
        
        slack_bot.chat_processor.process_message.assert_called_once()
        call_args = slack_bot.chat_processor.process_message.call_args
        assert call_args[1]["message"] == "Hello bot"
        assert call_args[1]["user_id"] == "U123456789"
        assert call_args[1]["channel_id"] == "C123456789"
        
        slack_bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_event_no_text(self, slack_bot):
        event = {
            "type": "message",
            "user": "U123456789",
            "channel": "C123456789",
            "ts": "1234567890.123"
        }
        
        slack_bot.send_message = AsyncMock()
        
        await slack_bot.handle_message_event(event)
        
        slack_bot.chat_processor.process_message.assert_not_called()
        slack_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_event_bot_message(self, slack_bot):
        event = {
            "type": "message",
            "text": "Hello",
            "user": "U123456789",
            "channel": "C123456789", 
            "ts": "1234567890.123",
            "bot_id": "B123456789"
        }
        
        slack_bot.send_message = AsyncMock()
        
        await slack_bot.handle_message_event(event)
        
        slack_bot.chat_processor.process_message.assert_not_called()
        slack_bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_message_event_processing_error(self, slack_bot):
        event = {
            "type": "message",
            "text": "Hello bot",
            "user": "U123456789",
            "channel": "C123456789",
            "ts": "1234567890.123"
        }
        
        slack_bot.chat_processor.process_message = AsyncMock(
            side_effect=Exception("Processing failed")
        )
        slack_bot.send_message = AsyncMock()
        
        await slack_bot.handle_message_event(event)
        
        slack_bot.send_message.assert_called_once()
        call_args = slack_bot.send_message.call_args
        assert "error" in call_args[1]["text"].lower()

    @pytest.mark.asyncio
    async def test_send_message_success(self, slack_bot):
        # Mock the executor and client response
        mock_response = {"ok": True, "ts": "1234567890.123"}
        
        # Mock asyncio.get_event_loop().run_in_executor
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor = AsyncMock(return_value=mock_response)
            
            result = await slack_bot.send_message(
                channel="C123456789",
                text="Hello from bot",
                thread_ts="1234567890.123"
            )
            
            assert result == mock_response
            mock_loop.run_in_executor.assert_called_once()

    @pytest.mark.asyncio 
    async def test_send_message_failure(self, slack_bot):
        # Mock the executor to raise an exception
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor = AsyncMock(
                side_effect=Exception("Slack API error")
            )
            
            result = await slack_bot.send_message(
                channel="C123456789",
                text="Hello from bot"
            )
            
            assert result == {"ok": False, "error": "Failed to send message"}

class TestSlackBotIntegration:
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        # Test the complete flow from message receipt to response
        mock_settings = Mock()
        mock_settings.slack_bot_token = "xoxb-test-token"
        mock_settings.slack_signing_secret = "test-signing-secret"
        
        mock_processor = Mock()
        mock_processor.process_message = AsyncMock(return_value={
            "response": "I understand you said hello!",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "conversation_history": [
                {"role": "user", "content": "[testuser]: Hello"},
                {"role": "assistant", "content": "I understand you said hello!"}
            ]
        })
        
        with patch('app.slack.bot.get_settings', return_value=mock_settings):
            with patch('app.slack.bot.get_chat_processor', return_value=mock_processor):
                with patch('app.slack.bot.get_conversation_manager'):
                    with patch('app.slack.bot.WebClient'):
                        with patch('app.slack.bot.SignatureVerifier'):
                            bot = SlackBot()
                            bot.send_message = AsyncMock(return_value={"ok": True})
                            
                            # Simulate receiving a message
                            event = {
                                "type": "message",
                                "text": "Hello",
                                "user": "testuser",
                                "channel": "testchannel",
                                "ts": "1234567890.123"
                            }
                            
                            await bot.handle_message_event(event)
                            
                            # Verify the flow
                            mock_processor.process_message.assert_called_once()
                            call_args = mock_processor.process_message.call_args
                            assert call_args[1]["message"] == "Hello"
                            assert call_args[1]["user_id"] == "testuser"
                            assert call_args[1]["channel_id"] == "testchannel"
                            
                            bot.send_message.assert_called_once()
                            call_args = bot.send_message.call_args
                            assert call_args[1]["channel"] == "testchannel"
                            assert call_args[1]["text"] == "I understand you said hello!"
                            assert call_args[1]["thread_ts"] == "1234567890.123"
