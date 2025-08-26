#!/usr/bin/env python3
"""
Mozilla Support RAG Chatbot with LLM generation
"""

import json
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any
from dotenv import load_dotenv

# Try OpenAI first, fallback to local options
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI not available, will use local model")

# For local LLM option
try:
    from langchain_community.llms import Ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

load_dotenv()

class MozillaSupportBotWithLLM:
    def __init__(self, persist_dir="./chroma_db", collection_name="sumo_kb", use_openai=True):
        """Initialize the Mozilla Support Bot with ChromaDB and LLM"""
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
        
        # Initialize LLM
        self.use_openai = use_openai and OPENAI_AVAILABLE
        if self.use_openai:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.llm_client = OpenAI(api_key=api_key)
                # Choose model: gpt-4o, gpt-4-turbo, or gpt-3.5-turbo
                self.model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
                print(f"✅ Using OpenAI {self.model}")
            else:
                print("⚠️ OPENAI_API_KEY not found in environment")
                self.use_openai = False
        
        if not self.use_openai and OLLAMA_AVAILABLE:
            # Use Ollama for local LLM (requires Ollama to be installed and running)
            self.llm_client = Ollama(model="llama2")
            print("✅ Using local Ollama (llama2)")
        elif not self.use_openai:
            print("⚠️ No LLM available. Will use retrieval-only mode.")
            self.llm_client = None
    
    def retrieve_context(self, query: str, n_results: int = 5) -> tuple:
        """
        Retrieve relevant documents for context
        
        Returns:
            Tuple of (formatted_context, source_documents)
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format context for LLM
        context_parts = []
        source_docs = []
        
        for i in range(len(results['ids'][0])):
            doc_text = results['documents'][0][i]
            metadata = results['metadatas'][0][i]
            
            context_parts.append(f"Article: {metadata['title']}\n{metadata['summary']}\n\nContent:\n{doc_text[:1500]}")
            
            source_docs.append({
                'title': metadata['title'],
                'url': metadata['url'],
                'summary': metadata['summary']
            })
        
        context = "\n\n---\n\n".join(context_parts)
        return context, source_docs
    
    def generate_with_llm(self, query: str, context: str) -> str:
        """
        Generate response using LLM with retrieved context
        """
        if not self.llm_client:
            return None
        
        system_prompt = """You are a helpful Mozilla Firefox support assistant. 
        Use the provided context from Mozilla's official support documentation to answer user questions.
        Be accurate, concise, and helpful. If the context doesn't contain enough information to fully answer, 
        say so and suggest what additional information might help.
        Format your response with clear steps when appropriate."""
        
        user_prompt = f"""Context from Mozilla Support Documentation:
{context}

User Question: {query}

Please provide a helpful answer based on the documentation above. Include specific steps or solutions when relevant."""
        
        try:
            if self.use_openai:
                # GPT-5 has different parameter requirements
                params = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                }
                
                if "gpt-5" in self.model:
                    # GPT-5 uses reasoning tokens, so needs higher limit
                    params["max_completion_tokens"] = 2000
                    # Temperature must be 1 (default) for GPT-5
                else:
                    params["max_tokens"] = 500
                    params["temperature"] = 0.3
                    
                response = self.llm_client.chat.completions.create(**params)
                return response.choices[0].message.content
            elif OLLAMA_AVAILABLE:
                # For Ollama/local models
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                return self.llm_client.invoke(full_prompt)
        except Exception as e:
            print(f"❌ LLM generation error: {e}")
            return None
    
    def generate_rag_response(self, query: str, n_results: int = 3) -> Dict[str, Any]:
        """
        Generate a complete RAG response
        
        Args:
            query: User's question
            n_results: Number of documents to use for context
            
        Returns:
            Dictionary with generated response and sources
        """
        # Retrieve relevant context
        context, source_docs = self.retrieve_context(query, n_results)
        
        # Generate response with LLM
        llm_response = None
        if self.llm_client:
            llm_response = self.generate_with_llm(query, context)
        
        # Build complete response
        response = {
            'query': query,
            'llm_response': llm_response,
            'sources': source_docs,
            'retrieval_only': llm_response is None
        }
        
        return response
    
    def format_response(self, response: Dict[str, Any]) -> str:
        """
        Format the RAG response for display
        """
        output = []
        
        if response['llm_response']:
            output.append("🤖 **AI-Generated Answer:**")
            output.append(response['llm_response'])
            output.append("")
        else:
            output.append("📚 **Relevant Documentation:**")
            output.append("(LLM not available - showing retrieved documents)")
            output.append("")
        
        output.append("📖 **Sources:**")
        for i, source in enumerate(response['sources'], 1):
            output.append(f"{i}. [{source['title']}]({source['url']})")
            output.append(f"   {source['summary']}")
        
        return "\n".join(output)

def test_rag_with_llm():
    """Test the RAG system with LLM generation"""
    print("\n🧪 Testing Mozilla Support RAG with LLM")
    print("=" * 60)
    
    # Initialize bot
    bot = MozillaSupportBotWithLLM(use_openai=True)
    
    # Test queries
    test_queries = [
        "My Firefox crashes when I try to play YouTube videos. What should I do?",
        "How do I import my bookmarks from Chrome to Firefox?",
        "Firefox is using 8GB of RAM with only 5 tabs open. How can I reduce memory usage?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}: {query}")
        print("-" * 60)
        
        response = bot.generate_rag_response(query)
        formatted = bot.format_response(response)
        print(formatted)
        
        if not response['llm_response']:
            # Show retrieval-only fallback
            print("\n💡 To enable AI-generated answers:")
            print("   1. Set OPENAI_API_KEY in .env file, or")
            print("   2. Install and run Ollama locally")

def interactive_chat_with_llm():
    """Run an interactive chat session with LLM-powered bot"""
    print("\n🦊 Mozilla Support Bot (AI-Powered)")
    print("=" * 50)
    print("Ask me anything about Firefox! Type 'quit' to exit.")
    print("=" * 50)
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("\n⚠️  No OpenAI API key found.")
        print("   Add OPENAI_API_KEY to .env file for AI responses")
        print("   Or install Ollama for local LLM")
        use_openai = False
    else:
        use_openai = True
    
    bot = MozillaSupportBotWithLLM(use_openai=use_openai)
    
    while True:
        try:
            user_input = input("\n🤔 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye! Have a great day!")
                break
            
            print("\n🤖 Bot: Thinking...", end="\r")
            
            response = bot.generate_rag_response(user_input)
            formatted = bot.format_response(response)
            
            print("🤖 Bot:          ")  # Clear "Thinking..."
            print(formatted)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    # Check if we're testing or running interactive
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_rag_with_llm()
    else:
        interactive_chat_with_llm()