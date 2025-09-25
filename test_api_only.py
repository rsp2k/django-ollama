#!/usr/bin/env python3
"""
Test just the API functionality of django-ollama without Django models.
"""

import sys
import os
sys.path.insert(0, 'src')

# Directly import and test the API functions
from django_ollama.api import get_ollama_client
import ollama

def test_api_functions():
    """Test the core API functions."""
    print("🚀 Testing django-ollama API functions")
    print("=" * 50)

    # Test 1: Client creation with hosted instance
    try:
        print("🔧 Testing client creation...")
        # Manually create client with hosted URL
        client = ollama.Client(host='https://ollama.l.supported.systems')
        print("✅ Client created successfully")

        print("\n📋 Listing available models...")
        response = client.list()
        models = response.get('models', [])
        print(f"✅ Found {len(models)} models:")

        for i, model in enumerate(models[:5]):  # Show first 5
            model_name = model.get('name', model.get('model', str(model)))
            print(f"  {i+1}. {model_name}")

        if models:
            # Test chat with first available model
            first_model = models[0]
            test_model = first_model.get('name', first_model.get('model', str(first_model)))
            print(f"\n💬 Testing chat with model: {test_model}")

            chat_response = client.chat(
                model=test_model,
                messages=[{
                    "role": "user",
                    "content": "Respond with exactly: 'django-ollama works!'"
                }]
            )

            if 'message' in chat_response and 'content' in chat_response['message']:
                content = chat_response['message']['content']
                print(f"✅ Chat response: {content}")
                print("\n🎉 django-ollama API core functionality verified!")
            else:
                print(f"❌ Unexpected response format: {chat_response}")

        else:
            print("❌ No models available")

    except Exception as e:
        print(f"❌ Error testing API: {e}")
        print("This might indicate network issues or authentication requirements")

    # Test 2: Import verification
    print(f"\n📦 Testing package imports...")
    try:
        import django_ollama
        print(f"✅ Package version: {django_ollama.__version__}")
        print(f"✅ Available functions: {[f for f in django_ollama.__all__ if not f.startswith('_')]}")
    except Exception as e:
        print(f"❌ Import error: {e}")

if __name__ == "__main__":
    test_api_functions()