# 🦊 Mozilla Support Bot - RAG Chatbot for Firefox Support

An intelligent chatbot that provides Firefox support using Retrieval-Augmented Generation (RAG) with Mozilla's SUMO knowledge base.

## Features

- **RAG-powered responses** - Uses ChromaDB vector database with 405+ Firefox support articles
- **Multi-turn conversations** - Maintains context across questions (powered by any-agent's TinyAgent framework)
- **Multiple LLM support** - Works with GPT-3.5-turbo, GPT-4o, and GPT-5 via any-agent framework
- **Web interface** - Clean, modern chat UI with conversation management
- **SUMO KB integration** - Direct access to Mozilla's official support documentation
- **Production ready** - Deployable with Docker, Railway (backend) and Vercel (frontend)

## Quick Start

### 1. Set up environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
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

**Option B: Docker**
```bash
docker build -t sumo-chatbot .
docker run -p 8080:8080 --env-file .env sumo-chatbot
```

**Option C: Command Line Testing**
```bash
python mozilla_support_bot_multiturn.py
```

## Project Structure

```
├── mozilla_support_bot_multiturn.py  # Core bot with TinyAgent & multi-turn support
├── app_multiturn.py                  # Flask web server with API endpoints
├── setup_chromadb.py                 # Vector database setup
├── sumo_kb_final.py                  # SUMO KB downloader and extractor
├── frontend/                         # Web UI
│   ├── index.html                   # Chat interface
│   └── config.js                    # Frontend configuration
├── chroma_db/                        # Vector database storage
├── sumo_kb_tools/                    # Downloaded Firefox documentation
├── Dockerfile                        # Docker container configuration
├── requirements.txt                  # Python dependencies
└── any-agent/                        # Local copy of any-agent framework
```

## Core Components

### Bot Implementation

- **`mozilla_support_bot_multiturn.py`** - Core bot using TinyAgent framework with any-llm for LLM calls
  - Supports multi-turn conversations with context retention
  - Configurable for GPT-3.5-turbo, GPT-4o, and GPT-5
  - Uses ChromaDB for vector search with cosine similarity

### Web Application

- **`app_multiturn.py`** - Flask server with conversation memory
- **`frontend/index.html`** - Modern chat interface with markdown support

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

Via any-agent framework with TinyAgent:
- **OpenAI**: GPT-3.5-turbo, GPT-4o, GPT-5
- **Other providers**: Can be added by modifying model_id format (e.g., "anthropic/claude-3")

## Deployment

### Deploy to Production

**Backend (Railway)**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway link
railway up
```

**Frontend (Vercel)**
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy frontend folder
cd frontend
vercel
```

**Environment Variables**
- Backend: Set `OPENAI_API_KEY` and `OPENAI_MODEL` in Railway dashboard
- Frontend: Set `VITE_API_URL` to your Railway backend URL in Vercel

### Development

**Test the bot locally**
```bash
# Test multi-turn conversations
python mozilla_support_bot_multiturn.py
```

**Add new models**
Edit the model_id in `set_model()` calls. TinyAgent with any-llm supports various providers.

## Technical Details

### Architecture
- **LLM Framework**: TinyAgent (from any-agent) using any-llm for API calls
- **Vector Database**: ChromaDB with HNSW index and cosine similarity
- **Embedding Model**: all-MiniLM-L6-v2 (384 dimensions)
- **Web Framework**: Flask with Gunicorn for production
- **Frontend**: Vanilla JavaScript with markdown rendering

### Notes
- Callbacks are disabled to prevent litellm imports (though litellm may still appear in logs due to dependency imports)
- TinyAgent uses any-llm (not litellm) for actual LLM API calls
- Multi-turn conversation context is maintained in memory per session

## Requirements

- Python 3.8+ (tested with 3.11)
- 2GB+ disk space for vector database
- OpenAI API key (or other LLM provider)
- Node.js (for Railway/Vercel CLIs)

## License

This project uses Mozilla's public support documentation. The bot implementation is provided as-is for educational purposes.