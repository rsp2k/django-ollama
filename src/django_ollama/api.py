"""
Ollama API integration for Django.

This module provides high-level functions for interacting with Ollama models,
including chat completions and text generation capabilities.
"""

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

import ollama
from django.conf import settings

logger = logging.getLogger(__name__)


# Enhanced exception hierarchy for better error handling
class OllamaConnectionError(Exception):
    """Raised when connection to Ollama server fails."""
    pass


class OllamaModelError(Exception):
    """Raised when model-related errors occur."""
    pass


class OllamaValidationError(Exception):
    """Raised when input validation fails."""
    pass


def get_default_model() -> str:
    """Get the default Ollama model from Django settings."""
    return getattr(settings, "OLLAMA_DEFAULT_MODEL", "llama3")


def get_ollama_client():
    """Get configured synchronous Ollama client."""
    host = getattr(settings, "OLLAMA_HOST", "http://localhost:11434")
    return ollama.Client(host=host)


def get_ollama_async_client():
    """Get configured asynchronous Ollama client."""
    host = getattr(settings, "OLLAMA_HOST", "http://localhost:11434")
    return ollama.AsyncClient(host=host)


def chat(
    prompt: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    model: Optional[str] = None,
    stream: bool = False,
    images: Optional[List[str]] = None,
    **kwargs: Any,
) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
    """
    Chat with an Ollama model.

    Args:
        prompt: Simple text prompt (will be converted to message format)
        messages: List of messages in chat format:
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"}
            ]
        model: Model name (defaults to settings.OLLAMA_DEFAULT_MODEL)
        stream: Whether to stream the response
        images: List of base64-encoded images for multimodal models
        **kwargs: Additional arguments passed to ollama.chat()

    Returns:
        Dictionary with response or iterator of response chunks if streaming

    Example:
        # Simple prompt
        response = chat("What is Python?")
        print(response['message']['content'])

        # Conversation with history
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"},
            {"role": "user", "content": "Tell me about Django"}
        ]
        response = chat(messages=messages)

        # Streaming response
        for chunk in chat("Tell me a story", stream=True):
            print(chunk['message']['content'], end='')
    """
    if model is None:
        model = get_default_model()

    # Prepare chat arguments
    chat_args = {"model": model, "stream": stream, **kwargs}

    # Handle prompt vs messages with enhanced validation
    if prompt and not messages:
        chat_args["messages"] = [{"role": "user", "content": prompt}]
    elif messages:
        # Validate message format
        if not isinstance(messages, list):
            raise OllamaValidationError("Messages must be a list of message dictionaries")

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                raise OllamaValidationError(f"Invalid message format at index {i}: must have 'role' and 'content' keys")

        chat_args["messages"] = messages
    elif not prompt and not messages:
        raise OllamaValidationError("Either 'prompt' or 'messages' must be provided")

    # Add images if provided
    if images:
        # Add images to the last user message
        if "messages" in chat_args and chat_args["messages"]:
            last_message = chat_args["messages"][-1]
            if last_message.get("role") == "user":
                last_message["images"] = images

    try:
        client = get_ollama_client()
        response = client.chat(**chat_args)
        return response

    except ollama.RequestError as e:
        logger.error(f"Ollama request error in chat: {str(e)}")
        raise OllamaConnectionError(f"Failed to connect to Ollama server: {str(e)}")
    except ollama.ResponseError as e:
        logger.error(f"Ollama response error in chat: {str(e)}")
        if "model" in str(e).lower():
            raise OllamaModelError(f"Model error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Ollama chat: {str(e)}")
        raise


