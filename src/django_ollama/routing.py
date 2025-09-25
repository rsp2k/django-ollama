"""
WebSocket URL routing for django-ollama.

This module defines the WebSocket URL patterns for the Ollama chat consumers.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/ollama/chat/$', consumers.OllamaChatConsumer.as_asgi()),
    re_path(r'ws/ollama/simple-chat/$', consumers.SimpleChatConsumer.as_asgi()),
]