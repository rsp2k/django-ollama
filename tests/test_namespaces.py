"""
Comprehensive tests for namespace functionality.

This ensures namespace isolation, access control, and management utilities
work correctly. Tests validate that security is enforced server-side.
"""

import pytest
from unittest.mock import Mock, patch
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import HttpRequest
from django.conf import settings
from django.test.utils import override_settings
import django

# Configure Django settings for tests
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test-secret-key",
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django_ollama',
        ],
        USE_TZ=True,
        TIME_ZONE='UTC',
        MIDDLEWARE=[],
    )
    django.setup()

from django_ollama.models import Namespace, KnowledgeBase
from django_ollama.namespace_manager import (
    NamespaceManager, KnowledgeBaseManager, initialize_namespaces
)
from django_ollama.namespace_security import (
    NamespaceAccessPolicy, DefaultNamespacePolicy,
    NamespaceSecurityMiddleware, get_security_middleware,
    reset_security_middleware, require_namespace_access
)

User = get_user_model()


class TestNamespaceModels(TransactionTestCase):
    """Test the Namespace and updated KnowledgeBase models."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

    def test_namespace_creation(self):
        """Test creating a namespace."""
        namespace = Namespace.objects.create(
            name="Test Namespace",
            slug="test-namespace",
            description="A test namespace",
            owner=self.user
        )

        assert namespace.name == "Test Namespace"
        assert namespace.slug == "test-namespace"
        assert namespace.owner == self.user
        assert namespace.is_active is True
        assert namespace.is_default is False

    def test_default_namespace_singleton(self):
        """Test that only one default namespace can exist."""
        # Create default namespace
        default1 = Namespace.objects.create(
            name="Default",
            slug="default",
            is_default=True
        )

        # Try to create another default namespace
        default2 = Namespace.objects.create(
            name="Another Default",
            slug="another-default",
            is_default=True
        )

        # Check that the first one is no longer default
        default1.refresh_from_db()
        assert default1.is_default is False
        assert default2.is_default is True

    def test_namespace_get_default(self):
        """Test getting or creating default namespace."""
        # Should create if doesn't exist
        default_ns = Namespace.objects.get_default()
        assert default_ns.is_default is True
        assert default_ns.slug == "default"

        # Should return existing if already exists
        default_ns2 = Namespace.objects.get_default()
        assert default_ns.id == default_ns2.id

    def test_knowledge_base_namespace_relationship(self):
        """Test knowledge base belongs to namespace."""
        namespace = Namespace.objects.create(
            name="KB Namespace",
            slug="kb-namespace"
        )

        kb = KnowledgeBase.objects.create(
            namespace=namespace,
            name="Test KB",
            slug="test-kb",
            owner=self.user
        )

        assert kb.namespace == namespace
        assert kb.get_namespace_slug() == "kb-namespace"
        assert namespace.knowledge_bases.count() == 1

    def test_knowledge_base_unique_slug_per_namespace(self):
        """Test KB slugs must be unique within namespace but not across."""
        ns1 = Namespace.objects.create(name="NS1", slug="ns1")
        ns2 = Namespace.objects.create(name="NS2", slug="ns2")

        # Same slug in different namespaces should work
        kb1 = KnowledgeBase.objects.create(
            namespace=ns1,
            name="Shared Name",
            slug="shared-slug"
        )
        kb2 = KnowledgeBase.objects.create(
            namespace=ns2,
            name="Shared Name",
            slug="shared-slug"
        )

        assert kb1.slug == kb2.slug
        assert kb1.namespace != kb2.namespace

        # Same slug in same namespace should fail
        with pytest.raises(Exception):  # IntegrityError
            KnowledgeBase.objects.create(
                namespace=ns1,
                name="Another KB",
                slug="shared-slug"
            )

    def test_namespace_statistics(self):
        """Test namespace statistics properties."""
        namespace = Namespace.objects.create(
            name="Stats NS",
            slug="stats-ns",
            owner=self.user
        )

        # Create knowledge bases
        for i in range(3):
            kb = KnowledgeBase.objects.create(
                namespace=namespace,
                name=f"KB {i}",
                slug=f"kb-{i}",
                is_public=(i == 0)  # First one is public
            )

            # Skip content items for now (requires GenericForeignKey setup)
            pass

        assert namespace.knowledge_base_count == 3
        assert namespace.public_knowledge_base_count == 1


class TestNamespaceManager(TransactionTestCase):
    """Test the NamespaceManager utility class."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_ensure_default_namespace(self):
        """Test ensuring default namespace exists."""
        default_ns = NamespaceManager.ensure_default_namespace()
        assert default_ns.is_default is True
        assert default_ns.slug == "default"

        # Should return same instance if called again
        default_ns2 = NamespaceManager.ensure_default_namespace()
        assert default_ns.id == default_ns2.id

    def test_create_namespace(self):
        """Test creating namespace through manager."""
        ns = NamespaceManager.create_namespace(
            name="Test Namespace",
            description="Test description",
            owner=self.user,
            metadata={"key": "value"}
        )

        assert ns.name == "Test Namespace"
        assert ns.slug == "test-namespace"
        assert ns.owner == self.user
        assert ns.metadata["key"] == "value"

    def test_create_namespace_duplicate_slug(self):
        """Test creating namespace with duplicate slug fails."""
        NamespaceManager.create_namespace("Test Name")

        with pytest.raises(ValidationError, match="already exists"):
            NamespaceManager.create_namespace("Test Name")

    def test_list_namespaces_filtering(self):
        """Test listing namespaces with filters."""
        # Create test namespaces
        ns1 = NamespaceManager.create_namespace("NS1", owner=self.user)
        ns2 = NamespaceManager.create_namespace("NS2")
        ns3 = NamespaceManager.create_namespace("NS3", owner=self.user)
        ns3.is_active = False
        ns3.save()

        # Test active_only filter
        active_namespaces = NamespaceManager.list_namespaces(active_only=True)
        assert ns1 in active_namespaces
        assert ns2 in active_namespaces
        assert ns3 not in active_namespaces

        # Test owner filter
        user_namespaces = NamespaceManager.list_namespaces(owner=self.user)
        assert ns1 in user_namespaces
        assert ns2 not in user_namespaces

    def test_delete_namespace(self):
        """Test deleting namespaces."""
        ns = NamespaceManager.create_namespace("To Delete")

        # Should delete empty namespace
        assert NamespaceManager.delete_namespace(ns) is True
        assert not Namespace.objects.filter(slug="to-delete").exists()

    def test_delete_default_namespace_fails(self):
        """Test cannot delete default namespace."""
        default_ns = NamespaceManager.ensure_default_namespace()

        with pytest.raises(ValidationError, match="Cannot delete the default namespace"):
            NamespaceManager.delete_namespace(default_ns)

    def test_delete_non_empty_namespace_fails(self):
        """Test cannot delete namespace with knowledge bases."""
        ns = NamespaceManager.create_namespace("With KBs")
        KnowledgeBase.objects.create(
            namespace=ns,
            name="KB",
            slug="kb"
        )

        with pytest.raises(ValidationError, match="contains 1 knowledge bases"):
            NamespaceManager.delete_namespace(ns)

        # Should work with force=True
        assert NamespaceManager.delete_namespace(ns, force=True) is True


