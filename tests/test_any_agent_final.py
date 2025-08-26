#!/usr/bin/env python3
"""
Test any-agent integration with Mozilla Support Bot
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_any_agent_with_rag():
    """Test any-agent with our RAG system"""
    from mozilla_support_bot_any_agent import MozillaSupportBotAnyAgent
    
    print("\n🧪 Testing Mozilla Support Bot with any-agent")
    print("=" * 60)
    
    # Initialize bot
    bot = MozillaSupportBotAnyAgent(agent_type="openai")
    
    # Test queries
    queries = [
        "How do I clear Firefox cache?",
        "Firefox crashes when playing videos"
    ]
    
    # Test with GPT-3.5 (should work with OpenAI key)
    if os.getenv('OPENAI_API_KEY'):
        print("\n### Testing with GPT-3.5-turbo")
        bot.set_model("gpt-3.5-turbo", agent_type="openai")
        
        for query in queries[:1]:  # Test one query
            print(f"\nQuery: {query}")
            print("-" * 40)
            response = bot.generate_response(query)
            
            if not response['error']:
                print(f"✅ Success!")
                print(f"Model: {response['model']}")
                print(f"Response preview: {response['response'][:200]}...")
            else:
                print(f"❌ Error: {response['response']}")
    
    # Test with GPT-5 if available
    if os.getenv('OPENAI_API_KEY'):
        print("\n### Testing with GPT-5")
        try:
            bot.set_model("gpt-5", agent_type="openai")
            
            query = queries[0]
            print(f"\nQuery: {query}")
            print("-" * 40)
            response = bot.generate_response(query)
            
            if not response['error']:
                print(f"✅ Success!")
                print(f"Model: {response['model']}")
                print(f"Response preview: {response['response'][:200]}...")
            else:
                print(f"❌ Error: {response['response']}")
        except Exception as e:
            print(f"❌ GPT-5 error: {e}")

def test_direct_any_agent():
    """Test any-agent directly without our wrapper"""
    from any_agent import AgentConfig, AnyAgent
    
    print("\n🧪 Testing any-agent directly")
    print("=" * 60)
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OPENAI_API_KEY not set")
        return
    
    try:
        # Create a simple agent
        config = AgentConfig(
            model_id="openai/gpt-3.5-turbo",
            instructions="Answer briefly about Firefox browser.",
            tools=[],
            model_args={"temperature": 0.5, "max_tokens": 100}
        )
        
        agent = AnyAgent.create("openai", config)
        result = agent.run("What is Firefox in one sentence?")
        
        print(f"Direct test result: {result}")
        
    except Exception as e:
        print(f"Error in direct test: {e}")

if __name__ == "__main__":
    print("🚀 Testing any-agent Integration with Mozilla Support Bot")
    print("=" * 60)
    
    # Test direct any-agent first
    test_direct_any_agent()
    
    # Test with our RAG system
    test_any_agent_with_rag()
    
    print("\n✅ Testing complete!")