# Django-Ollama Namespace Demo

This demo application showcases the namespace features of django-ollama with server-side security enforcement.

## Features Demonstrated

- **Namespace Isolation**: Content organized in separate namespaces
- **Server-Side Security**: All namespace access validated server-side
- **Multi-Tenant Support**: Different teams/organizations with isolated data
- **Flexible Access Control**: Default, owned, and public namespace access
- **API Security**: Client requests validated against server policies

## Quick Start

### 1. Set up the demo

```bash
cd demo_project

# Run migrations
python manage.py migrate

# Create demo data
python manage.py setup_demo_data

# Run the development server
python manage.py runserver
```

### 2. Access the demo

Visit http://localhost:8000 to see the demo.

### 3. Demo Users

The setup creates these demo users:

- **demo_alice** / demo123 - Engineering team owner
- **demo_bob** / demo123 - Marketing team owner
- **demo_charlie** / demo123 - Research team owner
- **demo_admin** / admin123 - Superuser with full access

### 4. Test Different Access Levels

1. **Anonymous Access**: Browse without logging in
   - Can see: Default namespace, public knowledge bases
   - Cannot see: Private namespaces or content

2. **Alice's Access**: Log in as demo_alice
   - Can see: Default, Engineering (owned), Marketing (public)
   - Cannot see: Research (private, not owned)

3. **Admin Access**: Log in as demo_admin
   - Can see: All namespaces and content
   - Can modify: Any namespace or content

## Key Components

### Models (`knowledge_demo/models.py`)

- **Project**: Groups content with a knowledge base in a namespace
- **Article**: Text content linked to knowledge bases
- **Document**: File uploads with namespace isolation

### Views (`knowledge_demo/views.py`)

- **index**: Shows accessible namespaces based on user permissions
- **namespace_detail**: Displays namespace content with access control
- **api_namespace_access**: API endpoint demonstrating server validation

### Security (`django_ollama/namespace_security.py`)

- **NamespaceSecurityMiddleware**: Enforces access control
- **DefaultNamespacePolicy**: Default role-based access
- **Custom Policies**: Overridable for custom requirements

## Testing Security

### API Test

The home page includes an API tester. Try requesting unauthorized namespaces:

1. Without logging in, request: `secret, private`
   - Result: Access denied

2. Log in as demo_alice, request: `engineering, research`
   - Result: Access denied to 'research'

3. Log in as demo_admin, request: `engineering, research`
   - Result: Access granted to all

### Integration Tests

Run the integration tests:

```bash
python manage.py test knowledge_demo
```

## Architecture

```
Client Request
     ↓
Server Validation (NamespaceSecurityMiddleware)
     ↓
Policy Check (DefaultNamespacePolicy)
     ↓
Access Granted/Denied
```

The key security principle: **The server always validates client requests**. Clients can request any namespaces, but the server determines what's actually accessible based on the user's permissions.

## Customization

### Custom Security Policy

Create a custom policy by subclassing `NamespaceAccessPolicy`:

```python
from django_ollama.namespace_security import NamespaceAccessPolicy

class MyCustomPolicy(NamespaceAccessPolicy):
    def get_allowed_namespaces(self, user, request=None, context=None):
        # Custom logic here
        pass

    def can_access_namespace(self, user, namespace, request=None, context=None):
        # Custom access check
        pass
```

Configure in settings.py:
```python
DJANGO_OLLAMA_NAMESPACE_POLICY = 'myapp.security.MyCustomPolicy'
```

## Production Considerations

1. **Database**: Use PostgreSQL for production
2. **Channels**: Use Redis channel layer instead of InMemoryChannelLayer
3. **Security**: Enable HTTPS and proper CORS settings
4. **Ollama**: Configure OLLAMA_HOST for your Ollama server