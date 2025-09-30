"""
URL patterns for knowledge_demo app.
"""
from django.urls import path
from . import views

app_name = 'knowledge_demo'

urlpatterns = [
    path('', views.index, name='index'),
    path('namespace/<slug:slug>/', views.namespace_detail, name='namespace_detail'),
    path('project/create/', views.create_project, name='create_project'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),

    # API endpoints demonstrating security
    path('api/namespace-access/', views.api_namespace_access, name='api_namespace_access'),

    # Interactive security demo
    path('security-demo/', views.security_demo, name='security_demo'),
]

# Import context demo URLs only if available
try:
    from . import views_context

    urlpatterns += [
        # Context injection demo URLs
        path('context-demo/', views_context.context_demo_view, name='context_demo'),
        path('article/<int:pk>/ai/', views_context.article_ai_view, name='article_ai'),
        path('api/project/<int:pk>/context/', views_context.ProjectContextAPIView.as_view(), name='project_context_api'),
        path('multi-context/', views_context.multi_context_view, name='multi_context'),
        path('streaming-chat/', views_context.streaming_chat_view, name='streaming_chat'),
    ]
except ImportError:
    pass  # Context demo views not available