"""Django models for Ollama integration."""

import mimetypes
import uuid
from typing import Any, Optional

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class KnowledgeBase(models.Model):
    """
    A collection of documents and media for AI context.

    This model represents a knowledge base that can be used to provide
    context to Ollama models for more accurate and relevant responses.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Knowledge Base")
        verbose_name_plural = _("Knowledge Bases")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    @property
    def content_count(self) -> int:
        """Return the number of content items in this knowledge base."""
        return self.content_items.count()

    @property
    def media_count(self) -> int:
        """Return the number of media items in this knowledge base."""
        return self.media_items.count()


class KnowledgeBaseMedia(models.Model):
    """
    Media files (images, documents, etc.) for knowledge bases.

    This model stores file uploads that can be processed and used as
    context for AI models, with automatic MIME type detection.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name="media_items",
        verbose_name=_("Knowledge Base"),
    )
    file = models.FileField(_("File"), upload_to="django_ollama/media/%Y/%m/")
    original_filename = models.CharField(_("Original Filename"), max_length=255)
    mime_type = models.CharField(_("MIME Type"), max_length=100, blank=True)
    file_size = models.PositiveIntegerField(_("File Size (bytes)"), null=True, blank=True)

    # Processing status
    is_processed = models.BooleanField(_("Is Processed"), default=False)
    processing_error = models.TextField(_("Processing Error"), blank=True)

    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Knowledge Base Media")
        verbose_name_plural = _("Knowledge Base Media")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.knowledge_base.name})"

    def save(self, *args, **kwargs):
        """Override save to set MIME type and file size automatically."""
        if self.file:
            # Set original filename if not set
            if not self.original_filename and hasattr(self.file, 'name'):
                self.original_filename = self.file.name

            # Set MIME type if not set
            if not self.mime_type:
                self.mime_type = mimetypes.guess_type(self.original_filename)[0] or "application/octet-stream"

            # Set file size if not set
            if not self.file_size and hasattr(self.file, 'size'):
                self.file_size = self.file.size

        super().save(*args, **kwargs)

    def clean(self):
        """Validate the media file."""
        super().clean()

        # Check file size (100MB limit by default)
        max_size = getattr(models.conf.settings if hasattr(models, 'conf') else None,
                          'DJANGO_OLLAMA_MAX_FILE_SIZE', 100 * 1024 * 1024)
        if self.file and hasattr(self.file, 'size') and self.file.size > max_size:
            raise ValidationError(
                _("File size exceeds maximum allowed size of %(max_size)s bytes.")
                % {'max_size': max_size}
            )


class KnowledgeBaseContent(models.Model):
    """
    Link arbitrary model instances to knowledge bases using content types.

    This model allows you to associate any Django model instance with a
    knowledge base. The linked model should have either a `__ai_text__`
    attribute/method returning text content or a `__ai_file__` attribute/method
    returning a file-like object.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.CASCADE,
        related_name="content_items",
        verbose_name=_("Knowledge Base"),
    )

    # Generic foreign key to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    # Metadata
    title = models.CharField(_("Title"), max_length=200, blank=True)
    summary = models.TextField(_("Summary"), blank=True)

    # Processing status
    is_processed = models.BooleanField(_("Is Processed"), default=False)
    processing_error = models.TextField(_("Processing Error"), blank=True)
    last_processed_at = models.DateTimeField(_("Last Processed At"), null=True, blank=True)

    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Knowledge Base Content")
        verbose_name_plural = _("Knowledge Base Content")
        ordering = ["-created_at"]
        unique_together = [["knowledge_base", "content_type", "object_id"]]

    def __str__(self) -> str:
        title = self.title or f"{self.content_type.name} #{self.object_id}"
        return f"{title} ({self.knowledge_base.name})"

    def get_ai_text(self) -> Optional[str]:
        """
        Extract text content from the linked object.

        Looks for `__ai_text__` attribute or method on the linked object.
        """
        if not self.content_object:
            return None

        # Try method first, then attribute
        if hasattr(self.content_object, '__ai_text__'):
            ai_text = getattr(self.content_object, '__ai_text__')
            if callable(ai_text):
                return ai_text()
            return str(ai_text)

        # Fallback to string representation
        return str(self.content_object)

    def get_ai_file(self) -> Any:
        """
        Extract file content from the linked object.

        Looks for `__ai_file__` attribute or method on the linked object.
        """
        if not self.content_object:
            return None

        # Try method first, then attribute
        if hasattr(self.content_object, '__ai_file__'):
            ai_file = getattr(self.content_object, '__ai_file__')
            if callable(ai_file):
                return ai_file()
            return ai_file

        return None

    @property
    def content_preview(self) -> str:
        """Return a short preview of the content."""
        text = self.get_ai_text()
        if text:
            return text[:200] + "..." if len(text) > 200 else text
        return "No text content available"


class ChatSession(models.Model):
    """
    Represents a chat session with an Ollama model.

    This model can be used to persist chat conversations and maintain
    context across multiple interactions.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Session Name"), max_length=200, blank=True)
    model = models.CharField(_("Ollama Model"), max_length=100)

    # Optional user association
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("User"),
        related_name="ollama_chat_sessions",
    )

    # Optional knowledge base association
    knowledge_base = models.ForeignKey(
        KnowledgeBase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Knowledge Base"),
        related_name="chat_sessions",
    )

    # Session metadata
    system_prompt = models.TextField(_("System Prompt"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    last_message_at = models.DateTimeField(_("Last Message At"), null=True, blank=True)

    class Meta:
        verbose_name = _("Chat Session")
        verbose_name_plural = _("Chat Sessions")
        ordering = ["-last_message_at", "-updated_at"]

    def __str__(self) -> str:
        if self.name:
            return self.name
        return f"Chat Session ({self.model}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def message_count(self) -> int:
        """Return the number of messages in this session."""
        return self.messages.count()


class ChatMessage(models.Model):
    """
    Individual messages within a chat session.
    """

    ROLE_CHOICES = [
        ("user", _("User")),
        ("assistant", _("Assistant")),
        ("system", _("System")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Chat Session"),
    )
    role = models.CharField(_("Role"), max_length=20, choices=ROLE_CHOICES)
    content = models.TextField(_("Content"))

    # Optional metadata
    metadata = models.JSONField(_("Metadata"), default=dict, blank=True)

    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Chat Message")
        verbose_name_plural = _("Chat Messages")
        ordering = ["created_at"]

    def __str__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.get_role_display()}: {content_preview}"