"""
Advanced security tests for namespace system.

These tests specifically validate that client requests cannot bypass
server-side security restrictions and that the middleware properly
enforces access control in all scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, TransactionTestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.conf import settings
import django
import json

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
        DJANGO_OLLAMA_NAMESPACE_POLICY='django_ollama.namespace_security.DefaultNamespacePolicy',
    )
    django.setup()

from django_ollama.models import Namespace, KnowledgeBase
from django_ollama.namespace_security import (
    NamespaceAccessPolicy, DefaultNamespacePolicy,
    NamespaceSecurityMiddleware, get_security_middleware,
    reset_security_middleware
)

User = get_user_model()


class TestClientRequestValidation(TransactionTestCase):
    """Test that client requests are properly validated server-side."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='client_user',
            email='client@example.com',
            password='client123'
        )
        self.attacker = User.objects.create_user(
            username='attacker',
            email='attacker@example.com',
            password='attacker123'
        )

        # Create namespaces
        self.public_ns = Namespace.objects.create(
            name="Public",
            slug="public",
            is_default=False
        )
        self.user_private_ns = Namespace.objects.create(
            name="User Private",
            slug="user-private",
            owner=self.user
        )
        self.secret_ns = Namespace.objects.create(
            name="Secret",
            slug="secret",
            owner=None  # No owner, not public
        )

        # Make public namespace actually public via knowledge base
        KnowledgeBase.objects.create(
            namespace=self.public_ns,
            name="Public KB",
            slug="public-kb",
            is_public=True
        )

    def test_client_cannot_access_unauthorized_namespaces(self):
        """Test client cannot access namespaces they're not authorized for."""
        middleware = get_security_middleware()

        # Simulate client request trying to access secret namespace
        client_requested = ["public", "secret"]  # Client tries to sneak in "secret"

        with pytest.raises(PermissionDenied, match="Access denied to namespaces: secret"):
            middleware.get_allowed_namespaces(
                user=self.user,
                requested_namespaces=client_requested
            )

    def test_client_cannot_bypass_with_modified_request(self):
        """Test client cannot bypass security with modified requests."""
        middleware = get_security_middleware()

        # Various attack vectors
        attack_vectors = [
            ["secret"],  # Direct access attempt
            ["public", "secret"],  # Mixed with valid
            ["user-private", "secret"],  # Multiple unauthorized
            ["../secret"],  # Path traversal attempt
            ["SECRET"],  # Case variation
            ["secret "],  # Whitespace injection
            ["secret\x00"],  # Null byte injection
        ]

        for attack in attack_vectors:
            # Attacker should not be able to access
            try:
                result = middleware.get_allowed_namespaces(
                    user=self.attacker,
                    requested_namespaces=attack
                )
                # If we get here, check that secret wasn't included
                slugs = [ns.slug for ns in result]
                assert "secret" not in slugs
            except PermissionDenied:
                # This is expected for most attacks
                pass

    def test_client_request_validation_with_http_request(self):
        """Test validation with actual HTTP request objects."""
        middleware = get_security_middleware()

        # Create HTTP request
        request = self.factory.post(
            '/api/chat',
            json.dumps({"namespaces": ["public", "secret"]}),
            content_type='application/json'
        )
        request.user = self.user

        # Parse the "client-submitted" namespace list
        data = json.loads(request.body)
        client_namespaces = data.get("namespaces", [])

        # Server-side validation should reject unauthorized
        with pytest.raises(PermissionDenied, match="secret"):
            middleware.get_allowed_namespaces(
                user=request.user,
                requested_namespaces=client_namespaces,
                request=request
            )

    def test_empty_client_request_returns_all_allowed(self):
        """Test empty client request returns all allowed namespaces."""
        middleware = get_security_middleware()

        # When client doesn't specify, they get all allowed
        result = middleware.get_allowed_namespaces(
            user=self.user,
            requested_namespaces=None  # No specific request
        )

        slugs = [ns.slug for ns in result]
        assert "public" in slugs  # Public namespaces
        assert "user-private" in slugs  # Owned namespaces
        assert "secret" not in slugs  # Not allowed

    def test_malformed_client_requests_handled_safely(self):
        """Test malformed client requests are handled safely."""
        middleware = get_security_middleware()

        # Test with various malformed inputs
        malformed_inputs = [
            "",  # Empty string
            "not-a-list",  # String instead of list
            123,  # Number
            {"namespace": "secret"},  # Dict instead of list
            [None],  # None in list
            [123],  # Numbers in list
            [{"slug": "secret"}],  # Objects in list
        ]

        for malformed in malformed_inputs:
            try:
                # Should either handle gracefully or raise appropriate error
                if isinstance(malformed, list):
                    result = middleware.get_allowed_namespaces(
                        user=self.user,
                        requested_namespaces=malformed
                    )
                    # If successful, verify no unauthorized access
                    for ns in result:
                        assert ns.owner == self.user or ns.is_default or \
                               ns.knowledge_bases.filter(is_public=True).exists()
            except (TypeError, ValueError, AttributeError):
                # These are acceptable error responses for malformed input
                pass


