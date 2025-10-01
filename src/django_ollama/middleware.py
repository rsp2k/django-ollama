"""
Django middleware for django-ollama.

Provides request-level dependency injection for security and context management.
"""

from typing import Callable
from django.http import HttpRequest, HttpResponse

from .namespace_security import NamespaceSecurityMiddleware


class SecurityMiddleware:
    """
    Django middleware that attaches NamespaceSecurityMiddleware to each request.

    This enables dependency injection pattern: views can access request.security
    instead of using global singletons.

    Usage in settings.py:
        MIDDLEWARE = [
            ...
            'django_ollama.middleware.SecurityMiddleware',
            ...
        ]
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        """
        Initialize middleware.

        Args:
            get_response: The next middleware or view in the chain
        """
        self.get_response = get_response
        # Create security middleware instance once per server process
        self._security_middleware = NamespaceSecurityMiddleware()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Attach security middleware to request.

        Args:
            request: The HTTP request

        Returns:
            HTTP response from downstream middleware/views
        """
        # Attach security middleware to request for dependency injection
        request.security = self._security_middleware

        response = self.get_response(request)
        return response
