"""
Namespace security and access control for django-ollama.

This module implements a middleware-style security system for controlling
access to namespaces and knowledge bases. The security checks are
overridable to allow for custom authorization logic.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Set, Dict, Any, Callable, TYPE_CHECKING
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.http import HttpRequest
from django.utils.functional import cached_property
import logging

if TYPE_CHECKING:
    from django.contrib.auth.models import User, AnonymousUser
    from .models import Namespace, KnowledgeBase

logger = logging.getLogger(__name__)


class NamespaceAccessPolicy(ABC):
    """
    Abstract base class for namespace access policies.

    Subclass this to implement custom access control logic.
    """

    @abstractmethod
    def get_allowed_namespaces(
        self,
        user: Optional['User'],
        request: Optional[HttpRequest] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Set[str]:
        """
        Get the set of namespace slugs that the user is allowed to access.

        Args:
            user: The user requesting access (may be None or AnonymousUser)
            request: The HTTP request context (optional)
            context: Additional context for the access check

        Returns:
            Set of namespace slugs that are allowed
        """
        pass

    @abstractmethod
    def can_access_namespace(
        self,
        user: Optional['User'],
        namespace: 'Namespace',
        request: Optional[HttpRequest] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a user can access a specific namespace.

        Args:
            user: The user requesting access
            namespace: The namespace to check
            request: The HTTP request context (optional)
            context: Additional context for the access check

        Returns:
            True if access is allowed, False otherwise
        """
        pass

    def can_modify_namespace(
        self,
        user: Optional['User'],
        namespace: 'Namespace',
        request: Optional[HttpRequest] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a user can modify a specific namespace.

        Args:
            user: The user requesting modification
            namespace: The namespace to modify
            request: The HTTP request context (optional)
            context: Additional context for the access check

        Returns:
            True if modification is allowed, False otherwise
        """
        from django.contrib.auth.models import AnonymousUser  # Import inside function to avoid AppRegistryNotReady

        # By default, only owners and superusers can modify
        if not user or isinstance(user, AnonymousUser):
            return False

        if user.is_superuser:
            return True

        return namespace.owner == user


class DefaultNamespacePolicy(NamespaceAccessPolicy):
    """
    Default namespace access policy implementation.

    This policy:
    - Allows access to default and public namespaces for all users
    - Allows access to owned namespaces for authenticated users
    - Allows superusers to access all namespaces
    """

    def get_allowed_namespaces(
        self,
        user: Optional['User'],
        request: Optional[HttpRequest] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Set[str]:
        """Get allowed namespace slugs for the user."""
        from django.contrib.auth.models import AnonymousUser  # Import inside function to avoid AppRegistryNotReady
        from .models import Namespace  # Import inside function to avoid AppRegistryNotReady

        allowed = set()

        # Everyone can access the default namespace
        try:
            default_ns = Namespace.objects.get(is_default=True)
            allowed.add(default_ns.slug)
        except Namespace.DoesNotExist:
            pass

        # Add public namespaces (those with public knowledge bases)
        public_namespaces = Namespace.objects.filter(
            is_active=True,
            knowledge_bases__is_public=True
        ).distinct().values_list('slug', flat=True)
        allowed.update(public_namespaces)

        # Authenticated users can access their owned namespaces
        if user and not isinstance(user, AnonymousUser):
            if user.is_superuser:
                # Superusers can access all namespaces
                all_namespaces = Namespace.objects.filter(
                    is_active=True
                ).values_list('slug', flat=True)
                allowed.update(all_namespaces)
            else:
                # Regular users can access owned namespaces
                owned_namespaces = Namespace.objects.filter(
                    owner=user,
                    is_active=True
                ).values_list('slug', flat=True)
                allowed.update(owned_namespaces)

                # Also add namespaces where user owns knowledge bases
                kb_namespaces = Namespace.objects.filter(
                    knowledge_bases__owner=user,
                    is_active=True
                ).distinct().values_list('slug', flat=True)
                allowed.update(kb_namespaces)

        return allowed

    def can_access_namespace(
        self,
        user: Optional['User'],
        namespace: 'Namespace',
        request: Optional[HttpRequest] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if user can access a specific namespace."""
        if not namespace.is_active:
            return False

        # Default namespace is accessible to all
        if namespace.is_default:
            return True

        # Public knowledge bases make namespace accessible
        if namespace.knowledge_bases.filter(is_public=True).exists():
            return True

        # Anonymous users can't access non-default/non-public namespaces
        if not user or isinstance(user, AnonymousUser):
            return False

        # Superusers can access everything
        if user.is_superuser:
            return True

        # Owners can access their namespaces
        if namespace.owner == user:
            return True

        # Users who own knowledge bases in the namespace can access it
        if namespace.knowledge_bases.filter(owner=user).exists():
            return True

        return False


class NamespaceSecurityMiddleware:
    """
    Middleware for enforcing namespace access control.

    This middleware validates namespace access for requests and
    filters the allowed namespaces based on the configured policy.
    """

    def __init__(self, policy: Optional[NamespaceAccessPolicy] = None):
        """
        Initialize the security middleware.

        Args:
            policy: The access policy to use (defaults to DefaultNamespacePolicy)
        """
        self.policy = policy or self._get_configured_policy()

    def _get_configured_policy(self) -> NamespaceAccessPolicy:
        """Get the policy from Django settings or use default."""
        policy_class_path = getattr(
            settings,
            'DJANGO_OLLAMA_NAMESPACE_POLICY',
            'django_ollama.namespace_security.DefaultNamespacePolicy'
        )

        # Import and instantiate the policy class
        if isinstance(policy_class_path, str):
            module_path, class_name = policy_class_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            policy_class = getattr(module, class_name)
            return policy_class()
        else:
            # Assume it's already an instance or class
            if isinstance(policy_class_path, type):
                return policy_class_path()
            return policy_class_path

    def get_allowed_namespaces(
        self,
        user: Optional['User'],
        requested_namespaces: Optional[List[str]] = None,
        request: Optional[HttpRequest] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List['Namespace']:
        """
        Get the list of allowed namespaces for a user.

        This is the main method that should be called to get filtered namespaces.
        It ensures that only allowed namespaces are returned, even if the client
        requests specific ones.

        Args:
            user: The user requesting access
            requested_namespaces: Optional list of namespace slugs requested by client
            request: The HTTP request context
            context: Additional context

        Returns:
            List of Namespace objects that are allowed

        Raises:
            PermissionDenied: If user requests namespaces they don't have access to
        """
        from .models import Namespace  # Import inside function to avoid AppRegistryNotReady

        # Get all allowed namespace slugs for the user
        allowed_slugs = self.policy.get_allowed_namespaces(user, request, context)

        # If client requested specific namespaces, validate them
        if requested_namespaces:
            requested_set = set(requested_namespaces)

            # Check if all requested namespaces are allowed
            unauthorized = requested_set - allowed_slugs
            if unauthorized:
                logger.warning(
                    f"User {user} requested unauthorized namespaces: {unauthorized}"
                )
                raise PermissionDenied(
                    f"Access denied to namespaces: {', '.join(unauthorized)}"
                )

            # Return only the requested namespaces (if they're allowed)
            return list(Namespace.objects.filter(
                slug__in=requested_namespaces,
                is_active=True
            ))
        else:
            # Return all allowed namespaces
            return list(Namespace.objects.filter(
                slug__in=allowed_slugs,
                is_active=True
            ))

    def filter_knowledge_bases(
        self,
        user: Optional['User'],
        knowledge_bases: List['KnowledgeBase'],
        request: Optional[HttpRequest] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List['KnowledgeBase']:
        """
        Filter knowledge bases to only those in allowed namespaces.

        Args:
            user: The user requesting access
            knowledge_bases: List of knowledge bases to filter
            request: The HTTP request context
            context: Additional context

        Returns:
            Filtered list of knowledge bases
        """
        allowed_slugs = self.policy.get_allowed_namespaces(user, request, context)

        return [
            kb for kb in knowledge_bases
            if kb.namespace.slug in allowed_slugs
        ]

    def check_namespace_access(
        self,
        user: Optional['User'],
        namespace: 'Namespace',
        request: Optional[HttpRequest] = None,
        context: Optional[Dict[str, Any]] = None,
        raise_exception: bool = True
    ) -> bool:
        """
        Check if a user has access to a specific namespace.

        Args:
            user: The user requesting access
            namespace: The namespace to check
            request: The HTTP request context
            context: Additional context
            raise_exception: Whether to raise PermissionDenied on failure

        Returns:
            True if access is allowed

        Raises:
            PermissionDenied: If access is denied and raise_exception=True
        """
        has_access = self.policy.can_access_namespace(user, namespace, request, context)

        if not has_access and raise_exception:
            raise PermissionDenied(
                f"Access denied to namespace '{namespace.slug}'"
            )

        return has_access

    def check_namespace_modification(
        self,
        user: Optional['User'],
        namespace: 'Namespace',
        request: Optional[HttpRequest] = None,
        context: Optional[Dict[str, Any]] = None,
        raise_exception: bool = True
    ) -> bool:
        """
        Check if a user can modify a specific namespace.

        Args:
            user: The user requesting modification
            namespace: The namespace to modify
            request: The HTTP request context
            context: Additional context
            raise_exception: Whether to raise PermissionDenied on failure

        Returns:
            True if modification is allowed

        Raises:
            PermissionDenied: If modification is denied and raise_exception=True
        """
        can_modify = self.policy.can_modify_namespace(user, namespace, request, context)

        if not can_modify and raise_exception:
            raise PermissionDenied(
                f"Permission denied to modify namespace '{namespace.slug}'"
            )

        return can_modify


# Global instance for convenience
_security_middleware = None


def get_security_middleware() -> NamespaceSecurityMiddleware:
    """
    Get the global security middleware instance.

    This creates a singleton instance that can be used throughout the application.
    """
    global _security_middleware
    if _security_middleware is None:
        _security_middleware = NamespaceSecurityMiddleware()
    return _security_middleware


def reset_security_middleware(policy: Optional[NamespaceAccessPolicy] = None):
    """
    Reset the global security middleware with a new policy.

    Args:
        policy: Optional new policy to use
    """
    global _security_middleware
    _security_middleware = NamespaceSecurityMiddleware(policy)


# Decorator for views/functions that need namespace security
def require_namespace_access(namespace_param: str = 'namespace'):
    """
    Decorator to enforce namespace access control on views/functions.

    Args:
        namespace_param: The parameter name that contains the namespace

    Example:
        @require_namespace_access('namespace_slug')
        def my_view(request, namespace_slug):
            # View code here
    """
    def decorator(func):
        def wrapped(*args, **kwargs):
            # Extract request and namespace from args/kwargs
            request = None
            namespace = None

            # Try to find request in args
            for arg in args:
                if isinstance(arg, HttpRequest):
                    request = arg
                    break

            # Get namespace from kwargs
            namespace_value = kwargs.get(namespace_param)
            if namespace_value:
                if isinstance(namespace_value, Namespace):
                    namespace = namespace_value
                else:
                    # Try to get by slug
                    try:
                        namespace = Namespace.objects.get(slug=namespace_value)
                    except Namespace.DoesNotExist:
                        raise PermissionDenied(f"Namespace '{namespace_value}' not found")

            if namespace and request:
                middleware = get_security_middleware()
                user = getattr(request, 'user', None)
                middleware.check_namespace_access(user, namespace, request=request)

            return func(*args, **kwargs)

        return wrapped
    return decorator