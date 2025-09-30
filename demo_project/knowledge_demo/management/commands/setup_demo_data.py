"""
Management command to set up demo data for namespace demonstration.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from django_ollama.models import Namespace, KnowledgeBase
from django_ollama.namespace_manager import NamespaceManager, KnowledgeBaseManager, initialize_namespaces
from knowledge_demo.models import Project, Article, Document


class Command(BaseCommand):
    help = 'Sets up demo data showcasing namespace features'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all demo data before creating new data',
        )

    def handle(self, *args, **options):
        self.stdout.write("Setting up demo data for django-ollama namespace features...")

        if options['reset']:
            self.stdout.write("Resetting existing data...")
            Project.objects.all().delete()
            Article.objects.all().delete()
            Document.objects.all().delete()
            KnowledgeBase.objects.all().delete()
            Namespace.objects.all().delete()
            User.objects.filter(username__startswith='demo_').delete()

        with transaction.atomic():
            # Initialize default namespaces
            self.stdout.write("Initializing namespaces...")
            default_ns = initialize_namespaces()

            # Create demo users
            self.stdout.write("Creating demo users...")
            alice = User.objects.create_user(
                username='demo_alice',
                email='alice@example.com',
                password='demo123',
                first_name='Alice',
                last_name='Developer'
            )

            bob = User.objects.create_user(
                username='demo_bob',
                email='bob@example.com',
                password='demo123',
                first_name='Bob',
                last_name='Manager'
            )

            charlie = User.objects.create_user(
                username='demo_charlie',
                email='charlie@example.com',
                password='demo123',
                first_name='Charlie',
                last_name='Analyst'
            )

            admin = User.objects.create_superuser(
                username='demo_admin',
                email='admin@example.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )

            # Create team/organization namespaces
            self.stdout.write("Creating team namespaces...")

            engineering_ns = Namespace.objects.create(
                name="Engineering Team",
                slug="engineering",
                description="Engineering team's private namespace",
                owner=alice
            )

            marketing_ns = Namespace.objects.create(
                name="Marketing Team",
                slug="marketing",
                description="Marketing team's namespace with public content",
                owner=bob
            )

            research_ns = Namespace.objects.create(
                name="Research Division",
                slug="research",
                description="Research team's secure namespace",
                owner=charlie
            )

            # Create knowledge bases in different namespaces
            self.stdout.write("Creating knowledge bases...")

            # Engineering KBs (private)
            eng_docs_kb = KnowledgeBaseManager.create_knowledge_base(
                name="Engineering Documentation",
                namespace=engineering_ns,
                description="Internal engineering documentation",
                owner=alice,
                is_public=False,
                tags=['engineering', 'documentation', 'internal']
            )

            eng_api_kb = KnowledgeBaseManager.create_knowledge_base(
                name="API Reference",
                namespace=engineering_ns,
                description="Internal API documentation",
                owner=alice,
                is_public=False,
                tags=['api', 'reference', 'internal']
            )

            # Marketing KBs (mixed public/private)
            marketing_public_kb = KnowledgeBaseManager.create_knowledge_base(
                name="Marketing Materials",
                namespace=marketing_ns,
                description="Public marketing content",
                owner=bob,
                is_public=True,
                tags=['marketing', 'public', 'content']
            )

            marketing_private_kb = KnowledgeBaseManager.create_knowledge_base(
                name="Marketing Strategy",
                namespace=marketing_ns,
                description="Private marketing strategies",
                owner=bob,
                is_public=False,
                tags=['marketing', 'strategy', 'private']
            )

            # Research KBs (highly restricted)
            research_data_kb = KnowledgeBaseManager.create_knowledge_base(
                name="Research Data",
                namespace=research_ns,
                description="Confidential research data",
                owner=charlie,
                is_public=False,
                tags=['research', 'confidential', 'data']
            )

            # Default namespace KBs (accessible to all)
            public_docs_kb = KnowledgeBaseManager.create_knowledge_base(
                name="Public Documentation",
                namespace=default_ns,
                description="Public documentation available to everyone",
                owner=admin,
                is_public=True,
                tags=['public', 'documentation', 'help']
            )

            # Create projects
            self.stdout.write("Creating demo projects...")

            # Engineering project
            eng_project = Project.objects.create(
                name="Django-Ollama Integration",
                description="Building namespace-aware Ollama integration for Django",
                owner=alice,
                knowledge_base=eng_docs_kb,
                is_public=False
            )
            eng_project.team_members.add(charlie)  # Add Charlie to team

            # Marketing project
            marketing_project = Project.objects.create(
                name="AI Product Launch",
                description="Marketing campaign for AI product launch",
                owner=bob,
                knowledge_base=marketing_public_kb,
                is_public=True
            )

            # Research project
            research_project = Project.objects.create(
                name="LLM Performance Study",
                description="Studying performance characteristics of various LLMs",
                owner=charlie,
                knowledge_base=research_data_kb,
                is_public=False
            )

            # Public project in default namespace
            public_project = Project.objects.create(
                name="Community Resources",
                description="Community-contributed resources and examples",
                owner=admin,
                knowledge_base=public_docs_kb,
                is_public=True
            )

            # Add sample articles
            self.stdout.write("Creating sample articles...")

            eng_project.add_article(
                title="Namespace Architecture Design",
                content="This document describes the namespace architecture...\n\n"
                       "Key features:\n"
                       "- Multi-tenant isolation\n"
                       "- Server-side security enforcement\n"
                       "- Flexible access control policies",
                author=alice
            )

            eng_project.add_article(
                title="Security Implementation Guide",
                content="Guide to implementing security middleware...\n\n"
                       "The security system uses a middleware pattern similar to Django's auth system.",
                author=alice
            )

            marketing_project.add_article(
                title="AI Features Overview",
                content="Our AI platform provides cutting-edge features...\n\n"
                       "- Natural language processing\n"
                       "- Context-aware responses\n"
                       "- Multi-modal capabilities",
                author=bob
            )

            research_project.add_article(
                title="Performance Benchmarks",
                content="Benchmark results for various models...\n\n"
                       "Testing methodology and results are confidential.",
                author=charlie
            )

            public_project.add_article(
                title="Getting Started Guide",
                content="Welcome to django-ollama!\n\n"
                       "This guide will help you get started with namespace features.",
                author=admin
            )

            # Print summary
            self.stdout.write(self.style.SUCCESS("\n✅ Demo data setup complete!"))
            self.stdout.write("\nCreated:")
            self.stdout.write(f"  - {User.objects.filter(username__startswith='demo_').count()} demo users")
            self.stdout.write(f"  - {Namespace.objects.count()} namespaces")
            self.stdout.write(f"  - {KnowledgeBase.objects.count()} knowledge bases")
            self.stdout.write(f"  - {Project.objects.count()} projects")
            self.stdout.write(f"  - {Article.objects.count()} articles")

            self.stdout.write("\n📝 Demo Users:")
            self.stdout.write("  - demo_alice / demo123 (Engineering team owner)")
            self.stdout.write("  - demo_bob / demo123 (Marketing team owner)")
            self.stdout.write("  - demo_charlie / demo123 (Research team owner)")
            self.stdout.write("  - demo_admin / admin123 (Superuser)")

            self.stdout.write("\n🏢 Namespaces:")
            for ns in Namespace.objects.all():
                access = "PUBLIC" if ns.is_default or ns.knowledge_bases.filter(is_public=True).exists() else "PRIVATE"
                self.stdout.write(f"  - {ns.name} ({ns.slug}) - {access}")

            self.stdout.write("\n🚀 Ready to demo namespace features!")