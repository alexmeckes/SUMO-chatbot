#!/usr/bin/env python3
"""
Simplified SUMO Knowledge Base Downloader for Chatbot with Citations
Downloads Mozilla Support documentation with metadata for vector DB ingestion.
Chunking is left to the vector database/RAG framework.
"""

import requests
import json
import os
import re
from datetime import datetime
from time import sleep
from typing import Dict, List, Optional
from pathlib import Path
from html.parser import HTMLParser

class HTMLTextExtractor(HTMLParser):
    """Extract clean text from HTML."""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'meta', 'link'}
        self.current_tag = None
        self.in_skip = False
    
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in self.skip_tags:
            self.in_skip = True
        elif tag in {'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'br', 'div', 'section'}:
            self.text_parts.append('\n')
    
    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.in_skip = False
    
    def handle_data(self, data):
        if not self.in_skip and data.strip():
            self.text_parts.append(data.strip())
    
    def get_text(self):
        text = ' '.join(self.text_parts)
        # Clean up excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()

class SimpleSUMODownloader:
    """Simplified downloader for SUMO documentation."""
    
    def __init__(self, output_dir: str = "sumo_kb", locale: str = "en-US"):
        self.base_url = "https://support.mozilla.org"
        self.api_base = f"{self.base_url}/api/1/kb"
        self.output_dir = Path(output_dir)
        self.locale = locale
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Progress tracking
        self.progress_file = self.output_dir / "progress.json"
        self.progress = self.load_progress()
    
    def load_progress(self) -> Dict:
        """Load download progress."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {"downloaded": [], "failed": []}
    
    def save_progress(self):
        """Save download progress."""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def fetch_document_list(self, page: int = 1, product: Optional[str] = None) -> Dict:
        """Fetch a page of documents from the API."""
        params = {"page": page, "locale": self.locale}
        if product:
            params["product"] = product
        
        try:
            response = requests.get(self.api_base, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            return {}
    
    def fetch_document(self, slug: str) -> Optional[Dict]:
        """Fetch full document details."""
        url = f"{self.api_base}/{slug}"
        params = {"locale": self.locale}
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching document {slug}: {e}")
            return None
    
    def process_document(self, doc: Dict) -> Dict:
        """Process document for vector DB ingestion."""
        # Extract clean text from HTML
        html_extractor = HTMLTextExtractor()
        html_content = doc.get('html', '')
        html_extractor.feed(html_content)
        clean_text = html_extractor.get_text()
        
        # Build the canonical URL
        article_url = f"{self.base_url}/{self.locale}/kb/{doc.get('slug', '')}"
        
        # Create document with all necessary metadata for chatbot
        processed = {
            # Core content
            "content": clean_text,
            "title": doc.get('title', ''),
            "summary": doc.get('summary', ''),
            
            # Citation information
            "url": article_url,
            "slug": doc.get('slug', ''),
            "source": "Mozilla Support (SUMO)",
            
            # Metadata for filtering/searching
            "products": doc.get('products', []),
            "topics": doc.get('topics', []),
            "locale": self.locale,
            
            # Additional metadata
            "metadata": {
                "char_count": len(clean_text),
                "word_count": len(clean_text.split()),
                "has_html": bool(html_content),
                "downloaded_at": datetime.now().isoformat()
            }
        }
        
        return processed
    
    def download_all(self, product: Optional[str] = None, max_docs: Optional[int] = None):
        """Download all documents."""
        print(f"\n{'='*60}")
        print(f"SUMO Knowledge Base Downloader (Simplified)")
        print(f"{'='*60}")
        print(f"Locale: {self.locale}")
        if product:
            print(f"Product: {product}")
        print(f"Output: {self.output_dir}/")
        print(f"{'='*60}\n")
        
        # Collect all document slugs
        all_slugs = []
        downloaded = set(self.progress.get('downloaded', []))
        page = 1
        
        print("Phase 1: Collecting document list...")
        while True:
            if max_docs and len(all_slugs) >= max_docs:
                break
            
            print(f"  Page {page}...", end=" ")
            data = self.fetch_document_list(page, product)
            
            if not data or not data.get('results'):
                print("done")
                break
            
            results = data.get('results', [])
            for doc in results:
                if doc['slug'] not in downloaded:
                    all_slugs.append(doc['slug'])
            
            print(f"{len(results)} docs")
            
            if not data.get('next'):
                break
            
            page += 1
            sleep(0.3)
        
        print(f"\nPhase 2: Downloading {len(all_slugs)} documents...")
        
        documents = []
        for i, slug in enumerate(all_slugs):
            if max_docs and i >= max_docs:
                break
            
            print(f"  [{i+1}/{min(len(all_slugs), max_docs or len(all_slugs))}] {slug[:40]}...", end=" ")
            
            # Fetch document
            doc = self.fetch_document(slug)
            if not doc:
                print("FAILED")
                self.progress['failed'].append(slug)
                continue
            
            # Process document
            processed = self.process_document(doc)
            documents.append(processed)
            
            # Save individual document
            doc_file = self.output_dir / f"{slug}.json"
            with open(doc_file, 'w', encoding='utf-8') as f:
                json.dump(processed, f, ensure_ascii=False, indent=2)
            
            print("OK")
            
            # Update progress
            self.progress['downloaded'].append(slug)
            if (i + 1) % 10 == 0:
                self.save_progress()
            
            sleep(0.5)
        
        # Save all documents in a single file
        all_docs_file = self.output_dir / "all_documents.json"
        with open(all_docs_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        
        # Save as JSONL for easy streaming
        jsonl_file = self.output_dir / "all_documents.jsonl"
        with open(jsonl_file, 'w', encoding='utf-8') as f:
            for doc in documents:
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')
        
        # Create a simple CSV index
        import csv
        csv_file = self.output_dir / "index.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['title', 'url', 'products', 'topics', 'word_count'])
            for doc in documents:
                writer.writerow([
                    doc['title'],
                    doc['url'],
                    ', '.join(doc['products']),
                    ', '.join(doc['topics']),
                    doc['metadata']['word_count']
                ])
        
        # Save final progress
        self.save_progress()
        
        # Summary
        print(f"\n{'='*60}")
        print("Download Complete!")
        print(f"{'='*60}")
        print(f"Documents: {len(documents)}")
        print(f"Failed: {len(self.progress.get('failed', []))}")
        print(f"\nOutput files:")
        print(f"  - Individual docs: {self.output_dir}/*.json")
        print(f"  - All documents: {all_docs_file}")
        print(f"  - JSONL format: {jsonl_file}")
        print(f"  - Index CSV: {csv_file}")
        print(f"\nReady for vector DB ingestion!")
        print("Your vector DB will handle chunking automatically.")
        
        return documents
    
    def create_sample_usage(self):
        """Show sample usage with popular vector DBs."""
        print(f"\n{'='*60}")
        print("Sample Usage with Vector Databases:")
        print(f"{'='*60}")
        
        sample_code = """
# Example with LangChain and ChromaDB:
from langchain.document_loaders import JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

# Load documents
loader = JSONLoader(
    file_path='sumo_kb/all_documents.json',
    jq_schema='.[].content',
    content_key="content",
    metadata_func=lambda record, metadata: {
        "title": record.get("title"),
        "url": record.get("url"),
        "products": ", ".join(record.get("products", [])),
        "topics": ", ".join(record.get("topics", []))
    }
)
docs = loader.load()

# Vector DB handles chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
chunks = text_splitter.split_documents(docs)

# Create vector store
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=OpenAIEmbeddings()
)

# Query with citations
results = vectorstore.similarity_search("how to clear cache")
for doc in results:
    print(f"Answer: {doc.page_content[:200]}...")
    print(f"Source: {doc.metadata['title']}")
    print(f"Link: {doc.metadata['url']}\\n")
"""
        print(sample_code)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download SUMO KB for chatbot')
    parser.add_argument('--locale', default='en-US', help='Locale (default: en-US)')
    parser.add_argument('--product', help='Filter by product (e.g., firefox)')
    parser.add_argument('--max-docs', type=int, help='Max documents (for testing)')
    parser.add_argument('--output-dir', default='sumo_kb', help='Output directory')
    parser.add_argument('--show-usage', action='store_true', help='Show usage examples')
    
    args = parser.parse_args()
    
    downloader = SimpleSUMODownloader(
        output_dir=args.output_dir,
        locale=args.locale
    )
    
    if args.show_usage:
        downloader.create_sample_usage()
    else:
        downloader.download_all(
            product=args.product,
            max_docs=args.max_docs
        )
        downloader.create_sample_usage()


if __name__ == "__main__":
    main()