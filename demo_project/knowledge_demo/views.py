"""
Demo views showcasing namespace features and security.

These views follow the Service Layer pattern and Dependency Injection
principles for improved testability and maintainability.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods

from django_ollama.models import Namespace, KnowledgeBase
from django_ollama.namespace_security import get_security_middleware
from .models import Project
from .services import NamespaceService, ProjectService, HomeService


def _get_security_middleware(request):
    """
    Get security middleware from request or create new instance.

    Uses dependency injection when available (from SecurityMiddleware),
    otherwise creates a new instance.
    """
    if hasattr(request, 'security'):
        return request.security
    return get_security_middleware()


def index(request):
    """
    Home page showing available namespaces and knowledge bases.

    Now uses HomeService for business logic separation.
    """
    # Get security middleware via dependency injection
    security = _get_security_middleware(request)

    # Use service layer for business logic
    service = HomeService(security)
    user = request.user if request.user.is_authenticated else None
    context = service.get_home_context(user, request)

    return render(request, 'knowledge_demo/index.html', context)


def namespace_detail(request, slug):
    """
    Display details about a specific namespace and its knowledge bases.

    Now uses NamespaceService for business logic separation.
    """
    namespace = get_object_or_404(Namespace, slug=slug, is_active=True)

    # Get security middleware via dependency injection
    security = _get_security_middleware(request)
    service = NamespaceService(security)

    try:
        # Use service to get context data (handles access control)
        user = request.user if request.user.is_authenticated else None
        ns_context = service.get_namespace_context(namespace, user, request)

        # Convert dataclass to dict for template
        context = {
            'namespace': ns_context.namespace,
            'knowledge_bases': ns_context.knowledge_bases,
            'projects': ns_context.projects,
            'stats': ns_context.stats,
            'can_modify': ns_context.can_modify
        }

        return render(request, 'knowledge_demo/namespace_detail.html', context)

    except PermissionDenied:
        messages.error(request, f"You don't have access to the '{namespace.name}' namespace.")
        return redirect('knowledge_demo:index')


@login_required
def create_project(request):
    """
    Create a new project with its own knowledge base in a namespace.

    Now uses ProjectService and NamespaceService for business logic.
    """
    # Get services via dependency injection
    security = _get_security_middleware(request)
    project_service = ProjectService(security)
    namespace_service = NamespaceService(security)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        namespace_slug = request.POST.get('namespace')
        is_public = request.POST.get('is_public') == 'on'

        # Get namespace
        namespace = get_object_or_404(Namespace, slug=namespace_slug)

        try:
            # Use service to create project (handles permissions)
            project = project_service.create_project(
                name=name,
                description=description,
                namespace=namespace,
                owner=request.user,
                is_public=is_public
            )

            messages.success(
                request,
                f"Project '{name}' created successfully in namespace '{namespace.name}'!"
            )
            return redirect('knowledge_demo:project_detail', pk=project.pk)

        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('knowledge_demo:create_project')

    # GET request - show form
    creatable_namespaces = namespace_service.get_creatable_namespaces(
        user=request.user,
        request=request
    )

    context = {'namespaces': creatable_namespaces}
    return render(request, 'knowledge_demo/create_project.html', context)


def project_detail(request, pk):
    """
    Display project details with its articles and documents.

    Now uses ProjectService for business logic separation.
    """
    project = get_object_or_404(Project, pk=pk)

    # Get service via dependency injection
    security = _get_security_middleware(request)
    service = ProjectService(security)

    try:
        # Use service to get context (handles access control)
        user = request.user if request.user.is_authenticated else None
        proj_context = service.get_project_context(project, user)

        # Convert dataclass to dict for template
        context = {
            'project': proj_context.project,
            'articles': proj_context.articles,
            'documents': proj_context.documents,
            'is_owner': proj_context.is_owner,
            'is_member': proj_context.is_member,
        }

        return render(request, 'knowledge_demo/project_detail.html', context)

    except PermissionDenied:
        if not user:
            messages.error(request, "This project is private. Please log in to view it.")
        else:
            messages.error(request, "You don't have access to this private project.")
        return redirect('knowledge_demo:index')


@require_http_methods(["GET"])
def api_namespace_access(request):
    """
    API endpoint demonstrating server-side namespace access control.

    This shows how client requests are validated server-side using
    the security middleware.
    """
    # Get requested namespaces from query params
    requested = request.GET.getlist('namespaces[]')

    # Get security via dependency injection
    security = _get_security_middleware(request)
    user = request.user if request.user.is_authenticated else None

    try:
        # Server validates the client request
        if requested:
            allowed = security.get_allowed_namespaces(
                user=user,
                requested_namespaces=requested,
                request=request
            )
        else:
            # No specific request - return all allowed
            allowed = security.get_allowed_namespaces(user=user, request=request)

        # Return allowed namespaces
        data = {
            'allowed_namespaces': [
                {
                    'slug': ns.slug,
                    'name': ns.name,
                    'is_default': ns.is_default,
                    'kb_count': ns.knowledge_base_count,
                }
                for ns in allowed
            ],
            'requested': requested,
            'user': user.username if user else 'anonymous',
        }

        return JsonResponse(data)

    except PermissionDenied as e:
        # Client requested unauthorized namespaces
        return JsonResponse({
            'error': str(e),
            'requested': requested,
            'user': user.username if user else 'anonymous',
        }, status=403)


def security_demo(request):
    """
    Interactive demo showing namespace security in action.

    Uses dependency injection for security middleware.
    """
    user = request.user if request.user.is_authenticated else None

    context = {
        'user': user,
        'is_authenticated': request.user.is_authenticated,
    }

    if user:
        # Get security via dependency injection
        security = _get_security_middleware(request)

        # Show what namespaces the user can access
        context['allowed_namespaces'] = security.get_allowed_namespaces(
            user=user,
            request=request
        )

        # Show owned namespaces
        context['owned_namespaces'] = Namespace.objects.filter(owner=user)

        # Show if user is superuser
        context['is_superuser'] = user.is_superuser

    return render(request, 'knowledge_demo/security_demo.html', context)