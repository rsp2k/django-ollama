# Django-Ollama

[![PyPI version](https://badge.fury.io/py/django-ollama.svg)](https://badge.fury.io/py/django-ollama)
[![Python versions](https://img.shields.io/pypi/pyversions/django-ollama.svg)](https://pypi.org/project/django-ollama/)
[![Django versions](https://img.shields.io/badge/Django-4.2%2B-blue.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Django integration for [Ollama](https://ollama.ai/) local LLM with real-time chat capabilities through WebSockets.

## Features

🚀 **Easy Integration**: Drop-in Django app with minimal configuration
💬 **Real-time Chat**: WebSocket-powered streaming responses
🧠 **Knowledge Base**: Link any Django model to provide context
🔄 **Session Management**: Persistent chat sessions with conversation history
🎨 **Flexible API**: Both sync and async Python API
🔧 **Production Ready**: Comprehensive testing, type hints, and documentation

## Quick Start

### Installation

```bash
pip install django-ollama
```

### Settings

Add to your Django `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... your other apps
    'channels',  # Required for WebSocket support
    'django_ollama',
]

# Ollama configuration
OLLAMA_HOST = "http://localhost:11434"  # Default
OLLAMA_DEFAULT_MODEL = "llama3.2"  # Default

# Channels configuration for WebSocket support
ASGI_APPLICATION = "your_project.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

### Database Migration

```bash
python manage.py migrate django_ollama
```

### WebSocket Routing

Add to your `routing.py`:

```python
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from django_ollama.consumers import OllamaChatConsumer

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/chat/", OllamaChatConsumer.as_asgi()),
        ])
    ),
})
```

## Usage Examples

### Python API

```python
from django_ollama import chat, generate

# Simple chat
response = chat("What is Django?")
print(response['message']['content'])

# Conversation with history
messages = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"},
    {"role": "user", "content": "What is Python?"}
]
response = chat(messages=messages)

# Streaming response
for chunk in chat("Tell me a story", stream=True):
    print(chunk['message']['content'], end='')

# Text generation
response = generate("Complete this: Django is")
print(response['response'])
```

### Async API

```python
import asyncio
from django_ollama import achat, agenerate

async def main():
    # Async chat
    response = await achat("What is Django?")
    print(response['message']['content'])

    # Async streaming
    async for chunk in achat("Tell me about AI", stream=True):
        print(chunk['message']['content'], end='')

asyncio.run(main())
```

### WebSocket Client (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/');

// Send a message
ws.send(JSON.stringify({
    type: 'chat_message',
    message: 'Hello, AI!',
    model: 'llama3.2',
    stream: true
}));

// Handle responses
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);

    if (data.type === 'chat_chunk') {
        // Stream content as it arrives
        document.getElementById('chat').innerHTML += data.content;
    } else if (data.type === 'chat_complete') {
        console.log('Chat completed:', data.full_message);
    } else if (data.type === 'error') {
        console.error('Error:', data.message);
    }
};
```

### Knowledge Base Integration

```python
from django_ollama.models import KnowledgeBase, KnowledgeBaseContent
from django.contrib.contenttypes.models import ContentType
from myapp.models import Article

# Create a knowledge base
kb = KnowledgeBase.objects.create(
    name="Company Docs",
    description="Internal documentation"
)

# Link existing Django models
article = Article.objects.create(
    title="Django Best Practices",
    content="Here are some Django best practices..."
)

# Your model needs an __ai_text__ method or property
class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()

    def __ai_text__(self):
        return f"{self.title}\\n\\n{self.content}"

# Add to knowledge base
KnowledgeBaseContent.objects.create(
    knowledge_base=kb,
    content_object=article,
    title="Django Best Practices Guide"
)

# Use in chat sessions
from django_ollama.models import ChatSession

session = ChatSession.objects.create(
    name="Help Session",
    model="llama3.2",
    knowledge_base=kb,
    system_prompt="Use the knowledge base to answer questions about Django."
)
```

## WebSocket Message Types

### Client → Server

```javascript
// Start a new session
{
    "type": "start_session",
    "name": "My Chat Session",
    "model": "llama3.2",
    "system_prompt": "You are a helpful assistant"
}

// Send chat message
{
    "type": "chat_message",
    "message": "Your question here",
    "model": "llama3.2",  // optional
    "session_id": "uuid",  // optional
    "stream": true  // optional, default: true
}

// End session
{
    "type": "end_session"
}
```

### Server → Client

```javascript
// Session started
{
    "type": "session_started",
    "session_id": "uuid",
    "model": "llama3.2",
    "name": "My Chat Session"
}

// Chat response start
{
    "type": "chat_start",
    "session_id": "uuid",
    "model": "llama3.2"
}

// Streaming content
{
    "type": "chat_chunk",
    "content": "partial response..."
}

// Chat complete
{
    "type": "chat_complete",
    "full_message": "complete response text"
}

// Error
{
    "type": "error",
    "message": "Error description"
}
```

## Models

### KnowledgeBase

Organize documents and content for AI context.

```python
kb = KnowledgeBase.objects.create(
    name="Documentation",
    description="Product documentation and guides",
    is_active=True
)
```

### ChatSession

Persistent chat conversations with history.

```python
session = ChatSession.objects.create(
    name="Customer Support",
    model="llama3.2",
    user=request.user,  # optional
    knowledge_base=kb,  # optional
    system_prompt="You are a helpful customer support agent.",
    is_active=True
)
```

### ChatMessage

Individual messages within sessions.

```python
message = ChatMessage.objects.create(
    session=session,
    role="user",  # or "assistant", "system"
    content="Hello, I need help with...",
    metadata={"source": "web", "ip": "127.0.0.1"}
)
```

