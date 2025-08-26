#!/usr/bin/env python3
"""
Mozilla Support RAG Chatbot using ChromaDB
"""

import json
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
import textwrap

class MozillaSupportBot:
    def __init__(self, persist_dir="./chroma_db", collection_name="sumo_kb"):
        """Initialize the Mozilla Support Bot with ChromaDB"""
        self.client = chromadb.PersistentClient(path=persist_dir)
        
        # Get or create collection
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=embedding_function
            )
            print(f"✅ Connected to existing collection: {collection_name}")
            print(f"📚 Documents in collection: {self.collection.count()}")
        except:
            print(f"❌ Collection '{collection_name}' not found. Please run setup_chromadb.py first.")
            raise
    
    def search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Search the knowledge base for relevant documents
        
        Args:
            query: User's search query
            n_results: Number of results to return
            
        Returns:
            Dictionary containing search results
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            doc = {
                'id': results['ids'][0][i],
                'title': results['metadatas'][0][i]['title'],
                'summary': results['metadatas'][0][i]['summary'],
                'url': results['metadatas'][0][i]['url'],
                'topics': json.loads(results['metadatas'][0][i]['topics']),
                'distance': results['distances'][0][i] if 'distances' in results else None
            }
            formatted_results.append(doc)
        
        return {
            'query': query,
            'results': formatted_results,
            'count': len(formatted_results)
        }
    
    def generate_response(self, query: str, n_results: int = 3) -> str:
        """
        Generate a response based on the user's query using RAG
        
        Args:
            query: User's question
            n_results: Number of documents to use for context
            
        Returns:
            Generated response string
        """
        # Search for relevant documents
        search_results = self.search(query, n_results)
        
        if search_results['count'] == 0:
            return "I couldn't find any relevant information in the Mozilla Support knowledge base for your query."
        
        # Build response
        response = []
        response.append(f"Based on the Mozilla Support documentation, here's what I found:\n")
        
        # Add top results
        for i, result in enumerate(search_results['results'], 1):
            response.append(f"\n**{i}. {result['title']}**")
            response.append(f"   {result['summary']}")
            response.append(f"   📖 Read more: {result['url']}")
            if result['topics']:
                response.append(f"   🏷️ Topics: {', '.join(result['topics'])}")
        
        # Add helpful context
        response.append("\n---")
        response.append(f"💡 These are the top {len(search_results['results'])} most relevant articles for your query: \"{query}\"")
        response.append("📝 Click the links above to read the full articles with detailed instructions.")
        
        return "\n".join(response)
    
    def get_similar_articles(self, article_id: str, n_results: int = 5) -> List[Dict]:
        """
        Find similar articles to a given article
        
        Args:
            article_id: The slug/ID of the article
            n_results: Number of similar articles to return
            
        Returns:
            List of similar articles
        """
        # Get the article's embedding
        article = self.collection.get(ids=[article_id], include=['embeddings', 'metadatas'])
        
        if not article['ids']:
            return []
        
        # Search for similar articles using the embedding
        results = self.collection.query(
            query_embeddings=article['embeddings'],
            n_results=n_results + 1  # +1 because it will include itself
        )
        
        # Format and filter out the original article
        similar = []
        for i in range(len(results['ids'][0])):
            if results['ids'][0][i] != article_id:
                doc = {
                    'id': results['ids'][0][i],
                    'title': results['metadatas'][0][i]['title'],
                    'summary': results['metadatas'][0][i]['summary'],
                    'url': results['metadatas'][0][i]['url']
                }
                similar.append(doc)
        
        return similar[:n_results]
    
    def get_articles_by_topic(self, topic: str) -> List[Dict]:
        """
        Get all articles related to a specific topic
        
        Args:
            topic: Topic to filter by
            
        Returns:
            List of articles for that topic
        """
        # Get all documents and filter by topic
        all_docs = self.collection.get(include=['metadatas'])
        
        filtered = []
        for i, metadata in enumerate(all_docs['metadatas']):
            topics = json.loads(metadata['topics'])
            if topic in topics:
                doc = {
                    'id': all_docs['ids'][i],
                    'title': metadata['title'],
                    'summary': metadata['summary'],
                    'url': metadata['url'],
                    'topics': topics
                }
                filtered.append(doc)
        
        return filtered

def interactive_chat():
    """Run an interactive chat session with the bot"""
    print("\n🦊 Mozilla Support Bot")
    print("=" * 50)
    print("Ask me anything about Firefox! Type 'quit' to exit.")
    print("Commands:")
    print("  /similar [article-id] - Find similar articles")
    print("  /topics - List all available topics")
    print("  /topic [topic-name] - Get articles for a topic")
    print("=" * 50)
    
    bot = MozillaSupportBot()
    
    while True:
        try:
            user_input = input("\n🤔 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye! Have a great day!")
                break
            
            if user_input.startswith('/similar'):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    article_id = parts[1]
                    similar = bot.get_similar_articles(article_id, n_results=5)
                    if similar:
                        print("\n🔗 Similar articles:")
                        for i, article in enumerate(similar, 1):
                            print(f"  {i}. {article['title']}")
                            print(f"     {article['url']}")
                    else:
                        print("❌ Article not found or no similar articles available.")
                else:
                    print("Usage: /similar [article-id]")
            
            elif user_input == '/topics':
                # Get all unique topics
                all_docs = bot.collection.get(include=['metadatas'])
                all_topics = set()
                for metadata in all_docs['metadatas']:
                    topics = json.loads(metadata['topics'])
                    all_topics.update(topics)
                
                print("\n📚 Available topics:")
                for topic in sorted(all_topics):
                    print(f"  • {topic}")
            
            elif user_input.startswith('/topic'):
                parts = user_input.split(maxsplit=1)
                if len(parts) > 1:
                    topic = parts[1]
                    articles = bot.get_articles_by_topic(topic)
                    if articles:
                        print(f"\n📑 Articles about '{topic}':")
                        for i, article in enumerate(articles, 1):
                            print(f"  {i}. {article['title']}")
                            print(f"     {article['url']}")
                    else:
                        print(f"❌ No articles found for topic: {topic}")
                else:
                    print("Usage: /topic [topic-name]")
            
            else:
                # Regular query
                print("\n🤖 Bot:", end=" ")
                response = bot.generate_response(user_input)
                print(response)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    interactive_chat()