"""Django app configuration for django-ollama."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DjangoOllamaConfig(AppConfig):
    """Django app configuration for Ollama integration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_ollama"
    verbose_name = _("Django Ollama")

    def ready(self):
        """Import signals when the app is ready."""
        try:
            from . import signals  # noqa: F401
        except ImportError:
            # Signals module is optional
            pass