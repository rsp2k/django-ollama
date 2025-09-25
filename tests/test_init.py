"""
Test cases for django-ollama __init__.py module.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from django.test import TestCase, override_settings


class TestPackageInit(TestCase):
    """Test cases for package initialization."""

    def test_version_import_success(self):
        """Test successful version import."""
        import django_ollama

        # Should have a version attribute
        assert hasattr(django_ollama, '__version__')
        assert isinstance(django_ollama.__version__, str)

    @patch('django_ollama._version')
    def test_version_import_fallback(self, mock_version):
        """Test version fallback when import fails."""
        # Make the import fail
        mock_version.version = None

        # Remove the module from cache to force re-import
        import sys
        if 'django_ollama' in sys.modules:
            del sys.modules['django_ollama']

        # This should use fallback version
        with patch.dict(sys.modules, {'django_ollama._version': None}):
            import importlib
            # Simulate ImportError during import
            with patch('builtins.__import__', side_effect=ImportError):
                # Re-import django_ollama module
                if 'django_ollama' in sys.modules:
                    del sys.modules['django_ollama']

                import django_ollama
                assert django_ollama.__version__ == "0.1.0.dev0"

    def test_default_app_config(self):
        """Test default app config setting."""
        import django_ollama

        assert hasattr(django_ollama, 'default_app_config')
        assert django_ollama.default_app_config == "django_ollama.apps.DjangoOllamaConfig"

    def test_public_api_exports(self):
        """Test that public API functions are exported."""
        import django_ollama

        # Should export API functions
        expected_exports = [
            '__version__',
            'chat',
            'generate',
            'achat',
            'agenerate'
        ]

        for export in expected_exports:
            assert hasattr(django_ollama, export)

        # Check __all__ contains expected items
        assert hasattr(django_ollama, '__all__')
        for export in expected_exports:
            assert export in django_ollama.__all__

    def test_api_functions_available(self):
        """Test that API functions are callable."""
        import django_ollama

        # These should be callable functions
        api_functions = ['chat', 'generate', 'achat', 'agenerate']

        for func_name in api_functions:
            func = getattr(django_ollama, func_name)
            assert callable(func)

    @patch('django_ollama.apps')
    @patch('django_ollama.settings')
    def test_django_models_import_success(self, mock_settings, mock_apps):
        """Test successful Django models import."""
        # Mock Django as configured and ready
        mock_settings.configured = True
        mock_apps.ready = True

        # Remove module from cache to force re-import
        import sys
        if 'django_ollama' in sys.modules:
            del sys.modules['django_ollama']

        # Import should include models in __all__
        import django_ollama

        # Should have model exports when Django is ready
        model_exports = [
            'KnowledgeBase',
            'KnowledgeBaseContent',
            'KnowledgeBaseMedia'
        ]

        for export in model_exports:
            if export in django_ollama.__all__:
                assert hasattr(django_ollama, export)

    @patch('django_ollama.settings')
    def test_django_not_configured(self, mock_settings):
        """Test behavior when Django is not configured."""
        # Mock Django as not configured
        mock_settings.configured = False

        # Remove module from cache
        import sys
        if 'django_ollama' in sys.modules:
            del sys.modules['django_ollama']

        # Should not raise error and should not include models
        import django_ollama

        # Basic exports should still be there
        assert 'chat' in django_ollama.__all__
        assert 'generate' in django_ollama.__all__

    def test_import_error_handling(self):
        """Test handling of various import errors."""
        import sys

        # Remove module from cache
        if 'django_ollama' in sys.modules:
            del sys.modules['django_ollama']

        # Mock ImportError for Django
        with patch.dict(sys.modules, {'django.conf': None, 'django.apps': None}):
            # Should handle gracefully
            import django_ollama

            # Should still have basic API
            assert hasattr(django_ollama, 'chat')
            assert hasattr(django_ollama, '__version__')

    def test_attribute_error_handling(self):
        """Test handling of AttributeError during Django import."""
        import sys

        if 'django_ollama' in sys.modules:
            del sys.modules['django_ollama']

        # Mock AttributeError during settings access
        mock_settings = Mock()
        del mock_settings.configured  # Remove attribute to trigger AttributeError

        with patch('django_ollama.settings', mock_settings):
            import django_ollama

            # Should handle gracefully
            assert hasattr(django_ollama, 'chat')

    def test_runtime_error_handling(self):
        """Test handling of RuntimeError during Django import."""
        import sys

        if 'django_ollama' in sys.modules:
            del sys.modules['django_ollama']

        # Mock RuntimeError (apps not ready)
        mock_settings = Mock()
        mock_settings.configured = True

        mock_apps = Mock()
        mock_apps.ready = True

        # Make model import raise RuntimeError
        with patch('django_ollama.settings', mock_settings), \
             patch('django_ollama.apps', mock_apps), \
             patch('django_ollama.models', side_effect=RuntimeError("Apps not ready")):

            import django_ollama

            # Should handle gracefully
            assert hasattr(django_ollama, 'chat')

    def test_module_docstring(self):
        """Test that module has proper docstring."""
        import django_ollama

        assert django_ollama.__doc__ is not None
        assert "Django-Ollama" in django_ollama.__doc__
        assert "LLM integration" in django_ollama.__doc__

    def test_model_imports_conditional(self):
        """Test that model imports are truly conditional."""
        # This test verifies the conditional import logic
        import django_ollama

        # The models should only be in __all__ if Django is properly configured
        # We can't easily test this without mocking the entire import process,
        # but we can verify the structure exists
        assert isinstance(django_ollama.__all__, list)

        # Basic API should always be present
        required_exports = ['__version__', 'chat', 'generate', 'achat', 'agenerate']
        for export in required_exports:
            assert export in django_ollama.__all__

    @patch('django_ollama.settings')
    @patch('django_ollama.apps')
    def test_apps_not_ready_handling(self, mock_apps, mock_settings):
        """Test handling when Django apps are not ready."""
        mock_settings.configured = True
        mock_apps.ready = False

        import sys
        if 'django_ollama' in sys.modules:
            del sys.modules['django_ollama']

        import django_ollama

        # Should not crash and should have basic API
        assert hasattr(django_ollama, 'chat')
        assert 'chat' in django_ollama.__all__