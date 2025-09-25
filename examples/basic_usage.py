"""
Basic usage examples for django-ollama.

This example demonstrates the core functionality of the django-ollama package.
"""

import asyncio
import os
import django
from django.conf import settings

# Configure Django settings for standalone script
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'channels',
            'django_ollama',
        ],
        SECRET_KEY='example-secret-key',
        OLLAMA_HOST=os.environ.get('OLLAMA_HOST', 'http://localhost:11434'),
        OLLAMA_DEFAULT_MODEL='llama3.2:1b',
    )
    django.setup()

from django_ollama import chat, generate, achat, agenerate
from django_ollama.models import KnowledgeBase, ChatSession, ChatMessage


def basic_chat_example():
    """Demonstrate basic chat functionality."""
    print("=== Basic Chat Example ===")

    # Simple question
    try:
        response = chat("What is Django?")
        print(f"AI: {response['message']['content']}")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure Ollama is running with: ollama serve")
        print("And pull a model with: ollama pull llama3.2:1b")


def conversation_example():
    """Demonstrate conversation with history."""
    print("\n=== Conversation Example ===")

    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help you today?"},
        {"role": "user", "content": "What is Python used for?"}
    ]

    try:
        response = chat(messages=messages)
        print(f"AI: {response['message']['content']}")
    except Exception as e:
        print(f"Error: {e}")


def streaming_example():
    """Demonstrate streaming responses."""
    print("\n=== Streaming Example ===")

    try:
        print("AI: ", end="", flush=True)
        for chunk in chat("Tell me a short joke about programming", stream=True):
            if chunk and 'message' in chunk and 'content' in chunk['message']:
                print(chunk['message']['content'], end="", flush=True)
        print()  # New line after streaming
    except Exception as e:
        print(f"Error: {e}")


def generation_example():
    """Demonstrate text generation."""
    print("\n=== Generation Example ===")

    try:
        response = generate("Complete this sentence: The best thing about Django is")
        print(f"Generated: {response['response']}")
    except Exception as e:
        print(f"Error: {e}")


async def async_examples():
    """Demonstrate async functionality."""
    print("\n=== Async Examples ===")

    try:
        # Async chat
        response = await achat("What is the meaning of life?")
        print(f"Async AI: {response['message']['content']}")

        # Async streaming
        print("Async streaming: ", end="", flush=True)
        async for chunk in achat("Count from 1 to 5", stream=True):
            if chunk and 'message' in chunk and 'content' in chunk['message']:
                print(chunk['message']['content'], end="", flush=True)
        print()

        # Async generation
        response = await agenerate("Django is a")
        print(f"Async generated: {response['response']}")

    except Exception as e:
        print(f"Async error: {e}")


def database_models_example():
    """Demonstrate Django models functionality."""
    print("\n=== Database Models Example ===")

    try:
        # Create tables
        from django.core.management import execute_from_command_line
        execute_from_command_line(['', 'migrate', '--run-syncdb'])

        # Create a knowledge base
        kb = KnowledgeBase.objects.create(
            name="Example KB",
            description="An example knowledge base for testing"
        )
        print(f"Created knowledge base: {kb}")

        # Create a chat session
        session = ChatSession.objects.create(
            name="Example Session",
            model="llama3.2:1b",
            system_prompt="You are a helpful assistant specializing in Django."
        )
        print(f"Created chat session: {session}")

        # Add some messages
        user_message = ChatMessage.objects.create(
            session=session,
            role="user",
            content="What is Django?"
        )

        assistant_message = ChatMessage.objects.create(
            session=session,
            role="assistant",
            content="Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design."
        )

        print(f"Session has {session.message_count} messages")

        # List all messages in session
        for message in session.messages.all():
            print(f"  {message.get_role_display()}: {message.content[:50]}...")

    except Exception as e:
        print(f"Database error: {e}")


def main():
    """Run all examples."""
    print("Django-Ollama Examples")
    print("=====================")
    print("Make sure Ollama is running: ollama serve")
    print("And you have a model: ollama pull llama3.2:1b")
    print()

    # Synchronous examples
    basic_chat_example()
    conversation_example()
    streaming_example()
    generation_example()
    database_models_example()

    # Async examples
    print("\nRunning async examples...")
    asyncio.run(async_examples())

    print("\n=== Examples Complete ===")


if __name__ == "__main__":
    main()