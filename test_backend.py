#!/usr/bin/env python3
"""
Test script to verify Astra Engine fixes
"""

import requests
import json

def test_backend_health():
    """Test backend health endpoint"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        print(f"Health Check Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Health Response: {response.json()}")
            return True
        else:
            print(f"Health Error: {response.text}")
            return False
    except Exception as e:
        print(f"Health Check Failed: {str(e)}")
        return False

def test_research_request():
    """Test research request with fixed LLM configuration"""
    try:
        payload = {"topic": "Explain Neural-Symbolic AI"}
        response = requests.post(
            "http://localhost:8000/stream",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print(f"Research Request Status: {response.status_code}")
        print(f"Research Response: {response.text[:500]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"Research Request Failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Astra Engine Fixes...")
    print("=" * 50)
    
    # Test health
    health_ok = test_backend_health()
    
    if health_ok:
        print("\n✅ Backend is healthy, testing research request...")
        # Test research
        research_ok = test_research_request()
        
        if research_ok:
            print("\n🎉 All tests passed! Astra Engine is working correctly.")
        else:
            print("\n⚠️ Research request failed - check LLM configuration.")
    else:
        print("\n❌ Backend health check failed - check if backend is running.")
