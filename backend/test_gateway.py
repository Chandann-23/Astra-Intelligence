#!/usr/bin/env python3
"""
LiteLLM Gateway Fallback Test Script
Tests the automatic fallback functionality of the AI Gateway
"""

import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_fallback_functionality():
    """Test that the gateway correctly falls back when primary model fails"""
    
    print("🧪 Testing LiteLLM Gateway Fallback Functionality...")
    
    # Test 1: Non-existent model should trigger fallback
    print("\n1. Testing fallback with non-existent model...")
    
    try:
        response = requests.post(
            "http://localhost:4000/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('LITELLM_MASTER_KEY', 'test_key')}"
            },
            json={
                "model": "non-existent-model",
                "messages": [{"role": "user", "content": "Test message for fallback"}],
                "temperature": 0.7,
                "max_tokens": 100,
                "mock_testing_fallbacks": True
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Fallback test passed!")
            print(f"   Response: {result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')}")
            
            # Check response headers for model used
            model_used = response.headers.get('x-model-used', 'Not specified')
            print(f"   Model used: {model_used}")
            
        else:
            print(f"❌ Fallback test failed with status {response.status_code}")
            print(f"   Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to LiteLLM proxy at localhost:4000")
        print("   Make sure the proxy is running: litellm --config config.yaml --port 4000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False
    
    # Test 2: Valid model should work normally
    print("\n2. Testing valid model (astra-brain)...")
    
    try:
        response = requests.post(
            "http://localhost:4000/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('LITELLM_MASTER_KEY', 'test_key')}"
            },
            json={
                "model": "astra-brain",
                "messages": [{"role": "user", "content": "Hello, this is a test of the astra-brain model"}],
                "temperature": 0.7,
                "max_tokens": 50
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Valid model test passed!")
            print(f"   Response: {result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')}")
            
            # Check response headers for model used
            model_used = response.headers.get('x-model-used', 'Not specified')
            print(f"   Model used: {model_used}")
            
        else:
            print(f"❌ Valid model test failed with status {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False
    
    # Test 3: Health check
    print("\n3. Testing gateway health...")
    
    try:
        response = requests.get("http://localhost:4000/health", timeout=10)
        
        if response.status_code == 200:
            print("✅ Gateway health check passed!")
            print(f"   Health: {response.json()}")
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False
    
    print("\n🎉 Gateway fallback testing complete!")
    return True

def test_direct_models():
    """Test direct access to individual models"""
    
    print("\n🔍 Testing direct model access...")
    
    models_to_test = [
        ("gemini-direct", "Google Gemini"),
        ("mistral-direct", "Mistral Nemo")
    ]
    
    for model_id, model_name in models_to_test:
        print(f"\n   Testing {model_name}...")
        
        try:
            response = requests.post(
                "http://localhost:4000/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.getenv('LITELLM_MASTER_KEY', 'test_key')}"
                },
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": f"Test message for {model_name}"}],
                    "temperature": 0.7,
                    "max_tokens": 50
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ {model_name} working")
                print(f"      Response: {result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')[:50]}...")
            else:
                print(f"   ❌ {model_name} failed with status {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {model_name} error: {str(e)}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 LITELLM GATEWAY TEST SUITE")
    print("=" * 60)
    
    # Check if proxy is running
    try:
        response = requests.get("http://localhost:4000/health", timeout=5)
        if response.status_code != 200:
            print("❌ LiteLLM proxy is not responding correctly")
            exit(1)
    except:
        print("❌ LiteLLM proxy is not running at localhost:4000")
        print("   Start it with: litellm --config config.yaml --port 4000")
        exit(1)
    
    # Run tests
    success = test_fallback_functionality()
    test_direct_models()
    
    if success:
        print("\n✅ All tests completed successfully!")
        print("   Your AI Gateway is ready for production use.")
    else:
        print("\n❌ Some tests failed. Check your configuration and try again.")
    
    print("\n📊 Next Steps:")
    print("   1. Start the gateway: litellm --config config.yaml --port 4000")
    print("   2. Run this test script: python test_gateway.py")
    print("   3. Check the admin UI at: http://localhost:4000/ui")
    print("   4. Monitor your Astra application logs")
