#!/usr/bin/env python3
"""
Test and demonstrate trace storage functionality
"""

import requests
import json
import time

API_BASE = "http://localhost:8080"  # Change to production URL as needed

def test_trace_storage():
    """Test that traces are being stored with conversations"""
    
    print("🔍 Testing Trace Storage System")
    print("=" * 50)
    
    # 1. Create session
    print("\n1. Creating session...")
    session_response = requests.post(f"{API_BASE}/api/session")
    session_id = session_response.json()['session_id']
    print(f"✅ Session created: {session_id}")
    
    # 2. Send a message that will trigger tool use
    print("\n2. Sending message that requires search...")
    chat_response = requests.post(
        f"{API_BASE}/api/chat",
        json={
            "query": "How do I enable dark mode in Firefox?",
            "session_id": session_id
        }
    )
    chat_data = chat_response.json()
    conversation_id = chat_data.get('conversation_id')
    
    print(f"✅ Got response with conversation_id: {conversation_id}")
    print(f"   Response time: {chat_data.get('response_time_ms', 0)}ms")
    
    # 3. Retrieve the trace data
    if conversation_id:
        print(f"\n3. Retrieving trace for conversation {conversation_id}...")
        
        trace_response = requests.get(
            f"{API_BASE}/api/conversation/{conversation_id}/trace"
        )
        
        if trace_response.status_code == 200:
            trace_info = trace_response.json()
            
            print("\n📊 Trace Analysis:")
            print("-" * 40)
            
            if trace_info['trace_data']:
                trace = trace_info['trace_data']
                
                print(f"Total Duration: {trace.get('total_duration_ms', 0)}ms")
                print(f"Number of Spans: {len(trace.get('spans', []))}")
                
                # Analyze tool calls
                if trace.get('tool_calls'):
                    print(f"\n🔧 Tool Calls Made: {len(trace['tool_calls'])}")
                    for i, tool_call in enumerate(trace['tool_calls'], 1):
                        if isinstance(tool_call, str):
                            # Parse if it's JSON string
                            try:
                                tool_call = json.loads(tool_call)
                            except:
                                pass
                        
                        if isinstance(tool_call, list):
                            for tc in tool_call:
                                if isinstance(tc, dict):
                                    print(f"   {i}. {tc.get('function', {}).get('name', 'unknown')}")
                
                # Analyze LLM calls
                if trace.get('llm_calls'):
                    print(f"\n🤖 LLM Calls: {len(trace['llm_calls'])}")
                    total_input_tokens = 0
                    total_output_tokens = 0
                    
                    for call in trace['llm_calls']:
                        input_tokens = call.get('input_tokens', 0) or 0
                        output_tokens = call.get('output_tokens', 0) or 0
                        total_input_tokens += input_tokens
                        total_output_tokens += output_tokens
                        
                        print(f"   - Model: {call.get('model')}")
                        print(f"     Input: {input_tokens} tokens")
                        print(f"     Output: {output_tokens} tokens")
                    
                    print(f"\n📈 Total Token Usage:")
                    print(f"   Input: {total_input_tokens} tokens")
                    print(f"   Output: {total_output_tokens} tokens")
                    print(f"   Total: {total_input_tokens + total_output_tokens} tokens")
                
                # Show span timeline
                if trace.get('spans'):
                    print(f"\n⏱️  Span Timeline:")
                    for span in trace['spans'][:5]:  # Show first 5 spans
                        print(f"   - {span['name']}")
                        if span.get('attributes'):
                            for key, value in span['attributes'].items():
                                print(f"      {key}: {value}")
            else:
                print("No trace data available for this conversation")
        else:
            print(f"❌ Could not retrieve trace: {trace_response.status_code}")
    
    print("\n" + "=" * 50)
    print("✅ Trace storage test complete!")

def analyze_recent_traces():
    """Analyze recent conversation traces from production"""
    
    print("\n📊 Analyzing Recent Traces")
    print("=" * 50)
    
    # Get feedback stats to find conversations
    stats_response = requests.get(f"{API_BASE}/api/feedback/stats?days=1")
    
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"Total conversations in last 24h: {stats['total_conversations']}")
        print(f"Average response time: {stats['avg_response_time_ms']:.0f}ms")
        
        # Note: In a real implementation, you'd have an endpoint to list recent conversations
        # For now, this shows how you'd analyze traces if you had the conversation IDs
        
        print("\n💡 To analyze specific traces:")
        print("   1. Get conversation_id from chat responses")
        print("   2. Fetch trace: GET /api/conversation/{id}/trace")
        print("   3. Analyze tool calls, token usage, and timing")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--prod":
        API_BASE = "https://sumo-chatbot-production.up.railway.app"
        print(f"🌐 Using production API: {API_BASE}\n")
    
    test_trace_storage()
    analyze_recent_traces()