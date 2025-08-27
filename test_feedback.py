#!/usr/bin/env python3
"""
Test the feedback system functionality
"""

import requests
import json
import time

API_BASE = "http://localhost:8080"

def test_feedback_system():
    """Test the feedback system end-to-end"""
    
    print("🧪 Testing Feedback System")
    print("=" * 50)
    
    # 1. Check status
    print("\n1. Checking API status...")
    try:
        response = requests.get(f"{API_BASE}/api/status")
        data = response.json()
        print(f"✅ API Status: {data['status']}")
        print(f"   Model: {data['model']}")
        print(f"   Feedback enabled: {data.get('feedback_enabled', False)}")
    except Exception as e:
        print(f"❌ Failed to get status: {e}")
        return
    
    # 2. Create session
    print("\n2. Creating feedback session...")
    try:
        response = requests.post(
            f"{API_BASE}/api/session",
            headers={"User-Agent": "TestScript/1.0"}
        )
        session_data = response.json()
        session_id = session_data['session_id']
        print(f"✅ Session created: {session_id}")
    except Exception as e:
        print(f"❌ Failed to create session: {e}")
        return
    
    # 3. Send a chat message with session
    print("\n3. Sending test message...")
    try:
        chat_response = requests.post(
            f"{API_BASE}/api/chat",
            json={
                "query": "How do I clear Firefox cache?",
                "session_id": session_id
            }
        )
        chat_data = chat_response.json()
        conversation_id = chat_data.get('conversation_id')
        print(f"✅ Response received")
        print(f"   Conversation ID: {conversation_id}")
        print(f"   Response time: {chat_data.get('response_time_ms', 0)}ms")
        print(f"   Response preview: {chat_data['response'][:100]}...")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")
        return
    
    # 4. Submit positive feedback
    print("\n4. Submitting positive feedback...")
    try:
        if conversation_id:
            feedback_response = requests.post(
                f"{API_BASE}/api/feedback",
                json={
                    "conversation_id": conversation_id,
                    "feedback_type": "positive"
                }
            )
            feedback_data = feedback_response.json()
            print(f"✅ Feedback submitted: {feedback_data['feedback_id']}")
        else:
            print("⚠️  No conversation ID - skipping feedback")
    except Exception as e:
        print(f"❌ Failed to submit feedback: {e}")
    
    # 5. Send another message with negative feedback
    print("\n5. Testing negative feedback with comment...")
    try:
        chat_response = requests.post(
            f"{API_BASE}/api/chat",
            json={
                "query": "What about Chrome bookmarks?",
                "session_id": session_id
            }
        )
        chat_data = chat_response.json()
        conversation_id2 = chat_data.get('conversation_id')
        
        if conversation_id2:
            feedback_response = requests.post(
                f"{API_BASE}/api/feedback",
                json={
                    "conversation_id": conversation_id2,
                    "feedback_type": "negative",
                    "comment": "This answer was about Firefox, not Chrome",
                    "rating": 2
                }
            )
            feedback_data = feedback_response.json()
            print(f"✅ Negative feedback submitted with comment")
        else:
            print("⚠️  No conversation ID for second message")
    except Exception as e:
        print(f"❌ Failed to test negative feedback: {e}")
    
    # 6. Get feedback statistics
    print("\n6. Retrieving feedback statistics...")
    try:
        stats_response = requests.get(f"{API_BASE}/api/feedback/stats?days=1")
        stats = stats_response.json()
        print(f"✅ Feedback Statistics (last 24 hours):")
        print(f"   Total conversations: {stats['total_conversations']}")
        print(f"   Feedback breakdown: {stats['feedback_breakdown']}")
        print(f"   Average response time: {stats['avg_response_time_ms']:.0f}ms")
        print(f"   Error rate: {stats['error_rate']:.1f}%")
        print(f"   Satisfaction rate: {stats['satisfaction_rate']:.1f}%")
    except Exception as e:
        print(f"❌ Failed to get statistics: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Feedback system test complete!")
    print("\n💡 Try the web interface at http://localhost:8080")
    print("   - Chat messages will show feedback buttons")
    print("   - Click 👍/👎 to provide feedback")
    print("   - Negative feedback prompts for comments")

if __name__ == "__main__":
    test_feedback_system()