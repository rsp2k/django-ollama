# Installation & Setup Guide

Complete installation and setup instructions for the Django-Ollama Test Dashboard system.

## 📋 Prerequisites

### System Requirements

- **Python**: 3.9 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 512MB RAM, recommended 1GB+
- **Storage**: 100MB+ free disk space
- **Network**: Internet connection for initial dependencies

### Required Dependencies

The test dashboard requires these core dependencies:

```bash
# Core Python packages
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
websockets>=12.0
sqlite3  # Built into Python
pathlib  # Built into Python

# Optional but recommended
redis>=5.0.0  # For advanced caching
nginx>=1.20   # For production reverse proxy
```

## 🚀 Installation Methods

### Method 1: Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/django-ollama.git
cd django-ollama

# Install the main package with test dashboard dependencies
pip install -e .[dev,testing]

# Install test dashboard specific requirements
pip install -r test_dashboard/requirements.txt

# Verify installation
python test_dashboard/server.py --help
```

### Method 2: Manual Installation

```bash
# 1. Install main django-ollama package
pip install django-ollama

# 2. Install test dashboard dependencies
pip install fastapi uvicorn[standard] websockets

# 3. Download test dashboard files (if not included)
curl -O https://raw.githubusercontent.com/your-org/django-ollama/main/test_dashboard.tar.gz
tar -xzf test_dashboard.tar.gz
```

### Method 3: Docker Installation

```bash
# Clone repository
git clone https://github.com/your-org/django-ollama.git
cd django-ollama

# Build Docker image
docker build -t django-ollama-dashboard -f test_dashboard/Dockerfile .

# Run container
docker run -p 8080:8080 -v $(pwd)/data:/app/data django-ollama-dashboard
```

## 🔧 Configuration

### 1. Basic Configuration

Create a configuration file:

```python
# test_dashboard/config.py
import os
from pathlib import Path

DASHBOARD_CONFIG = {
    # Database settings
    'database_path': os.getenv('DASHBOARD_DB_PATH', 'test_dashboard.db'),
    'retention_days': int(os.getenv('DASHBOARD_RETENTION_DAYS', '30')),

    # Server settings
    'host': os.getenv('DASHBOARD_HOST', '0.0.0.0'),
    'port': int(os.getenv('DASHBOARD_PORT', '8080')),

    # WebSocket settings
    'websocket_enabled': os.getenv('WEBSOCKET_ENABLED', 'true').lower() == 'true',
    'websocket_port': int(os.getenv('WEBSOCKET_PORT', '8765')),

    # Security settings
    'cors_origins': os.getenv('CORS_ORIGINS', '*').split(','),
    'auth_required': os.getenv('AUTH_REQUIRED', 'false').lower() == 'true',

    # Logging
    'log_level': os.getenv('LOG_LEVEL', 'info').upper(),
}
```

### 2. Environment Variables

Create a `.env` file in the `test_dashboard/` directory:

```bash
# .env file
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080
DASHBOARD_DB_PATH=test_dashboard.db

# Database configuration
DASHBOARD_RETENTION_DAYS=30
DB_BACKUP_ENABLED=true

# WebSocket configuration
WEBSOCKET_ENABLED=true
WEBSOCKET_PORT=8765

# Security settings
CORS_ORIGINS=http://localhost:3000,https://dashboard.company.com
AUTH_REQUIRED=false

# Logging
LOG_LEVEL=info
DEBUG=false

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379/0
```

### 3. Django Integration

Add to your Django `settings.py`:

```python
# settings.py
INSTALLED_APPS = [
    # ... your other apps
    'django_ollama',
]

# Test Dashboard Configuration
TEST_DASHBOARD = {
    'enabled': True,
    'database_path': BASE_DIR / 'test_dashboard.db',
    'auto_start': True,  # Start with runserver in development
    'websocket_enabled': True,
}

# Optional: Integration with Django test runner
TEST_RUNNER = 'test_dashboard.runners.DashboardTestRunner'
```

### 4. pytest Configuration

Update your `pytest.ini`:

```ini
[tool:pytest]
# Existing configuration...

# Dashboard integration
addopts =
    --strict-markers
    --strict-config
    --verbose
    --dashboard  # Enable by default