def generate(
    prompt: str,
    model: Optional[str] = None,
    stream: bool = False,
    **kwargs: Any,
) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
    """
    Generate text with an Ollama model.

    Args:
        prompt: Text prompt for generation
        model: Model name (defaults to settings.OLLAMA_DEFAULT_MODEL)
        stream: Whether to stream the response
        **kwargs: Additional arguments passed to ollama.generate()

    Returns:
        Dictionary with response or iterator of response chunks if streaming

    Example:
        # Simple generation
        response = generate("Complete this sentence: Python is")
        print(response['response'])

        # Streaming generation
        for chunk in generate("Write a poem", stream=True):
            print(chunk['response'], end='')
    """
    if not prompt:
        raise OllamaValidationError("Prompt cannot be empty")

    if model is None:
        model = get_default_model()

    generate_args = {"model": model, "prompt": prompt, "stream": stream, **kwargs}

    try:
        client = get_ollama_client()
        response = client.generate(**generate_args)
        return response

    except ollama.RequestError as e:
        logger.error(f"Ollama request error in generate: {str(e)}")
        raise OllamaConnectionError(f"Failed to connect to Ollama server: {str(e)}")
    except ollama.ResponseError as e:
        logger.error(f"Ollama response error in generate: {str(e)}")
        if "model" in str(e).lower():
            raise OllamaModelError(f"Model error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Ollama generate: {str(e)}")
        raise


async def achat(
    prompt: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    model: Optional[str] = None,
    stream: bool = False,
    images: Optional[List[str]] = None,
    **kwargs: Any,
) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
    """
    Async chat with an Ollama model using native AsyncClient.

    This is a TRUE async implementation that doesn't block the event loop.
    Same parameters as chat() but with native async support.
    """
    if model is None:
        model = get_default_model()

    # Prepare chat arguments with same validation as sync version
    chat_args = {"model": model, "stream": stream, **kwargs}

    # Handle prompt vs messages with enhanced validation
    if prompt and not messages:
        chat_args["messages"] = [{"role": "user", "content": prompt}]
    elif messages:
        # Validate message format
        if not isinstance(messages, list):
            raise OllamaValidationError("Messages must be a list of message dictionaries")

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                raise OllamaValidationError(f"Invalid message format at index {i}: must have 'role' and 'content' keys")

        chat_args["messages"] = messages
    elif not prompt and not messages:
        raise OllamaValidationError("Either 'prompt' or 'messages' must be provided")

    # Add images if provided
    if images:
        if "messages" in chat_args and chat_args["messages"]:
            last_message = chat_args["messages"][-1]
            if last_message.get("role") == "user":
                last_message["images"] = images

    try:
        async_client = get_ollama_async_client()

        # Use native async client - no run_in_executor needed!
        response = await async_client.chat(**chat_args)

        if stream:
            # Return the native async iterator directly
            async def _stream_wrapper():
                async for chunk in response:
                    yield chunk
            return _stream_wrapper()
        else:
            return response

    except ollama.RequestError as e:
        logger.error(f"Ollama request error in async chat: {str(e)}")
        raise OllamaConnectionError(f"Failed to connect to Ollama server: {str(e)}")
    except ollama.ResponseError as e:
        logger.error(f"Ollama response error in async chat: {str(e)}")
        if "model" in str(e).lower():
            raise OllamaModelError(f"Model error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in async Ollama chat: {str(e)}")
        raise


async def agenerate(
    prompt: str,
    model: Optional[str] = None,
    stream: bool = False,
    **kwargs: Any,
) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
    """
    Async generate text with an Ollama model using native AsyncClient.

    This is a TRUE async implementation that doesn't block the event loop.
    Same parameters as generate() but with native async support.
    """
    if not prompt:
        raise OllamaValidationError("Prompt cannot be empty")

    if model is None:
        model = get_default_model()

    generate_args = {"model": model, "prompt": prompt, "stream": stream, **kwargs}

    try:
        async_client = get_ollama_async_client()

        # Use native async client - no run_in_executor needed!
        response = await async_client.generate(**generate_args)

        if stream:
            # Return the native async iterator directly
            async def _stream_wrapper():
                async for chunk in response:
                    yield chunk
            return _stream_wrapper()
        else:
            return response

    except ollama.RequestError as e:
        logger.error(f"Ollama request error in async generate: {str(e)}")
        raise OllamaConnectionError(f"Failed to connect to Ollama server: {str(e)}")
    except ollama.ResponseError as e:
        logger.error(f"Ollama response error in async generate: {str(e)}")
        if "model" in str(e).lower():
            raise OllamaModelError(f"Model error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in async Ollama generate: {str(e)}")
        raise


