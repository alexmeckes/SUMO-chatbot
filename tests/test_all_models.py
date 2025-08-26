#!/usr/bin/env python3
"""
Comprehensive test of any-agent integration with all supported models
Tests GPT-5, GPT-4o, and GPT-3.5-turbo
"""

import os
import sys
from dotenv import load_dotenv
from mozilla_support_bot_any_agent import MozillaSupportBotAnyAgent
import time

# Suppress unnecessary warnings
import logging
logging.getLogger().setLevel(logging.WARNING)
os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

load_dotenv()

def test_model(bot, model_name, query):
    """Test a specific model with a query"""
    print(f"\n{'='*60}")
    print(f"🤖 Testing: {model_name}")
    print(f"📝 Query: {query}")
    print("-" * 60)
    
    try:
        # Set the model
        bot.set_model(model_name)
        
        # Generate response
        start_time = time.time()
        response = bot.generate_response(query)
        elapsed_time = time.time() - start_time
        
        if not response['error']:
            print(f"✅ Success! (Time: {elapsed_time:.2f}s)")
            print(f"Model: {response['model']}")
            print(f"Agent Type: {response['agent_type']}")
            
            # Show response preview
            resp_text = response['response']
            print(f"\n📖 Response:")
            if len(resp_text) > 500:
                print(resp_text[:500] + "...\n[truncated]")
            else:
                print(resp_text)
            
            # Show tool calls if any
            if 'tool_calls' in response and response['tool_calls']:
                print(f"\n🔧 Tool calls made: {len(response['tool_calls'])}")
            
            return True
        else:
            print(f"❌ Error: {response['response']}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    """Main test function"""
    print("\n🚀 Comprehensive Model Testing with any-agent Framework")
    print("=" * 70)
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Please set OPENAI_API_KEY in .env file")
        return
    
    # Initialize bot
    print("\n📚 Initializing Mozilla Support Bot...")
    try:
        bot = MozillaSupportBotAnyAgent(agent_type="openai")
        print(f"✅ Connected to knowledge base")
    except Exception as e:
        print(f"❌ Failed to initialize bot: {e}")
        return
    
    # Test queries - variety of Firefox support questions
    test_queries = [
        "How do I clear Firefox cache and cookies?",
        "Firefox crashes when playing YouTube videos, what should I do?",
        "How to import bookmarks from Chrome to Firefox?",
        "Firefox is running slowly, how can I speed it up?",
        "How do I reset Firefox to default settings?"
    ]
    
    # Models to test
    models_to_test = [
        "gpt-3.5-turbo",  # Should work
        "gpt-4o",         # GPT-4o model
        "gpt-5"           # GPT-5 model
    ]
    
    results = {}
    
    # Test each model with different queries
    for i, model in enumerate(models_to_test):
        query = test_queries[i % len(test_queries)]
        success = test_model(bot, model, query)
        results[model] = success
        
        # Brief pause between tests
        if i < len(models_to_test) - 1:
            time.sleep(1)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Results Summary:")
    print("-" * 70)
    
    for model, success in results.items():
        status = "✅ Passed" if success else "❌ Failed"
        print(f"{model:20} {status}")
    
    # Count successes
    successful = sum(1 for s in results.values() if s)
    total = len(results)
    
    print("-" * 70)
    print(f"Total: {successful}/{total} models working")
    
    if successful == total:
        print("\n🎉 All models tested successfully!")
    elif successful > 0:
        print(f"\n⚠️  {successful} out of {total} models working")
    else:
        print("\n❌ No models working - check API keys and configuration")
    
    # Additional information
    print("\n📌 Notes:")
    print("• GPT-5 uses max_completion_tokens instead of max_tokens")
    print("• GPT-5 requires default temperature (no custom temperature)")
    print("• All models use the Firefox KB search tool for RAG")
    print("• Responses are generated based on actual Mozilla support docs")

if __name__ == "__main__":
    main()