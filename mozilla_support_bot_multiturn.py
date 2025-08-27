#!/usr/bin/env python3
"""
Mozilla Support RAG Chatbot with multi-turn conversation support
Using any-agent framework with OpenAI agents
"""

import json
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from any_agent import AgentConfig, AnyAgent
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

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
    
    # Format results with markdown links
    formatted = []
    for i in range(len(results['ids'][0])):
        metadata = results['metadatas'][0][i]
        doc_text = results['documents'][0][i][:500]  # First 500 chars
        formatted.append(
            f"**[{metadata['title']}]({metadata['url']})**\n"
            f"Summary: {metadata['summary']}\n"
            f"Content: {doc_text}...\n"
        )
    
    return "\n---\n".join(formatted)

class MozillaSupportBotMultiTurn:
    def __init__(self, persist_dir="./chroma_db", collection_name="sumo_kb", agent_type="openai"):
        """
        Initialize the Mozilla Support Bot with multi-turn conversation support
        
        Args:
            persist_dir: ChromaDB persistence directory
            collection_name: Name of the ChromaDB collection
            agent_type: Type of agent (must be "openai" for multi-turn support)
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
        
        # Store agent type (must be openai for multi-turn)
        self.agent_type = agent_type
        if agent_type != "openai":
            logger.warning("⚠️  Multi-turn conversations only supported with OpenAI agent type")
            self.agent_type = "openai"
        
        # Initialize agent
        self.agent = None
        self.current_model = None
        
        # Conversation history - stores messages in OpenAI format
        self.conversation_history = []
    
    def set_model(self, model_id: str):
        """
        Configure the agent with a specific model
        
        Args:
            model_id: Model identifier (e.g., "gpt-5", "gpt-4o", "gpt-3.5-turbo")
        """
        # Map common model names to proper identifiers
        model_mapping = {
            "gpt-5": "openai/gpt-5",
            "gpt-4o": "openai/gpt-4o",
            "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
        }
        
        # Use mapping if available
        if model_id in model_mapping:
            model_id = model_mapping[model_id]
        
        # Configure agent based on model
        model_args = {}
        if "gpt-5" in model_id:
            # GPT-5 specific settings
            model_args['temperature'] = 1  # GPT-5 only supports temperature=1
            model_args['max_tokens'] = 15000  # Increased for more comprehensive responses
        else:
            model_args['temperature'] = 0.3
            model_args['max_tokens'] = 15000
        
        # Try creating config without tools first, then add them
        try:
            config = AgentConfig(
                model_id=model_id,
                instructions=(
                    "You are a helpful Mozilla Firefox support assistant. "
                    "ALWAYS use the search_firefox_kb tool first to find relevant documentation. "
                    "Then provide clear, step-by-step solutions based on the search results. "
                    "ALWAYS include a 'Sources:' section at the end with clickable markdown links. "
                    "Format your response with:\n"
                    "1. The answer to the question\n"
                    "2. A 'Sources:' section with markdown links like: [Article Title](url)\n"
                    "Example: Sources:\n- [How to clear cache](https://support.mozilla.org/...)\n"
                    "Remember context from previous messages in the conversation."
                ),
                tools=[],  # Start with empty tools
                model_args=model_args
            )
            # Add the tool after config creation if needed
            config.tools = [search_firefox_kb]
        except Exception as e:
            # If that fails, try without tools at all
            logger.warning(f"Could not add tools to config: {e}")
            config = AgentConfig(
                model_id=model_id,
                instructions=(
                    "You are a helpful Mozilla Firefox support assistant. "
                    "Search the Firefox knowledge base and provide clear, step-by-step solutions. "
                    "ALWAYS include a 'Sources:' section at the end with relevant URLs. "
                    "Remember context from previous messages."
                ),
                model_args=model_args
            )
        
        try:
            # Create the agent
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
            # Prepare input based on whether we're using history
            if use_history and self.conversation_history:
                # Build message list for multi-turn conversation
                messages = []
                
                # Add conversation history
                for msg in self.conversation_history:
                    messages.append(msg)
                
                # Add current user message
                messages.append({"role": "user", "content": query})
                
                # Run agent with full conversation context
                # Create new event loop for this thread if needed
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                agent_trace = loop.run_until_complete(self.agent.run_async(messages))
            else:
                # Simple single-turn query
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run with a timeout to prevent hanging
                agent_trace = loop.run_until_complete(
                    asyncio.wait_for(self.agent.run_async(query), timeout=60.0)
                )
            
            # Extract the response from AgentTrace
            response_text = None
            
            # Check final_output
            if hasattr(agent_trace, 'final_output'):
                response_text = agent_trace.final_output
                logger.info(f"final_output type: {type(response_text)}, value: {response_text[:100] if response_text else 'None or empty'}")
            
            # If final_output is empty, check the last span for the actual response
            if not response_text and hasattr(agent_trace, 'spans') and agent_trace.spans:
                logger.info(f"final_output empty, checking {len(agent_trace.spans)} spans")
                
                # Look through ALL spans to find the final LLM response
                for span in reversed(agent_trace.spans):
                    if hasattr(span, 'attributes') and span.attributes:
                        # Check for the final LLM output (not tool calls)
                        if 'gen_ai.output' in span.attributes:
                            output = span.attributes['gen_ai.output']
                            # Skip tool calls (they're JSON arrays or start with specific patterns)
                            if output and not output.startswith('[') and not output.startswith('**[') and not output.startswith('Title:'):
                                response_text = output
                                logger.info(f"Found response in span: {getattr(span, 'name', 'unnamed')}")
                                break
                        
                        # Also check for 'output' directly
                        elif 'output' in span.attributes:
                            output = span.attributes['output']
                            if output and not output.startswith('[') and not output.startswith('**[') and not output.startswith('Title:'):
                                response_text = output
                                logger.info(f"Found response in span.attributes['output']")
                                break
            
            # Fallback
            if not response_text:
                logger.error(f"Could not extract response. AgentTrace.final_output: {agent_trace.final_output}")
                logger.error(f"AgentTrace type: {type(agent_trace)}")
                
                # Debug: print all span outputs
                if hasattr(agent_trace, 'spans'):
                    for i, span in enumerate(agent_trace.spans):
                        if hasattr(span, 'attributes') and 'gen_ai.output' in span.attributes:
                            logger.error(f"Span {i} ({span.name}): {span.attributes['gen_ai.output'][:200]}")
                
                response_text = "I encountered an error processing the response. Please try again."
            
            # Update conversation history if using history
            if use_history:
                # Add user message to history
                self.conversation_history.append({"role": "user", "content": query})
                # Add assistant response to history
                self.conversation_history.append({"role": "assistant", "content": response_text})
                
                # Keep conversation history reasonable size (last 10 exchanges)
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]
            
            return {
                'query': query,
                'response': response_text,
                'model': self.current_model,
                'agent_type': self.agent_type,
                'conversation_length': len(self.conversation_history),
                'error': False
            }
            
        except asyncio.TimeoutError:
            logger.error("Agent timed out after 60 seconds")
            return {
                'query': query,
                'response': "The request timed out. This might be due to GPT-5 processing. Please try again or use a different model.",
                'model': self.current_model,
                'agent_type': self.agent_type,
                'error': True
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
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history"""
        return self.conversation_history.copy()

