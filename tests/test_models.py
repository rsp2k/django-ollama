"""
Test cases for django-ollama models.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from django_ollama.models import (
    ChatMessage,
    ChatSession,
    KnowledgeBase,
    KnowledgeBaseContent,
    KnowledgeBaseMedia,
)
from tests.test_app.models import TestArticle, TestDocument

User = get_user_model()


class KnowledgeBaseModelTests(TestCase):
    """Test cases for KnowledgeBase model."""

    def test_knowledge_base_creation(self):
        """Test creating a knowledge base."""
        kb = KnowledgeBase.objects.create(
            name="Test KB",
            description="A test knowledge base"
        )
        self.assertEqual(kb.name, "Test KB")
        self.assertEqual(kb.description, "A test knowledge base")
        self.assertTrue(kb.is_active)
        self.assertEqual(kb.content_count, 0)
        self.assertEqual(kb.media_count, 0)

    def test_knowledge_base_str(self):
        """Test string representation."""
        kb = KnowledgeBase.objects.create(name="Test KB")
        self.assertEqual(str(kb), "Test KB")


class KnowledgeBaseContentModelTests(TestCase):
    """Test cases for KnowledgeBaseContent model."""

    def setUp(self):
        self.kb = KnowledgeBase.objects.create(name="Test KB")
        self.doc = TestDocument.objects.create(
            title="Test Document",
            content="This is test content for the document."
        )

    def test_content_creation(self):
        """Test creating knowledge base content."""
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=self.doc,
            title="Custom Title",
            summary="Test summary"
        )
        self.assertEqual(content.knowledge_base, self.kb)
        self.assertEqual(content.content_object, self.doc)
        self.assertEqual(content.title, "Custom Title")
        self.assertEqual(content.summary, "Test summary")
        self.assertFalse(content.is_processed)

    def test_get_ai_text_method(self):
        """Test getting AI text from linked object with method."""
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=self.doc
        )
        ai_text = content.get_ai_text()
        expected = "Test Document\n\nThis is test content for the document."
        self.assertEqual(ai_text, expected)

    def test_get_ai_text_property(self):
        """Test getting AI text from linked object with property."""
        article = TestArticle.objects.create(
            headline="Test Article",
            body="Article body content",
            summary="Article summary"
        )
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=article
        )
        ai_text = content.get_ai_text()
        expected = "Test Article\n\nSummary: Article summary\n\nArticle body content"
        self.assertEqual(ai_text, expected)

    def test_content_preview(self):
        """Test content preview property."""
        content = KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=self.doc
        )
        preview = content.content_preview
        self.assertTrue(preview.startswith("Test Document"))
        self.assertLessEqual(len(preview), 203)  # 200 chars + "..."

    def test_unique_together_constraint(self):
        """Test unique together constraint."""
        KnowledgeBaseContent.objects.create(
            knowledge_base=self.kb,
            content_object=self.doc
        )
        # Creating another with same KB and content object should fail
        with self.assertRaises(Exception):  # IntegrityError
            KnowledgeBaseContent.objects.create(
                knowledge_base=self.kb,
                content_object=self.doc
            )


class ChatSessionModelTests(TestCase):
    """Test cases for ChatSession model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com"
        )
        self.kb = KnowledgeBase.objects.create(name="Test KB")

    def test_chat_session_creation(self):
        """Test creating a chat session."""
        session = ChatSession.objects.create(
            name="Test Session",
            model="llama3",
            user=self.user,
            knowledge_base=self.kb,
            system_prompt="You are a helpful assistant."
        )
        self.assertEqual(session.name, "Test Session")
        self.assertEqual(session.model, "llama3")
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.knowledge_base, self.kb)
        self.assertTrue(session.is_active)
        self.assertEqual(session.message_count, 0)

    def test_chat_session_str_with_name(self):
        """Test string representation with name."""
        session = ChatSession.objects.create(
            name="My Chat",
            model="llama3"
        )
        self.assertEqual(str(session), "My Chat")

    def test_chat_session_str_without_name(self):
        """Test string representation without name."""
        session = ChatSession.objects.create(model="llama3")
        self.assertIn("Chat Session", str(session))
        self.assertIn("llama3", str(session))


class ChatMessageModelTests(TestCase):
    """Test cases for ChatMessage model."""

    def setUp(self):
        self.session = ChatSession.objects.create(
            name="Test Session",
            model="llama3"
        )

    def test_chat_message_creation(self):
        """Test creating a chat message."""
        message = ChatMessage.objects.create(
            session=self.session,
            role="user",
            content="Hello, how are you?",
            metadata={"test": "value"}
        )
        self.assertEqual(message.session, self.session)
        self.assertEqual(message.role, "user")
        self.assertEqual(message.content, "Hello, how are you?")
        self.assertEqual(message.metadata["test"], "value")

    def test_message_str(self):
        """Test string representation."""
        message = ChatMessage.objects.create(
            session=self.session,
            role="assistant",
            content="I'm doing well, thank you for asking!"
        )
        str_repr = str(message)
        self.assertIn("Assistant", str_repr)
        self.assertIn("I'm doing well", str_repr)

    def test_message_str_truncation(self):
        """Test string representation truncation for long content."""
        long_content = "A" * 100  # 100 characters
        message = ChatMessage.objects.create(
            session=self.session,
            role="user",
            content=long_content
        )
        str_repr = str(message)
        self.assertIn("...", str_repr)
        self.assertLess(len(str_repr), len(long_content) + 20)


@pytest.mark.django_db
class TestKnowledgeBaseMediaModel:
    """Test cases for KnowledgeBaseMedia model using pytest."""

    def test_media_auto_fields(self):
        """Test automatic field setting on save."""
        kb = KnowledgeBase.objects.create(name="Test KB")
        # Create a simple file-like object for testing
        from django.core.files.base import ContentFile

        media = KnowledgeBaseMedia(
            knowledge_base=kb,
            file=ContentFile(b"test content", name="test.txt")
        )
        media.save()

        assert media.original_filename == "test.txt"
        assert media.mime_type == "text/plain"
        assert media.file_size > 0
        assert not media.is_processed