"""
ASGI config for django-ollama tests.

This module provides the ASGI application for testing WebSocket consumers
and other async functionality.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

# Import Django application for HTTP requests
django_asgi_app = get_asgi_application()

# Import WebSocket routing after Django setup
try:
    from django_ollama import routing
    websocket_urlpatterns = routing.websocket_urlpatterns
except ImportError:
    # Fallback if routing is not available
    websocket_urlpatterns = []

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})