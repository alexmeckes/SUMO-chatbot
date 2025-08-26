#!/usr/bin/env python3
"""
Mozilla Support RAG Chatbot with multi-turn conversation support
Universal approach that works with TinyAgent and other frameworks
"""

import json
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from any_agent import AgentConfig, AnyAgent
import logging

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global collection reference for the tool
_collection = None

def search_firefox_kb(query: str) -> str:
    """Search the Firefox support knowledge base for relevant documentation"""
    global _collection
    
    if not _collection:
        return "Error: Knowledge base not initialized"
    
    n_results = 3
    results = _collection.query(
        query_texts=[query],
        n_results=n_results,
        include=['documents', 'metadatas']
    )
    
    # Format results
    formatted = []
    for i in range(len(results['ids'][0])):
        metadata = results['metadatas'][0][i]
        doc_text = results['documents'][0][i][:500]  # First 500 chars
        formatted.append(
            f"**{metadata['title']}**\n"
            f"Summary: {metadata['summary']}\n"
            f"URL: {metadata['url']}\n"
            f"Content: {doc_text}...\n"
        )
    
    return "\n---\n".join(formatted)

class MozillaSupportBotUniversalMultiTurn:
    def __init__(self, persist_dir="./chroma_db", collection_name="sumo_kb", agent_type="tinyagent"):
        """
        Initialize the Mozilla Support Bot with universal multi-turn conversation support
        
        Args:
            persist_dir: ChromaDB persistence directory
            collection_name: Name of the ChromaDB collection
            agent_type: Type of agent (works with any: "tinyagent", "openai", etc.)
        """
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=persist_dir)
        
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=embedding_function
            )
            logger.info(f"✅ Connected to collection: {collection_name}")
            logger.info(f"📚 Documents: {self.collection.count()}")
        except:
            logger.error(f"❌ Collection '{collection_name}' not found")
            raise
        
        # Set global collection for the tool function
        global _collection
        _collection = self.collection
        
        # Store agent type
        self.agent_type = agent_type
        
        # Initialize agent
        self.agent = None
        self.current_model = None
        
        # Conversation history - stores messages as text
        self.conversation_history = []
    
    def set_model(self, model_id: str, agent_type: Optional[str] = None):
        """
        Configure the agent with a specific model
        
        Args:
            model_id: Model identifier
            agent_type: Override the agent type if needed
        """
        if agent_type:
            self.agent_type = agent_type
        
        # Map common model names
        model_mapping = {
            "gpt-5": "openai/gpt-5",
            "gpt-4o": "openai/gpt-4o",
            "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
            "tiny-agent": "hf/TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "mistral-small": "mistral/mistral-small-latest",
        }
        
        if model_id in model_mapping:
            model_id = model_mapping[model_id]
        
        # Special handling for TinyAgent
        if "tiny" in model_id.lower() or self.agent_type == "tinyagent":
            self.agent_type = "tinyagent"
            if not model_id.startswith("hf/"):
                model_id = f"hf/{model_id}"
        
        # Configure model args
        model_args = {}
        if "gpt-5" in model_id:
            model_args['max_completion_tokens'] = 2000
        else:
            model_args['temperature'] = 0.3
            model_args['max_tokens'] = 500
        
        # Build instructions with conversation awareness
        base_instructions = (
            "You are a helpful Mozilla Firefox support assistant. "
            "Use the search_firefox_kb tool to find relevant documentation, "
            "then provide clear, step-by-step solutions based on the search results. "
            "Always cite your sources with URLs."
        )
        
        config = AgentConfig(
            model_id=model_id,
            instructions=base_instructions,
            tools=[search_firefox_kb],
            model_args=model_args
        )
        
        try:
            self.agent = AnyAgent.create(self.agent_type, config)
            self.current_model = model_id
            logger.info(f"✅ Configured {self.agent_type} with model: {model_id}")
        except Exception as e:
            logger.error(f"❌ Failed to configure agent: {e}")
            raise
    
    def clear_conversation(self):
        """Clear the conversation history to start fresh"""
        self.conversation_history = []
        logger.info("🧹 Conversation history cleared")
    
    def _format_conversation_context(self) -> str:
        """Format conversation history as context string"""
        if not self.conversation_history:
            return ""
        
        context = "\n\n=== Previous conversation ===\n"
        for entry in self.conversation_history[-6:]:  # Last 3 exchanges
            role = entry['role'].capitalize()
            content = entry['content'][:200]  # Truncate long messages
            if len(entry['content']) > 200:
                content += "..."
            context += f"{role}: {content}\n"
        context += "=== End of previous conversation ===\n\n"
        return context
    
    def generate_response(self, query: str, use_history: bool = True) -> Dict[str, Any]:
        """
        Generate a response with optional conversation history
        
        Args:
            query: User's question
            use_history: Whether to include conversation history (default: True)
            
        Returns:
            Dictionary with response and metadata
        """
        if not self.agent:
            return {
                'query': query,
                'response': "No agent configured. Please set a model first.",
                'model': None,
                'agent_type': self.agent_type,
                'error': True
            }
        
        try:
            # Prepare input based on agent type
            if self.agent_type == "openai" and use_history and self.conversation_history:
                # OpenAI supports message lists directly
                messages = []
                for msg in self.conversation_history:
                    messages.append(msg)
                messages.append({"role": "user", "content": query})
                
                # Run agent with message list
                agent_trace = self.agent.run(messages)
            else:
                # For TinyAgent and others: include context in the prompt
                if use_history and self.conversation_history:
                    context = self._format_conversation_context()
                    full_prompt = (
                        f"{context}"
                        f"Now, please answer the following question based on our conversation:\n"
                        f"User: {query}"
                    )
                else:
                    full_prompt = query
                
                # Run agent with formatted prompt
                agent_trace = self.agent.run(full_prompt)
            
            # Extract the response
            response_text = None
            
            # Check for final_output first
            if hasattr(agent_trace, 'final_output') and agent_trace.final_output:
                response_text = agent_trace.final_output
            
            # If no final_output, look in spans
            if not response_text and hasattr(agent_trace, 'spans') and agent_trace.spans:
                for span in reversed(agent_trace.spans):
                    if hasattr(span, 'attributes') and 'gen_ai.output' in span.attributes:
                        output = span.attributes['gen_ai.output']
                        if output:
                            response_text = output
                            break
            
            if not response_text:
                response_text = "Response generated but could not extract text."
            
            # Update conversation history
            if use_history:
                self.conversation_history.append({"role": "user", "content": query})
                self.conversation_history.append({"role": "assistant", "content": response_text})
                
                # Keep reasonable size
                if len(self.conversation_history) > 10:
                    self.conversation_history = self.conversation_history[-10:]
            
            return {
                'query': query,
                'response': response_text,
                'model': self.current_model,
                'agent_type': self.agent_type,
                'conversation_length': len(self.conversation_history),
                'error': False
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                'query': query,
                'response': f"Error: {str(e)}",
                'model': self.current_model,
                'agent_type': self.agent_type,
                'error': True
            }

