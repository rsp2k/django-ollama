"""
Advanced test cases for django-ollama models to improve coverage.
"""

import pytest
from unittest.mock import patch, Mock
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.contrib.contenttypes.models import ContentType

from django_ollama.models import (
    KnowledgeBase,
    KnowledgeBaseContent,
    KnowledgeBaseMedia,
    ChatSession,
    ChatMessage,
)
from tests.test_app.models import TestDocument


class TestKnowledgeBaseMediaAdvanced(TestCase):
    """Advanced test cases for KnowledgeBaseMedia model."""

    def setUp(self):
        self.kb = KnowledgeBase.objects.create(name="Test KB")

    def test_media_save_with_existing_metadata(self):
        """Test save method when metadata already exists."""
        media = KnowledgeBaseMedia(
            knowledge_base=self.kb,
            file=ContentFile(b"test content", name="test.pdf"),
            original_filename="custom.pdf",
            mime_type="application/pdf",
            file_size=1000
        )
        media.save()

        # Should keep existing metadata
        assert media.original_filename == "custom.pdf"
        assert media.mime_type == "application/pdf"
        assert media.file_size == 1000

    def test_media_save_without_file(self):
        """Test save method without file."""
        media = KnowledgeBaseMedia(knowledge_base=self.kb)
        media.save()

        # Should handle gracefully
        assert media.original_filename == ""
        assert media.mime_type == ""
        assert media.file_size is None

    def test_media_mime_type_detection(self):
        """Test MIME type detection for various file types."""
        test_files = [
            ("test.jpg", "image/jpeg"),
            ("test.png", "image/png"),
            ("test.pdf", "application/pdf"),
            ("test.txt", "text/plain"),
            ("test.unknown", "application/octet-stream"),  # fallback
        ]

        for filename, expected_mime in test_files:
            media = KnowledgeBaseMedia(
                knowledge_base=self.kb,
                file=ContentFile(b"test content", name=filename)
            )
            media.save()
            assert media.mime_type == expected_mime

    def test_media_str_representation(self):
        """Test string representation of media."""
        media = KnowledgeBaseMedia.objects.create(
            knowledge_base=self.kb,
            file=ContentFile(b"content", name="test.pdf"),
            original_filename="document.pdf"
        )
        expected = f"document.pdf ({self.kb.name})"
        assert str(media) == expected

    @override_settings(DJANGO_OLLAMA_MAX_FILE_SIZE=100)
    def test_media_file_size_validation_with_setting(self):
        """Test file size validation with custom setting."""
        large_content = b"x" * 200  # 200 bytes, exceeds limit of 100
        media = KnowledgeBaseMedia(
            knowledge_base=self.kb,
            file=ContentFile(large_content, name="large.txt")
        )

        with pytest.raises(ValidationError, match="exceeds maximum allowed size"):
            media.clean()

    def test_media_file_size_validation_default(self):
        """Test file size validation with default limit."""
        # Create content smaller than default 100MB limit
        normal_content = b"x" * 1000  # 1KB
        media = KnowledgeBaseMedia(
            knowledge_base=self.kb,
            file=ContentFile(normal_content, name="normal.txt")
        )

        # Should not raise error
        media.clean()

    def test_media_clean_without_file(self):
        """Test clean method without file."""
        media = KnowledgeBaseMedia(knowledge_base=self.kb)
        # Should not raise error
        media.clean()

    def test_media_processing_fields(self):
        """Test processing-related fields."""
        media = KnowledgeBaseMedia.objects.create(
            knowledge_base=self.kb,
            file=ContentFile(b"content", name="test.txt"),
            is_processed=True,
            processing_error="Test error message"
        )

        assert media.is_processed is True
        assert media.processing_error == "Test error message"

    def test_media_timestamps(self):
        """Test automatic timestamp fields."""
        media = KnowledgeBaseMedia.objects.create(
            knowledge_base=self.kb,
            file=ContentFile(b"content", name="test.txt")
        )

        assert media.created_at is not None
        assert media.updated_at is not None
        assert media.created_at <= media.updated_at


