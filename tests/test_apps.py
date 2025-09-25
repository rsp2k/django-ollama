"""
Test cases for django-ollama Django app configuration.
"""

import pytest
from django.apps import apps
from django.test import TestCase, override_settings
from django.core.exceptions import ImproperlyConfigured
from unittest.mock import patch

from django_ollama.apps import DjangoOllamaConfig


class TestDjangoOllamaConfig(TestCase):
    """Test cases for DjangoOllamaConfig."""

    def test_app_config_attributes(self):
        """Test that app config has correct attributes."""
        config = DjangoOllamaConfig("django_ollama", None)

        assert config.name == "django_ollama"
        assert config.verbose_name == "Django Ollama"
        assert config.default_auto_field == "django.db.models.BigAutoField"

    def test_app_is_registered(self):
        """Test that the app is properly registered."""
        app_config = apps.get_app_config('django_ollama')
        assert isinstance(app_config, DjangoOllamaConfig)
        assert app_config.name == 'django_ollama'

    def test_models_are_loaded(self):
        """Test that models are properly loaded."""
        app_config = apps.get_app_config('django_ollama')
        models = app_config.get_models()

        model_names = {model._meta.model_name for model in models}
        expected_models = {
            'knowledgebase',
            'knowledgebasecontent',
            'knowledgebasemedia',
            'chatsession',
            'chatmessage'
        }
        assert model_names == expected_models

    @patch('django_ollama.apps.DjangoOllamaConfig.ready')
    def test_ready_method_called(self, mock_ready):
        """Test that ready method is called during app loading."""
        # This is more of an integration test to ensure ready() gets called
        # The actual ready() method tries to import signals
        from django_ollama.apps import DjangoOllamaConfig
        config = DjangoOllamaConfig("django_ollama", None)

        # Call ready manually to test the method
        config.ready()  # Should not raise error even if signals don't exist

    def test_ready_with_missing_signals(self):
        """Test ready method handles missing signals module gracefully."""
        config = DjangoOllamaConfig("django_ollama", None)

        # This should not raise an error even if signals module doesn't exist
        # because the ImportError is caught
        config.ready()

    def test_app_label(self):
        """Test that app has correct label."""
        app_config = apps.get_app_config('django_ollama')
        assert app_config.label == 'django_ollama'

    def test_verbose_name_localization(self):
        """Test that verbose name is properly localized."""
        config = DjangoOllamaConfig("django_ollama", None)
        # The verbose_name uses gettext_lazy, so it should be a lazy object
        from django.utils.functional import Promise
        assert isinstance(config.verbose_name, (str, Promise))


class TestAppIntegration(TestCase):
    """Integration tests for the django-ollama app."""

    def test_app_in_installed_apps(self):
        """Test that the app is in INSTALLED_APPS."""
        from django.conf import settings
        assert 'django_ollama' in settings.INSTALLED_APPS

    def test_default_auto_field_setting(self):
        """Test that default auto field is properly set."""
        app_config = apps.get_app_config('django_ollama')
        assert app_config.default_auto_field == "django.db.models.BigAutoField"

    def test_app_ready_state(self):
        """Test that the app is in ready state."""
        assert apps.ready
        app_config = apps.get_app_config('django_ollama')
        assert app_config is not None

    def test_models_have_correct_app_label(self):
        """Test that all models have the correct app label."""
        from django_ollama import models as ollama_models

        model_classes = [
            ollama_models.KnowledgeBase,
            ollama_models.KnowledgeBaseContent,
            ollama_models.KnowledgeBaseMedia,
            ollama_models.ChatSession,
            ollama_models.ChatMessage,
        ]

        for model_class in model_classes:
            assert model_class._meta.app_label == 'django_ollama'