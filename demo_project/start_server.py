#!/usr/bin/env python
"""
Startup script for Django-Ollama demo using Hypercorn.

This script starts the server with proper ASGI/WebSocket support and security configurations.
"""

import os
import sys
import subprocess
from pathlib import Path

# Ensure Django settings are configured
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo_project.demo_project.settings')

# Add the parent directory to path for django_ollama imports
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent / 'src'))

def run_server():
    """Start the Hypercorn server with configuration."""

    # Get server configuration from environment
    server_host = os.environ.get('SERVER_HOST', '0.0.0.0')
    server_port = os.environ.get('SERVER_PORT', '8000')
    bind_address = f"{server_host}:{server_port}"

    print("🚀 Starting Django-Ollama Demo Server with Hypercorn")
    print("=" * 60)
    print(f"🌐 Server binding to: {bind_address}")

    # Check if we're in the right directory
    if not (BASE_DIR / 'manage.py').exists():
        print("❌ Error: manage.py not found. Run this script from the demo_project directory.")
        sys.exit(1)

    # Check if django_ollama is importable
    try:
        import django_ollama
        print(f"✅ django-ollama imported successfully from: {django_ollama.__file__}")
    except ImportError as e:
        print(f"❌ Error importing django_ollama: {e}")
        print("Make sure you're in the virtual environment and the package is installed.")
        sys.exit(1)

    # Run database migrations first
    print("\n📦 Running database migrations...")
    try:
        subprocess.run([
            sys.executable, 'manage.py', 'migrate', '--run-syncdb'
        ], check=True, cwd=BASE_DIR)
        print("✅ Database migrations completed")
    except subprocess.CalledProcessError:
        print("❌ Database migration failed")
        sys.exit(1)

    # Collect static files (if needed)
    print("\n📁 Collecting static files...")
    try:
        subprocess.run([
            sys.executable, 'manage.py', 'collectstatic', '--noinput'
        ], check=True, cwd=BASE_DIR)
        print("✅ Static files collected")
    except subprocess.CalledProcessError:
        print("⚠️  Static file collection failed (continuing anyway)")

    # Start Hypercorn server
    print("\n🌐 Starting Hypercorn server...")
    print(f"📡 WebSocket endpoint: ws://localhost:{server_port}/ws/streaming-chat/")
    print(f"🌍 Web interface: http://localhost:{server_port}/")
    print(f"🎯 Streaming Chat: http://localhost:{server_port}/streaming-chat/")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)

    try:
        # Use direct configuration parameters
        subprocess.run([
            'hypercorn',
            '--bind', bind_address,
            '--workers', '1',
            '--access-logfile', '-',
            '--error-logfile', '-',
            '--log-level', 'info',
            '--websocket-ping-interval', '20',
            'demo_project.demo_project.asgi:application'
        ], cwd=BASE_DIR)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except FileNotFoundError:
        print("❌ Hypercorn not found. Install it with: pip install hypercorn")
        sys.exit(1)

if __name__ == '__main__':
    run_server()