#!/bin/bash

echo "🦊 Mozilla Support Chatbot Web Interface"
echo "========================================="
echo ""

# Activate virtual environment
source venv/bin/activate

# Check if ChromaDB is set up
if [ ! -d "chroma_db" ]; then
    echo "📚 Setting up ChromaDB..."
    python setup_chromadb.py
    echo ""
fi

# Start the web server
echo "🚀 Starting web server..."
echo "📱 Open your browser to: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================="
echo ""

python app.py