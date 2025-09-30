"""
WebSocket consumers for real-time chat with context injection.
"""
import json
import asyncio
from typing import TYPE_CHECKING
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from django_ollama import achat
from django_ollama.context_injection import get_ai_context, LazyQueryset

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from .models import Article, Document, Project


class StreamingChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for streaming chat with dynamic context selection.

    Supports:
    - Real-time context selection from knowledge bases
    - Streaming responses from Ollama
    - Dynamic queryset injection based on user selections
    """

    async def connect(self):
        await self.accept()

        # Initialize chat session
        await self.send_json({
            'type': 'connection_established',
            'message': 'Connected to streaming chat with context injection'
        })

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'get_available_context':
                await self.handle_get_available_context()
            elif message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'test_context':
                await self.handle_test_context(data)

        except json.JSONDecodeError:
            await self.send_json({
                'type': 'error',
                'message': 'Invalid JSON received'
            })
        except Exception as e:
            await self.send_json({
                'type': 'error',
                'message': f'Error processing message: {str(e)}'
            })

    async def handle_get_available_context(self):
        """Send available context sources to the client."""
        try:
            from .models import Article, Document, Project

            # Get counts of available content
            article_count = await sync_to_async(Article.objects.count)()
            document_count = await sync_to_async(Document.objects.count)()
            project_count = await sync_to_async(Project.objects.count)()
            public_project_count = await sync_to_async(
                Project.objects.filter(is_public=True).count
            )()

            context_sources = {
                'articles': {
                    'name': 'Recent Articles',
                    'description': 'Latest articles from the knowledge base',
                    'count': article_count,
                    'available_limits': [3, 5, 10, 20]
                },
                'documents': {
                    'name': 'Documents',
                    'description': 'Document metadata and descriptions',
                    'count': document_count,
                    'available_limits': [2, 5, 10]
                },
                'projects': {
                    'name': 'All Projects',
                    'description': 'Project information and team details',
                    'count': project_count,
                    'available_limits': [2, 5, 10]
                },
                'public_projects': {
                    'name': 'Public Projects Only',
                    'description': 'Only publicly accessible projects',
                    'count': public_project_count,
                    'available_limits': [2, 5, 10]
                }
            }

            await self.send_json({
                'type': 'available_context',
                'sources': context_sources
            })

        except Exception as e:
            await self.send_json({
                'type': 'error',
                'message': f'Error getting available context: {str(e)}'
            })

    async def handle_test_context(self, data):
        """Test context creation without sending to AI."""
        try:
            selected_context = data.get('selected_context', {})

            # Build querysets based on selections
            lazy_querysets = await self.build_context_querysets(selected_context)

            # Evaluate querysets to show what would be sent to AI
            context_preview = []
            total_items = 0

            for lazy_qs in lazy_querysets:
                # Get count and preview
                count = await sync_to_async(lazy_qs.count)()
                exists = await sync_to_async(lazy_qs.exists)()

                if exists and count > 0:
                    # Get first few items for preview
                    preview_items = []
                    items = await sync_to_async(list)(lazy_qs.queryset[:min(3, lazy_qs.limit or 3)])

                    for item in items:
                        if hasattr(item, '__ai_text__'):
                            ai_text = await sync_to_async(item.__ai_text__)()
                            preview_items.append({
                                'type': item.__class__.__name__,
                                'preview': ai_text[:200] + '...' if len(ai_text) > 200 else ai_text
                            })

                    context_preview.append({
                        'name': lazy_qs.name,
                        'priority': lazy_qs.priority,
                        'count': count,
                        'limit': lazy_qs.limit,
                        'preview_items': preview_items
                    })
                    total_items += count

            await self.send_json({
                'type': 'context_preview',
                'context': context_preview,
                'total_items': total_items,
                'message': f'Context preview generated with {len(context_preview)} sources and {total_items} total items'
            })

        except Exception as e:
            await self.send_json({
                'type': 'error',
                'message': f'Error testing context: {str(e)}'
            })

    async def handle_chat_message(self, data):
        """Handle chat message with context injection and streaming response."""
        try:
            user_message = data.get('message', '')
            selected_context = data.get('selected_context', {})

            if not user_message.strip():
                await self.send_json({
                    'type': 'error',
                    'message': 'Empty message received'
                })
                return

            # Build context from selections
            lazy_querysets = await self.build_context_querysets(selected_context)

            # Evaluate querysets for AI
            context_data = await self.evaluate_context(lazy_querysets)

            # Build context string for AI
            context_str = ""
            if context_data:
                context_str = "### Context Information:\n\n"
                for item in context_data:
                    context_str += f"#### {item['name']} ({item['count']} items):\n"
                    context_str += item['data'] + "\n\n"
                context_str += "### User Question:\n"

            # Complete prompt
            full_prompt = context_str + user_message

            # Send context info to client
            await self.send_json({
                'type': 'context_applied',
                'context_sources': len(context_data),
                'total_context_items': sum(item['count'] for item in context_data),
                'prompt_length': len(full_prompt)
            })

            # Send streaming start
            await self.send_json({
                'type': 'ai_response_start',
                'message': 'AI is processing your request...'
            })

            try:
                # Stream response from Ollama
                response = await achat(
                    message=full_prompt,
                    model='llama3.2:1b',  # Use lightweight model for demo
                    options={'temperature': 0.7, 'stream': True}
                )

                # Handle streaming response
                full_response = ""
                if hasattr(response, '__aiter__'):
                    # Streaming response
                    async for chunk in response:
                        if chunk and 'message' in chunk and 'content' in chunk['message']:
                            content = chunk['message']['content']
                            full_response += content
                            await self.send_json({
                                'type': 'ai_response_chunk',
                                'content': content
                            })
                else:
                    # Non-streaming response
                    if 'message' in response and 'content' in response['message']:
                        full_response = response['message']['content']
                        await self.send_json({
                            'type': 'ai_response_chunk',
                            'content': full_response
                        })

                # Send completion
                await self.send_json({
                    'type': 'ai_response_complete',
                    'full_response': full_response,
                    'message': 'Response completed'
                })

            except Exception as ollama_error:
                await self.send_json({
                    'type': 'ai_error',
                    'message': f'Ollama error: {str(ollama_error)}',
                    'fallback_response': 'Sorry, I encountered an error while processing your request. The context was built successfully, but the AI service is unavailable.'
                })

        except Exception as e:
            await self.send_json({
                'type': 'error',
                'message': f'Error processing chat message: {str(e)}'
            })

    async def build_context_querysets(self, selected_context):
        """Build LazyQueryset objects based on user selections."""
        from .models import Article, Document, Project

        lazy_querysets = []

        # Articles
        if 'articles' in selected_context:
            limit = selected_context['articles'].get('limit', 5)
            tags = selected_context['articles'].get('tags', [])

            if tags:
                # Filter by tags if specified
                queryset = Article.objects.filter(tags__overlap=tags)
            else:
                queryset = Article.objects.all()

            lazy_querysets.append(LazyQueryset(
                name='selected_articles',
                queryset=queryset[:limit],
                priority=20,
                limit=limit
            ))

        # Documents
        if 'documents' in selected_context:
            limit = selected_context['documents'].get('limit', 5)
            doc_types = selected_context['documents'].get('types', [])

            if doc_types:
                queryset = Document.objects.filter(document_type__in=doc_types)
            else:
                queryset = Document.objects.all()

            lazy_querysets.append(LazyQueryset(
                name='selected_documents',
                queryset=queryset[:limit],
                priority=15,
                limit=limit
            ))

        # Projects
        if 'projects' in selected_context:
            limit = selected_context['projects'].get('limit', 5)
            public_only = selected_context['projects'].get('public_only', False)

            if public_only:
                queryset = Project.objects.filter(is_public=True)
            else:
                queryset = Project.objects.all()

            lazy_querysets.append(LazyQueryset(
                name='selected_projects',
                queryset=queryset[:limit],
                priority=10,
                limit=limit
            ))

        # Sort by priority
        lazy_querysets.sort(key=lambda x: x.priority, reverse=True)

        return lazy_querysets

    async def evaluate_context(self, lazy_querysets):
        """Evaluate lazy querysets and return serialized data."""
        context_data = []

        for lazy_qs in lazy_querysets:
            try:
                # Check if queryset has data
                exists = await sync_to_async(lazy_qs.exists)()
                if not exists:
                    continue

                # Get items
                items = await sync_to_async(list)(lazy_qs.queryset)

                # Serialize items
                serialized_items = []
                for item in items:
                    if hasattr(item, '__ai_text__'):
                        ai_text = await sync_to_async(item.__ai_text__)()
                        serialized_items.append(ai_text)

                if serialized_items:
                    context_data.append({
                        'name': lazy_qs.name,
                        'count': len(serialized_items),
                        'data': '\n\n'.join(serialized_items)
                    })

            except Exception as e:
                # Skip problematic querysets
                continue

        return context_data

    async def send_json(self, content):
        """Helper to send JSON data."""
        await self.send(text_data=json.dumps(content))