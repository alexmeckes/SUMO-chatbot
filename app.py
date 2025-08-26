#!/usr/bin/env python3
"""
Flask backend for Mozilla Support RAG Chatbot
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from mozilla_support_bot_with_llm import MozillaSupportBotWithLLM
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Initialize the bot once at startup
print("Initializing Mozilla Support Bot...")
bot = None
try:
    bot = MozillaSupportBotWithLLM()
    model_name = bot.model
except Exception as e:
    print(f"Warning: Could not initialize bot with LLM: {e}")
    model_name = "Retrieval Only"

# Store chat history in memory (in production, use a database)
chat_history = []

@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template_string(open('templates/index.html').read())

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        data = request.json
        query = data.get('query', '')
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Generate response
        if bot:
            response = bot.generate_rag_response(query, n_results=3)
            formatted_response = bot.format_response(response)
            print(f"Query: {query}")
            print(f"Has LLM response: {response.get('llm_response') is not None}")
            print(f"LLM response length: {len(response.get('llm_response', ''))}")
        else:
            formatted_response = "Bot not initialized. Please check your configuration."
            response = {'query': query, 'llm_response': None, 'sources': []}
        
        # Store in history
        chat_entry = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'response': formatted_response,
            'sources': response.get('sources', [])
        }
        chat_history.append(chat_entry)
        
        return jsonify({
            'response': formatted_response,
            'sources': response.get('sources', []),
            'model': model_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search():
    """Handle search-only requests"""
    try:
        data = request.json
        query = data.get('query', '')
        n_results = data.get('n_results', 5)
        
        if not query or not bot:
            return jsonify({'error': 'No query provided or bot not initialized'}), 400
        
        # Perform search
        results = bot.search(query, n_results=n_results)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/topics', methods=['GET'])
def get_topics():
    """Get all available topics"""
    try:
        if not bot:
            return jsonify({'error': 'Bot not initialized'}), 500
            
        # Get all unique topics
        all_docs = bot.collection.get(include=['metadatas'])
        all_topics = set()
        for metadata in all_docs['metadatas']:
            topics = json.loads(metadata['topics'])
            all_topics.update(topics)
        
        return jsonify({'topics': sorted(list(all_topics))})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get chat history"""
    return jsonify({'history': chat_history})

@app.route('/api/clear_history', methods=['POST'])
def clear_history():
    """Clear chat history"""
    global chat_history
    chat_history = []
    return jsonify({'status': 'cleared'})

@app.route('/api/status', methods=['GET'])
def status():
    """Get system status"""
    return jsonify({
        'status': 'online',
        'model': model_name,
        'bot_initialized': bot is not None,
        'documents_count': bot.collection.count() if bot else 0,
        'history_count': len(chat_history)
    })

if __name__ == '__main__':
    print(f"\n🦊 Mozilla Support Chatbot")
    print(f"📊 Model: {model_name}")
    print(f"🌐 Starting web server at http://localhost:8080")
    print(f"{'=' * 50}\n")
    
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    app.run(debug=True, port=8080)