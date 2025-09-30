"""
WebSocket consumers for real-time Ollama chat functionality.

This module provides Django Channels consumers for real-time chat
interactions with Ollama models.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from channels.generic.websocket import AsyncWebsocketConsumer

from .api import achat

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from .models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


class OllamaChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat with Ollama models.

    This consumer handles WebSocket connections and provides real-time
    streaming responses from Ollama models.

    Expected message format:
    {
        "type": "chat_message",
        "message": "Your message here",
        "model": "llama3",  // optional
        "session_id": "uuid",  // optional
        "stream": true  // optional, defaults to true
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id: Optional[str] = None
        self.chat_session: Optional['ChatSession'] = None

    async def connect(self):
        """Accept WebSocket connection."""
        await self.accept()
        logger.info(f"WebSocket connected: {self.channel_name}")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        logger.info(f"WebSocket disconnected: {self.channel_name} (code: {close_code})")

    async def receive(self, text_data: str):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "chat_message")

            if message_type == "chat_message":
                await self.handle_chat_message(data)
            elif message_type == "start_session":
                await self.handle_start_session(data)
            elif message_type == "end_session":
                await self.handle_end_session(data)
            else:
                await self.send_error(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")
            await self.send_error("Internal server error")

    async def handle_chat_message(self, data: Dict[str, Any]):
        """Handle chat message and stream response from Ollama."""
        message_content = data.get("message", "").strip()
        if not message_content:
            await self.send_error("Message content is required")
            return

        model = data.get("model", "llama3")
        stream = data.get("stream", True)
        session_id = data.get("session_id")

        try:
            # Load or create chat session
            await self.load_chat_session(session_id, model)

            # Get conversation history
            messages = await self.get_conversation_history()

            # Add new user message
            messages.append({"role": "user", "content": message_content})

            # Save user message to database if we have a session
            if self.chat_session:
                await self.save_message("user", message_content)

            # Send response that we're processing
            await self.send_json({
                "type": "chat_start",
                "session_id": str(self.chat_session.id) if self.chat_session else None,
                "model": model,
            })

            if stream:
                # Stream response
                assistant_message = ""
                async for chunk in achat(messages=messages, model=model, stream=True):
                    if chunk and "message" in chunk and "content" in chunk["message"]:
                        content = chunk["message"]["content"]
                        assistant_message += content
                        await self.send_json({
                            "type": "chat_chunk",
                            "content": content,
                        })

                # Send completion signal
                await self.send_json({
                    "type": "chat_complete",
                    "full_message": assistant_message,
                })

                # Save assistant message to database if we have a session
                if self.chat_session and assistant_message:
                    await self.save_message("assistant", assistant_message)
            else:
                # Non-streaming response
                response = await achat(messages=messages, model=model, stream=False)
                assistant_message = response["message"]["content"]

                await self.send_json({
                    "type": "chat_complete",
                    "content": assistant_message,
                    "full_message": assistant_message,
                })

                # Save assistant message to database if we have a session
                if self.chat_session:
                    await self.save_message("assistant", assistant_message)

        except Exception as e:
            logger.error(f"Error in chat message handling: {str(e)}")
            await self.send_error(f"Chat error: {str(e)}")

    async def handle_start_session(self, data: Dict[str, Any]):
        """Handle session start request."""
        model = data.get("model", "llama3")
        session_name = data.get("name", "")
        system_prompt = data.get("system_prompt", "")

        try:
            # Create new chat session
            from django.utils import timezone
            from asgiref.sync import sync_to_async

            @sync_to_async
            def create_session():
                from django.contrib.auth.models import AnonymousUser
                from .models import ChatSession

                user = None if isinstance(self.scope["user"], AnonymousUser) else self.scope["user"]
                return ChatSession.objects.create(
                    name=session_name,
                    model=model,
                    user=user,
                    system_prompt=system_prompt,
                    last_message_at=timezone.now(),
                )

            self.chat_session = await create_session()
            self.session_id = str(self.chat_session.id)

            await self.send_json({
                "type": "session_started",
                "session_id": self.session_id,
                "model": model,
                "name": session_name,
            })

        except Exception as e:
            logger.error(f"Error starting session: {str(e)}")
            await self.send_error(f"Session start error: {str(e)}")

    async def handle_end_session(self, data: Dict[str, Any]):
        """Handle session end request."""
        try:
            if self.chat_session:
                # Mark session as inactive
                from asgiref.sync import sync_to_async

                @sync_to_async
                def end_session():
                    self.chat_session.is_active = False
                    self.chat_session.save()

                await end_session()

            self.chat_session = None
            self.session_id = None

            await self.send_json({
                "type": "session_ended",
            })

        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            await self.send_error(f"Session end error: {str(e)}")

    async def load_chat_session(self, session_id: Optional[str], model: str):
        """Load or create a chat session."""
        if session_id:
            try:
                from asgiref.sync import sync_to_async

                @sync_to_async
                def get_session():
                    from .models import ChatSession
                    return ChatSession.objects.filter(id=session_id, is_active=True).first()

                self.chat_session = await get_session()
                if self.chat_session:
                    self.session_id = session_id
                    return

            except Exception as e:
                logger.warning(f"Could not load session {session_id}: {str(e)}")

        # No persistent session for this connection
        self.chat_session = None
        self.session_id = None

    async def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history for the current session."""
        if not self.chat_session:
            return []

        try:
            from asgiref.sync import sync_to_async

            @sync_to_async
            def get_messages():
                messages = list(
                    self.chat_session.messages.order_by("created_at").values_list(
                        "role", "content", flat=False
                    )
                )
                return [{"role": role, "content": content} for role, content in messages]

            messages = await get_messages()

            # Add system prompt if present
            if self.chat_session.system_prompt:
                messages.insert(0, {"role": "system", "content": self.chat_session.system_prompt})

            return messages

        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []

    async def save_message(self, role: str, content: str):
        """Save a message to the database."""
        if not self.chat_session:
            return

        try:
            from django.utils import timezone
            from asgiref.sync import sync_to_async

            @sync_to_async
            def create_message():
                from .models import ChatMessage

                ChatMessage.objects.create(
                    session=self.chat_session,
                    role=role,
                    content=content,
                )
                # Update session's last message time
                self.chat_session.last_message_at = timezone.now()
                self.chat_session.save(update_fields=["last_message_at"])

            await create_message()

        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")

    async def send_json(self, content: Dict[str, Any]):
        """Send JSON data to WebSocket."""
        await self.send(text_data=json.dumps(content))

    async def send_error(self, message: str):
        """Send error message to WebSocket."""
        await self.send_json({
            "type": "error",
            "message": message,
        })


class SimpleChatConsumer(AsyncWebsocketConsumer):
    """
    Simplified WebSocket consumer for basic chat functionality.

    This is a simpler version that doesn't persist sessions to the database,
    useful for quick implementations or when you don't need conversation history.
    """

    async def connect(self):
        """Accept WebSocket connection."""
        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        pass

    async def receive(self, text_data: str):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message = data.get("message", "").strip()
            model = data.get("model", "llama3")

            if not message:
                await self.send_error("Message is required")
                return

            # Stream response from Ollama
            async for chunk in achat(prompt=message, model=model, stream=True):
                if chunk and "message" in chunk and "content" in chunk["message"]:
                    await self.send(text_data=json.dumps({
                        "message": chunk["message"]["content"]
                    }))

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON")
        except Exception as e:
            logger.error(f"Error in simple chat: {str(e)}")
            await self.send_error("Chat error")

    async def send_error(self, message: str):
        """Send error message."""
        await self.send(text_data=json.dumps({
            "error": message
        }))