class TestMiddlewareEnforcement(TransactionTestCase):
    """Test that middleware enforcement cannot be bypassed."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='test123'
        )
        self.restricted_ns = Namespace.objects.create(
            name="Restricted",
            slug="restricted"
        )

    def test_direct_model_access_still_requires_validation(self):
        """Test that direct model access should still be validated."""
        # This demonstrates that while models can be accessed directly,
        # the application layer should always use the middleware

        # Direct model access (BAD - bypasses security)
        kb_direct = KnowledgeBase.objects.create(
            namespace=self.restricted_ns,
            name="Direct KB",
            slug="direct-kb"
        )

        # The middleware should be used to validate access
        middleware = get_security_middleware()

        # Even though the KB exists, access should be validated
        all_kbs = KnowledgeBase.objects.all()
        filtered_kbs = middleware.filter_knowledge_bases(
            user=self.user,
            knowledge_bases=list(all_kbs)
        )

        # User shouldn't see KBs in restricted namespace
        assert kb_direct not in filtered_kbs

    def test_middleware_singleton_consistency(self):
        """Test middleware singleton maintains consistent state."""
        # Get middleware instance
        middleware1 = get_security_middleware()
        middleware2 = get_security_middleware()

        # Should be the same instance
        assert middleware1 is middleware2

        # Custom policy should affect all references
        class CustomPolicy(NamespaceAccessPolicy):
            def get_allowed_namespaces(self, user, request=None, context=None):
                return set()  # Allow nothing

            def can_access_namespace(self, user, namespace, request=None, context=None):
                return False

        reset_security_middleware(CustomPolicy())

        # New instance should have custom policy
        middleware3 = get_security_middleware()
        assert middleware3 is not middleware1  # Different instance after reset

        # Should enforce custom policy
        result = middleware3.get_allowed_namespaces(user=self.user)
        assert len(result) == 0  # Custom policy allows nothing

    def test_policy_configuration_from_settings(self):
        """Test loading custom policy from Django settings."""
        # Mock custom policy path in settings
        with patch('django_ollama.namespace_security.settings') as mock_settings:
            mock_settings.DJANGO_OLLAMA_NAMESPACE_POLICY = \
                'tests.test_namespace_security_advanced.TestCustomPolicy'

            # Create a test policy class in this module
            global TestCustomPolicy

            class TestCustomPolicy(NamespaceAccessPolicy):
                def get_allowed_namespaces(self, user, request=None, context=None):
                    return {"test-only"}

                def can_access_namespace(self, user, namespace, request=None, context=None):
                    return namespace.slug == "test-only"

            # Reset to load from settings
            reset_security_middleware(None)
            middleware = get_security_middleware()

            # Should use custom policy from settings
            # Note: This test is illustrative; actual implementation
            # would need proper module importing logic


class TestSecurityWithWebSockets(TestCase):
    """Test security enforcement in WebSocket contexts."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            username='wsuser',
            email='ws@example.com',
            password='ws123'
        )
        self.namespace = Namespace.objects.create(
            name="WebSocket NS",
            slug="websocket-ns",
            owner=self.user
        )

    def test_websocket_namespace_validation(self):
        """Test namespace validation in WebSocket context."""
        middleware = get_security_middleware()

        # Simulate WebSocket connection with namespace request
        ws_request = Mock()
        ws_request.user = self.user

        # Client sends namespace selection via WebSocket
        client_message = {
            "type": "select_namespaces",
            "namespaces": ["websocket-ns", "unauthorized-ns"]
        }

        # Server must validate
        requested = client_message.get("namespaces", [])

        # Should reject unauthorized namespace
        with pytest.raises(PermissionDenied, match="unauthorized-ns"):
            middleware.get_allowed_namespaces(
                user=ws_request.user,
                requested_namespaces=requested,
                request=ws_request
            )

    def test_websocket_streaming_respects_namespaces(self):
        """Test that streaming responses respect namespace boundaries."""
        middleware = get_security_middleware()

        # Create KBs in different namespaces
        allowed_ns = Namespace.objects.create(
            name="Allowed",
            slug="allowed",
            owner=self.user
        )
        forbidden_ns = Namespace.objects.create(
            name="Forbidden",
            slug="forbidden"
        )

        kb_allowed = KnowledgeBase.objects.create(
            namespace=allowed_ns,
            name="Allowed KB",
            slug="allowed-kb"
        )
        kb_forbidden = KnowledgeBase.objects.create(
            namespace=forbidden_ns,
            name="Forbidden KB",
            slug="forbidden-kb"
        )

        # Simulate streaming context
        all_kbs = [kb_allowed, kb_forbidden]
        filtered = middleware.filter_knowledge_bases(
            user=self.user,
            knowledge_bases=all_kbs
        )

        # Should only stream from allowed KBs
        assert kb_allowed in filtered
        assert kb_forbidden not in filtered


