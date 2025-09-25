"""
Advanced test cases for django-ollama API functions to improve coverage.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from django_ollama.api import (
    achat,
    agenerate,
    chat,
    generate,
    get_default_model,
    get_ollama_client,
    list_models,
    pull_model,
    show_model,
)


class TestAPIAdvanced:
    """Advanced test cases to improve API coverage."""

    @patch('django_ollama.api.get_ollama_client')
    def test_chat_streaming_response(self, mock_get_client):
        """Test chat function with streaming enabled."""
        mock_client = Mock()

        # Mock a generator for streaming response
        def mock_stream():
            chunks = [
                {"message": {"content": "Hello "}},
                {"message": {"content": "world!"}},
            ]
            for chunk in chunks:
                yield chunk

        mock_client.chat.return_value = mock_stream()
        mock_get_client.return_value = mock_client

        result = chat(prompt="Hello", stream=True)

        # Should return the generator
        chunks = list(result)
        assert len(chunks) == 2
        assert chunks[0]["message"]["content"] == "Hello "
        assert chunks[1]["message"]["content"] == "world!"

        mock_client.chat.assert_called_once_with(
            model="llama3",  # default model
            stream=True,
            messages=[{"role": "user", "content": "Hello"}]
        )

    @patch('django_ollama.api.get_ollama_client')
    def test_generate_streaming_response(self, mock_get_client):
        """Test generate function with streaming enabled."""
        mock_client = Mock()

        def mock_stream():
            chunks = [
                {"response": "Generated "},
                {"response": "content!"},
            ]
            for chunk in chunks:
                yield chunk

        mock_client.generate.return_value = mock_stream()
        mock_get_client.return_value = mock_client

        result = generate(prompt="Complete this", stream=True)

        chunks = list(result)
        assert len(chunks) == 2
        assert chunks[0]["response"] == "Generated "
        assert chunks[1]["response"] == "content!"

        mock_client.generate.assert_called_once_with(
            model="llama3",
            prompt="Complete this",
            stream=True
        )

    @patch('django_ollama.api.get_ollama_client')
    def test_chat_with_custom_model(self, mock_get_client):
        """Test chat with custom model parameter."""
        mock_client = Mock()
        mock_response = {"message": {"content": "Response"}}
        mock_client.chat.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = chat(prompt="Hello", model="custom-model")

        mock_client.chat.assert_called_once_with(
            model="custom-model",
            stream=False,
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert result == mock_response

    @patch('django_ollama.api.get_ollama_client')
    def test_generate_with_custom_model(self, mock_get_client):
        """Test generate with custom model parameter."""
        mock_client = Mock()
        mock_response = {"response": "Generated content"}
        mock_client.generate.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = generate(prompt="Test", model="custom-model")

        mock_client.generate.assert_called_once_with(
            model="custom-model",
            prompt="Test",
            stream=False
        )
        assert result == mock_response

    @patch('django_ollama.api.get_ollama_client')
    def test_list_models_empty_response(self, mock_get_client):
        """Test list_models with empty response."""
        mock_client = Mock()
        mock_client.list.return_value = {"models": []}
        mock_get_client.return_value = mock_client

        result = list_models()

        assert result == []

    @patch('django_ollama.api.get_ollama_client')
    def test_list_models_no_models_key(self, mock_get_client):
        """Test list_models when response has no models key."""
        mock_client = Mock()
        mock_client.list.return_value = {}
        mock_get_client.return_value = mock_client

        result = list_models()

        assert result == []

    @patch('django_ollama.api.get_ollama_client')
    def test_pull_model_with_streaming(self, mock_get_client):
        """Test pull_model function."""
        mock_client = Mock()

        def mock_pull_stream():
            return [
                {"status": "downloading"},
                {"status": "complete"}
            ]

        mock_client.pull.return_value = mock_pull_stream()
        mock_get_client.return_value = mock_client

        result = pull_model("test-model")

        mock_client.pull.assert_called_once_with("test-model")
        assert result == mock_pull_stream()

    @patch('django_ollama.api.get_ollama_client')
    def test_show_model_detailed(self, mock_get_client):
        """Test show_model function with detailed response."""
        mock_client = Mock()
        mock_response = {
            "modelfile": "FROM llama3:latest",
            "parameters": {"temperature": 0.8},
            "template": "{{ .System }}{{ .Prompt }}",
            "details": {"families": ["llama"]}
        }
        mock_client.show.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = show_model("llama3")

        mock_client.show.assert_called_once_with("llama3")
        assert result == mock_response

    @patch('django_ollama.api.ollama')
    @patch('django_ollama.api.settings')
    def test_get_ollama_client_default_host(self, mock_settings, mock_ollama):
        """Test getting Ollama client with default host."""
        mock_client = Mock()
        mock_ollama.Client.return_value = mock_client

        with patch('django_ollama.api.getattr') as mock_getattr:
            mock_getattr.return_value = "http://localhost:11434"

            client = get_ollama_client()

            mock_ollama.Client.assert_called_once_with(host="http://localhost:11434")
            assert client == mock_client

    def test_chat_both_prompt_and_messages_error(self):
        """Test that providing both prompt and messages raises error."""
        with pytest.raises(ValueError, match="Cannot provide both 'prompt' and 'messages'"):
            chat(prompt="Hello", messages=[{"role": "user", "content": "Hi"}])

    @patch('django_ollama.api.get_ollama_client')
    def test_chat_error_handling(self, mock_get_client):
        """Test chat function error handling."""
        mock_client = Mock()
        mock_client.chat.side_effect = Exception("Ollama connection failed")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception, match="Ollama connection failed"):
            chat(prompt="Hello")

    @patch('django_ollama.api.get_ollama_client')
    def test_generate_error_handling(self, mock_get_client):
        """Test generate function error handling."""
        mock_client = Mock()
        mock_client.generate.side_effect = Exception("Generation failed")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception, match="Generation failed"):
            generate(prompt="Test")


class TestAsyncAPIAdvanced:
    """Advanced test cases for async API functions."""

    @pytest.mark.asyncio
    @patch('django_ollama.api.chat')
    async def test_achat_streaming(self, mock_chat):
        """Test async chat function with streaming."""
        async def mock_stream():
            chunks = [
                {"message": {"content": "Async "}},
                {"message": {"content": "response!"}},
            ]
            for chunk in chunks:
                yield chunk

        mock_chat.return_value = mock_stream()

        result = achat(prompt="Hello", stream=True)

        chunks = []
        async for chunk in result:
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0]["message"]["content"] == "Async "
        assert chunks[1]["message"]["content"] == "response!"

        mock_chat.assert_called_once_with(
            prompt="Hello",
            messages=None,
            model=None,
            stream=True,
            images=None
        )

    @pytest.mark.asyncio
    @patch('django_ollama.api.generate')
    async def test_agenerate_streaming(self, mock_generate):
        """Test async generate function with streaming."""
        async def mock_stream():
            chunks = [
                {"response": "Async "},
                {"response": "generation!"},
            ]
            for chunk in chunks:
                yield chunk

        mock_generate.return_value = mock_stream()

        result = agenerate(prompt="Complete", stream=True)

        chunks = []
        async for chunk in result:
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0]["response"] == "Async "
        assert chunks[1]["response"] == "generation!"

        mock_generate.assert_called_once_with(
            prompt="Complete",
            model=None,
            stream=True
        )

    @pytest.mark.asyncio
    @patch('django_ollama.api.chat')
    async def test_achat_with_messages_and_images(self, mock_chat):
        """Test async chat with messages and images."""
        mock_response = {"message": {"content": "I see the image!"}}
        mock_chat.return_value = mock_response

        messages = [{"role": "user", "content": "What's in this image?"}]
        images = ["base64encodedimage"]

        result = await achat(messages=messages, images=images, stream=False)

        mock_chat.assert_called_once_with(
            prompt=None,
            messages=messages,
            model=None,
            stream=False,
            images=images
        )
        assert result == mock_response

    @pytest.mark.asyncio
    @patch('django_ollama.api.generate')
    async def test_agenerate_with_model(self, mock_generate):
        """Test async generate with specific model."""
        mock_response = {"response": "Custom model response"}
        mock_generate.return_value = mock_response

        result = await agenerate(prompt="Test", model="custom-model", stream=False)

        mock_generate.assert_called_once_with(
            prompt="Test",
            model="custom-model",
            stream=False
        )
        assert result == mock_response

    @pytest.mark.asyncio
    @patch('django_ollama.api.chat')
    async def test_achat_error_handling(self, mock_chat):
        """Test async chat error handling."""
        mock_chat.side_effect = Exception("Async error")

        with pytest.raises(Exception, match="Async error"):
            await achat(prompt="Hello", stream=False)

    @pytest.mark.asyncio
    @patch('django_ollama.api.generate')
    async def test_agenerate_error_handling(self, mock_generate):
        """Test async generate error handling."""
        mock_generate.side_effect = Exception("Async generation error")

        with pytest.raises(Exception, match="Async generation error"):
            await agenerate(prompt="Test", stream=False)