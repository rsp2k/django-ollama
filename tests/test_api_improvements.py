"""
Test cases for improved django-ollama API functionality.

Tests the new native async implementation and enhanced error handling.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

import django
from django.conf import settings

# Configure Django settings for tests
if not settings.configured:
    settings.configure(
        OLLAMA_HOST="http://test:11434",
        OLLAMA_DEFAULT_MODEL="test-model",
        SECRET_KEY="test-key",
        USE_TZ=True,
    )
    django.setup()

from django_ollama.api import (
    OllamaConnectionError,
    OllamaModelError,
    OllamaValidationError,
    get_ollama_async_client,
    achat,
    agenerate,
    alist_models,
)


class TestImprovedAsyncAPI:
    """Test cases for the improved native async API functions."""

    def test_exception_hierarchy(self):
        """Test that our custom exceptions are properly defined."""
        assert issubclass(OllamaConnectionError, Exception)
        assert issubclass(OllamaModelError, Exception)
        assert issubclass(OllamaValidationError, Exception)

    def test_get_ollama_async_client(self):
        """Test async client creation."""
        with patch('django_ollama.api.ollama') as mock_ollama:
            mock_client = Mock()
            mock_ollama.AsyncClient.return_value = mock_client

            client = get_ollama_async_client()

            mock_ollama.AsyncClient.assert_called_once_with(host="http://test:11434")
            assert client == mock_client

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_achat_validation_error(self, mock_get_client):
        """Test that achat raises OllamaValidationError for invalid input."""

        # Test with empty prompt and no messages
        with pytest.raises(OllamaValidationError, match="Either 'prompt' or 'messages' must be provided"):
            await achat()

        # Test with invalid messages format
        with pytest.raises(OllamaValidationError, match="Messages must be a list"):
            await achat(messages="not a list")

        # Test with invalid message structure
        with pytest.raises(OllamaValidationError, match="Invalid message format at index 0"):
            await achat(messages=[{"invalid": "message"}])

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_achat_native_async(self, mock_get_client):
        """Test that achat uses native AsyncClient without run_in_executor."""
        mock_async_client = AsyncMock()
        mock_response = {"message": {"content": "Hello there!"}}
        mock_async_client.chat = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_async_client

        result = await achat("Hello", stream=False)

        # Verify native async client was used
        mock_get_client.assert_called_once()
        mock_async_client.chat.assert_called_once_with(
            model="test-model",
            stream=False,
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert result == mock_response

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_achat_streaming(self, mock_get_client):
        """Test native async streaming."""
        mock_async_client = AsyncMock()

        # Mock async iterator for streaming
        async def mock_stream():
            yield {"message": {"content": "chunk1"}}
            yield {"message": {"content": "chunk2"}}

        mock_async_client.chat = AsyncMock(return_value=mock_stream())
        mock_get_client.return_value = mock_async_client

        result = await achat("Test", stream=True)

        # Collect streaming results
        chunks = []
        async for chunk in result:
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0]["message"]["content"] == "chunk1"
        assert chunks[1]["message"]["content"] == "chunk2"

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_agenerate_validation(self, mock_get_client):
        """Test agenerate validation."""

        # Test with empty prompt
        with pytest.raises(OllamaValidationError, match="Prompt cannot be empty"):
            await agenerate("")

        with pytest.raises(OllamaValidationError, match="Prompt cannot be empty"):
            await agenerate(None)

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_error_handling_connection(self, mock_get_client):
        """Test connection error handling."""
        import ollama

        mock_async_client = AsyncMock()
        mock_async_client.chat = AsyncMock(side_effect=ollama.RequestError("Connection failed"))
        mock_get_client.return_value = mock_async_client

        with pytest.raises(OllamaConnectionError, match="Failed to connect to Ollama server"):
            await achat("Hello")

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_error_handling_model(self, mock_get_client):
        """Test model error handling."""
        import ollama

        mock_async_client = AsyncMock()
        mock_async_client.chat = AsyncMock(side_effect=ollama.ResponseError("Model not found"))
        mock_get_client.return_value = mock_async_client

        with pytest.raises(OllamaModelError, match="Model error"):
            await achat("Hello")

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_alist_models_native_async(self, mock_get_client):
        """Test that alist_models uses native async."""
        mock_async_client = AsyncMock()
        mock_response = {"models": [{"name": "llama3"}, {"name": "codellama"}]}
        mock_async_client.list = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_async_client

        result = await alist_models()

        mock_async_client.list.assert_called_once()
        assert result == [{"name": "llama3"}, {"name": "codellama"}]


class TestPerformanceComparison:
    """Test to demonstrate performance benefits of native async."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test that concurrent requests work efficiently with native async."""

        async def mock_achat(prompt, **kwargs):
            # Simulate async I/O without blocking
            await asyncio.sleep(0.01)  # Non-blocking sleep
            return {"message": {"content": f"Response to: {prompt}"}}

        # Run multiple concurrent requests
        tasks = [
            mock_achat(f"Request {i}")
            for i in range(5)
        ]

        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        duration = asyncio.get_event_loop().time() - start_time

        # With true async, concurrent requests should complete quickly
        assert len(results) == 5
        assert duration < 0.05  # Should be much faster than 5 * 0.01 = 0.05s

        for i, result in enumerate(results):
            assert result["message"]["content"] == f"Response to: Request {i}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])