def list_models() -> List[Dict[str, Any]]:
    """
    List available Ollama models.

    Returns:
        List of model dictionaries with name, size, and other metadata
    """
    try:
        client = get_ollama_client()
        response = client.list()
        return response.get("models", [])
    except ollama.RequestError as e:
        logger.error(f"Ollama request error listing models: {str(e)}")
        raise OllamaConnectionError(f"Failed to connect to Ollama server: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error listing Ollama models: {str(e)}")
        raise


async def alist_models() -> List[Dict[str, Any]]:
    """
    List available Ollama models (async version).

    Returns:
        List of model dictionaries with name, size, and other metadata
    """
    try:
        async_client = get_ollama_async_client()
        response = await async_client.list()
        return response.get("models", [])
    except ollama.RequestError as e:
        logger.error(f"Ollama request error listing models: {str(e)}")
        raise OllamaConnectionError(f"Failed to connect to Ollama server: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error listing Ollama models: {str(e)}")
        raise


def pull_model(model: str) -> Dict[str, Any]:
    """
    Pull/download an Ollama model.

    Args:
        model: Name of the model to pull

    Returns:
        Dictionary with pull status information
    """
    if not model:
        raise OllamaValidationError("Model name cannot be empty")

    try:
        client = get_ollama_client()
        response = client.pull(model)
        return response
    except ollama.RequestError as e:
        logger.error(f"Ollama request error pulling model {model}: {str(e)}")
        raise OllamaConnectionError(f"Failed to connect to Ollama server: {str(e)}")
    except ollama.ResponseError as e:
        logger.error(f"Ollama response error pulling model {model}: {str(e)}")
        raise OllamaModelError(f"Failed to pull model '{model}': {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error pulling Ollama model {model}: {str(e)}")
        raise


async def apull_model(model: str) -> Dict[str, Any]:
    """
    Pull/download an Ollama model (async version).

    Args:
        model: Name of the model to pull

    Returns:
        Dictionary with pull status information
    """
    if not model:
        raise OllamaValidationError("Model name cannot be empty")

    try:
        async_client = get_ollama_async_client()
        response = await async_client.pull(model)
        return response
    except ollama.RequestError as e:
        logger.error(f"Ollama request error pulling model {model}: {str(e)}")
        raise OllamaConnectionError(f"Failed to connect to Ollama server: {str(e)}")
    except ollama.ResponseError as e:
        logger.error(f"Ollama response error pulling model {model}: {str(e)}")
        raise OllamaModelError(f"Failed to pull model '{model}': {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error pulling Ollama model {model}: {str(e)}")
        raise


def show_model(model: str) -> Dict[str, Any]:
    """
    Show information about an Ollama model.

    Args:
        model: Name of the model to show

    Returns:
        Dictionary with model information
    """
    if not model:
        raise OllamaValidationError("Model name cannot be empty")

    try:
        client = get_ollama_client()
        response = client.show(model)
        return response
    except ollama.RequestError as e:
        logger.error(f"Ollama request error showing model {model}: {str(e)}")
        raise OllamaConnectionError(f"Failed to connect to Ollama server: {str(e)}")
    except ollama.ResponseError as e:
        logger.error(f"Ollama response error showing model {model}: {str(e)}")
        raise OllamaModelError(f"Model '{model}' not found or invalid: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error showing Ollama model {model}: {str(e)}")
        raise


async def ashow_model(model: str) -> Dict[str, Any]:
    """
    Show information about an Ollama model (async version).

    Args:
        model: Name of the model to show

    Returns:
        Dictionary with model information
    """
    if not model:
        raise OllamaValidationError("Model name cannot be empty")

    try:
        async_client = get_ollama_async_client()
        response = await async_client.show(model)
        return response
    except ollama.RequestError as e:
        logger.error(f"Ollama request error showing model {model}: {str(e)}")
        raise OllamaConnectionError(f"Failed to connect to Ollama server: {str(e)}")
    except ollama.ResponseError as e:
        logger.error(f"Ollama response error showing model {model}: {str(e)}")
        raise OllamaModelError(f"Model '{model}' not found or invalid: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error showing Ollama model {model}: {str(e)}")
        raise