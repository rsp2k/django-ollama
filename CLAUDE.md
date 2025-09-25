# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the django-ollama package.

## Project Overview

Django-Ollama is a modern Python package that integrates Django with Ollama local LLMs, providing real-time chat capabilities through WebSockets and comprehensive test monitoring. This project uses modern Python packaging standards with src-layout structure and includes a production-ready test dashboard system.

## Development Environment

### Package Structure
- **src-layout**: Modern Python packaging with `src/django_ollama/` as the main package
- **uv for dependency management**: Use `uv` instead of pip for package management
- **setuptools-scm**: Automatic version management from git tags
- **Test dashboard**: Complete real-time test monitoring system in `test_dashboard/`
- **Comprehensive testing**: pytest with Django integration and 54%+ coverage

### Development Commands

#### Package Management (use uv!)
- `uv pip install -e ".[dev]"` - Install package in development mode with all dev dependencies
- `make install-dev` - Same as above, using Makefile
- `make install` - Install package without dev dependencies

#### Testing with Dashboard
- `pytest --dashboard tests/` - Run tests with dashboard integration
- `pytest --dashboard --dashboard-websocket tests/` - Run with real-time monitoring
- `python test_dashboard/launch_dashboard.py` - Start standalone dashboard
- `make test` - Run standard test suite
- `make test-cov` - Run tests with coverage reporting

#### Code Quality
- `make format` - Format code with black and isort
- `make lint` - Run linting (flake8, mypy, bandit)
- `make check` - Run all quality checks and tests
- `pre-commit run --all-files` - Run pre-commit hooks manually

#### Building and Publishing
- `make build` - Build package distributions
- `make publish-test` - Publish to TestPyPI
- `make publish` - Publish to PyPI (production)

### Dependencies

#### Runtime Dependencies (pyproject.toml)
- Django>=4.2: Web framework
- ollama>=0.3.0: Python client for Ollama
- channels>=4.0.0: WebSocket support
- channels-redis>=4.0.0: Redis channel layer

#### Dashboard Dependencies ([dashboard] extra)
- fastapi: Web server for dashboard
- websockets: Real-time communication
- jinja2: Template engine
- chart.js: Interactive charts
- sqlite3: Test result storage

#### Development Dependencies ([dev] extra)
- pytest ecosystem: Testing framework with Django integration
- black, isort, flake8, mypy: Code formatting and linting
- pre-commit: Git hook management
- sphinx: Documentation generation

## Architecture

### Core Components
- **`src/django_ollama/api.py`**: High-level API functions (sync/async)
- **`src/django_ollama/models.py`**: Django models for knowledge bases and chat sessions
- **`src/django_ollama/consumers.py`**: WebSocket consumers for real-time chat
- **`src/django_ollama/apps.py`**: Django app configuration

### Test Dashboard System
- **`test_dashboard/database.py`**: SQLite database operations for test results
- **`test_dashboard/server.py`**: FastAPI server with WebSocket support
- **`test_dashboard/templates/`**: Beautiful HTML dashboard interface
- **`test_dashboard/plugins/`**: pytest integration plugins

### Key Features
- **Real-time Chat**: WebSocket-powered streaming responses
- **Knowledge Base Integration**: Link any Django model using generic foreign keys
- **Session Management**: Persistent chat sessions with conversation history
- **Test Dashboard**: Live test monitoring with historical analytics
- **Async Support**: Both synchronous and asynchronous API patterns

## Testing Strategy

### Test Structure
- **`tests/test_api.py`**: API function tests (mocked, no Ollama required)
- **`tests/test_api_advanced.py`**: Advanced API scenarios and edge cases
- **`tests/test_models.py`**: Django model tests (require Django setup)
- **`tests/test_models_advanced.py`**: Complex model scenarios and relationships
- **`tests/test_consumers.py`**: WebSocket consumer testing
- **`tests/test_apps.py`**: Django app configuration tests
- **Integration tests**: End-to-end workflow validation

### Test Configuration
- **Django settings**: `tests/settings.py` with comprehensive configuration
- **ASGI/WSGI setup**: `tests/asgi.py` and `tests/wsgi.py` for WebSocket testing
- **In-memory database**: SQLite `:memory:` for fast tests
- **Mock services**: External services (Ollama) are mocked in unit tests