class TestNamespaceSecurity(TransactionTestCase):
    """Test namespace security and access control."""

    def setUp(self):
        """Set up test fixtures."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )

        # Create test namespaces
        self.default_ns = Namespace.objects.get_default()
        self.user1_ns = Namespace.objects.create(
            name="User1 NS",
            slug="user1-ns",
            owner=self.user1
        )
        self.user2_ns = Namespace.objects.create(
            name="User2 NS",
            slug="user2-ns",
            owner=self.user2
        )
        self.public_ns = Namespace.objects.create(
            name="Public NS",
            slug="public-ns"
        )

        # Create a public knowledge base in public namespace
        self.public_kb = KnowledgeBase.objects.create(
            namespace=self.public_ns,
            name="Public KB",
            slug="public-kb",
            is_public=True
        )

    def test_default_policy_anonymous_access(self):
        """Test anonymous user access with default policy."""
        policy = DefaultNamespacePolicy()
        allowed = policy.get_allowed_namespaces(user=None)

        # Anonymous users can access default and public namespaces
        assert "default" in allowed
        assert "public-ns" in allowed
        assert "user1-ns" not in allowed
        assert "user2-ns" not in allowed

    def test_default_policy_authenticated_access(self):
        """Test authenticated user access with default policy."""
        policy = DefaultNamespacePolicy()

        # User1 can access default, public, and owned namespaces
        allowed = policy.get_allowed_namespaces(user=self.user1)
        assert "default" in allowed
        assert "public-ns" in allowed
        assert "user1-ns" in allowed
        assert "user2-ns" not in allowed

        # User2 has different access
        allowed = policy.get_allowed_namespaces(user=self.user2)
        assert "default" in allowed
        assert "public-ns" in allowed
        assert "user1-ns" not in allowed
        assert "user2-ns" in allowed

    def test_default_policy_superuser_access(self):
        """Test superuser access with default policy."""
        policy = DefaultNamespacePolicy()
        allowed = policy.get_allowed_namespaces(user=self.superuser)

        # Superusers can access all namespaces
        assert "default" in allowed
        assert "public-ns" in allowed
        assert "user1-ns" in allowed
        assert "user2-ns" in allowed

    def test_middleware_get_allowed_namespaces(self):
        """Test middleware filtering of allowed namespaces."""
        middleware = NamespaceSecurityMiddleware()

        # Test with no requested namespaces - should return all allowed
        namespaces = middleware.get_allowed_namespaces(user=self.user1)
        slugs = [ns.slug for ns in namespaces]
        assert "default" in slugs
        assert "user1-ns" in slugs
        assert "user2-ns" not in slugs

    def test_middleware_validates_requested_namespaces(self):
        """Test middleware validates client-requested namespaces."""
        middleware = NamespaceSecurityMiddleware()

        # User1 requests only their allowed namespaces - should work
        allowed = middleware.get_allowed_namespaces(
            user=self.user1,
            requested_namespaces=["default", "user1-ns"]
        )
        slugs = [ns.slug for ns in allowed]
        assert len(slugs) == 2
        assert "default" in slugs
        assert "user1-ns" in slugs

    def test_middleware_rejects_unauthorized_namespaces(self):
        """Test middleware rejects unauthorized namespace requests."""
        middleware = NamespaceSecurityMiddleware()

        # User1 tries to request User2's namespace - should fail
        with pytest.raises(PermissionDenied, match="Access denied to namespaces: user2-ns"):
            middleware.get_allowed_namespaces(
                user=self.user1,
                requested_namespaces=["default", "user1-ns", "user2-ns"]
            )

    def test_middleware_check_namespace_access(self):
        """Test checking access to specific namespace."""
        middleware = NamespaceSecurityMiddleware()

        # User1 can access their namespace
        assert middleware.check_namespace_access(
            user=self.user1,
            namespace=self.user1_ns,
            raise_exception=False
        ) is True

        # User1 cannot access User2's namespace
        assert middleware.check_namespace_access(
            user=self.user1,
            namespace=self.user2_ns,
            raise_exception=False
        ) is False

        # With raise_exception=True, should raise
        with pytest.raises(PermissionDenied, match="Access denied to namespace 'user2-ns'"):
            middleware.check_namespace_access(
                user=self.user1,
                namespace=self.user2_ns,
                raise_exception=True
            )

    def test_middleware_check_namespace_modification(self):
        """Test checking modification permissions."""
        middleware = NamespaceSecurityMiddleware()

        # Owners can modify their namespaces
        assert middleware.check_namespace_modification(
            user=self.user1,
            namespace=self.user1_ns,
            raise_exception=False
        ) is True

        # Non-owners cannot modify
        assert middleware.check_namespace_modification(
            user=self.user2,
            namespace=self.user1_ns,
            raise_exception=False
        ) is False

        # Superusers can modify any namespace
        assert middleware.check_namespace_modification(
            user=self.superuser,
            namespace=self.user1_ns,
            raise_exception=False
        ) is True

    def test_middleware_filter_knowledge_bases(self):
        """Test filtering knowledge bases by allowed namespaces."""
        middleware = NamespaceSecurityMiddleware()

        # Create knowledge bases in different namespaces
        kb1 = KnowledgeBase.objects.create(
            namespace=self.user1_ns,
            name="KB1",
            slug="kb1"
        )
        kb2 = KnowledgeBase.objects.create(
            namespace=self.user2_ns,
            name="KB2",
            slug="kb2"
        )

        all_kbs = [kb1, kb2, self.public_kb]

        # Filter for user1
        filtered = middleware.filter_knowledge_bases(
            user=self.user1,
            knowledge_bases=all_kbs
        )
        assert kb1 in filtered
        assert kb2 not in filtered
        assert self.public_kb in filtered


class TestCustomSecurityPolicy(TransactionTestCase):
    """Test custom security policy implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='test123'
        )
        self.namespace = Namespace.objects.create(
            name="Test NS",
            slug="test-ns"
        )

    def test_custom_policy_override(self):
        """Test overriding security policy."""
        # Ensure default namespace exists
        default_ns = Namespace.objects.get_default()

        class RestrictivePolicy(NamespaceAccessPolicy):
            """A very restrictive policy for testing."""

            def get_allowed_namespaces(self, user, request=None, context=None):
                # Only allow default namespace
                return {"default"}

            def can_access_namespace(self, user, namespace, request=None, context=None):
                # Only allow default namespace
                return namespace.is_default

        # Reset middleware with custom policy
        reset_security_middleware(RestrictivePolicy())
        middleware = get_security_middleware()

        # Even authenticated users can only access default
        allowed = middleware.get_allowed_namespaces(user=self.user)
        slugs = [ns.slug for ns in allowed]
        assert len(slugs) == 1
        assert "default" in slugs

        # Cannot access other namespaces
        assert not middleware.check_namespace_access(
            user=self.user,
            namespace=self.namespace,
            raise_exception=False
        )

    def test_context_based_security_policy(self):
        """Test security policy using context for decisions."""
        # Ensure default namespace exists
        default_ns = Namespace.objects.get_default()

        class ContextAwarePolicy(NamespaceAccessPolicy):
            """Policy that uses context for access decisions."""

            def get_allowed_namespaces(self, user, request=None, context=None):
                allowed = {"default"}

                # Add namespaces based on context
                if context and context.get("include_test"):
                    allowed.add("test-ns")

                return allowed

            def can_access_namespace(self, user, namespace, request=None, context=None):
                if namespace.is_default:
                    return True

                if context and context.get("include_test"):
                    return namespace.slug == "test-ns"

                return False

        middleware = NamespaceSecurityMiddleware(ContextAwarePolicy())

        # Without context, only default is allowed
        allowed = middleware.get_allowed_namespaces(
            user=self.user,
            context={}
        )
        slugs = [ns.slug for ns in allowed]
        assert "default" in slugs
        assert "test-ns" not in slugs

        # With context, test-ns is also allowed
        allowed = middleware.get_allowed_namespaces(
            user=self.user,
            context={"include_test": True}
        )
        slugs = [ns.slug for ns in allowed]
        assert "default" in slugs
        assert "test-ns" in slugs


