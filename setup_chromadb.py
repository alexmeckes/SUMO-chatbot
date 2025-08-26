#!/usr/bin/env python3
"""
Setup ChromaDB for Mozilla Support Knowledge Base RAG system
"""

import json
import os
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from tqdm import tqdm

def load_sumo_documents(data_dir="sumo_kb_tools/sumo_kb_20pages"):
    """Load all SUMO KB documents from JSON files"""
    documents = []
    doc_files = Path(data_dir).glob("*.json")
    
    for file_path in doc_files:
        if file_path.name in ["all_documents.json", "index.json"]:
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            doc = json.load(f)
            documents.append(doc)
    
    return documents

def prepare_documents_for_chromadb(documents):
    """Prepare documents in ChromaDB format"""
    texts = []
    metadatas = []
    ids = []
    
    for doc in documents:
        # Create comprehensive text for embedding
        text_content = f"""
Title: {doc['title']}
Summary: {doc['summary']}
Topics: {', '.join(doc.get('topics', []))}
Products: {', '.join(doc.get('products', []))}

Content:
{doc['text']}
"""
        
        texts.append(text_content)
        
        # Store metadata
        metadata = {
            'title': doc['title'],
            'summary': doc['summary'],
            'url': doc['url'],
            'slug': doc['slug'],
            'topics': json.dumps(doc.get('topics', [])),
            'products': json.dumps(doc.get('products', [])),
            'word_count': doc['metadata'].get('word_count', 0)
        }
        metadatas.append(metadata)
        
        # Use slug as unique ID
        ids.append(doc['slug'])
    
    return texts, metadatas, ids

def setup_chromadb(persist_dir="./chroma_db", collection_name="sumo_kb"):
    """Initialize ChromaDB with SUMO KB documents"""
    
    print("Loading SUMO KB documents...")
    documents = load_sumo_documents()
    print(f"Loaded {len(documents)} documents")
    
    # Prepare documents
    texts, metadatas, ids = prepare_documents_for_chromadb(documents)
    
    # Initialize ChromaDB client with persistence
    print("\nInitializing ChromaDB...")
    client = chromadb.PersistentClient(path=persist_dir)
    
    # Delete collection if exists (for clean setup)
    try:
        client.delete_collection(collection_name)
        print(f"Deleted existing collection: {collection_name}")
    except:
        pass
    
    # Create collection with sentence transformer embeddings
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    
    collection = client.create_collection(
        name=collection_name,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )
    
    # Add documents to collection
    print("\nAdding documents to ChromaDB...")
    
    # ChromaDB has a limit on batch size, so we'll add in chunks
    batch_size = 50
    for i in tqdm(range(0, len(texts), batch_size)):
        end_idx = min(i + batch_size, len(texts))
        collection.add(
            documents=texts[i:end_idx],
            metadatas=metadatas[i:end_idx],
            ids=ids[i:end_idx]
        )
    
    print(f"\n✅ Successfully added {len(texts)} documents to ChromaDB")
    print(f"📁 Database persisted to: {persist_dir}")
    
    # Verify the collection
    print(f"\nCollection stats:")
    print(f"  - Total documents: {collection.count()}")
    
    # Test query
    test_query = "How to fix audio video issues in Firefox"
    results = collection.query(
        query_texts=[test_query],
        n_results=3
    )
    
    print(f"\nTest query: '{test_query}'")
    print(f"Top 3 results:")
    for i, (doc_id, metadata) in enumerate(zip(results['ids'][0], results['metadatas'][0])):
        print(f"  {i+1}. {metadata['title']} ({doc_id})")
    
    return client, collection

if __name__ == "__main__":
    client, collection = setup_chromadb()
    print("\n✨ ChromaDB setup complete!")