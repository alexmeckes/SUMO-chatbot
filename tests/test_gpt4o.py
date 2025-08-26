#!/usr/bin/env python3
"""
Quick test of GPT-4o model with any-agent
"""

import os
from dotenv import load_dotenv
from mozilla_support_bot_any_agent import MozillaSupportBotAnyAgent

# Suppress warnings
import logging
logging.getLogger().setLevel(logging.WARNING)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

load_dotenv()

def test_gpt4o():
    """Test GPT-4o specifically"""
    print("\n🧪 Testing GPT-4o with Mozilla Support Bot")
    print("=" * 60)
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OPENAI_API_KEY not set")
        return
    
    # Initialize bot
    bot = MozillaSupportBotAnyAgent(agent_type="openai")
    print("✅ Connected to knowledge base")
    
    # Set to GPT-4o
    print("\n📦 Configuring GPT-4o...")
    bot.set_model("gpt-4o")
    
    # Test query
    query = "Firefox crashes when playing YouTube videos, what should I do?"
    print(f"\n📝 Query: {query}")
    print("-" * 40)
    
    # Generate response
    response = bot.generate_response(query)
    
    if not response['error']:
        print(f"✅ Success with GPT-4o!")
        print(f"Model: {response['model']}")
        print(f"\n📖 Response:")
        print(response['response'][:800])
        if len(response['response']) > 800:
            print("...[truncated]")
    else:
        print(f"❌ Error: {response['response']}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_gpt4o()