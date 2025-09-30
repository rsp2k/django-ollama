"""
Test suite for the context injection system.

Tests lazy queryset handling, URL-based extraction, permissions,
and middleware integration.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from typing import List

# Configure Django settings BEFORE any Django imports
import django
from django.conf import settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'django_ollama',
        ],
        SECRET_KEY='test-secret-key',
        USE_TZ=True,
        ROOT_URLCONF='tests.urls',  # Add ROOT_URLCONF for URL resolution tests
    )
    django.setup()

# Now we can import Django modules
from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User, AnonymousUser
from django.db.models import QuerySet, Model
from django.http import HttpRequest
from django.urls import ResolverMatch

from django_ollama.context_injection import (
    LazyQueryset,
    QuerysetInjector,
    URLBasedQuerysetInjector,
    SmartQuerysetInjector,
    CompositeQuerysetInjector,
    AIContextMiddleware,
    inject_querysets,
    get_ai_context
)
from django_ollama.models import KnowledgeBase, Namespace


class TestLazyQueryset(TestCase):
    """Test the LazyQueryset wrapper."""

    def test_lazy_queryset_creation(self):
        """Test creating a lazy queryset."""
        mock_qs = Mock(spec=QuerySet)

        lazy_qs = LazyQueryset(
            name='test_qs',
            queryset=mock_qs,
            limit=5,
            priority=10,
            metadata={'source': 'test'}
        )

        assert lazy_qs.name == 'test_qs'
        assert lazy_qs.queryset == mock_qs
        assert lazy_qs.limit == 5
        assert lazy_qs.priority == 10
        assert lazy_qs.metadata == {'source': 'test'}

    def test_lazy_queryset_not_evaluated_on_creation(self):
        """Verify queryset is not evaluated when creating LazyQueryset."""
        mock_qs = Mock(spec=QuerySet)
        mock_qs.__iter__ = Mock(side_effect=Exception("Should not iterate!"))

        # This should NOT raise an exception
        lazy_qs = LazyQueryset(
            name='test_qs',
            queryset=mock_qs
        )

        # Queryset should not have been iterated
        mock_qs.__iter__.assert_not_called()

    def test_evaluate_for_ai_with_ai_text_method(self):
        """Test evaluating queryset with __ai_text__ method."""
        # Create mock objects with __ai_text__ method
        mock_obj1 = Mock()
        mock_obj1.__ai_text__ = Mock(return_value="AI text 1")

        mock_obj2 = Mock()
        mock_obj2.__ai_text__ = Mock(return_value="AI text 2")

        mock_qs = Mock(spec=QuerySet)
        mock_qs.__iter__ = Mock(return_value=iter([mock_obj1, mock_obj2]))
        mock_qs.__getitem__ = Mock(return_value=mock_qs)  # For slicing

        lazy_qs = LazyQueryset(
            name='test_qs',
            queryset=mock_qs,
            limit=2
        )

        result = lazy_qs.evaluate_for_ai()

        assert result == "AI text 1\n\nAI text 2"
        mock_obj1.__ai_text__.assert_called_once()
        mock_obj2.__ai_text__.assert_called_once()

    def test_evaluate_for_ai_with_limit(self):
        """Test that limit is respected during evaluation."""
        mock_objs = [Mock() for _ in range(10)]
        for i, obj in enumerate(mock_objs):
            obj.__ai_text__ = Mock(return_value=f"AI text {i}")

        mock_qs = Mock(spec=QuerySet)
        mock_qs.__getitem__ = Mock(return_value=Mock(
            __iter__=Mock(return_value=iter(mock_objs[:3]))
        ))

        lazy_qs = LazyQueryset(
            name='test_qs',
            queryset=mock_qs,
            limit=3
        )

        result = lazy_qs.evaluate_for_ai()

        # Should only evaluate first 3 objects
        assert "AI text 0" in result
        assert "AI text 1" in result
        assert "AI text 2" in result
        assert "AI text 3" not in result

        # Verify slicing was called with limit
        mock_qs.__getitem__.assert_called_once_with(slice(None, 3))

    def test_evaluate_for_ai_fallback_methods(self):
        """Test fallback to __ai_serialize__ and str()."""
        mock_obj1 = Mock()
        mock_obj1.__ai_serialize__ = Mock(return_value="Serialized 1")
        # Make sure hasattr returns False for __ai_text__
        del mock_obj1.__ai_text__

        mock_obj2 = Mock()
        mock_obj2.__str__ = Mock(return_value="String representation")
        # Make sure hasattr returns False for both AI methods
        del mock_obj2.__ai_text__
        del mock_obj2.__ai_serialize__

        mock_qs = Mock(spec=QuerySet)
        # Support slicing
        mock_qs.__getitem__ = Mock(return_value=mock_qs)
        mock_qs.__iter__ = Mock(return_value=iter([mock_obj1, mock_obj2]))

        lazy_qs = LazyQueryset(
            name='test_qs',
            queryset=mock_qs,
            limit=None  # No limit, so it won't slice
        )

        result = lazy_qs.evaluate_for_ai()

        assert "Serialized 1" in result
        assert "String representation" in result

    def test_count_without_evaluation(self):
        """Test count() doesn't evaluate the full queryset."""
        mock_qs = Mock(spec=QuerySet)
        mock_qs.count = Mock(return_value=42)
        mock_qs.__iter__ = Mock(side_effect=Exception("Should not iterate!"))

        lazy_qs = LazyQueryset(
            name='test_qs',
            queryset=mock_qs
        )

        count = lazy_qs.count()

        assert count == 42
        mock_qs.count.assert_called_once()
        mock_qs.__iter__.assert_not_called()

    def test_exists_without_evaluation(self):
        """Test exists() doesn't evaluate the full queryset."""
        mock_qs = Mock(spec=QuerySet)
        mock_qs.exists = Mock(return_value=True)
        mock_qs.__iter__ = Mock(side_effect=Exception("Should not iterate!"))

        lazy_qs = LazyQueryset(
            name='test_qs',
            queryset=mock_qs
        )

        exists = lazy_qs.exists()

        assert exists is True
        mock_qs.exists.assert_called_once()
        mock_qs.__iter__.assert_not_called()


