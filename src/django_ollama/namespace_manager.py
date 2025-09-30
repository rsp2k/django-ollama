"""
Namespace management utilities for django-ollama.

This module provides high-level functions for managing namespaces
and knowledge bases with proper isolation and organization.
"""

from typing import Dict, List, Optional, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from .models import Namespace, KnowledgeBase


class NamespaceManager:
    """High-level namespace management utilities."""

    @staticmethod
    def ensure_default_namespace() -> Namespace:
        """
        Ensure the default namespace exists.

        Returns:
            The default namespace instance
        """
        return Namespace.objects.get_default()

    @staticmethod
    def create_namespace(
        name: str,
        description: str = "",
        owner: Optional[User] = None,
        metadata: Optional[Dict[str, Any]] = None,
        make_default: bool = False
    ) -> Namespace:
        """
        Create a new namespace.

        Args:
            name: Human-readable name for the namespace
            description: Optional description
            owner: Optional user who owns the namespace
            metadata: Optional metadata dictionary
            make_default: Whether to make this the default namespace

        Returns:
            The created namespace instance

        Raises:
            ValidationError: If namespace with same slug already exists
        """
        from django.utils.text import slugify

        slug = slugify(name)

        # Check if namespace with this slug already exists
        if Namespace.objects.filter(slug=slug).exists():
            raise ValidationError(f"Namespace with slug '{slug}' already exists")

        with transaction.atomic():
            namespace = Namespace.objects.create(
                name=name,
                slug=slug,
                description=description,
                owner=owner,
                metadata=metadata or {},
                is_default=make_default
            )

        return namespace

    @staticmethod
    def list_namespaces(
        active_only: bool = True,
        owner: Optional[User] = None
    ) -> List[Namespace]:
        """
        List namespaces with optional filtering.

        Args:
            active_only: Only return active namespaces
            owner: Filter by owner

        Returns:
            List of namespace instances
        """
        queryset = Namespace.objects.all()

        if active_only:
            queryset = queryset.filter(is_active=True)

        if owner:
            queryset = queryset.filter(owner=owner)

        return list(queryset)

    @staticmethod
    def get_namespace_by_slug(slug: str) -> Optional[Namespace]:
        """
        Get a namespace by its slug.

        Args:
            slug: The namespace slug

        Returns:
            Namespace instance or None if not found
        """
        try:
            return Namespace.objects.get(slug=slug, is_active=True)
        except Namespace.DoesNotExist:
            return None

    @staticmethod
    def delete_namespace(
        namespace: Namespace,
        force: bool = False
    ) -> bool:
        """
        Delete a namespace.

        Args:
            namespace: The namespace to delete
            force: Force deletion even if not empty

        Returns:
            True if deleted, False otherwise

        Raises:
            ValidationError: If trying to delete default or non-empty namespace
        """
        if namespace.is_default:
            raise ValidationError("Cannot delete the default namespace")

        if not force and namespace.knowledge_base_count > 0:
            raise ValidationError(
                f"Cannot delete namespace '{namespace.name}' - contains {namespace.knowledge_base_count} knowledge bases"
            )

        namespace.delete()
        return True

    @staticmethod
    def migrate_knowledge_base(
        knowledge_base: KnowledgeBase,
        target_namespace: Namespace,
        keep_slug: bool = True
    ) -> KnowledgeBase:
        """
        Migrate a knowledge base to a different namespace.

        Args:
            knowledge_base: The knowledge base to migrate
            target_namespace: The target namespace
            keep_slug: Whether to keep the same slug (may cause conflicts)

        Returns:
            The migrated knowledge base

        Raises:
            ValidationError: If slug conflict occurs
        """
        from django.utils.text import slugify

        with transaction.atomic():
            # Check for slug conflicts
            if keep_slug:
                if KnowledgeBase.objects.filter(
                    namespace=target_namespace,
                    slug=knowledge_base.slug
                ).exists():
                    raise ValidationError(
                        f"Knowledge base with slug '{knowledge_base.slug}' already exists in namespace '{target_namespace.name}'"
                    )
            else:
                # Generate new slug if needed
                base_slug = knowledge_base.slug
                counter = 1
                new_slug = base_slug

                while KnowledgeBase.objects.filter(
                    namespace=target_namespace,
                    slug=new_slug
                ).exists():
                    new_slug = f"{base_slug}-{counter}"
                    counter += 1

                knowledge_base.slug = new_slug

            # Update namespace
            knowledge_base.namespace = target_namespace
            knowledge_base.save()

        return knowledge_base