# Dashboard markers
markers =
    dashboard_track: Track this test in dashboard with special attention
    dashboard_ignore: Run test but don't track in dashboard
    slow: Mark test as slow (may affect dashboard display)
    integration: Integration test marker
    unit: Unit test marker
    api: API test marker
    e2e: End-to-end test marker

# Dashboard plugin (optional - can enable via command line)
# pytest_plugins = test_dashboard.plugins.pytest_dashboard

# Test paths
testpaths = tests
```

## 🔨 Database Setup

### 1. Automatic Setup

The database will be automatically created when you first run the dashboard:

```bash
cd test_dashboard
python server.py

# Database will be created at test_dashboard.db
# Schema will be automatically migrated to latest version
```

### 2. Manual Database Setup

```bash
# Create database manually
cd test_dashboard
python -c "
from database import TestDashboardDB
db = TestDashboardDB('test_dashboard.db')
print('Database created successfully')
"

# Verify database schema
sqlite3 test_dashboard.db ".tables"
# Should output: test_runs, test_results, coverage_data, test_metrics
```

### 3. Database Migration

```bash
# Check current schema version
python -c "
from migrations.migration_manager import MigrationManager
manager = MigrationManager('test_dashboard.db', 'migrations/')
print(f'Current version: {manager.get_current_version()}')
print(f'Latest version: {manager.get_latest_version()}')
"

# Run migrations manually
python -c "
from migrations.migration_manager import MigrationManager
manager = MigrationManager('test_dashboard.db', 'migrations/')
success = manager.migrate()
print(f'Migration successful: {success}')
"
```

## 🌐 Web Server Setup

### 1. Development Server

```bash
# Basic development server
cd test_dashboard
python server.py

# With custom configuration
python server.py --host 127.0.0.1 --port 8080 --reload --log-level debug

# Using uvicorn directly
uvicorn server:app --host 0.0.0.0 --port 8080 --reload
```

### 2. Production Server

```bash
# Production server with gunicorn
pip install gunicorn

# Run with gunicorn
cd test_dashboard
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080

