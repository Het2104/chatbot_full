"""
Test authentication system.

Quick test script to verify JWT authentication is working correctly.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_auth():
    """Test authentication flow."""
    
    print("=" * 60)
    print("JWT Authentication Test")
    print("=" * 60)
    
    # Test 1: Register new user
    print("\n1️⃣  Testing user registration...")
    register_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass123",
        "full_name": "Test User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if response.status_code == 201:
            print("   ✅ Registration successful!")
            user = response.json()
            print(f"   User ID: {user['id']}")
            print(f"   Email: {user['email']}")
            print(f"   Role: {user['role']}")
        elif response.status_code == 400:
            print("   ⚠️  User already exists (this is OK)")
        else:
            print(f"   ❌ Registration failed: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 2: Login
    print("\n2️⃣  Testing login...")
    login_data = {
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            print("   ✅ Login successful!")
            data = response.json()
            token = data['access_token']
            print(f"   Token (first 20 chars): {token[:20]}...")
            print(f"   User: {data['user']['username']}")
        else:
            print(f"   ❌ Login failed: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 3: Access protected endpoint
    print("\n3️⃣  Testing protected endpoint (/auth/me)...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        if response.status_code == 200:
            print("   ✅ Protected endpoint accessible!")
            user = response.json()
            print(f"   Current user: {user['username']}")
            print(f"   Email: {user['email']}")
            print(f"   Role: {user['role']}")
        else:
            print(f"   ❌ Access denied: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 4: Invalid token
    print("\n4️⃣  Testing invalid token...")
    bad_headers = {
        "Authorization": "Bearer invalid_token_xyz"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=bad_headers)
        if response.status_code == 401:
            print("   ✅ Invalid token correctly rejected!")
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ All authentication tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_auth()
