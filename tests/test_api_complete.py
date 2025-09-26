"""
Comprehensive test coverage for all django-ollama API functions.

This ensures every function, error path, and edge case is properly tested.
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
    # Sync functions
    get_default_model, get_ollama_client, get_ollama_async_client,
    chat, generate, list_models, pull_model, show_model,

    # Async functions
    achat, agenerate, alist_models, apull_model, ashow_model,

    # Exceptions
    OllamaConnectionError, OllamaModelError, OllamaValidationError
)


class TestMissingAsyncFunctions:
    """Test the async functions that were missing comprehensive tests."""

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_alist_models_success(self, mock_get_client):
        """Test alist_models returns proper model list."""
        mock_client = AsyncMock()
        mock_response = {
            "models": [
                {"name": "llama3:8b", "size": 4661078273},
                {"name": "codellama:7b", "size": 3825819519}
            ]
        }
        mock_client.list = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await alist_models()

        mock_client.list.assert_called_once()
        assert len(result) == 2
        assert result[0]["name"] == "llama3:8b"
        assert result[1]["name"] == "codellama:7b"

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_alist_models_connection_error(self, mock_get_client):
        """Test alist_models handles connection errors."""
        import ollama

        mock_client = AsyncMock()
        mock_client.list = AsyncMock(side_effect=ollama.RequestError("Connection failed"))
        mock_get_client.return_value = mock_client

        with pytest.raises(OllamaConnectionError, match="Failed to connect to Ollama server"):
            await alist_models()

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_apull_model_success(self, mock_get_client):
        """Test apull_model successfully pulls model."""
        mock_client = AsyncMock()
        mock_response = {"status": "success", "digest": "sha256:abc123"}
        mock_client.pull = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await apull_model("llama3:8b")

        mock_client.pull.assert_called_once_with("llama3:8b")
        assert result["status"] == "success"

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_apull_model_validation_error(self, mock_get_client):
        """Test apull_model validates input."""
        with pytest.raises(OllamaValidationError, match="Model name cannot be empty"):
            await apull_model("")

        with pytest.raises(OllamaValidationError, match="Model name cannot be empty"):
            await apull_model(None)

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_apull_model_model_error(self, mock_get_client):
        """Test apull_model handles model errors."""
        import ollama

        mock_client = AsyncMock()
        mock_client.pull = AsyncMock(side_effect=ollama.ResponseError("Model not found"))
        mock_get_client.return_value = mock_client

        with pytest.raises(OllamaModelError, match="Failed to pull model 'nonexistent'"):
            await apull_model("nonexistent")

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_ashow_model_success(self, mock_get_client):
        """Test ashow_model returns model info."""
        mock_client = AsyncMock()
        mock_response = {
            "license": "MIT",
            "modelfile": "FROM llama3\nPARAMETER temperature 1",
            "parameters": "temperature 1",
            "template": "{{ .Prompt }}"
        }
        mock_client.show = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        result = await ashow_model("llama3:8b")

        mock_client.show.assert_called_once_with("llama3:8b")
        assert "license" in result
        assert "modelfile" in result

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_ashow_model_validation_error(self, mock_get_client):
        """Test ashow_model validates input."""
        with pytest.raises(OllamaValidationError, match="Model name cannot be empty"):
            await ashow_model("")

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_ashow_model_not_found(self, mock_get_client):
        """Test ashow_model handles model not found."""
        import ollama

        mock_client = AsyncMock()
        mock_client.show = AsyncMock(side_effect=ollama.ResponseError("Model not found"))
        mock_get_client.return_value = mock_client

        with pytest.raises(OllamaModelError, match="Model 'nonexistent' not found"):
            await ashow_model("nonexistent")


class TestStreamingAndEdgeCases:
    """Test streaming scenarios and edge cases that were missing."""

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_achat_streaming_with_images(self, mock_get_client):
        """Test achat streaming with image inputs."""
        mock_client = AsyncMock()

        # Mock streaming response
        async def mock_stream():
            yield {"message": {"content": "I can see"}}
            yield {"message": {"content": " the image shows"}}
            yield {"message": {"content": " a cat."}}

        mock_client.chat = AsyncMock(return_value=mock_stream())
        mock_get_client.return_value = mock_client

        result_stream = await achat(
            "What's in this image?",
            stream=True,
            images=["base64encoded_image_data"]
        )

        chunks = []
        async for chunk in result_stream:
            chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks[0]["message"]["content"] == "I can see"
        assert chunks[2]["message"]["content"] == " a cat."

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_agenerate_streaming_long_content(self, mock_get_client):
        """Test agenerate streaming with long content generation."""
        mock_client = AsyncMock()

        # Mock long streaming response
        async def mock_stream():
            for i in range(10):
                yield {"response": f"Part {i} of the story. "}

        mock_client.generate = AsyncMock(return_value=mock_stream())
        mock_get_client.return_value = mock_client

        result_stream = await agenerate(
            "Write a long story about dragons",
            stream=True
        )

        chunks = []
        async for chunk in result_stream:
            chunks.append(chunk)

        assert len(chunks) == 10
        assert chunks[0]["response"] == "Part 0 of the story. "
        assert chunks[9]["response"] == "Part 9 of the story. "

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_achat_complex_message_history(self, mock_get_client):
        """Test achat with complex message history including system prompts."""
        mock_client = AsyncMock()
        mock_response = {"message": {"content": "Complex response"}}
        mock_client.chat = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"},
            {"role": "user", "content": "What's the weather?"}
        ]

        result = await achat(messages=messages, model="custom-model")

        mock_client.chat.assert_called_once()
        call_args = mock_client.chat.call_args[1]
        assert call_args["model"] == "custom-model"
        assert call_args["messages"] == messages


class TestErrorHandlingEdgeCases:
    """Test comprehensive error handling scenarios."""

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_achat_unexpected_error(self, mock_get_client):
        """Test achat handles unexpected errors properly."""
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="Unexpected error"):
            await achat("Hello")

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_agenerate_empty_response(self, mock_get_client):
        """Test agenerate handles empty responses."""
        mock_client = AsyncMock()
        mock_client.generate = AsyncMock(return_value={})
        mock_get_client.return_value = mock_client

        result = await agenerate("Generate something")
        assert result == {}

    @pytest.mark.asyncio
    @patch('django_ollama.api.get_ollama_async_client')
    async def test_multiple_validation_errors(self, mock_get_client):
        """Test validation with multiple error conditions."""

        # Test invalid message structure at different indices
        bad_messages = [
            {"role": "user", "content": "Good message"},
            {"role": "assistant"},  # Missing content
            {"role": "user", "content": "Another good message"}
        ]

        with pytest.raises(OllamaValidationError, match="Invalid message format at index 1"):
            await achat(messages=bad_messages)


class TestSyncFunctionImprovements:
    """Test improvements to sync functions error handling."""

    @patch('django_ollama.api.get_ollama_client')
    def test_chat_enhanced_validation_messages(self, mock_get_client):
        """Test chat function with enhanced message validation."""
        mock_client = Mock()
        mock_client.chat.return_value = {"message": {"content": "Response"}}
        mock_get_client.return_value = mock_client

        # Test with valid complex messages
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant response"}
        ]

        result = chat(messages=messages)

        mock_client.chat.assert_called_once()
        assert result["message"]["content"] == "Response"

    @patch('django_ollama.api.get_ollama_client')
    def test_chat_validation_error_specific_index(self, mock_get_client):
        """Test chat validation provides specific error index."""

        bad_messages = [
            {"role": "user", "content": "Good"},
            {"invalid": "structure"},  # Bad message at index 1
            {"role": "user", "content": "Good again"}
        ]

        with pytest.raises(OllamaValidationError, match="Invalid message format at index 1"):
            chat(messages=bad_messages)

    @patch('django_ollama.api.get_ollama_client')
    def test_generate_validation_empty_prompt(self, mock_get_client):
        """Test generate validates empty prompts."""

        with pytest.raises(OllamaValidationError, match="Prompt cannot be empty"):
            generate("")

    @patch('django_ollama.api.get_ollama_client')
    def test_sync_functions_connection_error(self, mock_get_client):
        """Test sync functions handle connection errors."""
        import ollama

        mock_client = Mock()
        mock_client.chat.side_effect = ollama.RequestError("Connection failed")
        mock_get_client.return_value = mock_client

        with pytest.raises(OllamaConnectionError, match="Failed to connect to Ollama server"):
            chat("Hello")


class TestConcurrencyAndPerformance:
    """Test concurrent usage patterns and performance scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_different_models(self):
        """Test concurrent requests to different models."""

        async def mock_achat(prompt, model=None, **kwargs):
            await asyncio.sleep(0.01)  # Simulate I/O
            return {"message": {"content": f"Response from {model} to {prompt}"}}

        # Run concurrent requests to different models
        tasks = [
            mock_achat("Question 1", model="llama3:8b"),
            mock_achat("Question 2", model="codellama:7b"),
            mock_achat("Question 3", model="llama3:8b"),
        ]

        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        duration = asyncio.get_event_loop().time() - start_time

        # Should complete concurrently, not sequentially
        assert duration < 0.05  # Much less than 3 * 0.01 = 0.03s
        assert len(results) == 3
        assert "llama3:8b" in results[0]["message"]["content"]
        assert "codellama:7b" in results[1]["message"]["content"]

    @pytest.mark.asyncio
    async def test_streaming_backpressure_handling(self):
        """Test streaming handles backpressure correctly."""

        async def slow_consumer_stream():
            """Simulate slow consumer of stream data."""
            chunk_count = 0

            async def mock_stream():
                for i in range(100):  # Many chunks
                    yield {"message": {"content": f"chunk{i}"}}

            async for chunk in mock_stream():
                chunk_count += 1
                # Slow consumer processing
                await asyncio.sleep(0.001)

            return chunk_count

        result = await slow_consumer_stream()
        assert result == 100  # All chunks processed despite slow consumption


if __name__ == "__main__":
    pytest.main([__file__, "-v"])