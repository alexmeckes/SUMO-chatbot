#!/usr/bin/env python3
"""
Flask web server for Mozilla Support Chatbot with multi-turn conversation support
Using OpenAI agent via any-agent for native multi-turn capabilities
"""

from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from mozilla_support_bot_multiturn import MozillaSupportBotMultiTurn
from feedback_manager_production import get_feedback_manager
import os
from datetime import datetime
from dotenv import load_dotenv
import json
import time
import csv
import io

load_dotenv()

app = Flask(__name__)

# Configure CORS for production
cors_origin = os.getenv('CORS_ORIGIN', '*')
CORS(app, origins=cors_origin, allow_headers=['Content-Type'], methods=['GET', 'POST', 'OPTIONS'])

# Initialize the bot with multi-turn support (OpenAI agent only)
bot = None
model_name = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

try:
    bot = MozillaSupportBotMultiTurn(agent_type="tinyagent")
    print(f"✅ Bot created with TinyAgent, setting model to {model_name}")
    bot.set_model(model_name)
    print(f"✅ Bot initialized with {model_name}")
    print(f"✅ Agent configured: {bot.agent is not None}")
except Exception as e:
    print(f"❌ Failed to initialize bot: {e}")
    import traceback
    traceback.print_exc()
    # Try to create bot without model if possible
    try:
        bot = MozillaSupportBotMultiTurn(agent_type="tinyagent")
        print(f"⚠️  Bot created but model not set due to error")
    except:
        bot = None

# Initialize feedback manager (production-aware)
feedback_manager = get_feedback_manager()

# Store chat history for the UI (separate from bot's internal history)
chat_history = []

# Store session tracking
sessions = {}