class TestNamespaceAccessDecorator(TestCase):
    """Test the require_namespace_access decorator."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='test123'
        )
        self.namespace = Namespace.objects.create(
            name="Protected NS",
            slug="protected-ns",
            owner=self.user
        )
        self.other_namespace = Namespace.objects.create(
            name="Other NS",
            slug="other-ns"
        )

    def test_decorator_allows_authorized_access(self):
        """Test decorator allows authorized access."""
        from django_ollama.namespace_security import require_namespace_access

        @require_namespace_access('namespace_slug')
        def protected_view(request, namespace_slug):
            return f"Access granted to {namespace_slug}"

        # Create mock request
        request = Mock(spec=HttpRequest)
        request.user = self.user

        # Should allow access to owned namespace
        result = protected_view(request, namespace_slug="protected-ns")
        assert result == "Access granted to protected-ns"

    def test_decorator_denies_unauthorized_access(self):
        """Test decorator denies unauthorized access."""
        from django_ollama.namespace_security import require_namespace_access

        @require_namespace_access('namespace_slug')
        def protected_view(request, namespace_slug):
            return f"Access granted to {namespace_slug}"

        # Create mock request
        request = Mock(spec=HttpRequest)
        request.user = self.user

        # Should deny access to unowned namespace
        with pytest.raises(PermissionDenied, match="Access denied to namespace 'other-ns'"):
            protected_view(request, namespace_slug="other-ns")

    def test_decorator_handles_namespace_objects(self):
        """Test decorator handles namespace objects directly."""
        from django_ollama.namespace_security import require_namespace_access

        @require_namespace_access('namespace')
        def protected_view(request, namespace):
            return f"Access granted to {namespace.slug}"

        # Create mock request
        request = Mock(spec=HttpRequest)
        request.user = self.user

        # Should work with namespace object
        result = protected_view(request, namespace=self.namespace)
        assert result == "Access granted to protected-ns"

        # Should deny for unauthorized namespace object
        with pytest.raises(PermissionDenied):
            protected_view(request, namespace=self.other_namespace)


class TestInitializeNamespaces(TransactionTestCase):
    """Test namespace initialization function."""

    def test_initialize_creates_default_namespaces(self):
        """Test initialize_namespaces creates expected namespaces."""
        from django_ollama.namespace_manager import initialize_namespaces

        default_ns = initialize_namespaces()

        # Check default namespace was created
        assert default_ns.is_default is True
        assert default_ns.slug == "default"

        # Check other namespaces were created
        assert Namespace.objects.filter(slug="dev").exists()
        assert Namespace.objects.filter(slug="prod").exists()
        assert Namespace.objects.filter(slug="personal").exists()

    def test_initialize_idempotent(self):
        """Test initialize_namespaces is idempotent."""
        from django_ollama.namespace_manager import initialize_namespaces

        # Run twice
        initialize_namespaces()
        count1 = Namespace.objects.count()

        initialize_namespaces()
        count2 = Namespace.objects.count()

        # Should not create duplicates
        assert count1 == count2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])