### Running Tests
- **Basic testing**: `pytest tests/` - Standard test execution
- **With dashboard**: `pytest --dashboard tests/` - Test with dashboard integration
- **Real-time monitoring**: `pytest --dashboard --dashboard-websocket tests/`
- **Coverage analysis**: `pytest --cov=src/django_ollama --cov-report=html`
- **Integration tests**: `pytest -m integration` (require Ollama server)

### Test Dashboard Features
- **Live Test Execution**: Real-time progress bars and status updates
- **Coverage Visualization**: Interactive file-level coverage heatmaps
- **Historical Trends**: Performance analysis and flaky test detection
- **Error Analysis**: Detailed failure tracking with stack traces
- **Multi-Environment**: Support for dev, staging, and production test runs

## Integration with Ollama

### Development Setup
- **Hosted Instance**: Use `https://ollama.l.supported.systems` for testing
- **Local Instance**: Run `ollama serve` on `http://localhost:11434`
- **Test Models**: Use lightweight models like `llama3.2:1b` for development
- **Mock in Unit Tests**: Use `unittest.mock` to avoid requiring Ollama for basic tests

### Configuration
```python
# Django settings
OLLAMA_HOST = "http://localhost:11434"  # or hosted instance
OLLAMA_DEFAULT_MODEL = "llama3.2"

# Test dashboard
DJANGO_OLLAMA_DASHBOARD_PORT = 8080
DJANGO_OLLAMA_DASHBOARD_HOST = "localhost"
```

### Example Commands
```bash
# Test with hosted Ollama
OLLAMA_HOST=https://ollama.l.supported.systems pytest --dashboard tests/

# Run integration tests (requires Ollama server)
pytest -m ollama tests/

# Start dashboard with custom database
python test_dashboard/server.py --db=custom.db --port=9000
```

## Examples and Usage

### Testing the Package
- **`examples/basic_usage.py`**: Standalone example showing all core features
- **`examples/websocket_example.html`**: HTML/JavaScript WebSocket client
- **`test_dashboard/demo_integration.py`**: Complete dashboard integration example

### Key Usage Patterns
```python
# Direct API usage
from django_ollama import chat, generate

response = chat("Hello!")
print(response['message']['content'])

# Async usage
from django_ollama import achat
response = await achat("Hello!")

# Django models (requires Django configuration)
from django_ollama.models import KnowledgeBase, ChatSession

# Test dashboard integration
from test_dashboard import TestDashboardDB
db = TestDashboardDB()
run_id = db.create_test_run("pytest tests/")
```

## CI/CD and Automation

### GitHub Actions
- **`.github/workflows/test.yml`**: Run tests on multiple Python/Django versions with dashboard integration
- **`.github/workflows/publish.yml`**: Automated publishing to PyPI on git tags
- **`.github/workflows/docs.yml`**: Documentation building and deployment

### Version Management
- **setuptools-scm**: Versions automatically generated from git tags
- **Tag format**: Use `v1.0.0` format for releases
- **Development versions**: Generated from git commit info

### Test Dashboard in CI/CD
```yaml
# Example GitHub Actions integration
- name: Run tests with dashboard
  run: |
    pytest --dashboard --dashboard-name="Build ${{ github.run_number }}" \
           --dashboard-db=ci-results.db tests/

- name: Upload dashboard results
  uses: actions/upload-artifact@v3
  with:
    name: test-dashboard
    path: ci-results.db
```

## Package Distribution

### PyPI Publishing
- **Test releases**: Published to TestPyPI first
- **Production releases**: Tagged commits trigger automated PyPI publishing
- **Package name**: `django-ollama` on PyPI

### Installation by Users
```bash
# End users install with:
pip install django-ollama

# With dashboard support:
pip install django-ollama[dashboard]

# Add to Django INSTALLED_APPS:
INSTALLED_APPS = [
    # ...
    'channels',
    'django_ollama',
]
```

## Common Development Tasks

