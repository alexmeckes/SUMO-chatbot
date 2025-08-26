#!/usr/bin/env python3
"""
Mozilla Support RAG Chatbot using any-agent framework
Supports TinyAgent, GPT-5, and other models
"""

import json
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from any_agent import AgentConfig, AnyAgent
from any_agent.tools import search_web, visit_webpage
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

class MozillaSupportBotAnyAgent:
    def __init__(self, persist_dir="./chroma_db", collection_name="sumo_kb", agent_type="tinyagent"):
        """
        Initialize the Mozilla Support Bot with any-agent framework
        
        Args:
            persist_dir: ChromaDB persistence directory
            collection_name: Name of the ChromaDB collection
            agent_type: Type of agent ("tinyagent", "openai", "langchain", etc.)
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
        
        # Initialize agent (will be configured with set_model)
        self.agent = None
        self.current_model = None
    
    def set_model(self, model_id: str, agent_type: Optional[str] = None):
        """
        Configure the agent with a specific model
        
        Args:
            model_id: Model identifier (e.g., "gpt-5", "mistral/mistral-small-latest", "tiny-agent")
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
        
        # Special handling for TinyAgent
        if "tiny" in model_id.lower() or self.agent_type == "tinyagent":
            self.agent_type = "tinyagent"
            # TinyAgent uses Hugging Face models
            if not model_id.startswith("hf/"):
                model_id = f"hf/{model_id}"
        
        # Configure agent based on type
        model_args = {}
        if "gpt-5" in model_id:
            # GPT-5 specific settings
            model_args['max_completion_tokens'] = 2000
            # GPT-5 requires default temperature
        else:
            model_args['temperature'] = 0.3
            model_args['max_tokens'] = 500
        
        config = AgentConfig(
            model_id=model_id,
            instructions=(
                "You are a helpful Mozilla Firefox support assistant. "
                "Use the search_firefox_kb tool to find relevant documentation, "
                "then provide clear, step-by-step solutions based on the search results. "
                "Always cite your sources with URLs."
            ),
            tools=[search_firefox_kb],
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
    
    def generate_response(self, query: str) -> Dict[str, Any]:
        """
        Generate a response using the configured agent
        
        Args:
            query: User's question
            
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
            # Run the agent
            agent_trace = self.agent.run(query)
            
            # Extract the response - any-agent returns an AgentTrace object
            response_text = None
            
            # Check for final_output first (this is the preferred method)
            if hasattr(agent_trace, 'final_output') and agent_trace.final_output:
                response_text = agent_trace.final_output
            
            # If no final_output, look in spans for the LLM output
            if not response_text and hasattr(agent_trace, 'spans') and agent_trace.spans:
                # Iterate through spans in reverse to get the last LLM output
                for span in reversed(agent_trace.spans):
                    if hasattr(span, 'attributes') and 'gen_ai.output' in span.attributes:
                        output = span.attributes['gen_ai.output']
                        if output:
                            response_text = output
                            break
            
            # Final fallback
            if not response_text:
                response_text = "Response generated but could not extract text. Check agent trace for details."
            
            # Get tool calls if available
            tool_calls = []
            if hasattr(agent_trace, 'tool_calls'):
                tool_calls = agent_trace.tool_calls
            
            return {
                'query': query,
                'response': response_text,
                'model': self.current_model,
                'agent_type': self.agent_type,
                'tool_calls': tool_calls,
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
    
    def compare_models(self, query: str, models: List[str]) -> Dict[str, Any]:
        """
        Compare responses from different models
        
        Args:
            query: User's question
            models: List of model identifiers to compare
            
        Returns:
            Dictionary with responses from each model
        """
        results = {}
        
        for model_id in models:
            logger.info(f"Testing model: {model_id}")
            
            # Determine agent type based on model
            if "tiny" in model_id.lower():
                agent_type = "tinyagent"
            elif "gpt" in model_id.lower() or "openai" in model_id.lower():
                agent_type = "openai"
            else:
                agent_type = self.agent_type
            
            try:
                self.set_model(model_id, agent_type)
                response = self.generate_response(query)
                results[model_id] = response
            except Exception as e:
                results[model_id] = {
                    'query': query,
                    'response': f"Failed to load model: {str(e)}",
                    'model': model_id,
                    'error': True
                }
        
        return results

def test_any_agent():
    """Test the any-agent implementation"""
    print("\n🧪 Testing Mozilla Support Bot with any-agent")
    print("=" * 60)
    
    # Initialize bot
    bot = MozillaSupportBotAnyAgent()
    
    # Test query
    test_query = "How do I clear Firefox cache and cookies?"
    
    # Test with different models
    models_to_test = [
        "gpt-5",  # GPT-5 via OpenAI
        "tiny-agent",  # TinyAgent with TinyLlama
        # "mistral-small",  # Mistral (requires API key)
    ]
    
    print(f"\nQuery: {test_query}")
    print("-" * 60)
    
    for model in models_to_test:
        print(f"\n### Testing {model}")
        try:
            # Check for required API keys
            if "gpt" in model and not os.getenv('OPENAI_API_KEY'):
                print("⚠️  Skipping - OPENAI_API_KEY not set")
                continue
            if "mistral" in model and not os.getenv('MISTRAL_API_KEY'):
                print("⚠️  Skipping - MISTRAL_API_KEY not set")
                continue
            
            bot.set_model(model)
            response = bot.generate_response(test_query)
            
            if not response['error']:
                print(f"✅ Success!")
                print(f"Response preview: {response['response'][:200]}...")
            else:
                print(f"❌ Error: {response['response']}")
                
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Testing complete!")

if __name__ == "__main__":
    test_any_agent()