#!/usr/bin/env python3
"""
Test the Mozilla Support RAG system with various queries
"""

from mozilla_support_bot import MozillaSupportBot
import json

def test_rag_system():
    """Run various test queries against the RAG system"""
    
    print("🧪 Testing Mozilla Support RAG System")
    print("=" * 60)
    
    # Initialize bot
    bot = MozillaSupportBot()
    
    # Test queries
    test_queries = [
        "Firefox won't play videos",
        "How to import bookmarks from Chrome",
        "Firefox is using too much memory",
        "Can't hear audio in Firefox",
        "How to save a webpage",
        "Firefox crashes on startup",
        "How to clear cache and cookies",
        "Website looks wrong in Firefox"
    ]
    
    print("\n📊 Running test queries:\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}: {query}")
        print("-" * 60)
        
        # Get search results
        results = bot.search(query, n_results=3)
        
        print(f"Top 3 results (relevance scores):")
        for j, result in enumerate(results['results'], 1):
            score = 1 - result['distance'] if result['distance'] else "N/A"
            print(f"  {j}. {result['title'][:50]}... (score: {score:.3f})")
        
        print()
    
    # Test similar articles feature
    print("\n" + "=" * 60)
    print("🔗 Testing similar articles feature")
    print("-" * 60)
    
    test_article = "fix-common-audio-and-video-issues"
    similar = bot.get_similar_articles(test_article, n_results=5)
    
    print(f"Articles similar to '{test_article}':")
    for i, article in enumerate(similar, 1):
        print(f"  {i}. {article['title']}")
    
    # Test topic filtering
    print("\n" + "=" * 60)
    print("📚 Testing topic filtering")
    print("-" * 60)
    
    test_topic = "browse"
    topic_articles = bot.get_articles_by_topic(test_topic)
    
    print(f"Articles with topic '{test_topic}': {len(topic_articles)} found")
    for i, article in enumerate(topic_articles[:5], 1):
        print(f"  {i}. {article['title']}")
    
    # Test response generation
    print("\n" + "=" * 60)
    print("💬 Testing response generation")
    print("-" * 60)
    
    test_question = "My Firefox won't play YouTube videos and there's no sound. What should I do?"
    print(f"Question: {test_question}\n")
    
    response = bot.generate_response(test_question)
    print("Bot Response:")
    print(response)
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")

if __name__ == "__main__":
    test_rag_system()