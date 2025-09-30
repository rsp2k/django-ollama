"""
Improved async implementation for django-ollama using native AsyncClient.

This demonstrates how to properly implement async functions using ollama.AsyncClient
instead of wrapping sync functions with run_in_executor.
"""

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import ollama
from django.conf import settings

logger = logging.getLogger(__name__)


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


# Enhanced error handling with specific exception types
class OllamaConnectionError(Exception):
    """Raised when connection to Ollama server fails."""
    pass


class OllamaModelError(Exception):
    """Raised when model-related errors occur."""
    pass


class OllamaValidationError(Exception):
    """Raised when input validation fails."""
    pass


def chat(
    prompt: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    model: Optional[str] = None,
    stream: bool = False,
    images: Optional[List[str]] = None,
    **kwargs: Any,
) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
    """
    Chat with an Ollama model (synchronous version).
    """
    if model is None:
        model = get_default_model()

    # Prepare chat arguments
    chat_args = {"model": model, "stream": stream, **kwargs}

    # Handle prompt vs messages with better validation
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
    """
    if model is None:
        model = get_default_model()

    # Prepare chat arguments (same validation as sync version)
    chat_args = {"model": model, "stream": stream, **kwargs}

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
            # Return the async iterator directly
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


def generate(
    prompt: str,
    model: Optional[str] = None,
    stream: bool = False,
    **kwargs: Any,
) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
    """
    Generate text with an Ollama model (synchronous version).
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


async def agenerate(
    prompt: str,
    model: Optional[str] = None,
    stream: bool = False,
    **kwargs: Any,
) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
    """
    Async generate text with an Ollama model using native AsyncClient.

    This is a TRUE async implementation that doesn't block the event loop.
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
            # Return the async iterator directly
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


async def list_models() -> List[Dict[str, Any]]:
    """
    List available Ollama models (async version).
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


async def pull_model(model: str) -> Dict[str, Any]:
    """
    Pull/download an Ollama model (async version).
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


async def show_model(model: str) -> Dict[str, Any]:
    """
    Show information about an Ollama model (async version).
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