class TestURLBasedQuerysetInjector(TestCase):
    """Test URL-based queryset injection."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.injector = URLBasedQuerysetInjector()

    def test_register_pattern(self):
        """Test registering URL pattern handlers."""
        handler = Mock(return_value=[])

        self.injector.register_pattern('product_detail', handler)

        assert 'product_detail' in self.injector.pattern_handlers
        assert self.injector.pattern_handlers['product_detail'] == handler

    @patch('django_ollama.context_injection.resolve')
    @patch('django_ollama.context_injection.get_security_middleware')
    def test_get_querysets_with_registered_handler(self, mock_get_middleware, mock_resolve):
        """Test getting querysets with a registered handler."""
        # Create mock middleware
        mock_middleware = Mock()
        mock_middleware.get_allowed_namespaces = Mock(return_value=[])
        mock_get_middleware.return_value = mock_middleware

        # Create mock queryset
        mock_qs = Mock(spec=QuerySet)
        mock_qs.model = Mock()

        # Create handler that returns LazyQueryset
        def handler(context):
            return [LazyQueryset(
                name='product_qs',
                queryset=mock_qs,
                priority=15
            )]

        self.injector.register_pattern('product_detail', handler)

        # Mock URL resolution
        mock_match = Mock()
        mock_match.url_name = 'product_detail'
        mock_match.kwargs = {'pk': 1}
        mock_match.args = ()
        mock_match.func = Mock()
        mock_resolve.return_value = mock_match

        # Create request
        request = self.factory.get('/products/1/')
        request.user = Mock()

        # Get querysets
        querysets = self.injector.get_querysets(request)

        assert len(querysets) == 1
        assert querysets[0].name == 'product_qs'
        assert querysets[0].priority == 15

    @patch('django_ollama.context_injection.resolve')
    def test_get_querysets_from_view_function(self, mock_resolve):
        """Test getting querysets from view's get_ai_querysets method."""
        mock_qs = Mock(spec=QuerySet)
        mock_qs.model = Mock()

        # Create view function with get_ai_querysets
        view_func = Mock()
        view_func.get_ai_querysets = Mock(return_value=[
            LazyQueryset(name='view_qs', queryset=mock_qs)
        ])

        # Mock URL resolution
        mock_match = Mock()
        mock_match.url_name = 'some_view'
        mock_match.kwargs = {'id': 123}
        mock_match.args = ()
        mock_match.func = view_func
        mock_resolve.return_value = mock_match

        # Create request
        request = self.factory.get('/some/123/')
        request.user = Mock()

        # Get querysets
        querysets = self.injector.get_querysets(request)

        assert len(querysets) == 1
        assert querysets[0].name == 'view_qs'
        view_func.get_ai_querysets.assert_called_once_with(
            request, {'id': 123}
        )

    @patch('django_ollama.context_injection.resolve')
    @patch('django_ollama.context_injection.get_security_middleware')
    def test_filter_by_permissions(self, mock_get_middleware, mock_resolve):
        """Test permission filtering of querysets."""
        # Create mock namespace
        allowed_namespace = Mock(spec=Namespace)

        # Create mock middleware
        mock_middleware = Mock()
        mock_middleware.get_allowed_namespaces = Mock(
            return_value=[allowed_namespace]
        )
        mock_get_middleware.return_value = mock_middleware

        # Create mock querysets
        mock_kb_qs = Mock(spec=QuerySet)
        mock_kb_qs.model = KnowledgeBase
        mock_kb_qs.filter = Mock(return_value=mock_kb_qs)
        mock_kb_qs.exists = Mock(return_value=True)

        # Mock URL resolution
        mock_match = Mock()
        mock_match.url_name = 'test'
        mock_match.kwargs = {}
        mock_match.args = ()
        mock_match.func = Mock()
        mock_resolve.return_value = mock_match

        # Add queryset manually for testing
        lazy_qs = LazyQueryset(
            name='kb_qs',
            queryset=mock_kb_qs
        )

        # Create request
        request = self.factory.get('/test/')
        request.user = Mock()

        # Filter by permissions
        filtered = self.injector.filter_by_permissions([lazy_qs], request.user)

        assert len(filtered) == 1
        mock_kb_qs.filter.assert_called_once()

        # Verify namespace filtering was applied
        filter_call = mock_kb_qs.filter.call_args
        assert 'namespace__in' in filter_call[1]
        assert filter_call[1]['is_active'] is True