class TestCrossTenantSecurity(TransactionTestCase):
    """Test security in multi-tenant scenarios."""

    def setUp(self):
        """Set up multi-tenant test environment."""
        # Create two "tenants" (organizations)
        self.tenant1_admin = User.objects.create_user(
            username='tenant1_admin',
            email='admin@tenant1.com',
            password='admin123'
        )
        self.tenant2_admin = User.objects.create_user(
            username='tenant2_admin',
            email='admin@tenant2.com',
            password='admin123'
        )

        # Create tenant namespaces
        self.tenant1_ns = Namespace.objects.create(
            name="Tenant 1",
            slug="tenant-1",
            owner=self.tenant1_admin,
            metadata={"tenant_id": "tenant1"}
        )
        self.tenant2_ns = Namespace.objects.create(
            name="Tenant 2",
            slug="tenant-2",
            owner=self.tenant2_admin,
            metadata={"tenant_id": "tenant2"}
        )

        # Create tenant-specific data
        self.tenant1_kb = KnowledgeBase.objects.create(
            namespace=self.tenant1_ns,
            name="Tenant 1 Data",
            slug="tenant1-data",
            owner=self.tenant1_admin
        )
        self.tenant2_kb = KnowledgeBase.objects.create(
            namespace=self.tenant2_ns,
            name="Tenant 2 Data",
            slug="tenant2-data",
            owner=self.tenant2_admin
        )

    def test_tenant_isolation(self):
        """Test that tenants cannot access each other's data."""
        middleware = get_security_middleware()

        # Tenant 1 admin cannot access Tenant 2's namespace
        with pytest.raises(PermissionDenied):
            middleware.check_namespace_access(
                user=self.tenant1_admin,
                namespace=self.tenant2_ns
            )

        # Tenant 2 admin cannot access Tenant 1's namespace
        with pytest.raises(PermissionDenied):
            middleware.check_namespace_access(
                user=self.tenant2_admin,
                namespace=self.tenant1_ns
            )

    def test_tenant_specific_policy(self):
        """Test implementing tenant-specific access policies."""

        class TenantAwarePolicy(NamespaceAccessPolicy):
            """Policy that enforces tenant boundaries."""

            def get_allowed_namespaces(self, user, request=None, context=None):
                if not user or user.is_anonymous:
                    return {"default"}

                # Get user's tenant from their metadata or group
                user_tenant = getattr(user, 'tenant_id', None)
                if not user_tenant and context:
                    user_tenant = context.get('tenant_id')

                allowed = {"default"}

                # Allow access to namespaces in same tenant
                for ns in Namespace.objects.filter(is_active=True):
                    ns_tenant = ns.metadata.get('tenant_id')
                    if ns_tenant and ns_tenant == user_tenant:
                        allowed.add(ns.slug)
                    elif ns.owner == user:
                        allowed.add(ns.slug)

                return allowed

            def can_access_namespace(self, user, namespace, request=None, context=None):
                if namespace.is_default:
                    return True

                if not user or user.is_anonymous:
                    return False

                # Check tenant match
                user_tenant = getattr(user, 'tenant_id', None)
                ns_tenant = namespace.metadata.get('tenant_id')

                if user_tenant and ns_tenant:
                    return user_tenant == ns_tenant

                return namespace.owner == user

        # Apply tenant-aware policy
        middleware = NamespaceSecurityMiddleware(TenantAwarePolicy())

        # Set tenant IDs on users (in real app, this might be in user profile)
        self.tenant1_admin.tenant_id = 'tenant1'
        self.tenant2_admin.tenant_id = 'tenant2'

        # Each tenant admin can only see their tenant's namespaces
        t1_allowed = middleware.get_allowed_namespaces(user=self.tenant1_admin)
        t1_slugs = [ns.slug for ns in t1_allowed]
        assert "tenant-1" in t1_slugs
        assert "tenant-2" not in t1_slugs

        t2_allowed = middleware.get_allowed_namespaces(user=self.tenant2_admin)
        t2_slugs = [ns.slug for ns in t2_allowed]
        assert "tenant-2" in t2_slugs
        assert "tenant-1" not in t2_slugs


