"""
Quick script to verify backend is working with fixes
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_backend():
    print("="*70)
    print("BACKEND TEST - Verifying Server Status")
    print("="*70)
    
    # Test 1: Check if backend is running
    print("\n1. Checking if backend is running...")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=2)
        if response.status_code == 200:
            print("   ✅ Backend is running")
        else:
            print(f"   ❌ Backend returned status: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("   ❌ Backend is not running!")
        print("   Please start it with: uvicorn app.main:app --reload")
        return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 2: Start a chat session
    print("\n2. Starting chat session...")
    try:
        response = requests.post(f"{BASE_URL}/api/chat/start", json={"chatbot_id": 9})
        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session_id")
            print(f"   ✅ Chat session started: {session_id}")
            
            # Test 3: Send test message
            print("\n3. Testing RAG query...")
            test_message = {"session_id": session_id, "message": "features of PyPDF2"}
            response = requests.post(f"{BASE_URL}/api/chat/message", json=test_message)
            
            if response.status_code == 200:
                data = response.json()
                bot_response = data.get("response", "")
                
                if bot_response and bot_response != "I didn't understand":
                    print(f"   ✅ RAG working! Got {len(bot_response)} char answer")
                    print(f"\n   Response preview:")
                    preview = bot_response[:150] + "..." if len(bot_response) > 150 else bot_response
                    for line in preview.split('\n'):
                        print(f"   {line}")
                else:
                    print(f"   ❌ Got default response: {bot_response}")
            else:
                print(f"   ❌ Message failed: {response.status_code}")
        else:
            print(f"   ❌ Failed to start session: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    test_backend()
