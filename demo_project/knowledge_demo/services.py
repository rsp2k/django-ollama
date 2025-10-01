"""
Business logic services for knowledge demo application.

This module implements the Service Layer pattern, extracting business logic
from views to improve testability and follow Single Responsibility Principle.
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
from django.db.models import Count, Q, QuerySet
from django.core.exceptions import PermissionDenied

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http import HttpRequest
    from django_ollama.models import Namespace, KnowledgeBase
    from .models import Project, Article, Document

from django_ollama.models import Namespace, KnowledgeBase
from django_ollama.namespace_security import NamespaceSecurityMiddleware
from django_ollama.namespace_manager import KnowledgeBaseManager
from .models import Project, Article, Document


@dataclass
class NamespaceContext:
    """Data container for namespace view context."""
    namespace: 'Namespace'
    knowledge_bases: QuerySet
    projects: QuerySet
    stats: Dict[str, int]
    can_modify: bool


@dataclass
class ProjectContext:
    """Data container for project view context."""
    project: 'Project'
    articles: QuerySet
    documents: QuerySet
    is_owner: bool
    is_member: bool
    team_member_count: int


class NamespaceService:
    """
    Service for namespace-related business logic.

    Encapsulates namespace operations, access control, and data preparation.
    """

    def __init__(self, security_middleware: NamespaceSecurityMiddleware):
        """
        Initialize service with security middleware.

        Args:
            security_middleware: Security middleware for access control
        """
        self.security = security_middleware

    def get_accessible_namespaces(
        self,
        user: Optional['User'],
        request: Optional['HttpRequest'] = None
    ) -> List['Namespace']:
        """
        Get namespaces accessible to a user.

        Args:
            user: The user requesting access
            request: Optional HTTP request context

        Returns:
            List of accessible namespaces
        """
        return self.security.get_allowed_namespaces(user=user, request=request)

    def get_namespace_context(
        self,
        namespace: 'Namespace',
        user: Optional['User'],
        request: Optional['HttpRequest'] = None
    ) -> NamespaceContext:
        """
        Prepare complete context data for namespace detail view.

        Args:
            namespace: The namespace to prepare context for
            user: The current user
            request: Optional HTTP request context

        Returns:
            NamespaceContext with all required data

        Raises:
            PermissionDenied: If user doesn't have access
        """
        # Check access permission
        if not self.security.check_namespace_access(
            user=user,
            namespace=namespace,
            request=request,
            raise_exception=True
        ):
            raise PermissionDenied(f"Access denied to namespace '{namespace.slug}'")

        # Get accessible knowledge bases
        knowledge_bases = self._get_accessible_knowledge_bases(namespace, user)

        # Get projects in namespace
        projects = self._get_namespace_projects(namespace)

        # Calculate statistics
        stats = self._calculate_namespace_stats(namespace, knowledge_bases)

        # Check modification permission
        can_modify = self.security.check_namespace_modification(
            user=user,
            namespace=namespace,
            request=request,
            raise_exception=False
        )

        return NamespaceContext(
            namespace=namespace,
            knowledge_bases=knowledge_bases[:20],  # Limit results
            projects=projects[:10],
            stats=stats,
            can_modify=can_modify
        )

    def _get_accessible_knowledge_bases(
        self,
        namespace: 'Namespace',
        user: Optional['User']
    ) -> QuerySet:
        """Get knowledge bases in namespace filtered by user access."""
        knowledge_bases = KnowledgeBase.objects.filter(
            namespace=namespace,
            is_active=True
        )

        # Filter based on user permissions
        if not user or not user.is_authenticated:
            knowledge_bases = knowledge_bases.filter(is_public=True)
        elif not user.is_superuser and namespace.owner != user:
            knowledge_bases = knowledge_bases.filter(
                Q(is_public=True) | Q(owner=user)
            )

        return knowledge_bases

    def _get_namespace_projects(self, namespace: 'Namespace') -> QuerySet:
        """Get projects in namespace."""
        return Project.objects.filter(
            knowledge_base__namespace=namespace
        ).select_related('owner', 'knowledge_base')

    def _calculate_namespace_stats(
        self,
        namespace: 'Namespace',
        knowledge_bases: QuerySet
    ) -> Dict[str, int]:
        """Calculate statistics for namespace."""
        return {
            'total_kbs': knowledge_bases.count(),
            'public_kbs': knowledge_bases.filter(is_public=True).count(),
            'total_projects': Project.objects.filter(
                knowledge_base__namespace=namespace
            ).count(),
            'total_articles': Article.objects.filter(
                knowledge_base__namespace=namespace
            ).count(),
            'total_documents': Document.objects.filter(
                knowledge_base__namespace=namespace
            ).count(),
        }

    def get_creatable_namespaces(
        self,
        user: 'User',
        request: Optional['HttpRequest'] = None
    ) -> List['Namespace']:
        """
        Get namespaces where user can create projects.

        Args:
            user: The user to check
            request: Optional HTTP request context

        Returns:
            List of namespaces where user can create
        """
        allowed = self.get_accessible_namespaces(user, request)

        # Filter to namespaces where user can create
        return [
            ns for ns in allowed
            if ns.is_default or ns.owner == user or user.is_superuser
        ]


class ProjectService:
    """
    Service for project-related business logic.

    Handles project creation, access control, and data preparation.
    """

    def __init__(self, security_middleware: NamespaceSecurityMiddleware):
        """
        Initialize service with security middleware.

        Args:
            security_middleware: Security middleware for access control
        """
        self.security = security_middleware

    def create_project(
        self,
        name: str,
        description: str,
        namespace: 'Namespace',
        owner: 'User',
        is_public: bool = False
    ) -> 'Project':
        """
        Create a new project with knowledge base.

        Args:
            name: Project name
            description: Project description
            namespace: Target namespace
            owner: Project owner
            is_public: Whether project is public

        Returns:
            Created Project instance

        Raises:
            PermissionDenied: If user can't create in namespace
        """
        # Check creation permissions
        if not owner.is_superuser and namespace.owner != owner:
            if not namespace.is_default:
                raise PermissionDenied(
                    "You can only create projects in your own namespaces "
                    "or the default namespace."
                )

        # Create knowledge base for the project
        kb = KnowledgeBaseManager.create_knowledge_base(
            name=f"Project: {name}",
            namespace=namespace,
            description=description,
            owner=owner,
            is_public=is_public,
            tags=['project', 'demo']
        )

        # Create the project
        project = Project.objects.create(
            name=name,
            description=description,
            owner=owner,
            knowledge_base=kb,
            is_public=is_public
        )

        return project

    def get_project_context(
        self,
        project: 'Project',
        user: Optional['User']
    ) -> ProjectContext:
        """
        Prepare complete context data for project detail view.

        Args:
            project: The project to prepare context for
            user: The current user

        Returns:
            ProjectContext with all required data

        Raises:
            PermissionDenied: If user doesn't have access
        """
        # Check access
        if not self._can_access_project(project, user):
            raise PermissionDenied("You don't have access to this project")

        # Get related content
        articles = project.knowledge_base.demo_articles.all()[:10]
        documents = project.knowledge_base.demo_documents.all()[:10]

        # Check user relationship to project
        is_owner = user == project.owner if user and user.is_authenticated else False
        is_member = (
            user in project.team_members.all()
            if user and user.is_authenticated
            else False
        )

        return ProjectContext(
            project=project,
            articles=articles,
            documents=documents,
            is_owner=is_owner,
            is_member=is_member,
            team_member_count=project.team_members.count()
        )

    def _can_access_project(
        self,
        project: 'Project',
        user: Optional['User']
    ) -> bool:
        """Check if user can access project."""
        # Public projects are accessible to all
        if project.is_public:
            return True

        # Anonymous users can't access private projects
        if not user or not user.is_authenticated:
            return False

        # Owner, team members, and superusers can access
        if user == project.owner or user.is_superuser:
            return True

        if user in project.team_members.all():
            return True

        return False


class HomeService:
    """
    Service for home page business logic.

    Aggregates data from multiple sources for the home page.
    """

    def __init__(self, security_middleware: NamespaceSecurityMiddleware):
        """
        Initialize service with security middleware.

        Args:
            security_middleware: Security middleware for access control
        """
        self.security = security_middleware

    def get_home_context(
        self,
        user: Optional['User'],
        request: Optional['HttpRequest'] = None
    ) -> Dict[str, Any]:
        """
        Prepare complete context for home page.

        Args:
            user: The current user
            request: Optional HTTP request context

        Returns:
            Dictionary with home page data
        """
        # Get accessible namespaces
        allowed_namespaces = self.security.get_allowed_namespaces(
            user=user,
            request=request
        )

        # Get public knowledge bases
        public_kbs = KnowledgeBase.objects.filter(
            is_public=True,
            is_active=True,
            namespace__in=allowed_namespaces
        ).select_related('namespace', 'owner')[:10]

        # Get user's projects if authenticated
        user_projects = []
        if user and user.is_authenticated:
            user_projects = Project.objects.filter(
                owner=user
            ).select_related('knowledge_base__namespace')[:5]

        return {
            'namespaces': allowed_namespaces,
            'public_knowledge_bases': public_kbs,
            'user_projects': user_projects,
            'namespace_count': len(allowed_namespaces),
        }