def test_universal_multiturn():
    """Test multi-turn conversation with different agent types"""
    print("\n🧪 Testing Universal Multi-Turn Support")
    print("=" * 60)
    
    # Test queries
    queries = [
        "What is Firefox Sync?",
        "How do I set it up?",  # Should understand this refers to Firefox Sync
        "What if I forgot my password?",  # Should understand context
    ]
    
    # Test with different agent types
    test_configs = []
    
    # Add TinyAgent if no API key needed (local model)
    test_configs.append(("tinyagent", "tiny-agent"))
    
    # Add OpenAI if API key available
    if os.getenv('OPENAI_API_KEY'):
        test_configs.append(("openai", "gpt-3.5-turbo"))
    
    for agent_type, model in test_configs:
        print(f"\n\n🤖 Testing with {agent_type} / {model}")
        print("-" * 40)
        
        try:
            # Initialize bot
            bot = MozillaSupportBotUniversalMultiTurn(agent_type=agent_type)
            bot.set_model(model)
            
            # Run conversation
            for i, query in enumerate(queries[:2], 1):  # Just test first 2 queries
                print(f"\n👤 User (Turn {i}): {query}")
                
                response = bot.generate_response(query, use_history=True)
                
                if not response['error']:
                    resp_preview = response['response'][:200]
                    if len(response['response']) > 200:
                        resp_preview += "..."
                    print(f"🤖 Assistant: {resp_preview}")
                    print(f"📊 History: {response['conversation_length']} messages")
                else:
                    print(f"❌ Error: {response['response']}")
            
            # Clear for next test
            bot.clear_conversation()
            
        except Exception as e:
            print(f"❌ Failed to test {agent_type}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Universal multi-turn test complete!")

if __name__ == "__main__":
    test_universal_multiturn()