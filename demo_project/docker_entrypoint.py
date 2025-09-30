#!/usr/bin/env python
"""
Docker entrypoint script for Django-Ollama demo.
Handles demo data creation and starts the server.
"""

import os
import sys
import subprocess
from pathlib import Path

# Ensure Django settings are configured
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo_project.settings')

# Add the parent directory to path for django_ollama imports
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent / 'src'))

def main():
    """Main entrypoint function."""
    print("🚀 Django-Ollama Docker Container Starting...")
    print("=" * 60)

    # Skip virtual environment setup - use system packages installed during build
    print("🔄 Using system-installed packages...")

    # Run migrations using system Python
    print("🚀 Running migrations...")
    try:
        subprocess.run([
            "python", "manage.py", "migrate"
        ], check=True, cwd=BASE_DIR)
        print("✅ Migrations completed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Migrations failed: {e}")
        sys.exit(1)

    # Collect static files (skip if permission issues)
    print("📁 Collecting static files...")
    try:
        subprocess.run([
            "python", "manage.py", "collectstatic", "--noinput", "--clear"
        ], check=True, cwd=BASE_DIR)
        print("✅ Static files collected")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Static file collection failed: {e}")
        print("📝 Continuing without static files - development mode")

    # Create demo data if needed
    print("📊 Creating demo data...")
    try:
        subprocess.run([
            "python", "manage.py", "create_demo_data"
        ], check=False, cwd=BASE_DIR)  # Don't fail if demo data exists
        print("✅ Demo data ready")
    except Exception as e:
        print(f"⚠️  Demo data creation failed: {e}")

    # Get server configuration from environment
    server_host = os.environ.get('SERVER_HOST', '0.0.0.0')
    server_port = os.environ.get('SERVER_PORT', '8000')

    # Start the server
    print("\n🌐 Starting Django-Ollama server...")
    print(f"📡 WebSocket endpoint: ws://{server_host}:{server_port}/ws/streaming-chat/")
    print(f"🌍 Web interface: http://{server_host}:{server_port}/")
    print(f"🎯 Streaming Chat: http://{server_host}:{server_port}/streaming-chat/")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60)

    # Start Hypercorn server directly
    os.chdir(BASE_DIR)
    os.execvp("hypercorn", [
        "hypercorn",
        "--bind", f"{server_host}:{server_port}",
        "--workers", "1",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "--log-level", "info",
        "--websocket-ping-interval", "20",
        "demo_project.asgi:application"
    ])

if __name__ == '__main__':
    main()
