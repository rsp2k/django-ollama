"""
Demo views showcasing namespace features and security.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q

from django_ollama.models import Namespace, KnowledgeBase
from django_ollama.namespace_manager import NamespaceManager, KnowledgeBaseManager
from django_ollama.namespace_security import get_security_middleware
from .models import Project, Article, Document


def index(request):
    """
    Home page showing available namespaces and knowledge bases.
    """
    middleware = get_security_middleware()

    # Get namespaces accessible to current user
    allowed_namespaces = middleware.get_allowed_namespaces(
        user=request.user if request.user.is_authenticated else None,
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
    if request.user.is_authenticated:
        user_projects = Project.objects.filter(
            owner=request.user
        ).select_related('knowledge_base__namespace')[:5]

    context = {
        'namespaces': allowed_namespaces,
        'public_knowledge_bases': public_kbs,
        'user_projects': user_projects,
        'namespace_count': len(allowed_namespaces),
    }

    return render(request, 'knowledge_demo/index.html', context)


def namespace_detail(request, slug):
    """
    Display details about a specific namespace and its knowledge bases.
    """
    namespace = get_object_or_404(Namespace, slug=slug, is_active=True)

    # Check access permission
    middleware = get_security_middleware()
    if not middleware.check_namespace_access(
        user=request.user if request.user.is_authenticated else None,
        namespace=namespace,
        request=request,
        raise_exception=False
    ):
        messages.error(request, f"You don't have access to the '{namespace.name}' namespace.")
        return redirect('knowledge_demo:index')

    # Get knowledge bases in this namespace (filtered by access)
    knowledge_bases = KnowledgeBase.objects.filter(
        namespace=namespace,
        is_active=True
    )

    # Further filter based on user access
    if not request.user.is_authenticated:
        knowledge_bases = knowledge_bases.filter(is_public=True)
    elif not request.user.is_superuser and namespace.owner != request.user:
        knowledge_bases = knowledge_bases.filter(
            Q(is_public=True) | Q(owner=request.user)
        )

    # Get projects in this namespace
    projects = Project.objects.filter(
        knowledge_base__namespace=namespace
    ).select_related('owner', 'knowledge_base')

    # Get statistics
    stats = {
        'total_kbs': knowledge_bases.count(),
        'public_kbs': knowledge_bases.filter(is_public=True).count(),
        'total_projects': projects.count(),
        'total_articles': Article.objects.filter(
            knowledge_base__namespace=namespace
        ).count(),
        'total_documents': Document.objects.filter(
            knowledge_base__namespace=namespace
        ).count(),
    }

    context = {
        'namespace': namespace,
        'knowledge_bases': knowledge_bases[:20],
        'projects': projects[:10],
        'stats': stats,
        'can_modify': middleware.check_namespace_modification(
            user=request.user if request.user.is_authenticated else None,
            namespace=namespace,
            request=request,
            raise_exception=False
        )
    }

    return render(request, 'knowledge_demo/namespace_detail.html', context)


@login_required
def create_project(request):
    """
    Create a new project with its own knowledge base in a namespace.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        namespace_slug = request.POST.get('namespace')
        is_public = request.POST.get('is_public') == 'on'

        # Get namespace and check permissions
        namespace = get_object_or_404(Namespace, slug=namespace_slug)
        middleware = get_security_middleware()

        # Check if user can create in this namespace
        if not request.user.is_superuser and namespace.owner != request.user:
            if not namespace.is_default:
                messages.error(request, "You can only create projects in your own namespaces or the default namespace.")
                return redirect('knowledge_demo:create_project')

        # Create knowledge base for the project
        kb = KnowledgeBaseManager.create_knowledge_base(
            name=f"Project: {name}",
            namespace=namespace,
            description=description,
            owner=request.user,
            is_public=is_public,
            tags=['project', 'demo']
        )

        # Create the project
        project = Project.objects.create(
            name=name,
            description=description,
            owner=request.user,
            knowledge_base=kb,
            is_public=is_public
        )

        messages.success(request, f"Project '{name}' created successfully in namespace '{namespace.name}'!")
        return redirect('knowledge_demo:project_detail', pk=project.pk)

    # GET request - show form
    middleware = get_security_middleware()
    allowed_namespaces = middleware.get_allowed_namespaces(
        user=request.user,
        request=request
    )

    # Filter to namespaces where user can create
    creatable_namespaces = [
        ns for ns in allowed_namespaces
        if ns.is_default or ns.owner == request.user or request.user.is_superuser
    ]

    context = {
        'namespaces': creatable_namespaces
    }

    return render(request, 'knowledge_demo/create_project.html', context)


def project_detail(request, pk):
    """
    Display project details with its articles and documents.
    """
    project = get_object_or_404(Project, pk=pk)

    # Check access
    if not project.is_public and not request.user.is_authenticated:
        messages.error(request, "This project is private. Please log in to view it.")
        return redirect('knowledge_demo:index')

    if not project.is_public and request.user != project.owner:
        if request.user not in project.team_members.all() and not request.user.is_superuser:
            messages.error(request, "You don't have access to this private project.")
            return redirect('knowledge_demo:index')

    # Get related content
    articles = project.knowledge_base.demo_articles.all()[:10]
    documents = project.knowledge_base.demo_documents.all()[:10]

    context = {
        'project': project,
        'articles': articles,
        'documents': documents,
        'is_owner': request.user == project.owner if request.user.is_authenticated else False,
        'is_member': request.user in project.team_members.all() if request.user.is_authenticated else False,
    }

    return render(request, 'knowledge_demo/project_detail.html', context)


@require_http_methods(["GET"])
def api_namespace_access(request):
    """
    API endpoint demonstrating server-side namespace access control.
    This shows how client requests are validated server-side.
    """
    # Get requested namespaces from query params
    requested = request.GET.getlist('namespaces[]')

    middleware = get_security_middleware()

    try:
        # Server validates the client request
        if requested:
            allowed = middleware.get_allowed_namespaces(
                user=request.user if request.user.is_authenticated else None,
                requested_namespaces=requested,
                request=request
            )
        else:
            # No specific request - return all allowed
            allowed = middleware.get_allowed_namespaces(
                user=request.user if request.user.is_authenticated else None,
                request=request
            )

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
            'user': request.user.username if request.user.is_authenticated else 'anonymous',
        }

        return JsonResponse(data)

    except PermissionDenied as e:
        # Client requested unauthorized namespaces
        return JsonResponse({
            'error': str(e),
            'requested': requested,
            'user': request.user.username if request.user.is_authenticated else 'anonymous',
        }, status=403)


def security_demo(request):
    """
    Interactive demo showing namespace security in action.
    """
    context = {
        'user': request.user if request.user.is_authenticated else None,
        'is_authenticated': request.user.is_authenticated,
    }

    if request.user.is_authenticated:
        middleware = get_security_middleware()

        # Show what namespaces the user can access
        context['allowed_namespaces'] = middleware.get_allowed_namespaces(
            user=request.user,
            request=request
        )

        # Show owned namespaces
        context['owned_namespaces'] = Namespace.objects.filter(
            owner=request.user
        )

        # Show if user is superuser
        context['is_superuser'] = request.user.is_superuser

    return render(request, 'knowledge_demo/security_demo.html', context)