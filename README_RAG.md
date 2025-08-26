# Mozilla Support RAG Chatbot

A Retrieval-Augmented Generation (RAG) system for Mozilla Firefox support documentation.

## 🏗️ Architecture

### Current Implementation:

```
User Query → Embedding → ChromaDB Vector Search → Top K Documents → Response
                              ↓
                    (Semantic Similarity Search)
```

### With LLM Enhancement:

```
User Query → Embedding → ChromaDB Vector Search → Top K Documents → LLM → Generated Answer
                              ↓                         ↓              ↓
                    (Semantic Similarity)       (Context Window)  (GPT-3.5/Llama2)
```

## 📦 Components

### 1. **Basic Retrieval System** (`mozilla_support_bot.py`)
- ✅ Semantic search using sentence-transformers
- ✅ Returns relevant document links and summaries
- ✅ Topic filtering and similar article discovery
- ❌ No answer generation

### 2. **Full RAG System** (`mozilla_support_bot_with_llm.py`)
- ✅ Everything from basic system
- ✅ LLM integration (OpenAI GPT-3.5 or local Ollama)
- ✅ Synthesized answers from multiple sources
- ✅ Step-by-step solution generation

## 🚀 Setup

### 1. Install Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Ingest Data into ChromaDB
```bash
python setup_chromadb.py
```
This creates a persistent vector database at `./chroma_db/`

### 3. Configure LLM (Optional)
For AI-generated answers, choose one:

#### Option A: OpenAI (Recommended)
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

#### Option B: Local LLM with Ollama
```bash
# Install Ollama from https://ollama.ai
ollama pull llama2  # or mistral, codellama, etc.
```

## 💬 Usage

### Basic Retrieval-Only Bot
```bash
python mozilla_support_bot.py
```
- Returns relevant articles
- No answer generation
- No API key required

### Full RAG with LLM
```bash
python mozilla_support_bot_with_llm.py
```
- Generates comprehensive answers
- Cites sources
- Requires OpenAI API key or Ollama

## 🧪 Testing

### Test Basic Retrieval
```bash
python test_rag_system.py
```

### Test with LLM
```bash
python mozilla_support_bot_with_llm.py --test
```

## 📊 Performance Metrics

Based on testing with 90 documents:

| Query Type | Retrieval Accuracy | Response Time |
|------------|-------------------|---------------|
| Audio/Video Issues | 66-73% | <100ms |
| Import/Export | 75% | <100ms |
| Performance | 72% | <100ms |
| UI/Display | 72% | <100ms |

With LLM:
- OpenAI GPT-3.5: +1-2s latency, high quality answers
- Local Llama2: +3-5s latency, good quality answers

## 🎯 How It Works

### Retrieval Phase
1. User query is embedded using sentence-transformers
2. ChromaDB performs cosine similarity search
3. Top K most relevant documents retrieved

### Generation Phase (with LLM)
1. Retrieved documents become context
2. LLM receives context + query
3. Generates coherent answer citing sources

### Without LLM (Fallback)
1. Returns formatted list of relevant articles
2. Provides direct links to documentation
3. Shows relevance scores

## 🔄 Scaling Considerations

### Current Limitations
- 90 documents (rate-limited sample)
- ~427KB of text data
- Single-hop retrieval

### For Production
1. **More Data**: Ingest complete Mozilla KB (~1000+ articles)
2. **Better Embeddings**: Consider OpenAI embeddings or specialized models
3. **Hybrid Search**: Combine vector + keyword search
4. **Caching**: Cache common queries
5. **Reranking**: Add a reranking model for better precision
6. **Multi-hop**: Support follow-up questions with context

## 📈 Next Steps

1. **Expand Dataset**: Remove rate limiting, ingest all articles
2. **Fine-tune Embeddings**: Train on Mozilla-specific terminology
3. **Add Feedback Loop**: Track which articles actually help users
4. **Implement Chat Memory**: Maintain conversation context
5. **Add Streaming**: Stream LLM responses for better UX

## 🤔 Why ChromaDB?

- **Simplicity**: Easy setup, no external services
- **Persistence**: Data survives restarts
- **Performance**: Fast for <10K documents
- **Flexibility**: Supports metadata filtering

For larger scale, consider:
- Pinecone (managed, scalable)
- Weaviate (more features)
- Qdrant (better performance)
- pgvector (if using PostgreSQL)