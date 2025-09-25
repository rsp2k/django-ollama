"""
Test models for django-ollama testing.

These models are used to test the KnowledgeBaseContent functionality
with the generic foreign key relationships.
"""

from django.db import models


class TestDocument(models.Model):
    """A test document model for testing KnowledgeBaseContent."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def __ai_text__(self):
        """Return text content for AI processing."""
        return f"{self.title}\n\n{self.content}"


class TestArticle(models.Model):
    """Another test model with different AI text implementation."""

    headline = models.CharField(max_length=100)
    body = models.TextField()
    summary = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return self.headline

    @property
    def __ai_text__(self):
        """AI text as property instead of method."""
        if self.summary:
            return f"{self.headline}\n\nSummary: {self.summary}\n\n{self.body}"
        return f"{self.headline}\n\n{self.body}"