def test_multiturn():
    """Test multi-turn conversation capability"""
    print("\n🧪 Testing Multi-Turn Conversation Support")
    print("=" * 60)
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Please set OPENAI_API_KEY in .env file")
        return
    
    # Initialize bot
    bot = MozillaSupportBotMultiTurn()
    bot.set_model("gpt-3.5-turbo")
    
    # Test conversation flow
    queries = [
        "What is Firefox Sync?",
        "How do I set it up?",  # Should understand this refers to Firefox Sync
        "What if I forgot my password?",  # Should understand context
    ]
    
    print("\n🔄 Starting multi-turn conversation:")
    print("-" * 40)
    
    for i, query in enumerate(queries, 1):
        print(f"\n👤 User (Turn {i}): {query}")
        
        response = bot.generate_response(query, use_history=True)
        
        if not response['error']:
            print(f"🤖 Assistant: {response['response'][:400]}...")
            print(f"📊 Conversation length: {response['conversation_length']} messages")
        else:
            print(f"❌ Error: {response['response']}")
    
    # Test without history
    print("\n\n🔄 Testing single query without history:")
    print("-" * 40)
    query = "What about Chrome?"  # Without context, this should be unclear
    print(f"👤 User: {query}")
    
    bot.clear_conversation()
    response = bot.generate_response(query, use_history=False)
    
    if not response['error']:
        print(f"🤖 Assistant: {response['response'][:400]}...")
    
    print("\n" + "=" * 60)
    print("✅ Multi-turn conversation test complete!")

if __name__ == "__main__":
    test_multiturn()