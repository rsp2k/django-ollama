# Context Injection System Demo

## Overview

The context injection system in django-ollama provides automatic, lazy queryset injection for AI context based on the current request. This allows AI models to have contextually relevant data without manual configuration.

## Core Concept: Lazy Querysets

At its core, the system uses **lazy querysets** - Django QuerySets wrapped with metadata that are only evaluated when the AI needs them:

```python
@dataclass
class LazyQueryset:
    name: str               # Identifier
    queryset: QuerySet      # The Django queryset (not evaluated)
    ai_method: str         # Method to call for AI serialization
    limit: Optional[int]   # Max items to serialize
    priority: int          # Processing order
```

## Key Features

### 1. Automatic Context Injection via Middleware

The `AIContextMiddleware` automatically attaches querysets to every request:

```python
# In settings.py
MIDDLEWARE = [
    # ...
    'django_ollama.context_injection.AIContextMiddleware',
]
```

### 2. View-Level Queryset Injection

Use the `@inject_querysets` decorator to add specific querysets to a view:

```python
@inject_querysets(
    lambda kwargs: Article.objects.filter(pk=kwargs['pk']),
    lambda kwargs: Review.objects.filter(article_id=kwargs['pk'])[:5]
)
def article_detail(request, pk):
    # Querysets automatically available in AI context
    ai_context = get_ai_context(request, evaluate=True)
```

### 3. AI Serialization Protocol

Models implement `__ai_text__` method for AI-friendly serialization:

```python
class Article(models.Model):
    def __ai_text__(self):
        return f"Title: {self.title}\nContent: {self.content}"
```

### 4. Smart Context Detection

The `SmartQuerysetInjector` automatically builds relevant querysets:

- Extracts model from URL parameters (e.g., `/products/42/`)
- Includes user-specific knowledge bases
- Adds session-based querysets
- Filters by permissions automatically

## Demo Application

### Running the Demo

```bash
cd demo_project
python manage.py migrate
python manage.py setup_demo_data
python manage.py runserver
```

### Demo URLs

- **Context Demo**: http://localhost:8000/context-demo/
  - Shows all lazy querysets attached to request
  - Allows evaluating querysets to see AI serialization

- **Article AI View**: http://localhost:8000/article/1/ai/
  - Demonstrates context injection for a specific article
  - Shows related articles automatically included
  - Allows AI queries with injected context

- **Multi-Context View**: http://localhost:8000/multi-context/
  - Shows multiple queryset sources injection
  - Groups querysets by model type

- **Project Context API**: http://localhost:8000/api/project/1/context/
  - JSON API demonstrating programmatic context access
  - Shows priority-based queryset ordering

## Implementation Examples

### Basic Usage

```python
from django_ollama.context_injection import get_ai_context

def my_view(request):
    # Get lazy querysets (not evaluated)
    lazy_context = get_ai_context(request, evaluate=False)

    # Evaluate for AI consumption
    ai_context = get_ai_context(request, evaluate=True)

    # AI context contains serialized data
    for item in ai_context['content']:
        print(f"{item['name']}: {item['count']} items")
        print(item['data'])  # Serialized content
```

### Custom Queryset Injection

```python
from django_ollama.context_injection import LazyQueryset

def product_view(request, product_id):
    # Manually add querysets
    custom_querysets = [
        LazyQueryset(
            name='current_product',
            queryset=Product.objects.filter(pk=product_id),
            priority=20,  # High priority
            limit=1
        ),
        LazyQueryset(
            name='related_products',
            queryset=Product.objects.filter(category_id=...).exclude(pk=product_id),
            priority=10,
            limit=5
        )
    ]

    # Add to context
    request.ai_querysets.extend(custom_querysets)
```

### Custom Injector

```python
from django_ollama.context_injection import QuerysetInjector

class MyCustomInjector(QuerysetInjector):
    def get_querysets(self, request, context=None):
        querysets = []

        # Add custom logic
        if request.user.is_premium:
            querysets.append(LazyQueryset(
                name='premium_content',
                queryset=PremiumContent.objects.all()[:10],
                priority=15
            ))

        return self.filter_by_permissions(querysets, request.user)

# In settings.py
DJANGO_OLLAMA_QUERYSET_INJECTOR = 'myapp.injectors.MyCustomInjector'
```

## Performance Benefits

1. **Lazy Evaluation**: Querysets are not executed until AI needs them
2. **Efficient Counting**: `.count()` and `.exists()` use optimized SQL
3. **Automatic Limiting**: Prevents loading too much data
4. **Priority-Based Processing**: Most important context processed first

## Security Features

- **Server-Side Validation**: All namespace access validated server-side
- **Permission Filtering**: Querysets automatically filtered by user permissions
- **Namespace Isolation**: Content organized in separate namespaces
- **Configurable Policies**: Override security policies as needed

## Testing

The system includes comprehensive tests:

```bash
# Run context injection tests
pytest tests/test_context_injection.py -v

# Test results: 20 passing tests covering:
# - Lazy queryset behavior
# - URL-based injection
# - Permission filtering
# - Middleware integration
# - Decorator functionality
```

## Advanced Features

### URL-Based Injection

Register handlers for specific URL patterns:

```python
injector = URLBasedQuerysetInjector()
injector.register_pattern('product_detail', lambda ctx: [
    LazyQueryset(
        name='product',
        queryset=Product.objects.filter(pk=ctx['kwargs']['pk'])
    )
])
```

### Composite Injectors

Combine multiple injection strategies:

```python
composite = CompositeQuerysetInjector([
    SmartQuerysetInjector(),
    URLBasedQuerysetInjector(),
    CustomBusinessLogicInjector()
])
```

### Session-Based Context

Store queryset definitions in session:

```python
request.session['ai_context_queries'] = [
    {
        'model': 'Article',
        'name': 'user_favorites',
        'filters': {'is_favorite': True},
        'limit': 10,
        'priority': 8
    }
]
```

## Best Practices

1. **Use High Priority for Current Items**: Give the "current" item (e.g., article being viewed) highest priority
2. **Limit Related Items**: Use reasonable limits (3-5) for related content
3. **Implement __ai_text__**: Add AI serialization to all models that might be in context
4. **Test Permissions**: Verify security filtering works as expected
5. **Monitor Performance**: Use `.exists()` checks before evaluation

## Conclusion

The context injection system provides a powerful, flexible way to automatically provide relevant context to AI models based on the current request. By using lazy querysets as the core abstraction, it maintains Django's performance benefits while enabling intelligent context-aware AI responses.