"""
Demo models showcasing namespace-aware knowledge bases.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django_ollama.models import KnowledgeBase


class Article(models.Model):
    """
    Example content model that can be linked to knowledge bases.
    """
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Link to knowledge base (optional)
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='demo_articles'
    )

    # Tags for categorization
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def __ai_text__(self):
        """
        Method for django-ollama to extract AI-relevant text.
        This is used when the article is linked via KnowledgeBaseContent.
        """
        return f"Title: {self.title}\n\nContent: {self.content}\n\nTags: {', '.join(self.tags)}"


class Document(models.Model):
    """
    Example document model with file uploads.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/%Y/%m/')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    uploaded_at = models.DateTimeField(default=timezone.now)

    # Link to knowledge base
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='demo_documents'
    )

    # Document metadata
    document_type = models.CharField(max_length=50, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.name

    def __ai_file__(self):
        """
        Method for django-ollama to extract file for AI processing.
        """
        return self.file

    def __ai_text__(self):
        """
        AI serialization method for context injection.
        """
        return f"Document: {self.name}\nDescription: {self.description or 'No description'}\nType: {self.document_type}\nUploaded by: {self.uploaded_by.username}"

    def save(self, *args, **kwargs):
        """Auto-populate file size and type."""
        if self.file and not self.file_size:
            self.file_size = self.file.size
        if self.file and not self.document_type:
            # Extract file extension as document type
            import os
            _, ext = os.path.splitext(self.file.name)
            self.document_type = ext[1:] if ext else 'unknown'
        super().save(*args, **kwargs)


class Project(models.Model):
    """
    Example project model that groups content in a namespace.
    """
    name = models.CharField(max_length=200)
    description = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')

    # Each project gets its own knowledge base in a specific namespace
    knowledge_base = models.OneToOneField(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name='project'
    )

    # Project settings
    is_public = models.BooleanField(default=False)
    team_members = models.ManyToManyField(User, related_name='project_memberships', blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.knowledge_base.namespace.name})"

    def __ai_text__(self):
        """
        AI serialization method for context injection.
        """
        team_list = ", ".join([m.username for m in self.team_members.all()[:5]])
        return f"Project: {self.name}\nDescription: {self.description}\nOwner: {self.owner.username}\nPublic: {self.is_public}\nTeam: {team_list or 'No team members'}"

    def add_article(self, title, content, author=None):
        """Helper method to add an article to this project."""
        if author is None:
            author = self.owner
        return Article.objects.create(
            title=title,
            content=content,
            author=author,
            knowledge_base=self.knowledge_base
        )

    def add_document(self, name, file, uploaded_by=None):
        """Helper method to add a document to this project."""
        if uploaded_by is None:
            uploaded_by = self.owner
        return Document.objects.create(
            name=name,
            file=file,
            uploaded_by=uploaded_by,
            knowledge_base=self.knowledge_base
        )

    @property
    def article_count(self):
        """Count of articles in this project."""
        return self.knowledge_base.demo_articles.count()

    @property
    def document_count(self):
        """Count of documents in this project."""
        return self.knowledge_base.demo_documents.count()