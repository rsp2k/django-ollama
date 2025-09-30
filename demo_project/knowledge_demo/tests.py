"""
Integration tests for django-ollama namespace features.
"""
from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from django_ollama.models import Namespace, KnowledgeBase
from django_ollama.namespace_manager import NamespaceManager, KnowledgeBaseManager
from django_ollama.namespace_security import get_security_middleware
from .models import Project, Article, Document


class NamespaceIntegrationTest(TransactionTestCase):
    """Integration tests for namespace functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create users
        self.alice = User.objects.create_user(
            username='alice',
            password='testpass123',
            email='alice@test.com'
        )
        self.bob = User.objects.create_user(
            username='bob',
            password='testpass123',
            email='bob@test.com'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
            email='admin@test.com'
        )

        # Create namespaces
        self.default_ns = Namespace.objects.get_default()
        self.alice_ns = Namespace.objects.create(
            name="Alice's Space",
            slug="alice-space",
            owner=self.alice
        )
        self.bob_ns = Namespace.objects.create(
            name="Bob's Space",
            slug="bob-space",
            owner=self.bob
        )

        # Create knowledge bases
        self.alice_kb = KnowledgeBaseManager.create_knowledge_base(
            name="Alice's KB",
            namespace=self.alice_ns,
            owner=self.alice,
            is_public=False
        )
        self.bob_public_kb = KnowledgeBaseManager.create_knowledge_base(
            name="Bob's Public KB",
            namespace=self.bob_ns,
            owner=self.bob,
            is_public=True
        )

    def test_anonymous_namespace_access(self):
        """Test anonymous users can only see default and public namespaces."""
        response = self.client.get(reverse('knowledge_demo:index'))
        self.assertEqual(response.status_code, 200)

        # Check accessible namespaces
        namespaces = response.context['namespaces']
        namespace_slugs = [ns.slug for ns in namespaces]

        # Should see default and Bob's namespace (has public KB)
        self.assertIn('default', namespace_slugs)
        self.assertIn('bob-space', namespace_slugs)
        # Should NOT see Alice's private namespace
        self.assertNotIn('alice-space', namespace_slugs)

    def test_authenticated_user_namespace_access(self):
        """Test authenticated users see their owned namespaces."""
        self.client.login(username='alice', password='testpass123')
        response = self.client.get(reverse('knowledge_demo:index'))

        namespaces = response.context['namespaces']
        namespace_slugs = [ns.slug for ns in namespaces]

        # Alice should see default, her own, and Bob's public
        self.assertIn('default', namespace_slugs)
        self.assertIn('alice-space', namespace_slugs)
        self.assertIn('bob-space', namespace_slugs)

    def test_superuser_sees_all_namespaces(self):
        """Test superusers can see all namespaces."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('knowledge_demo:index'))

        namespaces = response.context['namespaces']
        namespace_slugs = [ns.slug for ns in namespaces]

        # Admin should see all namespaces
        self.assertIn('default', namespace_slugs)
        self.assertIn('alice-space', namespace_slugs)
        self.assertIn('bob-space', namespace_slugs)

    def test_namespace_detail_access_control(self):
        """Test namespace detail view respects access control."""
        # Anonymous user tries to access private namespace
        response = self.client.get(
            reverse('knowledge_demo:namespace_detail', args=['alice-space'])
        )
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)

        # Alice can access her own namespace
        self.client.login(username='alice', password='testpass123')
        response = self.client.get(
            reverse('knowledge_demo:namespace_detail', args=['alice-space'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['namespace'].slug, 'alice-space')

    def test_api_namespace_validation(self):
        """Test API endpoint validates namespace requests."""
        # Anonymous user requests unauthorized namespace
        response = self.client.get(
            reverse('knowledge_demo:api_namespace_access'),
            {'namespaces[]': ['alice-space', 'secret']}
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Access denied', data['error'])

        # Alice requests her allowed namespaces
        self.client.login(username='alice', password='testpass123')
        response = self.client.get(
            reverse('knowledge_demo:api_namespace_access'),
            {'namespaces[]': ['alice-space', 'default']}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['allowed_namespaces']), 2)

    def test_project_creation_in_namespace(self):
        """Test creating projects in allowed namespaces."""
        self.client.login(username='alice', password='testpass123')

        # Create project in Alice's namespace
        response = self.client.post(reverse('knowledge_demo:create_project'), {
            'name': 'Test Project',
            'description': 'Test description',
            'namespace': 'alice-space',
            'is_public': 'off'
        })
        self.assertEqual(response.status_code, 302)  # Redirect to project detail

        # Verify project was created
        project = Project.objects.get(name='Test Project')
        self.assertEqual(project.owner, self.alice)
        self.assertEqual(project.knowledge_base.namespace.slug, 'alice-space')

    def test_project_access_control(self):
        """Test project access respects privacy settings."""
        # Create a private project
        project = Project.objects.create(
            name='Private Project',
            description='Private',
            owner=self.alice,
            knowledge_base=self.alice_kb,
            is_public=False
        )

        # Anonymous user cannot access
        response = self.client.get(
            reverse('knowledge_demo:project_detail', args=[project.pk])
        )
        self.assertEqual(response.status_code, 302)  # Redirect

        # Bob cannot access Alice's private project
        self.client.login(username='bob', password='testpass123')
        response = self.client.get(
            reverse('knowledge_demo:project_detail', args=[project.pk])
        )
        self.assertEqual(response.status_code, 302)

        # Alice can access her own project
        self.client.login(username='alice', password='testpass123')
        response = self.client.get(
            reverse('knowledge_demo:project_detail', args=[project.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_namespace_security_middleware(self):
        """Test the security middleware functions correctly."""
        middleware = get_security_middleware()

        # Test anonymous access
        allowed = middleware.get_allowed_namespaces(user=None)
        slugs = [ns.slug for ns in allowed]
        self.assertIn('default', slugs)

        # Test authenticated user access
        allowed = middleware.get_allowed_namespaces(user=self.alice)
        slugs = [ns.slug for ns in allowed]
        self.assertIn('alice-space', slugs)

        # Test request validation
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            middleware.get_allowed_namespaces(
                user=self.alice,
                requested_namespaces=['alice-space', 'secret', 'unauthorized']
            )

    def test_knowledge_base_filtering(self):
        """Test knowledge bases are filtered by namespace access."""
        middleware = get_security_middleware()

        # Get all KBs and filter for anonymous user
        all_kbs = list(KnowledgeBase.objects.all())
        filtered = middleware.filter_knowledge_bases(
            user=None,
            knowledge_bases=all_kbs
        )

        # Anonymous should only see public KBs
        for kb in filtered:
            self.assertTrue(
                kb.is_public or kb.namespace.is_default,
                f"Anonymous user shouldn't see private KB: {kb.name}"
            )

        # Alice should see her own KBs
        filtered = middleware.filter_knowledge_bases(
            user=self.alice,
            knowledge_bases=all_kbs
        )
        alice_kb_ids = [kb.id for kb in filtered]
        self.assertIn(self.alice_kb.id, alice_kb_ids)


class DemoAppFunctionalTest(TestCase):
    """Functional tests for the demo app."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        # Run the setup_demo_data command
        from django.core.management import call_command
        call_command('setup_demo_data', '--reset')

    def test_demo_users_can_login(self):
        """Test that demo users can log in."""
        # Try logging in as Alice
        success = self.client.login(username='demo_alice', password='demo123')
        self.assertTrue(success)

        response = self.client.get(reverse('knowledge_demo:index'))
        self.assertContains(response, 'demo_alice')

    def test_demo_namespaces_exist(self):
        """Test that demo namespaces were created."""
        namespaces = Namespace.objects.all()
        namespace_slugs = [ns.slug for ns in namespaces]

        # Check expected namespaces exist
        self.assertIn('default', namespace_slugs)
        self.assertIn('engineering', namespace_slugs)
        self.assertIn('marketing', namespace_slugs)
        self.assertIn('research', namespace_slugs)

    def test_demo_projects_accessible(self):
        """Test that demo projects are accessible based on permissions."""
        # Get the public project
        public_project = Project.objects.get(name='Community Resources')

        # Anonymous user can access public project
        response = self.client.get(
            reverse('knowledge_demo:project_detail', args=[public_project.pk])
        )
        self.assertEqual(response.status_code, 200)

        # Get the engineering project (private)
        eng_project = Project.objects.get(name='Django-Ollama Integration')

        # Anonymous user cannot access private project
        response = self.client.get(
            reverse('knowledge_demo:project_detail', args=[eng_project.pk])
        )
        self.assertEqual(response.status_code, 302)

        # Alice (owner) can access
        self.client.login(username='demo_alice', password='demo123')
        response = self.client.get(
            reverse('knowledge_demo:project_detail', args=[eng_project.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_security_demo_page(self):
        """Test the security demo page works."""
        # Anonymous access
        response = self.client.get(reverse('knowledge_demo:security_demo'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Security Demo')

        # Authenticated access shows more info
        self.client.login(username='demo_alice', password='demo123')
        response = self.client.get(reverse('knowledge_demo:security_demo'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'demo_alice')
        self.assertContains(response, 'Accessible Namespaces')