### Adding New Features
1. Add functionality to appropriate module in `src/django_ollama/`
2. Add tests in corresponding `tests/test_*.py` file
3. Test with dashboard: `pytest --dashboard tests/`
4. Update documentation in README.md if needed
5. Run `make check` to ensure all tests and linting pass

### Working with Test Dashboard
1. **Start dashboard**: `python test_dashboard/launch_dashboard.py`
2. **Run tests with monitoring**: `pytest --dashboard --dashboard-websocket tests/`
3. **View results**: Visit `http://localhost:8080`
4. **Custom configuration**: Use CLI flags for database, port, naming
5. **Integration testing**: Use `test_dashboard/demo_integration.py` for examples

### Debugging Issues
- Use `pytest -v -s --dashboard` for verbose test output with dashboard
- Check dashboard logs at `test_dashboard/logs/`
- Verify Ollama server is running for integration tests
- Use `make clean` to clear build artifacts and test databases
- Check WebSocket connections in browser developer tools

### Performance Considerations
- **WebSocket streaming**: Designed for real-time response streaming
- **Database queries**: Models optimized with proper indexing
- **Test dashboard**: SQLite with WAL mode for concurrent access
- **Async patterns**: Full async/await support for non-blocking operations

## Important Notes

- **Always use uv**: Prefer `uv` over `pip` for dependency management
- **Test with dashboard**: Use `--dashboard` flag to monitor test health
- **Django compatibility**: Supports Django 4.2+
- **Python compatibility**: Supports Python 3.9+
- **Modern packaging**: Uses pyproject.toml, not setup.py
- **Test coverage**: Aim for 85%+ coverage, currently at 54%

## Test Dashboard Markers

The pytest configuration includes special markers for dashboard integration:

```python
# pytest.ini markers
dashboard_track: marks tests for special dashboard tracking
dashboard_ignore: marks tests to ignore in dashboard (still runs)
slow: marks tests as slow (deselect with '-m "not slow"')
integration: marks tests as integration tests
ollama: marks tests that require Ollama server connection
```

### Usage Examples
```python
import pytest

@pytest.mark.dashboard_track
@pytest.mark.integration
def test_important_workflow():
    """This test will be specially tracked in dashboard."""
    pass

@pytest.mark.dashboard_ignore
@pytest.mark.slow
def test_long_running():
    """This test runs but won't clutter dashboard."""
    pass
```

## Troubleshooting

### Common Issues
1. **Import errors**: Ensure package installed with `uv pip install -e ".[dev]"`
2. **Test failures**: Check Django settings and Ollama server status
3. **Dashboard not starting**: Verify port availability and dependencies
4. **WebSocket issues**: Check browser console and network tab
5. **Coverage problems**: Use test dashboard for detailed coverage analysis

### Test Dashboard Issues
- **Dashboard won't start**: Check `test_dashboard/requirements.txt` dependencies
- **No real-time updates**: Verify WebSocket connection in browser
- **Database locked**: Stop other dashboard instances or use different database
- **Port conflicts**: Use `--port` flag to specify different port

### Getting Help
- Check existing tests for usage patterns
- Run examples to verify setup (`examples/basic_usage.py`)
- Use `make help` to see all available commands
- Check GitHub Issues for known problems
- Review dashboard logs for debugging information

## Advanced Configuration

### Custom Dashboard Setup
```bash
# Production dashboard setup
python test_dashboard/server.py \
  --host=0.0.0.0 \
  --port=8080 \
  --db=/data/production-dashboard.db \
  --log-level=INFO

# Development with hot reload
python test_dashboard/server.py --reload --debug
```

### Integration Examples
```python
# Custom test run tracking
from test_dashboard import TestDashboardDB

db = TestDashboardDB("custom.db")
run_id = db.create_test_run(
    test_command="pytest api_tests/",
    git_branch="feature/new-api",
    environment_info={"deployment": "staging"}
)

# Real-time WebSocket updates
from test_dashboard.realtime import DashboardWebSocket
ws = DashboardWebSocket()
await ws.broadcast_test_update({
    "type": "test_completed",
    "test_name": "test_critical_feature",
    "status": "passed"
})
```

This comprehensive guide ensures that any developer working on django-ollama can quickly understand the architecture, run tests effectively, and utilize the powerful test dashboard system for monitoring and improving code quality.