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


def get_default_model() -> str:
    """Get the default Ollama model from Django settings."""
    return getattr(settings, "OLLAMA_DEFAULT_MODEL", "llama3")


def get_ollama_client():
    """Get configured Ollama client."""
    host = getattr(settings, "OLLAMA_HOST", "http://localhost:11434")
    return ollama.Client(host=host)


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

    # Handle prompt vs messages
    if prompt and not messages:
        chat_args["messages"] = [{"role": "user", "content": prompt}]
    elif messages:
        chat_args["messages"] = messages
    elif not prompt and not messages:
        raise ValueError("Either 'prompt' or 'messages' must be provided")

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

        if stream:
            return response
        else:
            return response
    except Exception as e:
        logger.error(f"Error in Ollama chat: {str(e)}")
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
    if model is None:
        model = get_default_model()

    generate_args = {"model": model, "prompt": prompt, "stream": stream, **kwargs}

    try:
        client = get_ollama_client()
        response = client.generate(**generate_args)

        if stream:
            return response
        else:
            return response
    except Exception as e:
        logger.error(f"Error in Ollama generate: {str(e)}")
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
    Async version of chat function.

    Same parameters as chat() but returns async iterator for streaming.
    """

    def _sync_chat():
        return chat(
            prompt=prompt,
            messages=messages,
            model=model,
            stream=stream,
            images=images,
            **kwargs,
        )

    if stream:
        # Convert sync generator to async generator
        async def _async_stream():
            loop = asyncio.get_event_loop()
            sync_iterator = await loop.run_in_executor(None, _sync_chat)
            for chunk in sync_iterator:
                yield chunk

        return _async_stream()
    else:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_chat)


async def agenerate(
    prompt: str,
    model: Optional[str] = None,
    stream: bool = False,
    **kwargs: Any,
) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
    """
    Async version of generate function.

    Same parameters as generate() but returns async iterator for streaming.
    """

    def _sync_generate():
        return generate(prompt=prompt, model=model, stream=stream, **kwargs)

    if stream:
        # Convert sync generator to async generator
        async def _async_stream():
            loop = asyncio.get_event_loop()
            sync_iterator = await loop.run_in_executor(None, _sync_generate)
            for chunk in sync_iterator:
                yield chunk

        return _async_stream()
    else:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_generate)


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
    except Exception as e:
        logger.error(f"Error listing Ollama models: {str(e)}")
        raise


def pull_model(model: str) -> Dict[str, Any]:
    """
    Pull/download an Ollama model.

    Args:
        model: Name of the model to pull

    Returns:
        Dictionary with pull status information
    """
    try:
        client = get_ollama_client()
        response = client.pull(model)
        return response
    except Exception as e:
        logger.error(f"Error pulling Ollama model {model}: {str(e)}")
        raise


def show_model(model: str) -> Dict[str, Any]:
    """
    Show information about an Ollama model.

    Args:
        model: Name of the model to show

    Returns:
        Dictionary with model information
    """
    try:
        client = get_ollama_client()
        response = client.show(model)
        return response
    except Exception as e:
        logger.error(f"Error showing Ollama model {model}: {str(e)}")
        raise