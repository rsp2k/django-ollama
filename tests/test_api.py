"""
Test cases for django-ollama API functions.
"""

import pytest
from unittest.mock import Mock, patch

from django_ollama.api import (
    chat,
    generate,
    get_default_model,
    get_ollama_client,
    list_models,
    pull_model,
    show_model,
)


class TestOllamaAPI:
    """Test cases for Ollama API functions."""

    @patch('django_ollama.api.settings')
    def test_get_default_model_with_setting(self, mock_settings):
        """Test getting default model when setting is configured."""
        mock_settings.OLLAMA_DEFAULT_MODEL = "custom-model"
        assert get_default_model() == "custom-model"

    @patch('django_ollama.api.settings')
    def test_get_default_model_fallback(self, mock_settings):
        """Test getting default model fallback."""
        # Mock getattr to return default when attribute doesn't exist
        with patch('django_ollama.api.getattr') as mock_getattr:
            mock_getattr.return_value = "llama3"
            assert get_default_model() == "llama3"
            mock_getattr.assert_called_once_with(mock_settings, "OLLAMA_DEFAULT_MODEL", "llama3")

    @patch('django_ollama.api.settings')
    @patch('django_ollama.api.ollama')
    def test_get_ollama_client_with_host(self, mock_ollama, mock_settings):
        """Test getting Ollama client with custom host."""
        mock_client = Mock()
        mock_ollama.Client.return_value = mock_client

        with patch('django_ollama.api.getattr') as mock_getattr:
            mock_getattr.return_value = "http://custom:11434"

            client = get_ollama_client()

            mock_ollama.Client.assert_called_once_with(host="http://custom:11434")
            assert client == mock_client

    @patch('django_ollama.api.get_ollama_client')
    @patch('django_ollama.api.get_default_model')
    def test_chat_with_prompt(self, mock_get_model, mock_get_client):
        """Test chat function with simple prompt."""
        mock_get_model.return_value = "llama3"
        mock_client = Mock()
        mock_response = {"message": {"content": "Hello!"}}
        mock_client.chat.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = chat(prompt="Hello")

        mock_client.chat.assert_called_once_with(
            model="llama3",
            stream=False,
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert result == mock_response

    @patch('django_ollama.api.get_ollama_client')
    @patch('django_ollama.api.get_default_model')
    def test_chat_with_messages(self, mock_get_model, mock_get_client):
        """Test chat function with message history."""
        mock_get_model.return_value = "llama3"
        mock_client = Mock()
        mock_response = {"message": {"content": "Hi there!"}}
        mock_client.chat.return_value = mock_response
        mock_get_client.return_value = mock_client

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "How are you?"}
        ]

        result = chat(messages=messages, model="custom-model")

        mock_client.chat.assert_called_once_with(
            model="custom-model",
            stream=False,
            messages=messages
        )
        assert result == mock_response

    @patch('django_ollama.api.get_ollama_client')
    def test_chat_with_images(self, mock_get_client):
        """Test chat function with images."""
        mock_client = Mock()
        mock_response = {"message": {"content": "I see an image!"}}
        mock_client.chat.return_value = mock_response
        mock_get_client.return_value = mock_client

        images = ["base64encodedimage1", "base64encodedimage2"]
        result = chat(prompt="What's in this image?", images=images)

        # Check that images were added to the last user message
        call_args = mock_client.chat.call_args[1]
        assert call_args["messages"][-1]["images"] == images

    def test_chat_no_prompt_or_messages(self):
        """Test chat function raises error when neither prompt nor messages provided."""
        with pytest.raises(ValueError, match="Either 'prompt' or 'messages' must be provided"):
            chat()

    @patch('django_ollama.api.get_ollama_client')
    @patch('django_ollama.api.get_default_model')
    def test_generate(self, mock_get_model, mock_get_client):
        """Test generate function."""
        mock_get_model.return_value = "llama3"
        mock_client = Mock()
        mock_response = {"response": "Generated text"}
        mock_client.generate.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = generate(prompt="Complete this: Python is")

        mock_client.generate.assert_called_once_with(
            model="llama3",
            prompt="Complete this: Python is",
            stream=False
        )
        assert result == mock_response

    @patch('django_ollama.api.get_ollama_client')
    def test_list_models(self, mock_get_client):
        """Test list_models function."""
        mock_client = Mock()
        mock_response = {"models": [{"name": "llama3"}, {"name": "codellama"}]}
        mock_client.list.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = list_models()

        mock_client.list.assert_called_once()
        assert result == [{"name": "llama3"}, {"name": "codellama"}]

    @patch('django_ollama.api.get_ollama_client')
    def test_pull_model(self, mock_get_client):
        """Test pull_model function."""
        mock_client = Mock()
        mock_response = {"status": "success"}
        mock_client.pull.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = pull_model("llama3")

        mock_client.pull.assert_called_once_with("llama3")
        assert result == mock_response

    @patch('django_ollama.api.get_ollama_client')
    def test_show_model(self, mock_get_client):
        """Test show_model function."""
        mock_client = Mock()
        mock_response = {"modelfile": "FROM llama3", "parameters": {}}
        mock_client.show.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = show_model("llama3")

        mock_client.show.assert_called_once_with("llama3")
        assert result == mock_response


class TestAsyncAPI:
    """Test cases for async API functions."""

    @pytest.mark.asyncio
    @patch('django_ollama.api.chat')
    async def test_achat_non_streaming(self, mock_chat):
        """Test async chat function without streaming."""
        from django_ollama.api import achat

        mock_response = {"message": {"content": "Hello!"}}
        mock_chat.return_value = mock_response

        result = await achat(prompt="Hello", stream=False)

        mock_chat.assert_called_once_with(
            prompt="Hello",
            messages=None,
            model=None,
            stream=False,
            images=None
        )
        assert result == mock_response

    @pytest.mark.asyncio
    @patch('django_ollama.api.generate')
    async def test_agenerate_non_streaming(self, mock_generate):
        """Test async generate function without streaming."""
        from django_ollama.api import agenerate

        mock_response = {"response": "Generated text"}
        mock_generate.return_value = mock_response

        result = await agenerate(prompt="Test prompt", stream=False)

        mock_generate.assert_called_once_with(
            prompt="Test prompt",
            model=None,
            stream=False
        )
        assert result == mock_response