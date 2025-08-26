#!/usr/bin/env python3
"""
Simple test of any-agent integration with Mozilla Support Bot
"""

import os
from dotenv import load_dotenv
from mozilla_support_bot_any_agent import MozillaSupportBotAnyAgent

load_dotenv()

def test_with_openai():
    """Test with OpenAI models (GPT-5)"""
    print("\n🧪 Testing with OpenAI GPT-5")
    print("=" * 60)
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OPENAI_API_KEY not set, skipping OpenAI test")
        return
    
    # Initialize bot
    bot = MozillaSupportBotAnyAgent(agent_type="openai")
    
    # Configure for GPT-5
    bot.set_model("gpt-5")
    
    # Test query
    query = "How do I clear Firefox cache?"
    print(f"Query: {query}")
    print("-" * 40)
    
    response = bot.generate_response(query)
    
    if not response['error']:
        print(f"✅ Success with {response['model']}")
        print(f"Response: {response['response'][:300]}...")
    else:
        print(f"❌ Error: {response['response']}")

def test_with_litellm():
    """Test using LiteLLM which any-agent supports"""
    print("\n🧪 Testing with LiteLLM (GPT-3.5)")
    print("=" * 60)
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OPENAI_API_KEY not set, skipping")
        return
    
    # Initialize bot
    bot = MozillaSupportBotAnyAgent(agent_type="openai")
    
    # Use GPT-3.5-turbo which should work
    bot.set_model("gpt-3.5-turbo")
    
    # Test query
    query = "Firefox won't play videos"
    print(f"Query: {query}")
    print("-" * 40)
    
    response = bot.generate_response(query)
    
    if not response['error']:
        print(f"✅ Success with {response['model']}")
        print(f"Response: {response['response'][:300]}...")
    else:
        print(f"❌ Error: {response['response']}")

def test_simple_query():
    """Test without any tools, just basic generation"""
    print("\n🧪 Testing simple generation without tools")
    print("=" * 60)
    
    from any_agent import AgentConfig, AnyAgent
    
    try:
        # Create a simple agent
        config = AgentConfig(
            model_id="openai/gpt-3.5-turbo",
            instructions="You are a helpful assistant. Answer briefly.",
            tools=[],  # No tools
            temperature=0.3,
            max_tokens=100
        )
        
        agent = AnyAgent.create("openai", config)
        
        # Run a simple query
        result = agent.run("What is Firefox?")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("🚀 Testing any-agent Integration")
    print("=" * 60)
    
    # Test simple generation first
    test_simple_query()
    
    # Test with OpenAI
    test_with_openai()
    
    # Test with LiteLLM
    test_with_litellm()
    
    print("\n✅ Testing complete!")