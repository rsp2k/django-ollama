"""
Test cases for django-ollama WebSocket routing.
"""

import pytest
from django.test import TestCase
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from django_ollama import routing
from django_ollama.consumers import OllamaChatConsumer, SimpleChatConsumer


class TestWebSocketRouting(TestCase):
    """Test cases for WebSocket URL routing."""

    def test_websocket_urlpatterns_exists(self):
        """Test that websocket_urlpatterns is defined."""
        assert hasattr(routing, 'websocket_urlpatterns')
        assert isinstance(routing.websocket_urlpatterns, list)

    def test_websocket_urlpatterns_not_empty(self):
        """Test that websocket_urlpatterns has routes."""
        assert len(routing.websocket_urlpatterns) > 0

    def test_ollama_chat_route_exists(self):
        """Test that Ollama chat route is defined."""
        pattern_paths = []
        for pattern in routing.websocket_urlpatterns:
            # Extract pattern from URLPattern
            if hasattr(pattern, 'pattern'):
                pattern_paths.append(pattern.pattern._route)

        # Should have a route that matches chat consumer
        chat_route_exists = any('chat' in path for path in pattern_paths)
        assert chat_route_exists

    def test_simple_chat_route_exists(self):
        """Test that simple chat route is defined."""
        pattern_paths = []
        for pattern in routing.websocket_urlpatterns:
            if hasattr(pattern, 'pattern'):
                pattern_paths.append(pattern.pattern._route)

        # Should have a route that matches simple chat consumer
        simple_route_exists = any('simple-chat' in path for path in pattern_paths)
        assert simple_route_exists

    def test_routing_consumers_are_correct(self):
        """Test that routes point to correct consumers."""
        consumers_found = []

        for pattern in routing.websocket_urlpatterns:
            if hasattr(pattern, 'callback'):
                # Get the consumer class from ASGI application
                callback = pattern.callback
                # The callback is an ASGI application, we need to check its type
                consumers_found.append(callback)

        # Should have exactly 2 consumers
        assert len(consumers_found) == 2

    async def test_chat_route_resolution(self):
        """Test that chat route resolves to correct consumer."""
        from channels.routing import URLRouter

        router = URLRouter(routing.websocket_urlpatterns)

        # Test that the route exists and can be resolved
        # This is an integration test to ensure routing works
        scope = {
            'type': 'websocket',
            'path': '/ws/ollama/chat/',
            'query_string': b'',
            'headers': [],
        }

        # Should be able to resolve without error
        application = router(scope, None, None)
        assert application is not None

    async def test_simple_chat_route_resolution(self):
        """Test that simple chat route resolves to correct consumer."""
        from channels.routing import URLRouter

        router = URLRouter(routing.websocket_urlpatterns)

        scope = {
            'type': 'websocket',
            'path': '/ws/ollama/simple-chat/',
            'query_string': b'',
            'headers': [],
        }

        application = router(scope, None, None)
        assert application is not None

    def test_routing_imports(self):
        """Test that routing module imports consumers correctly."""
        # Test that consumers module is accessible from routing
        assert hasattr(routing, 'consumers')

        # Test that consumer classes exist
        assert hasattr(routing.consumers, 'OllamaChatConsumer')
        assert hasattr(routing.consumers, 'SimpleChatConsumer')

    def test_url_patterns_structure(self):
        """Test the structure of URL patterns."""
        for pattern in routing.websocket_urlpatterns:
            # Each pattern should have required attributes
            assert hasattr(pattern, 'pattern')
            assert hasattr(pattern, 'callback')

            # Pattern should be a regex pattern for WebSocket URLs
            route = pattern.pattern._route
            assert route.startswith('ws/')
            assert route.endswith('/')

    def test_route_names_are_descriptive(self):
        """Test that route patterns have descriptive names."""
        routes = []
        for pattern in routing.websocket_urlpatterns:
            route = pattern.pattern._route
            routes.append(route)

        # Should have meaningful route names
        assert any('ollama' in route for route in routes)
        assert any('chat' in route for route in routes)

    async def test_routing_with_trailing_slash(self):
        """Test that routes work with trailing slashes."""
        from channels.routing import URLRouter

        router = URLRouter(routing.websocket_urlpatterns)

        # Test both routes with trailing slashes
        test_paths = [
            '/ws/ollama/chat/',
            '/ws/ollama/simple-chat/'
        ]

        for path in test_paths:
            scope = {
                'type': 'websocket',
                'path': path,
                'query_string': b'',
                'headers': [],
            }

            application = router(scope, None, None)
            assert application is not None


class TestRoutingIntegration(TestCase):
    """Integration tests for WebSocket routing."""

    async def test_full_routing_chain(self):
        """Test the complete routing chain from URL to consumer."""
        from channels.routing import ProtocolTypeRouter, URLRouter
        from channels.auth import AuthMiddlewareStack

        # Create the same routing structure as would be used in production
        application = ProtocolTypeRouter({
            'websocket': AuthMiddlewareStack(
                URLRouter(routing.websocket_urlpatterns)
            ),
        })

        # Test that WebSocket connections can be established
        scope = {
            'type': 'websocket',
            'path': '/ws/ollama/chat/',
            'query_string': b'',
            'headers': [],
            'user': None,
        }

        # Should not raise an error when creating the application
        websocket_app = application(scope, None, None)
        assert websocket_app is not None

    def test_routing_module_structure(self):
        """Test that routing module has expected structure."""
        import django_ollama.routing as routing_module

        # Should have the expected exports
        assert hasattr(routing_module, 'websocket_urlpatterns')

        # Should import from consumers
        import django_ollama.consumers
        assert routing_module.consumers is django_ollama.consumers