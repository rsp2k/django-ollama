"""
Hypercorn configuration for Django-Ollama demo with WSGI middleware and security settings.

This configuration enables:
- ASGI and WSGI support for Django + WebSockets
- Request body size limits for security
- HTTP/2 support for better performance
- WebSocket handling for streaming chat
"""

import os
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent

# Server configuration
bind = ["0.0.0.0:8001"]
workers = 1  # Single worker for demo (increase for production)

# Protocol support
h2 = True  # Enable HTTP/2 for better performance
websocket_ping_interval = 20  # Keep WebSocket connections alive

# Security and limits
max_request_size = 16 * 1024 * 1024  # 16MB max request body size
max_request_body_size = 16 * 1024 * 1024  # Alternative setting name

# For file uploads and streaming context
body_timeout = 60  # 60 seconds timeout for request body
request_timeout = 120  # 2 minutes total request timeout

# WebSocket specific settings
websocket_max_message_size = 1024 * 1024  # 1MB max WebSocket message
websocket_ping_timeout = 10

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Error log to stderr
loglevel = "info"

# Development vs Production
debug = True  # Set to False in production

# SSL/TLS (disabled for development)
# keyfile = None
# certfile = None

# Worker class for mixed ASGI/WSGI
# hypercorn automatically detects ASGI apps
worker_class = "asyncio"

# Application import
# Point to Django ASGI application
application_path = "demo_project.demo_project.asgi:application"

# Environment variables
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo_project.demo_project.settings')

# Graceful shutdown
graceful_timeout = 30

# Keep-alive settings
keep_alive_timeout = 5

# Additional security headers (can be configured in Django middleware instead)
# server_names = ["localhost", "127.0.0.1"]

print("Hypercorn configuration loaded:")
print(f"  - Bind: {bind}")
print(f"  - Max request size: {max_request_size} bytes")
print(f"  - HTTP/2: {h2}")
print(f"  - WebSocket ping interval: {websocket_ping_interval}s")
print(f"  - Application: {application_path}")