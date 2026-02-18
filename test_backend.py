"""Quick test to verify backend endpoints are working"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_server():
    print("Testing backend server at", BASE_URL)
    print("-" * 50)
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/chatbots")
        print("✓ Server is running")
        print(f"✓ GET /chatbots - Status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("✗ Server is NOT running")
        print("  Please start the backend server:")
        print("  cd backend")
        print("  python -m uvicorn app.main:app --reload")
        return
    
    # Test 2: Create a test chatbot
    try:
        response = requests.post(
            f"{BASE_URL}/chatbots",
            json={"name": "Test Bot", "description": "Test"}
        )
        print(f"✓ POST /chatbots - Status: {response.status_code}")
        chatbot_data = response.json()
        chatbot_id = chatbot_data["id"]
        print(f"  Created chatbot ID: {chatbot_id}")
    except Exception as e:
        print(f"✗ Failed to create chatbot: {e}")
        return
    
    # Test 3: Start chat
    try:
        response = requests.post(
            f"{BASE_URL}/chat/start",
            json={"chatbot_id": chatbot_id}
        )
        print(f"✓ POST /chat/start - Status: {response.status_code}")
        chat_data = response.json()
        session_id = chat_data["session_id"]
        print(f"  Created session ID: {session_id}")
    except Exception as e:
        print(f"✗ Failed to start chat: {e}")
        return
    
    # Test 4: Send message (THIS IS WHERE THE ERROR IS)
    try:
        response = requests.post(
            f"{BASE_URL}/chat/message",
            json={"session_id": session_id, "message": "Hello"}
        )
        print(f"✓ POST /chat/message - Status: {response.status_code}")
        if response.status_code == 200:
            message_data = response.json()
            print(f"  Bot response: {message_data['bot_response'][:50]}...")
        else:
            print(f"  Error: {response.text}")
    except Exception as e:
        print(f"✗ Failed to send message: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("-" * 50)
    print("All tests passed!")

if __name__ == "__main__":
    test_server()
