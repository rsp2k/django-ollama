"""
Views demonstrating context injection system.

Shows how querysets are automatically injected into AI context
based on URL parameters and request context.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

from django_ollama.context_injection import (
    inject_querysets,
    get_ai_context,
    LazyQueryset
)
from django_ollama import chat
from .models import Article, Document, Project


def article_context(url_kwargs):
    """Get article and related content for AI context."""
    if 'pk' in url_kwargs:
        article = Article.objects.filter(pk=url_kwargs['pk'])
        # Return article and related documents
        return [
            LazyQueryset(
                name='current_article',
                queryset=article,
                priority=20,
                limit=1
            ),
            LazyQueryset(
                name='related_articles',
                queryset=Article.objects.filter(
                    tags__overlap=article.first().tags if article.exists() else []
                ).exclude(pk=url_kwargs['pk'])[:3],
                priority=10,
                limit=3
            )
        ]
    return []


@inject_querysets(article_context, limit=5, priority=15)
def article_ai_view(request, pk):
    """
    Article view with AI assistance and automatic context injection.

    The decorator automatically injects the current article and related
    articles into the AI context.
    """
    article = get_object_or_404(Article, pk=pk)

    # Get AI context (lazy querysets attached by middleware)
    ai_context = get_ai_context(request, evaluate=False)

    # Prepare context summary for display
    context_summary = []
    for lazy_qs in ai_context:
        context_summary.append({
            'name': lazy_qs.name,
            'model': lazy_qs.queryset.model.__name__ if hasattr(lazy_qs.queryset, 'model') else 'Unknown',
            'priority': lazy_qs.priority,
            'limit': lazy_qs.limit,
            'count': lazy_qs.count() if lazy_qs.exists() else 0
        })

    # Handle AI chat if requested
    ai_response = None
    if request.method == 'POST':
        user_message = request.POST.get('message', '')
        if user_message:
            # Evaluate context for AI
            evaluated_context = get_ai_context(request, evaluate=True)

            # Build context string
            context_str = "### Context:\n"
            for item in evaluated_context['content']:
                context_str += f"\n#### {item['name']} ({item['count']} items):\n"
                context_str += item['data'] + "\n"

            # Send to AI with context
            full_prompt = f"{context_str}\n### User Question:\n{user_message}"

            try:
                response = chat(
                    message=full_prompt,
                    model='llama3.2:1b',  # Use lightweight model
                    options={'temperature': 0.7}
                )
                ai_response = response['message']['content']
            except Exception as e:
                ai_response = f"AI Error: {str(e)}"

    return render(request, 'knowledge_demo/article_ai.html', {
        'article': article,
        'context_summary': context_summary,
        'ai_response': ai_response,
        'total_context_items': len(ai_context)
    })


class ProjectContextAPIView(View):
    """
    API endpoint demonstrating programmatic context injection.

    Shows how to add custom querysets to the AI context dynamically.
    """

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        """Get project with AI context information."""
        project = get_object_or_404(Project, pk=pk)

        # Manually add project-specific querysets to context
        custom_querysets = [
            LazyQueryset(
                name='project_info',
                queryset=Project.objects.filter(pk=pk),
                priority=25,
                limit=1
            ),
            LazyQueryset(
                name='project_team',
                queryset=project.team_members.all(),
                priority=15,
                limit=10,
                metadata={'type': 'team_members'}
            ),
            LazyQueryset(
                name='project_documents',
                queryset=Document.objects.filter(
                    knowledge_base=project.knowledge_base
                ),
                priority=10,
                limit=5
            )
        ]

        # Get current AI context from request
        existing_context = get_ai_context(request, evaluate=False)

        # Combine contexts
        all_querysets = existing_context + custom_querysets

        # Sort by priority
        all_querysets.sort(key=lambda x: x.priority, reverse=True)

        # Prepare response
        response_data = {
            'project': {
                'id': str(project.id),
                'name': project.name,
                'description': project.description,
            },
            'ai_context': {
                'total_querysets': len(all_querysets),
                'querysets': [
                    {
                        'name': qs.name,
                        'priority': qs.priority,
                        'limit': qs.limit,
                        'exists': qs.exists(),
                        'count': qs.count() if qs.exists() else 0,
                        'metadata': qs.metadata
                    }
                    for qs in all_querysets
                ]
            }
        }

        return JsonResponse(response_data)

    def post(self, request, pk):
        """Process AI query with project context."""
        project = get_object_or_404(Project, pk=pk)

        try:
            data = json.loads(request.body)
            query = data.get('query', '')
            include_context = data.get('include_context', True)

            if not query:
                return JsonResponse({'error': 'No query provided'}, status=400)

            # Build response
            response_data = {
                'project_id': str(project.id),
                'query': query
            }

            if include_context:
                # Get and evaluate AI context
                context = get_ai_context(request, evaluate=True)

                # Build context string
                context_str = ""
                for item in context['content']:
                    context_str += f"### {item['name']}:\n{item['data']}\n\n"

                # Add to response
                response_data['context'] = {
                    'total_items': context['metadata']['evaluated'],
                    'content_preview': context_str[:500] + '...' if len(context_str) > 500 else context_str
                }

                # Query AI with context
                full_query = f"Context:\n{context_str}\n\nQuestion: {query}"

                try:
                    ai_response = chat(
                        message=full_query,
                        model='llama3.2:1b',
                        options={'temperature': 0.5}
                    )
                    response_data['ai_response'] = ai_response['message']['content']
                except Exception as e:
                    response_data['ai_error'] = str(e)

            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


def context_demo_view(request):
    """
    Demo page showing how context injection works.

    Displays all lazy querysets attached to the request and allows
    testing context evaluation.
    """
    # Get lazy querysets (not evaluated)
    lazy_querysets = get_ai_context(request, evaluate=False)

    # Prepare display data
    context_info = []
    for qs in lazy_querysets:
        info = {
            'name': qs.name,
            'priority': qs.priority,
            'limit': qs.limit,
            'exists': qs.exists(),  # This is efficient
            'count': qs.count() if qs.exists() else 0,  # Also efficient
            'model': 'Unknown'
        }

        # Try to get model name
        if hasattr(qs.queryset, 'model'):
            info['model'] = qs.queryset.model.__name__

        context_info.append(info)

    # Handle evaluation request
    evaluated_content = None
    if request.method == 'POST' and 'evaluate' in request.POST:
        # Evaluate all querysets
        evaluated = get_ai_context(request, evaluate=True)
        evaluated_content = {
            'total_evaluated': evaluated['metadata']['evaluated'],
            'items': evaluated['content']
        }

    return render(request, 'knowledge_demo/context_demo_simple.html', {
        'context_info': context_info,
        'total_querysets': len(lazy_querysets),
        'evaluated_content': evaluated_content,
        'user': request.user
    })


# Custom view with multiple context sources
@inject_querysets(
    lambda kwargs: Article.objects.all()[:5],
    lambda kwargs: Document.objects.all()[:3],
    lambda kwargs: Project.objects.filter(is_public=True)[:2],
    priority=5
)
def multi_context_view(request):
    """
    View demonstrating multiple queryset injection.

    The decorator injects articles, documents, and public projects
    into the AI context.
    """
    context = get_ai_context(request, evaluate=False)

    # Group by model type
    grouped_context = {}
    for qs in context:
        model_name = qs.queryset.model.__name__ if hasattr(qs.queryset, 'model') else 'Unknown'
        if model_name not in grouped_context:
            grouped_context[model_name] = []
        grouped_context[model_name].append(qs)

    return render(request, 'knowledge_demo/multi_context.html', {
        'grouped_context': grouped_context,
        'total_querysets': len(context)
    })


def streaming_chat_view(request):
    """
    Interactive streaming chat demo with dynamic context selection.

    Allows users to:
    - Select specific querysets for context injection
    - Configure limits and filters for each queryset type
    - See real-time context preview before sending to AI
    - Experience streaming responses with full context awareness
    """
    from .models import Article, Document, Project

    # Get available content counts
    context_stats = {
        'articles': {
            'total': Article.objects.count(),
            'with_tags': Article.objects.exclude(tags=[]).count(),
            'recent': Article.objects.filter(created_at__gte=timezone.now() - timezone.timedelta(days=30)).count(),
        },
        'documents': {
            'total': Document.objects.count(),
            'types': list(Document.objects.values_list('document_type', flat=True).distinct()),
        },
        'projects': {
            'total': Project.objects.count(),
            'public': Project.objects.filter(is_public=True).count(),
        }
    }

    # Get some sample tags for filtering
    all_tags = []
    for article in Article.objects.exclude(tags=[]):
        all_tags.extend(article.tags)
    unique_tags = list(set(all_tags))[:20]  # Limit to 20 most common

    return render(request, 'knowledge_demo/streaming_chat.html', {
        'context_stats': context_stats,
        'available_tags': unique_tags,
        'websocket_url': f'{"wss" if request.is_secure() else "ws"}://{request.get_host()}/ws/streaming-chat/'
    })