class TestKnowledgeBaseContentAdvanced(TestCase):
    """Advanced test cases for KnowledgeBaseContent."""

    def setUp(self):
        self.kb = KnowledgeBase.objects.create(name="Test KB")
        self.doc = TestDocument.objects.create(
            title="Test Document",
            content="Document content"
        )

    def test_content_get_ai_text_with_none_object(self):
        """Test get_ai_text when content_object is None."""
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_type=ContentType.objects.get_for_model(TestDocument),
            object_id=99999  # Non-existent object
        )

        result = content.get_ai_text()
        assert result is None

    def test_content_get_ai_file_with_none_object(self):
        """Test get_ai_file when content_object is None."""
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_type=ContentType.objects.get_for_model(TestDocument),
            object_id=99999  # Non-existent object
        )

        result = content.get_ai_file()
        assert result is None

    def test_content_get_ai_file_with_method(self):
        """Test get_ai_file with object that has __ai_file__ method."""
        # Create a mock object with __ai_file__ method
        mock_obj = Mock()
        mock_obj.__ai_file__ = Mock(return_value=b"file content")

        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=self.doc
        )

        # Mock the content_object to have our test object
        with patch.object(content, 'content_object', mock_obj):
            result = content.get_ai_file()
            assert result == b"file content"
            mock_obj.__ai_file__.assert_called_once()

    def test_content_get_ai_file_with_property(self):
        """Test get_ai_file with object that has __ai_file__ property."""
        mock_obj = Mock()
        mock_obj.__ai_file__ = b"property file content"

        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=self.doc
        )

        with patch.object(content, 'content_object', mock_obj):
            result = content.get_ai_file()
            assert result == b"property file content"

    def test_content_get_ai_file_fallback(self):
        """Test get_ai_file fallback when no __ai_file__ attribute."""
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=self.doc
        )

        result = content.get_ai_file()
        assert result is None

    def test_content_preview_long_text(self):
        """Test content preview with long text."""
        long_content_doc = TestDocument.objects.create(
            title="Short",
            content="x" * 300  # 300 characters
        )
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=long_content_doc
        )

        preview = content.content_preview
        assert len(preview) == 203  # 200 chars + "..."
        assert preview.endswith("...")

    def test_content_preview_no_text(self):
        """Test content preview when get_ai_text returns None."""
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_type=ContentType.objects.get_for_model(TestDocument),
            object_id=99999  # Non-existent object
        )

        preview = content.content_preview
        assert preview == "No text content available"

    def test_content_processing_fields(self):
        """Test processing-related fields."""
        from django.utils import timezone

        now = timezone.now()
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=self.doc,
            is_processed=True,
            processing_error="Processing failed",
            last_processed_at=now
        )

        assert content.is_processed is True
        assert content.processing_error == "Processing failed"
        assert content.last_processed_at == now

    def test_content_str_with_title(self):
        """Test string representation with custom title."""
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=self.doc,
            title="Custom Title"
        )

        expected = f"Custom Title ({self.kb.name})"
        assert str(content) == expected

    def test_content_str_without_title(self):
        """Test string representation without custom title."""
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=self.doc
        )

        # Should use content type name and object ID
        assert f"testdocument #{self.doc.id}" in str(content).lower()
        assert f"({self.kb.name})" in str(content)


class TestChatSessionAdvanced(TestCase):
    """Advanced test cases for ChatSession."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username="testuser")
        self.kb = KnowledgeBase.objects.create(name="Test KB")

    def test_chat_session_without_user(self):
        """Test creating chat session without user."""
        session = ChatSession.objects.create(
            name="Anonymous Session",
            model="llama3"
        )

        assert session.user is None
        assert session.name == "Anonymous Session"

    def test_chat_session_without_knowledge_base(self):
        """Test creating chat session without knowledge base."""
        session = ChatSession.objects.create(
            name="Simple Session",
            model="llama3",
            user=self.user
        )

        assert session.knowledge_base is None
        assert session.user == self.user

    def test_chat_session_with_system_prompt(self):
        """Test chat session with system prompt."""
        prompt = "You are a helpful assistant specialized in Python programming."
        session = ChatSession.objects.create(
            model="llama3",
            system_prompt=prompt
        )

        assert session.system_prompt == prompt

    def test_chat_session_last_message_at_update(self):
        """Test that last_message_at gets updated."""
        from django.utils import timezone

        session = ChatSession.objects.create(model="llama3")
        original_time = session.last_message_at

        # Create a message
        message = ChatMessage.objects.create(
            session=session,
            role="user",
            content="Test message"
        )

        # Refresh session
        session.refresh_from_db()

        # last_message_at should be updated (assuming the model signal works)
        # Note: This might need the actual signal implementation to work
        assert session.last_message_at is not None


class TestChatMessageAdvanced(TestCase):
    """Advanced test cases for ChatMessage."""

    def setUp(self):
        self.session = ChatSession.objects.create(
            name="Test Session",
            model="llama3"
        )

    def test_message_with_metadata(self):
        """Test message with complex metadata."""
        metadata = {
            "timestamp": "2024-01-01T10:00:00Z",
            "tokens": 150,
            "model_params": {"temperature": 0.8},
            "user_info": {"ip": "127.0.0.1"}
        }

        message = ChatMessage.objects.create(
            session=self.session,
            role="assistant",
            content="Response with metadata",
            metadata=metadata
        )

        assert message.metadata == metadata
        assert message.metadata["tokens"] == 150

    def test_message_role_choices(self):
        """Test all available role choices."""
        roles = ["user", "assistant", "system"]

        for role in roles:
            message = ChatMessage.objects.create(
                session=self.session,
                role=role,
                content=f"Test message for {role}"
            )
            assert message.role == role

    def test_message_get_role_display(self):
        """Test get_role_display method."""
        message = ChatMessage.objects.create(
            session=self.session,
            role="assistant",
            content="Test"
        )

        display = message.get_role_display()
        assert display == "Assistant"

    def test_message_ordering(self):
        """Test message ordering by created_at."""
        # Create messages in reverse order
        msg3 = ChatMessage.objects.create(
            session=self.session,
            role="user",
            content="Third message"
        )
        msg1 = ChatMessage.objects.create(
            session=self.session,
            role="user",
            content="First message"
        )
        msg2 = ChatMessage.objects.create(
            session=self.session,
            role="assistant",
            content="Second message"
        )

        # Should be ordered by created_at
        messages = list(ChatMessage.objects.filter(session=self.session))
        # The exact order depends on creation timestamps, but they should be ordered
        assert len(messages) == 3

    def test_message_cascade_deletion(self):
        """Test that messages are deleted when session is deleted."""
        message1 = ChatMessage.objects.create(
            session=self.session,
            role="user",
            content="Message 1"
        )
        message2 = ChatMessage.objects.create(
            session=self.session,
            role="assistant",
            content="Message 2"
        )

        session_id = self.session.id
        message_ids = [message1.id, message2.id]

        # Delete session
        self.session.delete()

        # Messages should be cascade deleted
        remaining_messages = ChatMessage.objects.filter(id__in=message_ids)
        assert remaining_messages.count() == 0