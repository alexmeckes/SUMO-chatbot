# 🦊 Mozilla Support Bot - RAG Chatbot for Firefox Support

An intelligent chatbot that provides Firefox support using Retrieval-Augmented Generation (RAG) with Mozilla's SUMO knowledge base.

## Features

- **RAG-powered responses** - Uses ChromaDB vector database with 405+ Firefox support articles
- **Multi-turn conversations** - Maintains context across questions (powered by OpenAI agents)
- **Multiple LLM support** - Works with GPT-3.5-turbo, GPT-4o, and GPT-5 via any-agent framework
- **Web interface** - Clean, modern chat UI with conversation management
- **SUMO KB integration** - Direct access to Mozilla's official support documentation

## Quick Start

### 1. Set up environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install chromadb sentence-transformers flask flask-cors openai any-agent python-dotenv
```

### 2. Configure API keys

Create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-3.5-turbo  # or gpt-4o, gpt-5
```

### 3. Set up the knowledge base

```bash
# Download SUMO knowledge base (if not already present)
python sumo_kb_final.py

# Load data into ChromaDB
python setup_chromadb.py
```

### 4. Run the chatbot

**Option A: Web Interface (Recommended)**
```bash
python app_multiturn.py
# Open http://localhost:8080 in your browser
```

**Option B: Command Line**
```bash
python mozilla_support_bot_with_llm.py
```

## Project Structure

```
├── mozilla_support_bot*.py      # Core bot implementations
├── app_multiturn.py             # Flask web server with multi-turn support
├── setup_chromadb.py            # Vector database setup
├── sumo_kb*.py                  # SUMO KB downloaders and extractors
├── templates/                   # Web UI templates
├── chroma_db/                   # Vector database storage
├── sumo_kb*/                    # Downloaded Firefox documentation
└── any-agent/                   # Multi-agent framework
```

## Core Components

### Bot Implementations

- **`mozilla_support_bot_multiturn.py`** - Multi-turn conversation support with OpenAI
- **`mozilla_support_bot_any_agent.py`** - any-agent integration for multiple models
- **`mozilla_support_bot_with_llm.py`** - Basic RAG implementation with LLM

### Web Application

- **`app_multiturn.py`** - Flask server with conversation memory
- **`templates/index_multiturn.html`** - Modern chat interface

### Data Pipeline

1. **Download**: `sumo_kb_final.py` fetches articles from Mozilla Support API
2. **Extract**: HTML content is cleaned and structured
3. **Index**: `setup_chromadb.py` creates vector embeddings
4. **Retrieve**: Bot searches relevant documents for user queries

## API Endpoints

- `POST /api/chat` - Send a message with optional conversation history
- `GET /api/status` - Check system status and conversation state
- `POST /api/clear_conversation` - Clear conversation memory
- `GET /api/conversation_history` - Get current conversation

## Multi-turn Conversations

The bot maintains conversation context, understanding references like "it", "that", etc.:

```
User: What is Firefox Sync?
Bot: Firefox Sync is a feature that lets you securely keep your Firefox data...

User: How do I set it up?  
Bot: Here's the quickest way to set up Firefox Sync... [understands "it" = Firefox Sync]
```

## Models Supported

Via any-agent framework:
- OpenAI: GPT-3.5-turbo, GPT-4o, GPT-5
- Mistral: mistral-small-latest
- TinyAgent: TinyLlama (local, no API key needed)

## Development

### Test the system
```bash
python test_rag_system.py
python test_all_models.py
```

### Add new models
Edit `mozilla_support_bot_any_agent.py` to add model configurations.

## Requirements

- Python 3.8+
- 2GB+ disk space for vector database
- OpenAI API key (or other LLM provider)

## License

This project uses Mozilla's public support documentation. The bot implementation is provided as-is for educational purposes.