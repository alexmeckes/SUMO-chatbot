#!/usr/bin/env python3
"""
Quick test of GPT-5 model with any-agent
"""

import os
from dotenv import load_dotenv
from mozilla_support_bot_any_agent import MozillaSupportBotAnyAgent

# Suppress warnings
import logging
logging.getLogger().setLevel(logging.WARNING)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

load_dotenv()

def test_gpt5():
    """Test GPT-5 specifically"""
    print("\n🧪 Testing GPT-5 with Mozilla Support Bot")
    print("=" * 60)
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OPENAI_API_KEY not set")
        return
    
    # Initialize bot
    bot = MozillaSupportBotAnyAgent(agent_type="openai")
    print("✅ Connected to knowledge base")
    
    # Set to GPT-5
    print("\n📦 Configuring GPT-5...")
    bot.set_model("gpt-5")
    
    # Test query
    query = "How to import bookmarks from Chrome to Firefox?"
    print(f"\n📝 Query: {query}")
    print("-" * 40)
    
    # Generate response
    response = bot.generate_response(query)
    
    if not response['error']:
        print(f"✅ Success with GPT-5!")
        print(f"Model: {response['model']}")
        print(f"\n📖 Response:")
        print(response['response'][:800])
        if len(response['response']) > 800:
            print("...[truncated]")
    else:
        print(f"❌ Error: {response['response']}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_gpt5()