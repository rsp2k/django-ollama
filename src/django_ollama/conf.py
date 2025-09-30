"""
Django-Ollama configuration management.

This module provides a centralized configuration system for django-ollama
with validation, defaults, and automatic documentation generation.

All settings are prefixed with 'DJANGO_OLLAMA_' in Django settings.
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DjangoOllamaSettings:
    """
    Centralized configuration for django-ollama package.

    This class loads and validates all django-ollama settings from Django's
    settings module, providing defaults and comprehensive validation.
    """

    def __init__(self):
        """Initialize and validate all django-ollama settings."""

        # Core Ollama Connection Settings
        self.OLLAMA_HOST = self._get_setting(
            'OLLAMA_HOST',
            'http://localhost:11434'
        )
        """
        str: Ollama server host URL.

        The base URL for the Ollama API server. Should include protocol (http/https)
        and port if different from default.

        Examples:
            - 'http://localhost:11434' (default local)
            - 'https://ollama.example.com'
            - 'http://192.168.1.100:11434'
        """

        self.OLLAMA_DEFAULT_MODEL = self._get_setting(
            'OLLAMA_DEFAULT_MODEL',
            'llama3.2'
        )
        """
        str: Default Ollama model to use for chat and generation.

        The model name that will be used when no specific model is requested.
        Must be available on the Ollama server.

        Popular options:
            - 'llama3.2' (default, good balance)
            - 'llama3.2:1b' (lightweight, fast)
            - 'llama3.2:70b' (powerful, slower)
            - 'codellama' (code-focused)
        """

        self.OLLAMA_TIMEOUT = self._get_setting(
            'OLLAMA_TIMEOUT',
            30
        )
        """
        int: Request timeout for Ollama API calls in seconds.

        Maximum time to wait for Ollama API responses before timing out.
        Should be balanced between user experience and model response time.
        """

        self.OLLAMA_MAX_RETRIES = self._get_setting(
            'OLLAMA_MAX_RETRIES',
            3
        )
        """
        int: Maximum number of retry attempts for failed Ollama requests.

        Number of times to retry failed API calls before giving up.
        Helps handle temporary network issues or server overload.
        """

        # Context Injection Settings
        self.CONTEXT_INJECTION_ENABLED = self._get_setting(
            'CONTEXT_INJECTION_ENABLED',
            True
        )
        """
        bool: Enable/disable the context injection middleware system.

        When enabled, the AIContextMiddleware will automatically attach
        lazy querysets to requests for AI context injection.
        """

        self.CONTEXT_INJECTION_MAX_ITEMS = self._get_setting(
            'CONTEXT_INJECTION_MAX_ITEMS',
            50
        )
        """
        int: Maximum number of items across all querysets for context injection.

        Total limit for all queryset items that can be evaluated and sent
        to AI models. Prevents memory issues with large datasets.
        """

        self.CONTEXT_INJECTION_DEFAULT_PRIORITY = self._get_setting(
            'CONTEXT_INJECTION_DEFAULT_PRIORITY',
            10
        )
        """
        int: Default priority for context injection querysets.

        Higher numbers have higher priority. Used when querysets don't
        specify their own priority level.
        """

        self.CONTEXT_INJECTION_CACHE_TIMEOUT = self._get_setting(
            'CONTEXT_INJECTION_CACHE_TIMEOUT',
            300
        )
        """
        int: Cache timeout for evaluated context in seconds.

        How long to cache evaluated queryset results to avoid
        re-evaluation on subsequent requests. 0 disables caching.
        """

        # Namespace Security Settings
        self.NAMESPACE_POLICY = self._get_setting(
            'NAMESPACE_POLICY',
            'django_ollama.namespace_security.DefaultNamespacePolicy'
        )
        """
        str: Python path to the namespace security policy class.

        Policy class that determines which namespaces users can access.
        Must implement the namespace policy interface.

        Built-in options:
            - 'django_ollama.namespace_security.DefaultNamespacePolicy'
            - 'django_ollama.namespace_security.StrictNamespacePolicy'
            - 'django_ollama.namespace_security.PublicOnlyNamespacePolicy'
        """

        self.NAMESPACE_DEFAULT_ACCESS = self._get_setting(
            'NAMESPACE_DEFAULT_ACCESS',
            'private'
        )
        """
        str: Default access level for new namespaces.

        Access level assigned to newly created namespaces.

        Options:
            - 'private': Only owner and explicit members can access
            - 'public': Anyone can read, owner can write
            - 'readonly': Anyone can read, no one can write
        """

        self.NAMESPACE_MAX_PER_USER = self._get_setting(
            'NAMESPACE_MAX_PER_USER',
            10
        )
        """
        int: Maximum number of namespaces a user can own.

        Prevents users from creating unlimited namespaces.
        Set to 0 for unlimited (not recommended in production).
        """

        # Knowledge Base Settings
        self.KNOWLEDGE_BASE_MAX_SIZE_MB = self._get_setting(
            'KNOWLEDGE_BASE_MAX_SIZE_MB',
            100
        )
        """
        int: Maximum size for a single knowledge base in megabytes.

        Total size limit for all content linked to a knowledge base.
        Helps manage storage and memory usage.
        """

        self.KNOWLEDGE_BASE_CONTENT_TYPES = self._get_setting(
            'KNOWLEDGE_BASE_CONTENT_TYPES',
            ['django_ollama.KnowledgeBaseContent']
        )
        """
        List[str]: Allowed content types for knowledge base linking.

        List of model class paths that can be linked to knowledge bases
        via generic foreign keys.
        """

        # Chat and Session Settings
        self.CHAT_SESSION_TIMEOUT = self._get_setting(
            'CHAT_SESSION_TIMEOUT',
            3600
        )
        """
        int: Chat session timeout in seconds.

        How long chat sessions remain active without activity.
        After timeout, sessions may be cleaned up.
        """

        self.CHAT_MESSAGE_MAX_LENGTH = self._get_setting(
            'CHAT_MESSAGE_MAX_LENGTH',
            10000
        )
        """
        int: Maximum length for chat messages in characters.

        Prevents extremely long messages that could cause memory
        or processing issues.
        """

        self.CHAT_HISTORY_LIMIT = self._get_setting(
            'CHAT_HISTORY_LIMIT',
            100
        )
        """
        int: Maximum number of messages to keep in chat history.

        Older messages beyond this limit may be archived or deleted
        to manage database size.
        """

        # WebSocket Settings
        self.WEBSOCKET_MESSAGE_SIZE_LIMIT = self._get_setting(
            'WEBSOCKET_MESSAGE_SIZE_LIMIT',
            1024 * 1024
        )
        """
        int: Maximum WebSocket message size in bytes.

        Prevents large messages from overwhelming the WebSocket
        connection or server memory.
        """

        self.WEBSOCKET_PING_INTERVAL = self._get_setting(
            'WEBSOCKET_PING_INTERVAL',
            20
        )
        """
        int: WebSocket ping interval in seconds.

        How often to send ping frames to keep connections alive
        and detect disconnected clients.
        """

        # Logging and Debugging
        self.DEBUG_CONTEXT_INJECTION = self._get_setting(
            'DEBUG_CONTEXT_INJECTION',
            False
        )
        """
        bool: Enable detailed debug logging for context injection.

        When enabled, logs detailed information about queryset
        evaluation and context building. Useful for debugging
        but may impact performance.
        """

        self.LOG_OLLAMA_REQUESTS = self._get_setting(
            'LOG_OLLAMA_REQUESTS',
            False
        )
        """
        bool: Enable logging of all Ollama API requests and responses.

        When enabled, logs full request/response data for debugging.
        WARNING: May log sensitive data. Only enable in development.
        """

        # Performance Settings
        self.ASYNC_BATCH_SIZE = self._get_setting(
            'ASYNC_BATCH_SIZE',
            10
        )
        """
        int: Batch size for async operations.

        Number of operations to process in parallel for async
        context evaluation and bulk operations.
        """

        self.QUERY_CACHE_SIZE = self._get_setting(
            'QUERY_CACHE_SIZE',
            1000
        )
        """
        int: Maximum number of cached query results.

        Size of the LRU cache for database query results.
        Helps improve performance for repeated queries.
        """

        # Feature Flags
        self.ENABLE_STREAMING_RESPONSES = self._get_setting(
            'ENABLE_STREAMING_RESPONSES',
            True
        )
        """
        bool: Enable streaming responses for chat.

        When enabled, chat responses are streamed in real-time
        rather than waiting for complete responses.
        """

        self.ENABLE_CONTEXT_PREVIEW = self._get_setting(
            'ENABLE_CONTEXT_PREVIEW',
            True
        )
        """
        bool: Enable context preview functionality.

        Allows users to preview what context will be sent to AI
        before submitting requests.
        """

        self.ENABLE_RATE_LIMITING = self._get_setting(
            'ENABLE_RATE_LIMITING',
            True
        )
        """
        bool: Enable rate limiting for API requests.

        When enabled, applies rate limits to prevent abuse
        and manage server load.
        """

        # Rate Limiting Settings
        self.RATE_LIMIT_REQUESTS_PER_MINUTE = self._get_setting(
            'RATE_LIMIT_REQUESTS_PER_MINUTE',
            60
        )
        """
        int: Maximum requests per minute per user/IP.

        Rate limit for API requests to prevent abuse.
        Only applies when ENABLE_RATE_LIMITING is True.
        """

        self.RATE_LIMIT_BURST_SIZE = self._get_setting(
            'RATE_LIMIT_BURST_SIZE',
            10
        )
        """
        int: Burst size for rate limiting.

        Number of requests that can exceed the rate limit
        temporarily (token bucket burst size).
        """

        # Validate all settings
        self._validate()

        # Log configuration summary
        if logger.isEnabledFor(logging.INFO):
            self._log_config_summary()

    def _get_setting(self, name: str, default: Any) -> Any:
        """
        Get a setting value from Django settings with fallback to default.

        Args:
            name: Setting name (will be prefixed with DJANGO_OLLAMA_)
            default: Default value if setting not found

        Returns:
            Setting value or default
        """
        setting_name = f'DJANGO_OLLAMA_{name}'
        return getattr(settings, setting_name, default)

    def _validate(self) -> None:
        """Validate all settings for correctness and consistency."""

        # Validate Ollama connection settings
        if not self.OLLAMA_HOST:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_OLLAMA_HOST cannot be empty"
            )

        if not self.OLLAMA_HOST.startswith(('http://', 'https://')):
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_OLLAMA_HOST must start with http:// or https://"
            )

        if self.OLLAMA_TIMEOUT <= 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_OLLAMA_TIMEOUT must be positive"
            )

        if self.OLLAMA_MAX_RETRIES < 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_OLLAMA_MAX_RETRIES must be non-negative"
            )

        # Validate context injection settings
        if self.CONTEXT_INJECTION_MAX_ITEMS <= 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_CONTEXT_INJECTION_MAX_ITEMS must be positive"
            )

        if self.CONTEXT_INJECTION_DEFAULT_PRIORITY < 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_CONTEXT_INJECTION_DEFAULT_PRIORITY must be non-negative"
            )

        if self.CONTEXT_INJECTION_CACHE_TIMEOUT < 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_CONTEXT_INJECTION_CACHE_TIMEOUT must be non-negative"
            )

        # Validate namespace settings
        if self.NAMESPACE_DEFAULT_ACCESS not in ['private', 'public', 'readonly']:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_NAMESPACE_DEFAULT_ACCESS must be 'private', 'public', or 'readonly'"
            )

        if self.NAMESPACE_MAX_PER_USER < 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_NAMESPACE_MAX_PER_USER must be non-negative"
            )

        # Validate knowledge base settings
        if self.KNOWLEDGE_BASE_MAX_SIZE_MB <= 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_KNOWLEDGE_BASE_MAX_SIZE_MB must be positive"
            )

        if not isinstance(self.KNOWLEDGE_BASE_CONTENT_TYPES, list):
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_KNOWLEDGE_BASE_CONTENT_TYPES must be a list"
            )

        # Validate chat settings
        if self.CHAT_SESSION_TIMEOUT <= 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_CHAT_SESSION_TIMEOUT must be positive"
            )

        if self.CHAT_MESSAGE_MAX_LENGTH <= 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_CHAT_MESSAGE_MAX_LENGTH must be positive"
            )

        if self.CHAT_HISTORY_LIMIT <= 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_CHAT_HISTORY_LIMIT must be positive"
            )

        # Validate WebSocket settings
        if self.WEBSOCKET_MESSAGE_SIZE_LIMIT <= 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_WEBSOCKET_MESSAGE_SIZE_LIMIT must be positive"
            )

        if self.WEBSOCKET_PING_INTERVAL <= 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_WEBSOCKET_PING_INTERVAL must be positive"
            )

        # Validate performance settings
        if self.ASYNC_BATCH_SIZE <= 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_ASYNC_BATCH_SIZE must be positive"
            )

        if self.QUERY_CACHE_SIZE < 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_QUERY_CACHE_SIZE must be non-negative"
            )

        # Validate rate limiting settings
        if self.RATE_LIMIT_REQUESTS_PER_MINUTE <= 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_RATE_LIMIT_REQUESTS_PER_MINUTE must be positive"
            )

        if self.RATE_LIMIT_BURST_SIZE <= 0:
            raise ImproperlyConfigured(
                "DJANGO_OLLAMA_RATE_LIMIT_BURST_SIZE must be positive"
            )

    def _log_config_summary(self) -> None:
        """Log a summary of the current configuration."""
        logger.info("Django-Ollama Configuration Summary:")
        logger.info(f"  Ollama Host: {self.OLLAMA_HOST}")
        logger.info(f"  Default Model: {self.OLLAMA_DEFAULT_MODEL}")
        logger.info(f"  Context Injection: {'Enabled' if self.CONTEXT_INJECTION_ENABLED else 'Disabled'}")
        logger.info(f"  Streaming Responses: {'Enabled' if self.ENABLE_STREAMING_RESPONSES else 'Disabled'}")
        logger.info(f"  Rate Limiting: {'Enabled' if self.ENABLE_RATE_LIMITING else 'Disabled'}")

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all settings as a dictionary.

        Returns:
            Dictionary of all setting names and values
        """
        return {
            name: getattr(self, name)
            for name in dir(self)
            if not name.startswith('_') and not callable(getattr(self, name))
        }

    def get_setting_info(self, name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific setting.

        Args:
            name: Setting name

        Returns:
            Dictionary with setting value, type, and documentation
        """
        if not hasattr(self, name):
            raise ValueError(f"Setting '{name}' not found")

        value = getattr(self, name)
        doc = getattr(self.__class__, name).__doc__ or "No documentation available"

        return {
            'name': name,
            'value': value,
            'type': type(value).__name__,
            'documentation': doc.strip()
        }


# Global settings instance
app_settings = DjangoOllamaSettings()


def get_setting(name: str, default: Any = None) -> Any:
    """
    Convenience function to get a setting value.

    Args:
        name: Setting name (without DJANGO_OLLAMA_ prefix)
        default: Default value if setting not found

    Returns:
        Setting value
    """
    try:
        return getattr(app_settings, name)
    except AttributeError:
        if default is not None:
            return default
        raise ValueError(f"Setting '{name}' not found and no default provided")


def validate_settings() -> List[str]:
    """
    Validate all settings and return any validation errors.

    Returns:
        List of validation error messages (empty if all valid)
    """
    try:
        app_settings._validate()
        return []
    except ImproperlyConfigured as e:
        return [str(e)]