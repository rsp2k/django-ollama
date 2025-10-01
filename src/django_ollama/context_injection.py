"""
Context injection system for django-ollama.

This module provides a flexible system for injecting querysets into AI context
based on the current request context (URL, user, etc.). At its core, it manages
lists of lazy querysets that are only evaluated when needed.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Union, Type, Callable, Tuple
from dataclasses import dataclass, field
from django.db.models import QuerySet, Model, Q, Prefetch
from django.http import HttpRequest
from django.urls import resolve, Resolver404
from django.conf import settings
import logging

if TYPE_CHECKING:
    from django.contrib.auth.models import User

from .namespace_security import get_security_middleware

logger = logging.getLogger(__name__)


@dataclass
class LazyQueryset:
    """
    Wrapper for a lazy queryset with metadata.

    The queryset is not evaluated until explicitly needed, maintaining
    Django's lazy evaluation benefits.
    """
    name: str  # Identifier for this queryset
    queryset: QuerySet  # The lazy queryset
    ai_method: str = '__ai_text__'  # Method to call for AI serialization
    limit: Optional[int] = 10  # Max items to serialize (None = all)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher priority querysets are processed first

    def evaluate_for_ai(self) -> str:
        """
        Evaluate the queryset and serialize for AI consumption.

        This is where the actual database query happens.
        """
        items = []

        # Apply limit if specified
        qs = self.queryset[:self.limit] if self.limit else self.queryset

        for obj in qs:
            # Try to get AI representation from the model
            if hasattr(obj, self.ai_method):
                ai_func = getattr(obj, self.ai_method)
                content = ai_func() if callable(ai_func) else str(ai_func)
            elif hasattr(obj, '__ai_serialize__'):
                # Fallback to alternative method
                ai_func = getattr(obj, '__ai_serialize__')
                content = ai_func() if callable(ai_func) else str(ai_func)
            else:
                # Ultimate fallback
                content = str(obj)

            items.append(content)

        return f"\n\n".join(items)

    def count(self) -> int:
        """Get count without evaluating the full queryset."""
        return self.queryset.count()

    def exists(self) -> bool:
        """Check if queryset has any results without full evaluation."""
        return self.queryset.exists()


class QuerysetInjector(ABC):
    """
    Abstract base class for queryset injection policies.

    Subclass this to implement custom logic for determining which
    querysets should be available in the AI context.
    """

    @abstractmethod
    def get_querysets(
        self,
        request: HttpRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> List[LazyQueryset]:
        """
        Get the list of querysets to inject for the current request.

        Args:
            request: The HTTP request object
            context: Additional context data

        Returns:
            List of LazyQueryset objects
        """
        pass

    def filter_by_permissions(
        self,
        querysets: List[LazyQueryset],
        user: Optional['User']
    ) -> List[LazyQueryset]:
        """
        Filter querysets based on user permissions.

        This ensures that querysets respect namespace and model-level permissions.
        """
        from .models import KnowledgeBase  # Import inside function to avoid AppRegistryNotReady

        filtered = []
        # Create middleware instance for permission filtering
        middleware = get_security_middleware()

        for lazy_qs in querysets:
            # Check if it's a KnowledgeBase queryset
            if lazy_qs.queryset.model == KnowledgeBase:
                # Filter knowledge bases by namespace access
                allowed_namespaces = middleware.get_allowed_namespaces(user=user)
                filtered_qs = lazy_qs.queryset.filter(
                    namespace__in=allowed_namespaces,
                    is_active=True
                )

                # Only add if there are results
                if filtered_qs.exists():
                    lazy_qs.queryset = filtered_qs
                    filtered.append(lazy_qs)
            else:
                # For other models, check if they have namespace filtering
                if hasattr(lazy_qs.queryset.model, 'namespace'):
                    allowed_namespaces = middleware.get_allowed_namespaces(user=user)
                    lazy_qs.queryset = lazy_qs.queryset.filter(
                        namespace__in=allowed_namespaces
                    )

                # Apply any model-specific permission filtering
                if hasattr(lazy_qs.queryset.model, 'filter_by_user'):
                    lazy_qs.queryset = lazy_qs.queryset.model.filter_by_user(
                        lazy_qs.queryset, user
                    )

                filtered.append(lazy_qs)

        return filtered


class URLBasedQuerysetInjector(QuerysetInjector):
    """
    Injects querysets based on URL patterns and parameters.

    This injector maps URL patterns to queryset factories.
    """

    def __init__(self):
        """Initialize with URL pattern mappings."""
        self.pattern_handlers = {}
        self._register_default_patterns()

    def _register_default_patterns(self):
        """Register default URL pattern handlers."""
        # Example patterns - would be customized per project
        pass

    def register_pattern(
        self,
        url_name: str,
        handler: Callable[[Dict[str, Any]], List[LazyQueryset]]
    ):
        """
        Register a queryset handler for a URL pattern.

        Args:
            url_name: Name of the URL pattern
            handler: Function that returns list of LazyQuerysets
        """
        self.pattern_handlers[url_name] = handler

    def get_querysets(
        self,
        request: HttpRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> List[LazyQueryset]:
        """Get querysets based on current URL."""
        querysets = []

        try:
            # Resolve current URL
            match = resolve(request.path)

            # Get handler for this URL pattern
            if match.url_name in self.pattern_handlers:
                handler = self.pattern_handlers[match.url_name]
                handler_context = {
                    'kwargs': match.kwargs,
                    'args': match.args,
                    'request': request,
                    **(context or {})
                }
                querysets.extend(handler(handler_context))

            # Check if view has custom queryset provider
            if hasattr(match.func, 'get_ai_querysets'):
                view_querysets = match.func.get_ai_querysets(request, match.kwargs)
                querysets.extend(view_querysets)

        except Resolver404:
            logger.debug(f"Could not resolve URL: {request.path}")

        return self.filter_by_permissions(querysets, request.user)


class SmartQuerysetInjector(QuerysetInjector):
    """
    Intelligent queryset injector that automatically builds relevant querysets.

    This injector analyzes the request context and builds appropriate querysets
    without explicit configuration.
    """

    def get_querysets(
        self,
        request: HttpRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> List[LazyQueryset]:
        """Build querysets based on smart detection."""
        from .models import KnowledgeBase  # Import inside function to avoid AppRegistryNotReady

        querysets = []

        # 1. Get namespace-filtered knowledge bases
        if request.user.is_authenticated:
            # User's knowledge bases (lazy)
            user_kbs = KnowledgeBase.objects.filter(
                Q(owner=request.user) |
                Q(namespace__owner=request.user) |
                Q(is_public=True)
            ).select_related('namespace').order_by('-updated_at')

            querysets.append(LazyQueryset(
                name='user_knowledge_bases',
                queryset=user_kbs,
                limit=5,
                priority=10
            ))
        else:
            # Public knowledge bases only
            public_kbs = KnowledgeBase.objects.filter(
                is_public=True,
                is_active=True
            ).select_related('namespace')

            querysets.append(LazyQueryset(
                name='public_knowledge_bases',
                queryset=public_kbs,
                limit=3,
                priority=5
            ))

        # 2. Extract model from URL if possible
        try:
            match = resolve(request.path)

            # Common patterns
            if 'pk' in match.kwargs or 'id' in match.kwargs:
                # Try to infer model from view
                model_class = self._infer_model_from_view(match.func)
                if model_class and hasattr(model_class, '__ai_text__'):
                    pk = match.kwargs.get('pk') or match.kwargs.get('id')

                    # Create single-item queryset
                    model_qs = model_class.objects.filter(pk=pk)

                    querysets.append(LazyQueryset(
                        name=f'{model_class.__name__.lower()}_current',
                        queryset=model_qs,
                        limit=1,
                        priority=20  # High priority for current item
                    ))

                    # Add related items if model defines them
                    if hasattr(model_class, 'get_ai_related_querysets'):
                        related = model_class.get_ai_related_querysets(pk)
                        querysets.extend(related)

            elif 'slug' in match.kwargs:
                # Handle slug-based lookups
                from django.apps import apps

                for model in apps.get_models():
                    if hasattr(model, 'slug') and hasattr(model, '__ai_text__'):
                        model_qs = model.objects.filter(slug=match.kwargs['slug'])
                        if model_qs.exists():
                            querysets.append(LazyQueryset(
                                name=f'{model.__name__.lower()}_current',
                                queryset=model_qs,
                                limit=1,
                                priority=20
                            ))
                            break

        except Resolver404:
            pass

        # 3. Add session-based querysets
        if hasattr(request, 'session') and 'ai_context_queries' in request.session:
            # Session can store queryset definitions
            for query_def in request.session['ai_context_queries']:
                try:
                    model_class = self._get_model_class(query_def['model'])
                    if model_class:
                        qs = model_class.objects.filter(**query_def.get('filters', {}))
                        if 'order_by' in query_def:
                            qs = qs.order_by(query_def['order_by'])

                        querysets.append(LazyQueryset(
                            name=query_def.get('name', f'session_{query_def["model"]}'),
                            queryset=qs,
                            limit=query_def.get('limit', 5),
                            priority=query_def.get('priority', 3)
                        ))
                except Exception as e:
                    logger.debug(f"Failed to build session queryset: {e}")

        # 4. Add explicitly provided querysets
        if context and 'querysets' in context:
            for qs_data in context['querysets']:
                if isinstance(qs_data, LazyQueryset):
                    querysets.append(qs_data)
                elif isinstance(qs_data, QuerySet):
                    # Wrap raw queryset
                    querysets.append(LazyQueryset(
                        name='explicit_queryset',
                        queryset=qs_data,
                        priority=15
                    ))

        # Sort by priority and filter by permissions
        querysets.sort(key=lambda x: x.priority, reverse=True)
        return self.filter_by_permissions(querysets, request.user)

    def _infer_model_from_view(self, view_func) -> Optional[Type[Model]]:
        """Try to infer model class from view."""
        if hasattr(view_func, 'view_class'):
            view_class = view_func.view_class
            if hasattr(view_class, 'model'):
                return view_class.model
            if hasattr(view_class, 'queryset'):
                return view_class.queryset.model

        if hasattr(view_func, 'model'):
            return view_func.model

        return None

    def _get_model_class(self, model_name: str) -> Optional[Type[Model]]:
        """Get model class from string name."""
        from django.apps import apps

        try:
            if '.' in model_name:
                app_label, model_name = model_name.split('.')
                return apps.get_model(app_label, model_name)
            else:
                # Try to find model by name alone
                for model in apps.get_models():
                    if model.__name__.lower() == model_name.lower():
                        return model
        except Exception:
            pass

        return None


class CompositeQuerysetInjector(QuerysetInjector):
    """
    Combines multiple queryset injectors.

    Allows using multiple injection strategies together.
    """

    def __init__(self, injectors: List[QuerysetInjector] = None):
        """Initialize with list of injectors."""
        self.injectors = injectors or []

    def add_injector(self, injector: QuerysetInjector):
        """Add an injector."""
        self.injectors.append(injector)

    def get_querysets(
        self,
        request: HttpRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> List[LazyQueryset]:
        """Combine querysets from all injectors."""
        all_querysets = []
        seen_names = set()

        for injector in self.injectors:
            querysets = injector.get_querysets(request, context)

            # Deduplicate by name
            for qs in querysets:
                if qs.name not in seen_names:
                    all_querysets.append(qs)
                    seen_names.add(qs.name)

        # Sort by priority
        all_querysets.sort(key=lambda x: x.priority, reverse=True)
        return all_querysets


def inject_querysets(*queryset_funcs, **kwargs):
    """
    Decorator to specify querysets for a view.

    Usage:
        @inject_querysets(
            lambda kwargs: Product.objects.filter(category_id=kwargs['category_id']),
            lambda kwargs: Review.objects.filter(product_id=kwargs['pk'])[:5]
        )
        def product_detail(request, pk, category_id):
            ...
    """
    def decorator(view_func):
        def get_ai_querysets(request, url_kwargs):
            querysets = []

            for i, qs_func in enumerate(queryset_funcs):
                # Call the queryset function with URL kwargs
                qs = qs_func(url_kwargs)

                if isinstance(qs, QuerySet):
                    querysets.append(LazyQueryset(
                        name=f'view_queryset_{i}',
                        queryset=qs,
                        priority=kwargs.get('priority', 10),
                        limit=kwargs.get('limit', 10)
                    ))
                elif isinstance(qs, LazyQueryset):
                    querysets.append(qs)

            return querysets

        view_func.get_ai_querysets = get_ai_querysets
        return view_func

    return decorator


class AIContextMiddleware:
    """
    Middleware that attaches lazy querysets to the request.
    """

    def __init__(self, get_response):
        """Initialize middleware."""
        self.get_response = get_response
        self.injector = self._get_configured_injector()

    def _get_configured_injector(self) -> QuerysetInjector:
        """Get configured injector from settings."""
        injector_path = getattr(
            settings,
            'DJANGO_OLLAMA_QUERYSET_INJECTOR',
            'django_ollama.context_injection.SmartQuerysetInjector'
        )

        if isinstance(injector_path, str):
            module_path, class_name = injector_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            injector_class = getattr(module, class_name)
            return injector_class()
        elif isinstance(injector_path, type):
            return injector_path()
        else:
            return injector_path

    def __call__(self, request):
        """Attach querysets to request."""
        # Get lazy querysets for this request
        request.ai_querysets = self.injector.get_querysets(request)

        # Process request
        response = self.get_response(request)

        return response


def get_ai_context(request: HttpRequest, evaluate: bool = False) -> Union[List[LazyQueryset], Dict[str, Any]]:
    """
    Get AI context for a request.

    Args:
        request: The HTTP request
        evaluate: If True, evaluate querysets and return serialized content

    Returns:
        List of LazyQuerysets if evaluate=False, or dict of evaluated content if True
    """
    if not hasattr(request, 'ai_querysets'):
        # Middleware hasn't run, get querysets manually
        injector = SmartQuerysetInjector()
        request.ai_querysets = injector.get_querysets(request)

    if not evaluate:
        return request.ai_querysets

    # Evaluate querysets for AI consumption
    context = {
        'content': [],
        'metadata': {
            'total_querysets': len(request.ai_querysets),
            'evaluated': 0
        }
    }

    for lazy_qs in request.ai_querysets:
        if lazy_qs.exists():  # Only evaluate non-empty querysets
            context['content'].append({
                'name': lazy_qs.name,
                'data': lazy_qs.evaluate_for_ai(),
                'count': lazy_qs.count(),
                'metadata': lazy_qs.metadata
            })
            context['metadata']['evaluated'] += 1

    return context