"""Test script for portfolio chatbot features.

Tests:
1. Tool calling (Calendly, Contact, Portfolio)
2. Lead signal detection
3. Lead capture
4. Admin endpoints
"""

import json
import requests
import time

API_URL = "http://localhost:8000"


def test_health():
    """Test API health check."""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200, "Health check failed"
    print("✓ Health check passed")


def test_chat_with_tools():
    """Test chat with function calling."""
    print("\n=== Testing Chat with Function Calling ===")

    # Test message that should trigger scheduling tool
    response = requests.post(
        f"{API_URL}/chat",
        json={
            "message": "I'd like to schedule a technical interview with Dan",
            "user_id": "test_recruiter",
            "model": "gpt-4o-mini",
            "top_k": 3,
        },
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    if response.status_code != 200:
        print(f"ERROR Response: {json.dumps(data, indent=2)}")
        raise Exception(f"Chat request failed: {data}")

    print(f"Answer: {data['answer'][:200]}...")
    print(f"Session ID: {data['session_id']}")
    print(f"Tool Calls: {json.dumps(data.get('tool_calls', []), indent=2)}")
    print(f"Lead Capture: {data.get('lead_capture')}")

    assert response.status_code == 200, "Chat request failed"
    print("✓ Chat with tools test passed")

    return data["session_id"]


def test_lead_detection(session_id):
    """Test lead signal detection with multiple messages."""
    print("\n=== Testing Lead Signal Detection ===")

    # Simulate a recruiting conversation
    messages = [
        "What experience does Dan have with Python?",
        "Tell me about his system design skills",
        "Has he worked with microservices architecture?",
        "What's his availability for a full-time role?",
        "Can you tell me about his compensation expectations?",
    ]

    for i, msg in enumerate(messages, 1):
        print(f"\nMessage {i}: {msg}")
        response = requests.post(
            f"{API_URL}/chat",
            json={
                "message": msg,
                "session_id": session_id,
                "user_id": "test_recruiter",
                "model": "gpt-4o-mini",
                "top_k": 3,
            },
        )

        data = response.json()
        lead_capture = data.get("lead_capture")

        if lead_capture:
            print("🎯 Lead capture triggered!")
            print(f"   Interest level: {lead_capture.get('interest_level')}")
            print(f"   Trigger: {lead_capture.get('trigger')}")
            print(f"   Message: {lead_capture.get('message')}")
            return session_id
        else:
            print("   No lead capture yet")

        time.sleep(0.5)  # Small delay between messages

    print("✓ Lead detection test completed")
    return session_id


def test_lead_capture(session_id):
    """Test lead capture endpoint."""
    print("\n=== Testing Lead Capture ===")

    response = requests.post(
        f"{API_URL}/leads/capture",
        json={
            "session_id": session_id,
            "email": "recruiter@example.com",
            "name": "Jane Smith",
            "company": "Tech Corp",
            "role": "Senior Recruiter",
            "interest_level": "high",
        },
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Lead ID: {data.get('lead_id')}")
    print(f"Message: {data.get('message')}")

    assert response.status_code == 200, "Lead capture failed"
    print("✓ Lead capture test passed")

    return data.get("lead_id")


def test_admin_endpoints(session_id, lead_id):
    """Test admin endpoints."""
    print("\n=== Testing Admin Endpoints ===")

    # Test conversations list
    print("\n1. List Conversations")
    response = requests.get(
        f"{API_URL}/admin/conversations",
        params={"user_id": "test_recruiter", "limit": 10},
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found {data.get('total')} conversations")
    if data.get("conversations"):
        print(f"Latest: {data['conversations'][0]['session_id']}")

    # Test get specific conversation
    print("\n2. Get Specific Conversation")
    response = requests.get(f"{API_URL}/admin/conversations/{session_id}")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Session: {data['session']['id']}")
    print(f"Messages: {len(data['messages'])}")
    print(f"Lead: {data.get('lead', {}).get('email', 'None')}")

    # Test list leads
    print("\n3. List Leads")
    response = requests.get(f"{API_URL}/admin/leads", params={"limit": 10})
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Found {data.get('total')} leads")
    if data.get("leads"):
        for lead in data["leads"][:3]:
            print(f"  - {lead['email']} ({lead['interest_level']})")

    # Test analytics
    print("\n4. Analytics Dashboard")
    response = requests.get(f"{API_URL}/admin/analytics")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Lead stats: {data.get('leads')}")
    print(
        f"Pipeline stats: Vector count = {data.get('pipeline', {}).get('vector_count', 0)}"
    )

    print("✓ Admin endpoints test passed")


def test_contact_tool():
    """Test contact information tool."""
    print("\n=== Testing Contact Tool ===")

    response = requests.post(
        f"{API_URL}/chat",
        json={
            "message": "How can I reach out to Dan via email?",
            "user_id": "test_contact",
            "model": "gpt-4o-mini",
        },
    )

    data = response.json()
    print(f"Answer: {data['answer'][:150]}...")
    print(f"Tool Calls: {json.dumps(data.get('tool_calls', []), indent=2)}")

    assert response.status_code == 200
    print("✓ Contact tool test passed")


def test_portfolio_tool():
    """Test portfolio resource tool."""
    print("\n=== Testing Portfolio Tool ===")

    response = requests.post(
        f"{API_URL}/chat",
        json={
            "message": "I'd like to see Dan's resume",
            "user_id": "test_portfolio",
            "model": "gpt-4o-mini",
        },
    )

    data = response.json()
    print(f"Answer: {data['answer'][:150]}...")
    print(f"Tool Calls: {json.dumps(data.get('tool_calls', []), indent=2)}")

    assert response.status_code == 200
    print("✓ Portfolio tool test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Portfolio Chatbot Features - Test Suite")
    print("=" * 60)

    try:
        # Give server time to start
        print("\nWaiting for server to start...")
        time.sleep(3)

        # Run tests
        test_health()
        session_id = test_chat_with_tools()
        test_contact_tool()
        test_portfolio_tool()
        session_id = test_lead_detection(session_id)
        lead_id = test_lead_capture(session_id)
        test_admin_endpoints(session_id, lead_id)

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
