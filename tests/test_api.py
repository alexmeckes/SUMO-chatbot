#!/usr/bin/env python3
"""Test the API directly"""

import requests
import json
from mozilla_support_bot_with_llm import MozillaSupportBotWithLLM

# First test the bot directly
print("1. Testing bot directly...")
bot = MozillaSupportBotWithLLM()
response = bot.generate_rag_response("How do I clear cache?", n_results=2)
print(f"   Has LLM response: {response.get('llm_response') is not None}")
if response.get('llm_response'):
    print(f"   Response preview: {response['llm_response'][:100]}...")
print()

# Test the Flask app
print("2. Starting Flask app...")
from app import app, bot as app_bot
print(f"   App bot initialized: {app_bot is not None}")
print(f"   Model: {app_bot.model if app_bot else 'None'}")

# Test with Flask test client
print("\n3. Testing with Flask test client...")
with app.test_client() as client:
    test_response = client.post('/api/chat', 
                                json={'query': 'How do I clear cache?'},
                                content_type='application/json')
    print(f"   Status code: {test_response.status_code}")
    if test_response.status_code == 200:
        data = json.loads(test_response.data)
        print(f"   Has response: {'response' in data}")
        if 'response' in data:
            print(f"   Response preview: {data['response'][:100]}...")
    else:
        print(f"   Error: {test_response.data}")

print("\n✅ Tests complete")