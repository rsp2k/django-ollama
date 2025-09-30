"""
WebSocket routing for knowledge_demo app.
"""
from django.urls import path
from django_ollama import consumers
from . import consumers as demo_consumers

websocket_urlpatterns = [
    path('ws/chat/<str:session_id>/', consumers.OllamaChatConsumer.as_asgi()),
    path('ws/streaming-chat/', demo_consumers.StreamingChatConsumer.as_asgi()),
]