class KnowledgeBaseManager:
    """High-level knowledge base management utilities."""

    @staticmethod
    def create_knowledge_base(
        name: str,
        namespace: Optional[Namespace] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
        settings: Optional[Dict[str, Any]] = None,
        owner: Optional[User] = None,
        is_public: bool = False
    ) -> KnowledgeBase:
        """
        Create a new knowledge base.

        Args:
            name: Name of the knowledge base
            namespace: Namespace to create in (defaults to default namespace)
            description: Optional description
            tags: Optional list of tags
            settings: Optional settings dictionary
            owner: Optional owner user
            is_public: Whether the knowledge base is public

        Returns:
            The created knowledge base instance
        """
        if namespace is None:
            namespace = Namespace.objects.get_default()

        knowledge_base = KnowledgeBase.objects.create(
            namespace=namespace,
            name=name,
            description=description,
            tags=tags or [],
            settings=settings or {},
            owner=owner,
            is_public=is_public
        )

        return knowledge_base

    @staticmethod
    def list_knowledge_bases(
        namespace: Optional[Namespace] = None,
        owner: Optional[User] = None,
        active_only: bool = True,
        public_only: bool = False
    ) -> List[KnowledgeBase]:
        """
        List knowledge bases with filtering.

        Args:
            namespace: Filter by namespace
            owner: Filter by owner
            active_only: Only return active knowledge bases
            public_only: Only return public knowledge bases

        Returns:
            List of knowledge base instances
        """
        queryset = KnowledgeBase.objects.all()

        if namespace:
            queryset = queryset.filter(namespace=namespace)

        if owner:
            queryset = queryset.filter(owner=owner)

        if active_only:
            queryset = queryset.filter(is_active=True)

        if public_only:
            queryset = queryset.filter(is_public=True)

        return list(queryset.select_related('namespace'))

    @staticmethod
    def get_knowledge_base(
        namespace_slug: str,
        kb_slug: str
    ) -> Optional[KnowledgeBase]:
        """
        Get a knowledge base by namespace and slug.

        Args:
            namespace_slug: The namespace slug
            kb_slug: The knowledge base slug

        Returns:
            Knowledge base instance or None if not found
        """
        try:
            return KnowledgeBase.objects.select_related('namespace').get(
                namespace__slug=namespace_slug,
                slug=kb_slug,
                is_active=True
            )
        except KnowledgeBase.DoesNotExist:
            return None

    @staticmethod
    def search_knowledge_bases(
        query: str,
        namespace: Optional[Namespace] = None,
        limit: int = 10
    ) -> List[KnowledgeBase]:
        """
        Search knowledge bases by name or description.

        Args:
            query: Search query
            namespace: Optional namespace filter
            limit: Maximum results to return

        Returns:
            List of matching knowledge base instances
        """
        from django.db.models import Q

        queryset = KnowledgeBase.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__contains=query)
        ).filter(is_active=True)

        if namespace:
            queryset = queryset.filter(namespace=namespace)

        return list(queryset.select_related('namespace')[:limit])

    @staticmethod
    def clone_knowledge_base(
        source_kb: KnowledgeBase,
        target_namespace: Optional[Namespace] = None,
        new_name: Optional[str] = None,
        include_content: bool = False,
        include_media: bool = False
    ) -> KnowledgeBase:
        """
        Clone a knowledge base.

        Args:
            source_kb: The source knowledge base to clone
            target_namespace: Target namespace (defaults to same namespace)
            new_name: New name for the clone
            include_content: Whether to clone content items
            include_media: Whether to clone media items

        Returns:
            The cloned knowledge base
        """
        if target_namespace is None:
            target_namespace = source_kb.namespace

        with transaction.atomic():
            # Clone the knowledge base
            clone = source_kb.clone_to_namespace(
                target_namespace,
                new_name
            )

            # Clone content if requested
            if include_content:
                for content_item in source_kb.content_items.all():
                    content_item.pk = None  # Create new instance
                    content_item.knowledge_base = clone
                    content_item.save()

            # Clone media if requested
            if include_media:
                for media_item in source_kb.media_items.all():
                    media_item.pk = None  # Create new instance
                    media_item.knowledge_base = clone
                    media_item.save()

        return clone


def initialize_namespaces():
    """
    Initialize the namespace system with default namespace.

    This should be called during application setup or migration.
    """
    default_namespace = NamespaceManager.ensure_default_namespace()

    # Create additional default namespaces if needed
    default_namespaces = [
        {
            "name": "Development",
            "slug": "dev",
            "description": "Development and testing knowledge bases"
        },
        {
            "name": "Production",
            "slug": "prod",
            "description": "Production knowledge bases"
        },
        {
            "name": "Personal",
            "slug": "personal",
            "description": "Personal knowledge bases"
        }
    ]

    for ns_data in default_namespaces:
        if not Namespace.objects.filter(slug=ns_data["slug"]).exists():
            Namespace.objects.create(**ns_data)

    return default_namespace