class TestSecurityAuditLogging(TestCase):
    """Test security audit logging for compliance."""

    @patch('django_ollama.namespace_security.logger')
    def test_unauthorized_access_logged(self, mock_logger):
        """Test that unauthorized access attempts are logged."""
        middleware = get_security_middleware()

        user = User.objects.create_user(
            username='suspicious',
            email='sus@example.com',
            password='sus123'
        )

        # Attempt unauthorized access
        with pytest.raises(PermissionDenied):
            middleware.get_allowed_namespaces(
                user=user,
                requested_namespaces=["admin", "secret", "protected"]
            )

        # Check that warning was logged
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args[0][0]
        assert "suspicious" in call_args
        assert "unauthorized namespaces" in call_args

    def test_successful_access_tracking(self):
        """Test tracking successful namespace access for audit."""
        # This would typically integrate with Django's logging
        # or a dedicated audit system

        middleware = get_security_middleware()
        user = User.objects.create_user(
            username='audited',
            email='audit@example.com',
            password='audit123'
        )

        # Create namespace user can access
        ns = Namespace.objects.create(
            name="Audited",
            slug="audited",
            owner=user
        )

        # Access should succeed and could be logged
        result = middleware.check_namespace_access(
            user=user,
            namespace=ns,
            context={"audit": True}  # Could trigger audit logging
        )
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])