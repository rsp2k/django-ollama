#!/usr/bin/env python3
"""
Quick test of django-ollama with hosted Ollama instance.
"""

import sys
import os
sys.path.insert(0, 'src')

# Configure the hosted Ollama directly
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
os.environ['OLLAMA_HOST'] = 'https://ollama.l.supported.systems'

import django
from django.conf import settings
settings.configure(
    DEBUG=True,
    SECRET_KEY='test',
    INSTALLED_APPS=['django_ollama'],
    OLLAMA_HOST='https://ollama.l.supported.systems',
    OLLAMA_DEFAULT_MODEL='llama3.2',
)
django.setup()

from django_ollama.api import list_models, chat

def test_hosted_ollama():
    """Test the hosted Ollama instance."""
    print("🚀 Testing django-ollama with hosted Ollama instance")
    print("=" * 50)

    try:
        print("📋 Listing available models...")
        models = list_models()
        print(f"Found {len(models)} models:")
        for i, model in enumerate(models[:5]):  # Show first 5
            print(f"  {i+1}. {model['name']}")

        if models:
            # Use the first available model
            test_model = models[0]['name']
            print(f"\n💬 Testing chat with model: {test_model}")

            response = chat(
                prompt="Hello! Can you respond with just 'Hello from django-ollama!' please?",
                model=test_model
            )

            print(f"✅ Response: {response['message']['content']}")
            print("\n🎉 django-ollama package working perfectly!")

        else:
            print("❌ No models available on hosted instance")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("This might be expected if the hosted instance requires authentication")

if __name__ == "__main__":
    test_hosted_ollama()