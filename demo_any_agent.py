#!/usr/bin/env python3
"""
Demo of any-agent integration with Mozilla Support Bot
Shows how to use GPT-5 and other models through any-agent framework
"""

import os
import sys
from dotenv import load_dotenv
from mozilla_support_bot_any_agent import MozillaSupportBotAnyAgent

# Suppress INFO logs for cleaner output
import logging
logging.getLogger().setLevel(logging.WARNING)
os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'

load_dotenv()

def demo():
    """Demonstrate any-agent with Mozilla Support Bot"""
    
    print("\n🦊 Mozilla Support Bot with any-agent Framework")
    print("=" * 60)
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Please set OPENAI_API_KEY in .env file")
        return
    
    # Initialize bot
    print("Initializing bot...")
    bot = MozillaSupportBotAnyAgent(agent_type="openai")
    print(f"✅ Connected to knowledge base with {405} documents")
    
    # Test queries
    queries = [
        "How do I clear Firefox cache and cookies?",
        "Firefox crashes when playing YouTube videos",
        "How to import bookmarks from Chrome?"
    ]
    
    models = ["gpt-3.5-turbo", "gpt-5"]
    
    for model in models:
        print(f"\n{'='*60}")
        print(f"🤖 Testing with {model}")
        print("=" * 60)
        
        try:
            bot.set_model(model)
            
            # Test one query per model
            query = queries[0] if model == "gpt-5" else queries[1]
            
            print(f"\n📝 Query: {query}")
            print("-" * 40)
            
            response = bot.generate_response(query)
            
            if not response['error']:
                print(f"✅ Success!")
                print(f"\n📖 Response:")
                # Print first 800 chars of response
                resp_text = response['response']
                if len(resp_text) > 800:
                    print(resp_text[:800] + "...\n[truncated]")
                else:
                    print(resp_text)
            else:
                print(f"❌ Error: {response['response']}")
                
        except Exception as e:
            print(f"❌ Failed to use {model}: {e}")
    
    print("\n" + "=" * 60)
    print("✨ Demo complete!")
    print("\nany-agent allows you to:")
    print("• Use multiple LLM providers (OpenAI, Mistral, Anthropic, etc.)")
    print("• Switch between models easily")
    print("• Add custom tools (like our Firefox KB search)")
    print("• Get detailed tracing of agent actions")
    print("• Build multi-agent systems")

if __name__ == "__main__":
    demo()