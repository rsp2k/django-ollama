"""
Django-Ollama: Local LLM integration for Django applications.

This package provides seamless integration between Django and Ollama,
enabling local large language model capabilities with real-time chat
functionality through WebSockets.
"""

try:
    from ._version import version as __version__
except ImportError:
    # Fallback version for development
    __version__ = "0.1.0.dev0"

# Default Django app configuration
default_app_config = "django_ollama.apps.DjangoOllamaConfig"

# Public API exports
from .api import (
    chat, generate, achat, agenerate, get_default_model,
    list_models, pull_model, show_model,
    alist_models, apull_model, ashow_model,
    OllamaConnectionError, OllamaModelError, OllamaValidationError
)

# Conditional imports for Django models (only when Django is available and configured)
__all__ = [
    "__version__",
    "chat",
    "generate",
    "achat",
    "agenerate",
    "get_default_model",
    "list_models",
    "pull_model",
    "show_model",
    "alist_models",
    "apull_model",
    "ashow_model",
    "OllamaConnectionError",
    "OllamaModelError",
    "OllamaValidationError",
]

try:
    from django.conf import settings
    from django.apps import apps
    if settings.configured and apps.ready:
        from .models import KnowledgeBase, KnowledgeBaseContent, KnowledgeBaseMedia
        __all__.extend([
            "KnowledgeBase",
            "KnowledgeBaseContent",
            "KnowledgeBaseMedia",
        ])
except (ImportError, AttributeError, RuntimeError):
    # Django not available, not configured, or apps not ready
    pass