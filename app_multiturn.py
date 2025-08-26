#!/usr/bin/env python3
"""
Flask web server for Mozilla Support Chatbot with multi-turn conversation support
Using OpenAI agent via any-agent for native multi-turn capabilities
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from mozilla_support_bot_multiturn import MozillaSupportBotMultiTurn
import os
from datetime import datetime
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)

# Configure CORS for production
cors_origin = os.getenv('CORS_ORIGIN', '*')
CORS(app, origins=cors_origin, allow_headers=['Content-Type'], methods=['GET', 'POST', 'OPTIONS'])

# Initialize the bot with multi-turn support (OpenAI agent only)
bot = None
model_name = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

try:
    bot = MozillaSupportBotMultiTurn(agent_type="openai")
    bot.set_model(model_name)
    print(f"✅ Bot initialized with {model_name}")
except Exception as e:
    print(f"❌ Failed to initialize bot: {e}")
    import traceback
    traceback.print_exc()
    # Keep bot as None but log the full error

# Store chat history for the UI (separate from bot's internal history)
chat_history = []

@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests with multi-turn support"""
    try:
        data = request.json
        query = data.get('query', '')
        use_history = data.get('use_history', True)  # Default to using history
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Generate response with multi-turn context
        if bot:
            response = bot.generate_response(query, use_history=use_history)
            
            if not response['error']:
                formatted_response = response['response']
            else:
                formatted_response = f"Error: {response['response']}"
            
            # Include conversation info in response
            conversation_info = {
                'conversation_length': response.get('conversation_length', 0),
                'using_history': use_history
            }
        else:
            formatted_response = "Bot not initialized. Please check your configuration."
            response = {'query': query, 'response': formatted_response, 'error': True}
            conversation_info = {'conversation_length': 0, 'using_history': False}
        
        # Store in UI history
        chat_entry = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'response': formatted_response,
            'conversation_info': conversation_info
        }
        chat_history.append(chat_entry)
        
        return jsonify({
            'response': formatted_response,
            'model': model_name,
            'conversation_info': conversation_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear_conversation', methods=['POST'])
def clear_conversation():
    """Clear the conversation history in the bot"""
    try:
        if bot:
            bot.clear_conversation()
            return jsonify({'status': 'success', 'message': 'Conversation history cleared'})
        else:
            return jsonify({'error': 'Bot not initialized'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation_history', methods=['GET'])
def get_conversation_history():
    """Get the current conversation history from the bot"""
    try:
        if bot:
            history = bot.get_conversation_history()
            return jsonify({
                'history': history,
                'length': len(history)
            })
        else:
            return jsonify({'error': 'Bot not initialized'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_ui_history():
    """Get chat history for the UI"""
    return jsonify({'history': chat_history})

@app.route('/api/clear_ui_history', methods=['POST'])
def clear_ui_history():
    """Clear UI chat history (doesn't affect bot's conversation memory)"""
    global chat_history
    chat_history = []
    return jsonify({'status': 'cleared'})

@app.route('/api/status', methods=['GET'])
def status():
    """Get system status including conversation state"""
    conversation_length = 0
    if bot:
        conversation_length = len(bot.get_conversation_history())
    
    return jsonify({
        'status': 'online',
        'model': model_name,
        'bot_initialized': bot is not None,
        'documents_count': bot.collection.count() if bot else 0,
        'ui_history_count': len(chat_history),
        'conversation_memory_count': conversation_length,
        'supports_multiturn': True
    })

if __name__ == '__main__':
    print(f"\n🦊 Mozilla Support Chatbot with Multi-turn Conversations")
    print(f"📊 Model: {model_name}")
    print(f"🔄 Multi-turn support: Enabled (OpenAI agent)")
    print(f"🌐 Starting web server at http://localhost:8080")
    print(f"{'=' * 50}\n")
    
    app.run(debug=True, port=8080)