@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Serve the analytics dashboard"""
    return render_template('dashboard.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests with multi-turn support"""
    try:
        data = request.json
        query = data.get('query', '')
        use_history = data.get('use_history', True)  # Default to using history
        session_id = data.get('session_id')  # Optional session ID for tracking
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Track response time
        start_time = time.time()
        
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
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Save to feedback manager if session exists
        conversation_id = None
        if session_id and feedback_manager:
            try:
                # Extract sources if available (for future use)
                sources = []
                
                # Extract trace data if available
                trace_data = response.get('trace_data') if not response.get('error', False) else None
                
                conversation_id = feedback_manager.save_conversation(
                    session_id=session_id,
                    query=query,
                    response=formatted_response,
                    model=model_name,
                    response_time_ms=response_time_ms,
                    sources=sources,
                    trace_data=trace_data,
                    error=response.get('error', False)
                )
            except Exception as e:
                # Log but don't fail the request
                print(f"Warning: Could not save conversation to feedback DB: {e}")
        
        # Store in UI history
        chat_entry = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'response': formatted_response,
            'conversation_info': conversation_info,
            'conversation_id': conversation_id,
            'response_time_ms': response_time_ms
        }
        chat_history.append(chat_entry)
        
        return jsonify({
            'response': formatted_response,
            'model': model_name,
            'conversation_info': conversation_info,
            'conversation_id': conversation_id,
            'response_time_ms': response_time_ms
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

@app.route('/api/session', methods=['POST'])
def create_session():
    """Create a new feedback session"""
    try:
        user_agent = request.headers.get('User-Agent', '')
        remote_addr = request.remote_addr
        
        session_id = feedback_manager.create_session(
            user_agent=user_agent, 
            ip_address=remote_addr
        )
        sessions[session_id] = {'created': datetime.now()}
        
        return jsonify({
            'session_id': session_id,
            'status': 'created'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback for a conversation"""
    try:
        data = request.json
        conversation_id = data.get('conversation_id')
        feedback_type = data.get('feedback_type')  # 'positive' or 'negative'
        comment = data.get('comment', '')
        rating = data.get('rating')
        
        if not conversation_id or not feedback_type:
            return jsonify({'error': 'Missing required fields'}), 400
        
        feedback_id = feedback_manager.add_feedback(
            conversation_id=conversation_id,
            feedback_type=feedback_type,
            rating=rating,
            comment=comment
        )
        
        return jsonify({
            'feedback_id': feedback_id,
            'status': 'recorded'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback/stats', methods=['GET'])
def get_feedback_stats():
    """Get feedback statistics"""
    try:
        days = request.args.get('days', 7, type=int)
        stats = feedback_manager.get_feedback_stats(days=days)
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/<conversation_id>/trace', methods=['GET'])
def get_conversation_trace(conversation_id):
    """Get trace data for a specific conversation"""
    try:
        import sqlite3
        
        with sqlite3.connect(feedback_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT query, response, model, response_time_ms, trace_data, timestamp
                FROM conversations
                WHERE id = ?
            """, (conversation_id,))
            
            row = cursor.fetchone()
            
            if row:
                import json
                result = dict(row)
                # Parse trace_data from JSON if it exists
                if result['trace_data']:
                    result['trace_data'] = json.loads(result['trace_data'])
                return jsonify(result)
            else:
                return jsonify({'error': 'Conversation not found'}), 404
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/recent', methods=['GET'])
def get_recent_conversations():
    """Get recent conversations with feedback info"""
    try:
        days = request.args.get('days', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        import sqlite3
        with sqlite3.connect(feedback_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    c.id,
                    c.session_id,
                    c.query,
                    c.response,
                    c.model,
                    c.response_time_ms,
                    c.timestamp,
                    c.error,
                    f.feedback_type,
                    f.rating,
                    f.comment,
                    CASE 
                        WHEN c.trace_data IS NOT NULL THEN 1 
                        ELSE 0 
                    END as has_trace
                FROM conversations c
                LEFT JOIN feedback f ON c.id = f.conversation_id
                WHERE c.timestamp > datetime('now', '-' || ? || ' days')
                ORDER BY c.timestamp DESC
                LIMIT ?
            """, (days, limit))
            
            conversations = []
            for row in cursor.fetchall():
                conv = dict(row)
                # Truncate response for list view
                conv['response'] = conv['response'][:200] + '...' if len(conv['response']) > 200 else conv['response']
                conversations.append(conv)
            
            return jsonify({
                'conversations': conversations,
                'count': len(conversations)
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/csv', methods=['GET'])
def export_to_csv():
    """Export conversations and feedback to CSV"""
    try:
        days = request.args.get('days', 7, type=int)
        include_traces = request.args.get('include_traces', 'false').lower() == 'true'
        
        import sqlite3
        with sqlite3.connect(feedback_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    c.id as conversation_id,
                    c.session_id,
                    c.timestamp,
                    c.query,
                    c.response,
                    c.model,
                    c.response_time_ms,
                    c.error,
                    f.feedback_type,
                    f.rating,
                    f.comment as feedback_comment,
                    f.timestamp as feedback_timestamp
            """
            
            if include_traces:
                query += ", c.trace_data"
            
            query += """
                FROM conversations c
                LEFT JOIN feedback f ON c.id = f.conversation_id
                WHERE c.timestamp > datetime('now', '-' || ? || ' days')
                ORDER BY c.timestamp DESC
            """
            
            cursor.execute(query, (days,))
            rows = cursor.fetchall()
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            headers = ['conversation_id', 'session_id', 'timestamp', 'query', 'response', 
                      'model', 'response_time_ms', 'error', 'feedback_type', 'rating', 
                      'feedback_comment', 'feedback_timestamp']
            
            if include_traces:
                headers.extend(['tool_calls_count', 'total_input_tokens', 'total_output_tokens'])
            
            writer.writerow(headers)
            
            # Write data
            for row in rows:
                row_data = [
                    row['conversation_id'],
                    row['session_id'],
                    row['timestamp'],
                    row['query'],
                    row['response'][:500],  # Truncate long responses
                    row['model'],
                    row['response_time_ms'],
                    row['error'],
                    row['feedback_type'],
                    row['rating'],
                    row['feedback_comment'],
                    row['feedback_timestamp']
                ]
                
                if include_traces and row.get('trace_data'):
                    try:
                        trace = json.loads(row['trace_data'])
                        tool_calls_count = len(trace.get('tool_calls', []))
                        
                        # Calculate total tokens
                        total_input = 0
                        total_output = 0
                        for llm_call in trace.get('llm_calls', []):
                            total_input += llm_call.get('input_tokens', 0) or 0
                            total_output += llm_call.get('output_tokens', 0) or 0
                        
                        row_data.extend([tool_calls_count, total_input, total_output])
                    except:
                        row_data.extend([0, 0, 0])
                elif include_traces:
                    row_data.extend([0, 0, 0])
                
                writer.writerow(row_data)
            
            # Create response
            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=feedback_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                }
            )
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/costs', methods=['GET'])
def calculate_costs():
    """Calculate API costs based on token usage"""
    try:
        days = request.args.get('days', 7, type=int)
        
        # OpenAI pricing (as of 2024)
        pricing = {
            'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},  # per 1K tokens
            'gpt-4o': {'input': 0.005, 'output': 0.015},  # per 1K tokens
            'gpt-5': {'input': 0.03, 'output': 0.06},  # estimated pricing
        }
        
        import sqlite3
        with sqlite3.connect(feedback_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT model, trace_data
                FROM conversations
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                AND trace_data IS NOT NULL
            """, (days,))
            
            costs_by_model = {}
            total_cost = 0
            total_conversations = 0
            total_tokens = {'input': 0, 'output': 0}
            
            for row in cursor.fetchall():
                model = row[0]
                trace_data = row[1]
                
                if trace_data:
                    try:
                        trace = json.loads(trace_data)
                        
                        # Sum tokens from all LLM calls
                        input_tokens = 0
                        output_tokens = 0
                        
                        for llm_call in trace.get('llm_calls', []):
                            input_tokens += llm_call.get('input_tokens', 0) or 0
                            output_tokens += llm_call.get('output_tokens', 0) or 0
                        
                        # Calculate cost
                        model_key = model.lower() if model else 'gpt-3.5-turbo'
                        if model_key not in pricing:
                            model_key = 'gpt-3.5-turbo'  # Default pricing
                        
                        input_cost = (input_tokens / 1000) * pricing[model_key]['input']
                        output_cost = (output_tokens / 1000) * pricing[model_key]['output']
                        conversation_cost = input_cost + output_cost
                        
                        # Update totals
                        if model not in costs_by_model:
                            costs_by_model[model] = {
                                'conversations': 0,
                                'total_cost': 0,
                                'input_tokens': 0,
                                'output_tokens': 0
                            }
                        
                        costs_by_model[model]['conversations'] += 1
                        costs_by_model[model]['total_cost'] += conversation_cost
                        costs_by_model[model]['input_tokens'] += input_tokens
                        costs_by_model[model]['output_tokens'] += output_tokens
                        
                        total_cost += conversation_cost
                        total_conversations += 1
                        total_tokens['input'] += input_tokens
                        total_tokens['output'] += output_tokens
                        
                    except Exception as e:
                        print(f"Error parsing trace data: {e}")
            
            return jsonify({
                'period_days': days,
                'total_cost': round(total_cost, 4),
                'total_conversations': total_conversations,
                'total_tokens': total_tokens,
                'average_cost_per_conversation': round(total_cost / total_conversations, 4) if total_conversations > 0 else 0,
                'costs_by_model': costs_by_model,
                'pricing_used': pricing,
                'note': 'Costs are estimated based on standard OpenAI pricing'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        'supports_multiturn': True,
        'feedback_enabled': True
    })

if __name__ == '__main__':
    print(f"\n🦊 Mozilla Support Chatbot with Multi-turn Conversations")
    print(f"📊 Model: {model_name}")
    print(f"🔄 Multi-turn support: Enabled (OpenAI agent)")
    print(f"🌐 Starting web server at http://localhost:8080")
    print(f"{'=' * 50}\n")
    
    app.run(debug=True, port=8080)