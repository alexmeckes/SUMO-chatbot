#!/usr/bin/env python3
"""
Test the analytics and export endpoints
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8080"  # Change to production URL as needed

def test_analytics_endpoints():
    """Test all the new analytics endpoints"""
    
    print("📊 Testing Analytics Endpoints")
    print("=" * 50)
    
    # 1. Get recent conversations
    print("\n1. Getting recent conversations...")
    try:
        response = requests.get(f"{API_BASE}/api/conversations/recent?days=7&limit=10")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['count']} recent conversations")
            
            if data['conversations']:
                print("\n   Recent queries:")
                for conv in data['conversations'][:5]:
                    feedback = conv.get('feedback_type', 'No feedback')
                    print(f"   - '{conv['query'][:50]}...'")
                    print(f"     Feedback: {feedback}, Has trace: {conv.get('has_trace', False)}")
        else:
            print(f"❌ Failed to get conversations: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 2. Calculate costs
    print("\n2. Calculating API costs...")
    try:
        response = requests.get(f"{API_BASE}/api/costs?days=7")
        if response.status_code == 200:
            costs = response.json()
            print(f"✅ Cost Analysis (last {costs['period_days']} days):")
            print(f"   Total cost: ${costs['total_cost']:.4f}")
            print(f"   Conversations analyzed: {costs['total_conversations']}")
            print(f"   Average cost per conversation: ${costs['average_cost_per_conversation']:.4f}")
            
            if costs['total_tokens']['input'] > 0:
                print(f"\n   Token usage:")
                print(f"   - Input tokens: {costs['total_tokens']['input']:,}")
                print(f"   - Output tokens: {costs['total_tokens']['output']:,}")
                print(f"   - Total tokens: {costs['total_tokens']['input'] + costs['total_tokens']['output']:,}")
            
            if costs['costs_by_model']:
                print(f"\n   Costs by model:")
                for model, data in costs['costs_by_model'].items():
                    print(f"   - {model}: ${data['total_cost']:.4f} ({data['conversations']} conversations)")
        else:
            print(f"❌ Failed to calculate costs: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # 3. Test CSV export
    print("\n3. Testing CSV export...")
    try:
        # Without traces
        response = requests.get(f"{API_BASE}/api/export/csv?days=7")
        if response.status_code == 200:
            lines = response.text.split('\n')
            print(f"✅ CSV export successful")
            print(f"   Rows exported: {len(lines) - 1}")  # Subtract header
            print(f"   Headers: {lines[0][:100]}...")
            
            # Save sample
            filename = f"feedback_export_sample_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w') as f:
                f.write(response.text[:1000])  # Save first 1000 chars as sample
            print(f"   Sample saved to: {filename}")
        else:
            print(f"❌ Failed to export CSV: {response.status_code}")
            
        # With traces
        print("\n   Testing CSV export with traces...")
        response = requests.get(f"{API_BASE}/api/export/csv?days=7&include_traces=true")
        if response.status_code == 200:
            lines = response.text.split('\n')
            if 'tool_calls_count' in lines[0]:
                print(f"   ✅ Token data included in export")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Analytics test complete!")

def generate_usage_report():
    """Generate a usage report from the API"""
    
    print("\n📈 Usage Report")
    print("=" * 50)
    
    try:
        # Get feedback stats
        stats_response = requests.get(f"{API_BASE}/api/feedback/stats?days=7")
        stats = stats_response.json()
        
        # Get cost data
        costs_response = requests.get(f"{API_BASE}/api/costs?days=7")
        costs = costs_response.json()
        
        print(f"\n🗓️  Last 7 Days Summary:")
        print(f"   Conversations: {stats['total_conversations']}")
        print(f"   Satisfaction rate: {stats['satisfaction_rate']:.1f}%")
        print(f"   Average response time: {stats['avg_response_time_ms']:.0f}ms")
        print(f"   Error rate: {stats['error_rate']:.1f}%")
        
        if stats['feedback_breakdown']:
            print(f"\n   Feedback breakdown:")
            for feedback_type, count in stats['feedback_breakdown'].items():
                print(f"   - {feedback_type}: {count}")
        
        if costs['total_conversations'] > 0:
            print(f"\n💰 Cost Analysis:")
            print(f"   Total cost: ${costs['total_cost']:.2f}")
            print(f"   Per conversation: ${costs['average_cost_per_conversation']:.4f}")
            print(f"   Total tokens used: {costs['total_tokens']['input'] + costs['total_tokens']['output']:,}")
        
        print(f"\n📊 Model Usage:")
        print(f"   Most used: {stats.get('most_used_model', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--prod":
        API_BASE = "https://sumo-chatbot-production.up.railway.app"
        print(f"🌐 Using production API: {API_BASE}\n")
    
    test_analytics_endpoints()
    generate_usage_report()
    
    print("\n💡 Quick commands:")
    print(f"   Download CSV: curl '{API_BASE}/api/export/csv?days=30' -o feedback.csv")
    print(f"   Get costs: curl '{API_BASE}/api/costs?days=30'")
    print(f"   Recent conversations: curl '{API_BASE}/api/conversations/recent?days=1&limit=10'")