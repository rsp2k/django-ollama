"""
Admin configuration for knowledge_demo models.
"""
from django.contrib import admin
from .models import Project, Article, Document


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'knowledge_base', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at', 'knowledge_base__namespace']
    search_fields = ['name', 'description', 'owner__username']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['team_members']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('owner', 'knowledge_base__namespace')


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'knowledge_base', 'created_at']
    list_filter = ['created_at', 'knowledge_base__namespace']
    search_fields = ['title', 'content', 'author__username']
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('author', 'knowledge_base__namespace')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'uploaded_by', 'knowledge_base', 'document_type', 'uploaded_at']
    list_filter = ['document_type', 'uploaded_at', 'knowledge_base__namespace']
    search_fields = ['name', 'description', 'uploaded_by__username']
    readonly_fields = ['uploaded_at', 'file_size', 'document_type']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('uploaded_by', 'knowledge_base__namespace')