# With configuration file
gunicorn -c gunicorn.conf.py server:app
```

Create `gunicorn.conf.py`:

```python
# gunicorn.conf.py
bind = "0.0.0.0:8080"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
keepalive = 5
timeout = 30
graceful_timeout = 30
```

### 3. Reverse Proxy Setup (Nginx)

Create `/etc/nginx/sites-available/test-dashboard`:

```nginx
server {
    listen 80;
    server_name dashboard.your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dashboard.your-domain.com;

    # SSL configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Static files
    location /static/ {
        alias /path/to/test_dashboard/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API and dashboard
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/test-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🐳 Docker Setup

### 1. Basic Docker Setup

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run server
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8080"]
```

### 2. Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  dashboard:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - dashboard_data:/app/data
      - ./logs:/app/logs
    environment:
      - DASHBOARD_DB_PATH=/app/data/dashboard.db
      - LOG_LEVEL=info
      - WEBSOCKET_ENABLED=true
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - dashboard
    restart: unless-stopped

volumes:
  dashboard_data:
  redis_data:
```

## 🔧 Advanced Configuration

### 1. Database Optimization

```python
# Advanced database configuration
DATABASE_CONFIG = {
    'connection_pool_size': 20,
    'wal_mode': True,
    'synchronous': 'NORMAL',
    'cache_size': 10000,
    'temp_store': 'MEMORY',
    'mmap_size': 268435456,  # 256MB
    'vacuum_schedule': 'weekly',
    'analyze_schedule': 'daily',
}
```

### 2. WebSocket Configuration

```python
# WebSocket server configuration
WEBSOCKET_CONFIG = {
    'host': '0.0.0.0',
    'port': 8765,
    'max_connections': 100,
    'ping_interval': 20,
    'ping_timeout': 10,
    'close_timeout': 10,
    'max_message_size': 1024 * 1024,  # 1MB
    'compression': 'deflate',
}
```

### 3. Security Configuration

```python
# Security settings
SECURITY_CONFIG = {
    'cors_origins': ['https://dashboard.company.com'],
    'cors_credentials': True,
    'cors_methods': ['GET', 'POST', 'PUT', 'DELETE'],
    'cors_headers': ['*'],

    # Rate limiting
    'rate_limits': {
        'api': '100/minute',
        'websocket': '10/second',
        'global': '1000/hour',
    },

    # Authentication
    'auth_required': True,
    'auth_header': 'Authorization',
    'jwt_secret': 'your-secret-key',
    'jwt_algorithm': 'HS256',
    'jwt_expiry': 3600,  # 1 hour

    # HTTPS
    'https_only': True,
    'ssl_cert_path': '/path/to/cert.pem',
    'ssl_key_path': '/path/to/key.pem',
}
```

## ✅ Verification & Testing

### 1. Installation Verification

```bash
# 1. Check Python version
python --version
# Should output: Python 3.9.x or higher

# 2. Verify package installation
python -c "import test_dashboard; print('Test dashboard imported successfully')"

# 3. Check database creation
cd test_dashboard
python -c "
from database import TestDashboardDB
db = TestDashboardDB('test.db')
print('Database created successfully')
"

# 4. Test server startup
python server.py --help
# Should show command-line options

# 5. Test API endpoints
curl http://localhost:8080/api/health
# Should return: {"status": "healthy", ...}
```

### 2. Integration Testing

```bash
# Run complete integration test
cd test_dashboard
python -m pytest test_integration.py -v

# Test pytest plugin
cd ..
pytest --dashboard --dashboard-name="Installation Test" tests/ -v

# Test WebSocket functionality
cd test_dashboard
python websocket_test.py
```

### 3. Performance Testing

```bash
# Database performance test
python -c "
from database import TestDashboardDB
import time

db = TestDashboardDB('perf_test.db')
start = time.time()

# Create 1000 test runs
for i in range(1000):
    run_id = db.create_test_run(f'test-{i}')

end = time.time()
print(f'Created 1000 test runs in {end-start:.2f}s')
"

# Server load test (requires 'ab' - Apache Bench)
ab -n 1000 -c 10 http://localhost:8080/api/health
```

## 🚨 Troubleshooting Installation

### Common Issues

**1. Python Version Error**
```bash
# Error: Python 3.8 or lower
# Solution: Upgrade Python
sudo apt update
sudo apt install python3.11
python3.11 -m venv venv
source venv/bin/activate
```

**2. Permission Denied**
```bash
# Error: Permission denied on database file
# Solution: Fix permissions
chmod 755 test_dashboard/
chmod 644 test_dashboard.db
chown $USER:$USER test_dashboard.db
```

**3. Port Already in Use**
```bash
# Error: Port 8080 already in use
# Solution: Find and kill process or use different port
sudo lsof -i :8080
sudo kill -9 <PID>
# Or use different port
python server.py --port 8081
```

**4. Module Import Error**
```bash
# Error: ModuleNotFoundError: No module named 'test_dashboard'
# Solution: Install in development mode
pip install -e .
# Or add to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**5. SQLite Database Locked**
```bash
# Error: Database is locked
# Solution: Close all connections and restart
fuser test_dashboard.db
sudo kill -9 <PID>
# Or delete and recreate
rm test_dashboard.db
python -c "from database import TestDashboardDB; TestDashboardDB()"
```

### Getting Help

If you encounter issues not covered here:

1. **Check the logs**:
   ```bash
   python server.py --log-level debug
   ```

2. **Search existing issues**:
   [GitHub Issues](https://github.com/your-org/django-ollama/issues)

3. **Create a new issue** with:
   - Python version (`python --version`)
   - Operating system
   - Full error message
   - Steps to reproduce

4. **Community support**:
   - [Discord Server](https://discord.gg/django-ollama)
   - [Stack Overflow](https://stackoverflow.com/questions/tagged/django-ollama)

## 🎉 Next Steps

Once installation is complete:

1. **[Quick Start Guide](QUICK_START.md)** - Get your first dashboard running
2. **[Configuration Guide](CONFIGURATION.md)** - Advanced configuration options
3. **[API Reference](API_REFERENCE.md)** - Complete API documentation
4. **[Dashboard Guide](DASHBOARD_GUIDE.md)** - Using the web interface

---

**Installation complete!** 🎉 Ready to start monitoring your tests? Head to the [Quick Start Guide](QUICK_START.md)!