class TestSmartQuerysetInjector(TestCase):
    """Test smart queryset injection."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.injector = SmartQuerysetInjector()

    @patch('django_ollama.models.KnowledgeBase.objects')
    def test_get_querysets_for_authenticated_user(self, mock_kb_objects):
        """Test getting querysets for authenticated user."""
        # Mock user
        user = Mock(spec=User)
        user.is_authenticated = True

        # Mock queryset
        mock_qs = Mock(spec=QuerySet)
        mock_qs.filter = Mock(return_value=mock_qs)
        mock_qs.select_related = Mock(return_value=mock_qs)
        mock_qs.order_by = Mock(return_value=mock_qs)
        mock_kb_objects.filter = Mock(return_value=mock_qs)

        # Create request
        request = self.factory.get('/')
        request.user = user

        # Get querysets
        querysets = self.injector.get_querysets(request)

        # Should have user knowledge bases
        assert len(querysets) > 0
        assert querysets[0].name == 'user_knowledge_bases'
        assert querysets[0].priority == 10
        assert querysets[0].limit == 5

    @patch('django_ollama.models.KnowledgeBase.objects')
    def test_get_querysets_for_anonymous_user(self, mock_kb_objects):
        """Test getting querysets for anonymous user."""
        # Mock queryset
        mock_qs = Mock(spec=QuerySet)
        mock_qs.filter = Mock(return_value=mock_qs)
        mock_qs.select_related = Mock(return_value=mock_qs)
        mock_kb_objects.filter = Mock(return_value=mock_qs)

        # Create request
        request = self.factory.get('/')
        request.user = AnonymousUser()

        # Get querysets
        querysets = self.injector.get_querysets(request)

        # Should have public knowledge bases
        assert len(querysets) > 0
        assert querysets[0].name == 'public_knowledge_bases'
        assert querysets[0].priority == 5
        assert querysets[0].limit == 3

    @patch('django_ollama.context_injection.resolve')
    def test_extract_model_from_url_with_pk(self, mock_resolve):
        """Test extracting model from URL with pk parameter."""
        # Create mock model
        MockModel = Mock()
        MockModel.__name__ = 'Product'
        MockModel.__ai_text__ = Mock()
        MockModel.objects = Mock()
        MockModel.objects.filter = Mock(return_value=Mock(spec=QuerySet))

        # Mock view with model
        mock_view = Mock()
        mock_view.view_class = Mock()
        mock_view.view_class.model = MockModel

        # Mock URL resolution
        mock_match = Mock()
        mock_match.url_name = 'product_detail'
        mock_match.kwargs = {'pk': 42}
        mock_match.args = ()
        mock_match.func = mock_view
        mock_resolve.return_value = mock_match

        # Mock _infer_model_from_view
        with patch.object(self.injector, '_infer_model_from_view', return_value=MockModel):
            # Create request
            request = self.factory.get('/products/42/')
            request.user = Mock()
            request.user.is_authenticated = False

            # Get querysets
            querysets = self.injector.get_querysets(request)

            # Should have product queryset with high priority
            product_qs = next((qs for qs in querysets if qs.name == 'product_current'), None)
            assert product_qs is not None
            assert product_qs.priority == 20
            assert product_qs.limit == 1

            # Verify filter was called with correct pk
            MockModel.objects.filter.assert_called_with(pk=42)

    def test_session_based_querysets(self):
        """Test adding querysets from session."""
        # Create mock model
        MockModel = Mock()
        MockModel.__name__ = 'Article'
        MockModel.objects = Mock()
        mock_qs = Mock(spec=QuerySet)
        MockModel.objects.filter = Mock(return_value=mock_qs)
        mock_qs.order_by = Mock(return_value=mock_qs)

        # Mock _get_model_class to return our model
        with patch.object(self.injector, '_get_model_class', return_value=MockModel):
            # Create request with session data
            request = self.factory.get('/')
            request.user = Mock()
            request.user.is_authenticated = False
            request.session = {
                'ai_context_queries': [
                    {
                        'model': 'Article',
                        'name': 'recent_articles',
                        'filters': {'is_published': True},
                        'order_by': '-created_at',
                        'limit': 10,
                        'priority': 8
                    }
                ]
            }

            # Get querysets
            querysets = self.injector.get_querysets(request)

            # Should have session queryset
            session_qs = next((qs for qs in querysets if qs.name == 'recent_articles'), None)
            assert session_qs is not None
            assert session_qs.limit == 10
            assert session_qs.priority == 8

            # Verify queryset was built correctly
            MockModel.objects.filter.assert_called_with(is_published=True)
            mock_qs.order_by.assert_called_with('-created_at')

    def test_explicit_context_querysets(self):
        """Test adding explicitly provided querysets from context."""
        # Create mock querysets
        mock_qs1 = Mock(spec=QuerySet)
        mock_qs2 = Mock(spec=QuerySet)

        lazy_qs = LazyQueryset(
            name='explicit_1',
            queryset=mock_qs1,
            priority=25
        )

        # Create request
        request = self.factory.get('/')
        request.user = Mock()
        request.user.is_authenticated = False

        # Provide context with querysets
        context = {
            'querysets': [
                lazy_qs,
                mock_qs2  # Raw queryset should be wrapped
            ]
        }

        # Get querysets
        querysets = self.injector.get_querysets(request, context)

        # Should have both querysets
        explicit_1 = next((qs for qs in querysets if qs.name == 'explicit_1'), None)
        assert explicit_1 is not None
        assert explicit_1.priority == 25

        explicit_2 = next((qs for qs in querysets if qs.name == 'explicit_queryset'), None)
        assert explicit_2 is not None
        assert explicit_2.queryset == mock_qs2

    def test_querysets_sorted_by_priority(self):
        """Test that querysets are sorted by priority."""
        # Create request
        request = self.factory.get('/')
        request.user = Mock()
        request.user.is_authenticated = False

        # Provide context with querysets of different priorities
        context = {
            'querysets': [
                LazyQueryset('low', Mock(spec=QuerySet), priority=1),
                LazyQueryset('high', Mock(spec=QuerySet), priority=20),
                LazyQueryset('medium', Mock(spec=QuerySet), priority=10),
            ]
        }

        # Get querysets
        querysets = self.injector.get_querysets(request, context)

        # Filter to only our test querysets
        test_querysets = [qs for qs in querysets if qs.name in ['low', 'medium', 'high']]

        # Should be sorted by priority (descending)
        assert test_querysets[0].name == 'high'
        assert test_querysets[1].name == 'medium'
        assert test_querysets[2].name == 'low'


class TestCompositeQuerysetInjector(TestCase):
    """Test composite queryset injector."""

    def test_combine_multiple_injectors(self):
        """Test combining querysets from multiple injectors."""
        # Create mock injectors
        injector1 = Mock(spec=QuerysetInjector)
        injector1.get_querysets = Mock(return_value=[
            LazyQueryset('qs1', Mock(spec=QuerySet), priority=10)
        ])

        injector2 = Mock(spec=QuerysetInjector)
        injector2.get_querysets = Mock(return_value=[
            LazyQueryset('qs2', Mock(spec=QuerySet), priority=5),
            LazyQueryset('qs3', Mock(spec=QuerySet), priority=15)
        ])

        # Create composite injector
        composite = CompositeQuerysetInjector([injector1, injector2])

        # Create request
        request = Mock(spec=HttpRequest)

        # Get querysets
        querysets = composite.get_querysets(request)

        assert len(querysets) == 3
        # Should be sorted by priority
        assert querysets[0].name == 'qs3'  # priority 15
        assert querysets[1].name == 'qs1'  # priority 10
        assert querysets[2].name == 'qs2'  # priority 5

    def test_deduplicate_by_name(self):
        """Test that duplicate names are deduplicated."""
        # Create mock injectors with duplicate names
        injector1 = Mock(spec=QuerysetInjector)
        injector1.get_querysets = Mock(return_value=[
            LazyQueryset('duplicate', Mock(spec=QuerySet), priority=10)
        ])

        injector2 = Mock(spec=QuerysetInjector)
        injector2.get_querysets = Mock(return_value=[
            LazyQueryset('duplicate', Mock(spec=QuerySet), priority=15),
            LazyQueryset('unique', Mock(spec=QuerySet), priority=5)
        ])

        # Create composite injector
        composite = CompositeQuerysetInjector([injector1, injector2])

        # Create request
        request = Mock(spec=HttpRequest)

        # Get querysets
        querysets = composite.get_querysets(request)

        # Should only have one 'duplicate' and one 'unique'
        assert len(querysets) == 2
        names = [qs.name for qs in querysets]
        assert 'duplicate' in names
        assert 'unique' in names

        # First occurrence wins
        duplicate_qs = next(qs for qs in querysets if qs.name == 'duplicate')
        assert duplicate_qs.priority == 10  # From injector1


class TestInjectQuerysetDecorator(TestCase):
    """Test the inject_querysets decorator."""

    def test_decorator_adds_get_ai_querysets(self):
        """Test that decorator adds get_ai_querysets to view."""
        mock_qs = Mock(spec=QuerySet)

        @inject_querysets(
            lambda kwargs: mock_qs,
            priority=20,
            limit=5
        )
        def my_view(request, pk):
            pass

        # Should have get_ai_querysets method
        assert hasattr(my_view, 'get_ai_querysets')

        # Call get_ai_querysets
        request = Mock()
        url_kwargs = {'pk': 1}
        querysets = my_view.get_ai_querysets(request, url_kwargs)

        assert len(querysets) == 1
        assert querysets[0].name == 'view_queryset_0'
        assert querysets[0].priority == 20
        assert querysets[0].limit == 5
        assert querysets[0].queryset == mock_qs

    def test_decorator_with_lazy_queryset(self):
        """Test decorator when function returns LazyQueryset."""
        lazy_qs = LazyQueryset('custom', Mock(spec=QuerySet), priority=30)

        @inject_querysets(
            lambda kwargs: lazy_qs
        )
        def my_view(request):
            pass

        # Call get_ai_querysets
        querysets = my_view.get_ai_querysets(Mock(), {})

        assert len(querysets) == 1
        assert querysets[0] == lazy_qs
        assert querysets[0].name == 'custom'
        assert querysets[0].priority == 30


class TestAIContextMiddleware(TestCase):
    """Test AI context middleware."""

    @patch('django_ollama.context_injection.SmartQuerysetInjector')
    def test_middleware_attaches_querysets(self, mock_injector_class):
        """Test middleware attaches querysets to request."""
        # Create mock injector
        mock_injector = Mock()
        mock_querysets = [
            LazyQueryset('test', Mock(spec=QuerySet))
        ]
        mock_injector.get_querysets = Mock(return_value=mock_querysets)
        mock_injector_class.return_value = mock_injector

        # Create middleware
        get_response = Mock()
        middleware = AIContextMiddleware(get_response)

        # Create request
        request = Mock(spec=HttpRequest)

        # Process request
        middleware(request)

        # Should have attached querysets
        assert hasattr(request, 'ai_querysets')
        assert request.ai_querysets == mock_querysets

        # Should have called get_response
        get_response.assert_called_once_with(request)

    @patch('django_ollama.context_injection.settings')
    def test_middleware_uses_configured_injector(self, mock_settings):
        """Test middleware uses injector from settings."""
        # Configure custom injector path
        mock_settings.DJANGO_OLLAMA_QUERYSET_INJECTOR = \
            'django_ollama.context_injection.URLBasedQuerysetInjector'

        # Create middleware
        get_response = Mock()
        with patch('django_ollama.context_injection.URLBasedQuerysetInjector') as MockInjector:
            mock_instance = Mock()
            MockInjector.return_value = mock_instance

            middleware = AIContextMiddleware(get_response)

            assert middleware.injector == mock_instance
            MockInjector.assert_called_once()


class TestGetAIContext(TestCase):
    """Test get_ai_context helper function."""

    def test_get_ai_context_without_evaluation(self):
        """Test getting AI context without evaluating querysets."""
        # Create request with querysets
        request = Mock(spec=HttpRequest)
        request.ai_querysets = [
            LazyQueryset('qs1', Mock(spec=QuerySet)),
            LazyQueryset('qs2', Mock(spec=QuerySet))
        ]

        # Get context without evaluation
        result = get_ai_context(request, evaluate=False)

        assert result == request.ai_querysets

    def test_get_ai_context_with_evaluation(self):
        """Test getting AI context with queryset evaluation."""
        # Create mock querysets
        mock_qs1 = Mock(spec=QuerySet)
        mock_qs2 = Mock(spec=QuerySet)

        lazy_qs1 = LazyQueryset('qs1', mock_qs1)
        lazy_qs1.exists = Mock(return_value=True)
        lazy_qs1.evaluate_for_ai = Mock(return_value="Content 1")
        lazy_qs1.count = Mock(return_value=3)

        lazy_qs2 = LazyQueryset('qs2', mock_qs2, metadata={'type': 'test'})
        lazy_qs2.exists = Mock(return_value=True)
        lazy_qs2.evaluate_for_ai = Mock(return_value="Content 2")
        lazy_qs2.count = Mock(return_value=1)

        # Create request
        request = Mock(spec=HttpRequest)
        request.ai_querysets = [lazy_qs1, lazy_qs2]

        # Get evaluated context
        result = get_ai_context(request, evaluate=True)

        assert 'content' in result
        assert 'metadata' in result

        assert len(result['content']) == 2

        assert result['content'][0]['name'] == 'qs1'
        assert result['content'][0]['data'] == "Content 1"
        assert result['content'][0]['count'] == 3

        assert result['content'][1]['name'] == 'qs2'
        assert result['content'][1]['data'] == "Content 2"
        assert result['content'][1]['metadata'] == {'type': 'test'}

        assert result['metadata']['total_querysets'] == 2
        assert result['metadata']['evaluated'] == 2

    def test_get_ai_context_skips_empty_querysets(self):
        """Test that empty querysets are skipped during evaluation."""
        # Create mock querysets
        lazy_qs1 = LazyQueryset('qs1', Mock(spec=QuerySet))
        lazy_qs1.exists = Mock(return_value=True)
        lazy_qs1.evaluate_for_ai = Mock(return_value="Content 1")
        lazy_qs1.count = Mock(return_value=1)

        lazy_qs2 = LazyQueryset('qs2', Mock(spec=QuerySet))
        lazy_qs2.exists = Mock(return_value=False)  # Empty queryset

        # Create request
        request = Mock(spec=HttpRequest)
        request.ai_querysets = [lazy_qs1, lazy_qs2]

        # Get evaluated context
        result = get_ai_context(request, evaluate=True)

        # Should only have one content item (non-empty)
        assert len(result['content']) == 1
        assert result['content'][0]['name'] == 'qs1'
        assert result['metadata']['evaluated'] == 1

    @patch('django_ollama.context_injection.SmartQuerysetInjector')
    def test_get_ai_context_without_middleware(self, mock_injector_class):
        """Test get_ai_context when middleware hasn't run."""
        # Create mock injector
        mock_injector = Mock()
        mock_querysets = [
            LazyQueryset('fallback', Mock(spec=QuerySet))
        ]
        mock_injector.get_querysets = Mock(return_value=mock_querysets)
        mock_injector_class.return_value = mock_injector

        # Create request without ai_querysets
        request = Mock(spec=HttpRequest)

        # Get context - should create querysets
        result = get_ai_context(request, evaluate=False)

        assert result == mock_querysets
        assert request.ai_querysets == mock_querysets
        mock_injector.get_querysets.assert_called_once_with(request)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])