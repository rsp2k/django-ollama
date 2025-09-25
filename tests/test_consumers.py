"""
Test cases for django-ollama WebSocket consumers.
"""

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase

from django_ollama.consumers import OllamaChatConsumer, SimpleChatConsumer
from django_ollama.models import ChatSession, ChatMessage, KnowledgeBase

User = get_user_model()


class TestOllamaChatConsumer(TransactionTestCase):
    """Test cases for OllamaChatConsumer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com"
        )
        self.kb = KnowledgeBase.objects.create(name="Test KB")

    async def test_consumer_connection(self):
        """Test WebSocket connection."""
        communicator = WebsocketCommunicator(OllamaChatConsumer.as_asgi(), "/ws/chat/")
        connected, subprotocol = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_start_session(self):
        """Test starting a chat session."""
        communicator = WebsocketCommunicator(OllamaChatConsumer.as_asgi(), "/ws/chat/")
        await communicator.connect()

        # Send start session message
        await communicator.send_json_to({
            "type": "start_session",
            "model": "llama3",
            "name": "Test Session",
            "system_prompt": "You are helpful."
        })

        # Receive response
        response = await communicator.receive_json_from()
        assert response["type"] == "session_started"
        assert response["model"] == "llama3"
        assert response["name"] == "Test Session"
        assert "session_id" in response

        await communicator.disconnect()

    async def test_end_session(self):
        """Test ending a chat session."""
        communicator = WebsocketCommunicator(OllamaChatConsumer.as_asgi(), "/ws/chat/")
        await communicator.connect()

        # Start session first
        await communicator.send_json_to({
            "type": "start_session",
            "model": "llama3"
        })
        await communicator.receive_json_from()  # Consume start response

        # End session
        await communicator.send_json_to({
            "type": "end_session"
        })

        response = await communicator.receive_json_from()
        assert response["type"] == "session_ended"

        await communicator.disconnect()

    @patch('django_ollama.consumers.achat')
    async def test_chat_message_non_streaming(self, mock_achat):
        """Test sending a chat message without streaming."""
        mock_achat.return_value = {
            "message": {"content": "Hello! How can I help you?"}
        }

        communicator = WebsocketCommunicator(OllamaChatConsumer.as_asgi(), "/ws/chat/")
        await communicator.connect()

        # Send chat message
        await communicator.send_json_to({
            "type": "chat_message",
            "message": "Hello",
            "model": "llama3",
            "stream": False
        })

        # Should receive chat_start
        response = await communicator.receive_json_from()
        assert response["type"] == "chat_start"
        assert response["model"] == "llama3"

        # Should receive chat_complete with full response
        response = await communicator.receive_json_from()
        assert response["type"] == "chat_complete"
        assert response["full_message"] == "Hello! How can I help you?"

        await communicator.disconnect()

    @patch('django_ollama.consumers.achat')
    async def test_chat_message_streaming(self, mock_achat):
        """Test sending a chat message with streaming."""
        # Mock streaming response
        async def mock_stream():
            chunks = [
                {"message": {"content": "Hello! "}},
                {"message": {"content": "How can "}},
                {"message": {"content": "I help you?"}}
            ]
            for chunk in chunks:
                yield chunk

        mock_achat.return_value = mock_stream()

        communicator = WebsocketCommunicator(OllamaChatConsumer.as_asgi(), "/ws/chat/")
        await communicator.connect()

        # Send chat message
        await communicator.send_json_to({
            "type": "chat_message",
            "message": "Hello",
            "model": "llama3",
            "stream": True
        })

        # Should receive chat_start
        response = await communicator.receive_json_from()
        assert response["type"] == "chat_start"

        # Should receive streaming chunks
        chunks = []
        for _ in range(3):  # 3 chunks expected
            response = await communicator.receive_json_from()
            if response["type"] == "chat_chunk":
                chunks.append(response["content"])

        # Should receive chat_complete
        response = await communicator.receive_json_from()
        assert response["type"] == "chat_complete"
        assert response["full_message"] == "Hello! How can I help you?"

        await communicator.disconnect()

    async def test_empty_message_error(self):
        """Test error handling for empty messages."""
        communicator = WebsocketCommunicator(OllamaChatConsumer.as_asgi(), "/ws/chat/")
        await communicator.connect()

        # Send empty message
        await communicator.send_json_to({
            "type": "chat_message",
            "message": ""
        })

        response = await communicator.receive_json_from()
        assert response["type"] == "error"
        assert "required" in response["message"].lower()

        await communicator.disconnect()

    async def test_invalid_json_error(self):
        """Test error handling for invalid JSON."""
        communicator = WebsocketCommunicator(OllamaChatConsumer.as_asgi(), "/ws/chat/")
        await communicator.connect()

        # Send invalid JSON
        await communicator.send_to(text_data="invalid json")

        response = await communicator.receive_json_from()
        assert response["type"] == "error"
        assert "json" in response["message"].lower()

        await communicator.disconnect()

    async def test_unknown_message_type_error(self):
        """Test error handling for unknown message types."""
        communicator = WebsocketCommunicator(OllamaChatConsumer.as_asgi(), "/ws/chat/")
        await communicator.connect()

        # Send unknown message type
        await communicator.send_json_to({
            "type": "unknown_type"
        })

        response = await communicator.receive_json_from()
        assert response["type"] == "error"
        assert "unknown" in response["message"].lower()

        await communicator.disconnect()

    async def test_load_existing_session(self):
        """Test loading an existing chat session."""
        # Create a session in the database
        session = await database_sync_to_async(ChatSession.objects.create)(
            name="Existing Session",
            model="llama3",
            system_prompt="Test prompt"
        )

        communicator = WebsocketCommunicator(OllamaChatConsumer.as_asgi(), "/ws/chat/")
        await communicator.connect()

        # Send message with existing session ID
        with patch('django_ollama.consumers.achat') as mock_achat:
            mock_achat.return_value = {"message": {"content": "Response"}}

            await communicator.send_json_to({
                "type": "chat_message",
                "message": "Hello",
                "session_id": str(session.id),
                "stream": False
            })

            # Should load existing session
            response = await communicator.receive_json_from()
            assert response["type"] == "chat_start"
            assert response["session_id"] == str(session.id)

        await communicator.disconnect()


class TestSimpleChatConsumer(TransactionTestCase):
    """Test cases for SimpleChatConsumer."""

    async def test_simple_consumer_connection(self):
        """Test WebSocket connection for simple consumer."""
        communicator = WebsocketCommunicator(SimpleChatConsumer.as_asgi(), "/ws/simple/")
        connected, subprotocol = await communicator.connect()
        assert connected
        await communicator.disconnect()

    @patch('django_ollama.consumers.achat')
    async def test_simple_chat_message(self, mock_achat):
        """Test sending a message to simple consumer."""
        # Mock streaming response
        async def mock_stream():
            chunks = [
                {"message": {"content": "Hello"}},
                {"message": {"content": " there!"}}
            ]
            for chunk in chunks:
                yield chunk

        mock_achat.return_value = mock_stream()

        communicator = WebsocketCommunicator(SimpleChatConsumer.as_asgi(), "/ws/simple/")
        await communicator.connect()

        # Send message
        await communicator.send_json_to({
            "message": "Hello",
            "model": "llama3"
        })

        # Should receive streamed responses
        messages = []
        for _ in range(2):  # 2 chunks expected
            response = await communicator.receive_json_from()
            messages.append(response["message"])

        assert messages == ["Hello", " there!"]

        await communicator.disconnect()

    async def test_simple_empty_message_error(self):
        """Test error handling for empty message in simple consumer."""
        communicator = WebsocketCommunicator(SimpleChatConsumer.as_asgi(), "/ws/simple/")
        await communicator.connect()

        # Send empty message
        await communicator.send_json_to({
            "message": ""
        })

        response = await communicator.receive_json_from()
        assert "error" in response
        assert "required" in response["error"].lower()

        await communicator.disconnect()

    async def test_simple_invalid_json_error(self):
        """Test error handling for invalid JSON in simple consumer."""
        communicator = WebsocketCommunicator(SimpleChatConsumer.as_asgi(), "/ws/simple/")
        await communicator.connect()

        # Send invalid JSON
        await communicator.send_to(text_data="invalid json")

        response = await communicator.receive_json_from()
        assert "error" in response

        await communicator.disconnect()


@pytest.mark.asyncio
class TestConsumerMethods:
    """Test individual consumer methods in isolation."""

    async def test_get_conversation_history_empty(self):
        """Test getting conversation history for empty session."""
        consumer = OllamaChatConsumer()
        consumer.chat_session = None
        history = await consumer.get_conversation_history()
        assert history == []

    async def test_save_message_no_session(self):
        """Test saving message without active session."""
        consumer = OllamaChatConsumer()
        consumer.chat_session = None
        # Should not raise error, just return without saving
        await consumer.save_message("user", "test message")

    async def test_send_error_method(self):
        """Test send_error method."""
        consumer = OllamaChatConsumer()
        consumer.send = AsyncMock()

        await consumer.send_error("Test error")

        consumer.send.assert_called_once()
        call_args = consumer.send.call_args[1]
        data = json.loads(call_args["text_data"])
        assert data["type"] == "error"
        assert data["message"] == "Test error"

    async def test_send_json_method(self):
        """Test send_json method."""
        consumer = OllamaChatConsumer()
        consumer.send = AsyncMock()

        test_data = {"type": "test", "data": "value"}
        await consumer.send_json(test_data)

        consumer.send.assert_called_once()
        call_args = consumer.send.call_args[1]
        assert json.loads(call_args["text_data"]) == test_data