## Configuration

### Environment Variables

```bash
# Ollama server configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.2

# File upload limits
DJANGO_OLLAMA_MAX_FILE_SIZE=104857600  # 100MB default
```

### Django Settings

```python
# Ollama configuration
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3.2"

# File upload configuration
DJANGO_OLLAMA_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Logging
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django_ollama': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

## 🧪 Test Dashboard

Django-Ollama includes a powerful **real-time test monitoring dashboard** that provides comprehensive analytics and live monitoring of your test suites.

### ✨ Dashboard Features

- **🔴 Live Test Monitoring**: Real-time WebSocket updates during test execution
- **📊 Interactive Analytics**: Charts, trends, and comprehensive test statistics
- **🎨 Beautiful Terminal UI**: Gruvbox-inspired theme with professional design
- **📱 Multi-Device Support**: Responsive design for desktop, tablet, and mobile
- **🔍 Smart Test Classification**: Automatic categorization of Unit, Integration, API, and E2E tests
- **📈 Historical Trends**: Long-term performance analysis and flakiness detection
- **🐳 Production Ready**: Docker support, security features, and enterprise-grade architecture

### 🚀 Quick Start with Dashboard

```bash
# 1. Install dashboard dependencies
pip install -r test_dashboard/requirements.txt

# 2. Launch the dashboard server
cd test_dashboard
python launch_dashboard.py

# 3. In another terminal, run your tests with dashboard integration
pytest --dashboard --dashboard-websocket tests/

# 4. Open http://localhost:8080 to see real-time results!
```

### 📚 Complete Dashboard Documentation

The test dashboard system is comprehensively documented:

- **[📊 Dashboard Overview](docs/TEST_DASHBOARD.md)** - Complete feature guide
- **[🔧 Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions
- **[🔌 API Reference](docs/API_REFERENCE.md)** - REST API and WebSocket documentation
- **[🐳 Docker Deployment](docs/DOCKER_DEPLOYMENT.md)** - Container deployment guide
- **[📈 Performance Guide](docs/PERFORMANCE.md)** - Optimization and benchmarks

### 🎯 Dashboard Usage Examples

```bash
# Basic dashboard integration
pytest --dashboard

# Custom database and WebSocket support
pytest --dashboard --dashboard-db=myproject.db --dashboard-websocket

# Named test runs for releases
pytest --dashboard --dashboard-name="Release 2.1.0 Tests"

# Production CI/CD integration
pytest --dashboard --dashboard-name="Build ${BUILD_NUMBER}" \
       --dashboard-db=/data/ci-dashboard.db
```

### 📊 Dashboard API Integration

```python
from test_dashboard.database import TestDashboardDB
from test_dashboard.models import TestResult, TestStatus, TestType

# Programmatic dashboard integration
db = TestDashboardDB("dashboard.db")

# Create test run with metadata
run_id = db.create_test_run(
    test_command="pytest tests/api/",
    git_branch="feature/new-endpoint",
    git_commit="abc123",
    environment_info={
        "python_version": "3.11.0",
        "django_version": "4.2.0",
        "ci_build": "12345"
    }
)

# Add test results
test_result = TestResult(
    test_name="test_chat_endpoint",
    test_file="tests/api/test_chat.py",
    test_type=TestType.API,
    status=TestStatus.PASSED,
    duration_seconds=1.23
)

db.add_test_result(run_id, test_result)
```

### 🏆 Enterprise Features

- **High Performance**: SQLite with WAL mode, connection pooling, optimized queries
- **Real-Time Updates**: WebSocket broadcasting with connection management
- **Security**: CORS protection, input validation, SQL injection prevention
- **Scalability**: Supports 100+ concurrent users, handles 1000+ test runs efficiently
- **Monitoring**: Built-in health checks, metrics, and alerting capabilities
- **Multi-Environment**: Development, staging, and production configurations

---

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/django-ollama.git
cd django-ollama

# Install in development mode
make install-dev

# Run tests
make test

# Run tests with coverage
make test-cov

# Run tests with dashboard monitoring
pytest --dashboard --dashboard-websocket tests/

# Format code
make format

# Run linting
make lint

# Run all checks
make check
```

### Running Tests

```bash
# Install test dependencies
pip install -e .[dev]

# Run all tests
pytest

# Run with coverage
pytest --cov=src/django_ollama --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run with markers
pytest -m "not integration"  # Skip integration tests
pytest -m "ollama"  # Only Ollama-dependent tests
```

### Using with Docker

Create a `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  django:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - ollama
      - redis

volumes:
  ollama_data:
```

## Requirements

- Python 3.9+
- Django 4.2+
- channels 4.0+
- channels-redis 4.0+
- ollama 0.3.0+

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `make check`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### [Unreleased]

#### Added
- Initial release
- WebSocket chat consumer with streaming support
- Knowledge base integration with generic foreign keys
- Session management with conversation history
- Comprehensive test suite
- Type hints throughout
- Async API support
- File upload handling for knowledge bases

#### Changed
- Enhanced from original ollama-django app
- Modern src-layout package structure
- Improved error handling and validation
- Better documentation and examples

## Acknowledgments

- [Ollama](https://ollama.ai/) for the fantastic local LLM platform
- [Django](https://www.djangoproject.com/) for the web framework
- [Django Channels](https://channels.readthedocs.io/) for WebSocket support

## Support

- 📖 [Documentation](https://django-ollama.readthedocs.io/)
- 🐛 [Issue Tracker](https://github.com/yourusername/django-ollama/issues)
- 💬 [Discussions](https://github.com/yourusername/django-ollama/discussions)
- 📧 [Email Support](mailto:support@django-ollama.com)

---

**Made with ❤️ for the Django and Ollama communities**