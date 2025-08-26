#!/usr/bin/env python3
"""
Mozilla Support RAG Chatbot with official any-agent multi-turn conversation support
Using spans_to_messages() method as documented
"""

import json
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from any_agent import AgentConfig, AnyAgent, AgentTrace
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

class MozillaSupportBotOfficialMultiTurn:
    def __init__(self, persist_dir="./chroma_db", collection_name="sumo_kb", agent_type="openai"):
        """
        Initialize the Mozilla Support Bot with official any-agent multi-turn support
        
        Args:
            persist_dir: ChromaDB persistence directory
            collection_name: Name of the ChromaDB collection
            agent_type: Type of agent (any framework supported by any-agent)
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
        
        # Store conversation traces for multi-turn
        self.conversation_traces = []
        self.conversation_messages = []
    
    def set_model(self, model_id: str, agent_type: Optional[str] = None):
        """
        Configure the agent with a specific model
        
        Args:
            model_id: Model identifier
            agent_type: Override the agent type if needed
        """
        if agent_type:
            self.agent_type = agent_type
        
        # Map common model names to proper identifiers
        model_mapping = {
            "gpt-5": "openai/gpt-5",
            "gpt-4o": "openai/gpt-4o",
            "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
            "tiny-agent": "hf/TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            "mistral-small": "mistral/mistral-small-latest",
        }
        
        # Use mapping if available
        if model_id in model_mapping:
            model_id = model_mapping[model_id]
        
        # Configure model args
        model_args = {}
        if "gpt-5" in model_id:
            model_args['max_completion_tokens'] = 2000
        else:
            model_args['temperature'] = 0.3
            model_args['max_tokens'] = 500
        
        config = AgentConfig(
            model_id=model_id,
            instructions=(
                "You are a helpful Mozilla Firefox support assistant. "
                "Use the search_firefox_kb tool to find relevant documentation, "
                "then provide clear, step-by-step solutions based on the search results. "
                "Always cite your sources with URLs. "
                "Pay attention to the conversation history when provided."
            ),
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
        self.conversation_traces = []
        self.conversation_messages = []
        logger.info("🧹 Conversation history cleared")
    
    def _format_conversation_for_prompt(self) -> str:
        """Format conversation messages for including in prompt"""
        if not self.conversation_messages:
            return ""
        
        # Build conversation context
        context_lines = ["=== Previous conversation ==="]
        for msg in self.conversation_messages[-6:]:  # Last 3 exchanges
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            # Truncate long messages
            if len(content) > 300:
                content = content[:300] + "..."
            
            if role == 'user':
                context_lines.append(f"User: {content}")
            elif role == 'assistant':
                context_lines.append(f"Assistant: {content}")
        
        context_lines.append("=== End of previous conversation ===\n")
        return "\n".join(context_lines)
    
    def generate_response(self, query: str, use_history: bool = True) -> Dict[str, Any]:
        """
        Generate a response with optional conversation history using official any-agent approach
        
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
            # Prepare prompt based on conversation history
            if use_history and self.conversation_messages:
                # Format conversation context in the prompt
                conversation_context = self._format_conversation_for_prompt()
                full_prompt = f"{conversation_context}\nNow, please answer the following question based on our conversation:\n\nUser: {query}"
            else:
                full_prompt = query
            
            # Run agent
            agent_trace = self.agent.run(full_prompt)
            
            # Store trace for history
            self.conversation_traces.append(agent_trace)
            
            # Extract messages using the official method
            if hasattr(agent_trace, 'spans_to_messages'):
                try:
                    # Get messages from the current trace
                    new_messages = agent_trace.spans_to_messages()
                    
                    # Update our conversation messages
                    if use_history:
                        # Add to existing conversation
                        self.conversation_messages.extend(new_messages)
                    else:
                        # Start fresh
                        self.conversation_messages = new_messages
                except Exception as e:
                    logger.warning(f"Could not extract messages using spans_to_messages: {e}")
                    # Fall back to manual extraction
                    self.conversation_messages.append({"role": "user", "content": query})
            
            # Extract the response text
            response_text = None
            
            # Check for final_output first
            if hasattr(agent_trace, 'final_output') and agent_trace.final_output:
                response_text = agent_trace.final_output
            
            # If no final_output, look in spans for the LLM output
            if not response_text and hasattr(agent_trace, 'spans') and agent_trace.spans:
                for span in reversed(agent_trace.spans):
                    if hasattr(span, 'attributes') and 'gen_ai.output' in span.attributes:
                        output = span.attributes['gen_ai.output']
                        if output:
                            response_text = output
                            break
            
            if not response_text:
                response_text = "Response generated but could not extract text."
            
            # Add assistant response to messages if not already added
            if use_history and response_text:
                # Check if last message is already the assistant's response
                if not self.conversation_messages or self.conversation_messages[-1].get('content') != response_text:
                    self.conversation_messages.append({"role": "assistant", "content": response_text})
            
            # Keep conversation size reasonable
            if len(self.conversation_messages) > 10:
                self.conversation_messages = self.conversation_messages[-10:]
            
            return {
                'query': query,
                'response': response_text,
                'model': self.current_model,
                'agent_type': self.agent_type,
                'conversation_length': len(self.conversation_messages),
                'has_spans_to_messages': hasattr(agent_trace, 'spans_to_messages'),
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
    
    def get_conversation_messages(self) -> List[Dict[str, str]]:
        """Get the current conversation messages extracted via spans_to_messages"""
        return self.conversation_messages.copy()

def test_official_multiturn():
    """Test official multi-turn conversation approach"""
    print("\n🧪 Testing Official any-agent Multi-Turn Support")
    print("=" * 60)
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Please set OPENAI_API_KEY in .env file")
        return
    
    # Initialize bot
    bot = MozillaSupportBotOfficialMultiTurn()
    bot.set_model("gpt-3.5-turbo")
    
    # Test conversation flow
    queries = [
        "What is Firefox Sync?",
        "How do I set it up?",  # Should understand this refers to Firefox Sync
        "What if I forgot my password?",  # Should understand context
    ]
    
    print("\n🔄 Multi-turn conversation using official any-agent approach:")
    print("-" * 40)
    
    for i, query in enumerate(queries, 1):
        print(f"\n👤 User (Turn {i}): {query}")
        
        response = bot.generate_response(query, use_history=True)
        
        if not response['error']:
            print(f"🤖 Assistant: {response['response'][:400]}...")
            print(f"📊 Conversation length: {response['conversation_length']} messages")
            print(f"✅ Using spans_to_messages: {response['has_spans_to_messages']}")
        else:
            print(f"❌ Error: {response['response']}")
    
    # Show extracted conversation
    print("\n\n📜 Extracted conversation messages:")
    print("-" * 40)
    messages = bot.get_conversation_messages()
    for msg in messages[-4:]:  # Show last 2 exchanges
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')[:100]
        print(f"{role}: {content}...")
    
    print("\n" + "=" * 60)
    print("✅ Official multi-turn test complete!")

if __name__ == "__main__":
    test_official_multiturn()