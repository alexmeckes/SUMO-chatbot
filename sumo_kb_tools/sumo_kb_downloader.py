#!/usr/bin/env python3
"""
SUMO Knowledge Base Downloader for Chatbot with Citations
This script downloads Mozilla Support documentation and structures it 
for use in a RAG (Retrieval-Augmented Generation) chatbot system with 
proper citations and links back to source articles.
"""

import requests
import json
import os
import hashlib
import re
from datetime import datetime
from time import sleep
from typing import Dict, List, Optional, Set
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin

class HTMLTextExtractor(HTMLParser):
    """Extract clean text from HTML while preserving structure."""
    
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

class SUMOKnowledgeBaseDownloader:
    """Download and structure SUMO documentation for chatbot use."""
    
    def __init__(self, base_url: str = "https://support.mozilla.org", 
                 output_dir: str = "sumo_knowledge_base",
                 locale: str = "en-US"):
        """
        Initialize the downloader.
        
        Args:
            base_url: Base URL for SUMO
            output_dir: Directory to save downloaded content
            locale: Language/locale to download
        """
        self.base_url = base_url
        self.api_base = f"{base_url}/api/1/kb"
        self.output_dir = Path(output_dir)
        self.locale = locale
        
        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "raw_html").mkdir(exist_ok=True)
        (self.output_dir / "processed").mkdir(exist_ok=True)
        (self.output_dir / "chunks").mkdir(exist_ok=True)
        
        # Track progress
        self.progress_file = self.output_dir / "download_progress.json"
        self.progress = self.load_progress()
    
    def load_progress(self) -> Dict:
        """Load download progress from file."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            "downloaded_slugs": [],
            "failed_slugs": [],
            "last_page": 0,
            "total_documents": 0
        }
    
    def save_progress(self):
        """Save download progress to file."""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def fetch_document_list(self, page: int = 1, product: Optional[str] = None) -> Dict:
        """Fetch a page of documents from the API."""
        params = {
            "page": page,
            "locale": self.locale
        }
        if product:
            params["product"] = product
        
        try:
            response = requests.get(self.api_base, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            return {}
    
    def fetch_document_detail(self, slug: str) -> Optional[Dict]:
        """Fetch full details for a single document."""
        url = f"{self.api_base}/{slug}"
        params = {"locale": self.locale}
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching document {slug}: {e}")
            return None
    
    def process_document_for_chatbot(self, doc: Dict) -> Dict:
        """
        Process a document into a format suitable for chatbot RAG system.
        
        Args:
            doc: Raw document from API
        
        Returns:
            Processed document with metadata and clean text
        """
        # Extract clean text from HTML
        html_extractor = HTMLTextExtractor()
        html_content = doc.get('html', '')
        html_extractor.feed(html_content)
        clean_text = html_extractor.get_text()
        
        # Create document ID for consistent referencing
        doc_id = hashlib.md5(f"{doc.get('slug', '')}_{self.locale}".encode()).hexdigest()[:12]
        
        # Build the canonical URL for this article
        article_url = f"{self.base_url}/{self.locale}/kb/{doc.get('slug', '')}"
        
        # Structure the document for chatbot use
        processed_doc = {
            "id": doc_id,
            "slug": doc.get('slug', ''),
            "title": doc.get('title', ''),
            "url": article_url,
            "locale": self.locale,
            "products": doc.get('products', []),
            "topics": doc.get('topics', []),
            "summary": doc.get('summary', ''),
            "clean_text": clean_text,
            "html_content": html_content,
            "metadata": {
                "char_count": len(clean_text),
                "word_count": len(clean_text.split()),
                "has_images": '<img' in html_content,
                "has_videos": any(x in html_content for x in ['<video', 'youtube.com', 'vimeo.com']),
                "download_timestamp": datetime.utcnow().isoformat(),
                "api_url": doc.get('url', '')
            },
            "citation": {
                "title": doc.get('title', ''),
                "url": article_url,
                "source": "Mozilla Support (SUMO)",
                "locale": self.locale,
                "products": ", ".join(doc.get('products', [])),
                "topics": ", ".join(doc.get('topics', []))
            }
        }
        
        return processed_doc
    
    def chunk_document(self, processed_doc: Dict, chunk_size: int = 500, 
                      chunk_overlap: int = 100) -> List[Dict]:
        """
        Split document into chunks for vector embedding while maintaining citation info.
        
        Args:
            processed_doc: Processed document
            chunk_size: Target size for chunks in words
            chunk_overlap: Number of words to overlap between chunks
        
        Returns:
            List of document chunks with citation metadata
        """
        text = processed_doc['clean_text']
        words = text.split()
        chunks = []
        
        if len(words) <= chunk_size:
            # Document is small enough to be a single chunk
            chunk = {
                "chunk_id": f"{processed_doc['id']}_chunk_0",
                "doc_id": processed_doc['id'],
                "chunk_index": 0,
                "text": text,
                "citation": processed_doc['citation'],
                "metadata": {
                    "chunk_words": len(words),
                    "total_chunks": 1,
                    "slug": processed_doc['slug'],
                    "title": processed_doc['title']
                }
            }
            chunks.append(chunk)
        else:
            # Split into overlapping chunks
            chunk_start = 0
            chunk_index = 0
            
            while chunk_start < len(words):
                chunk_end = min(chunk_start + chunk_size, len(words))
                chunk_words = words[chunk_start:chunk_end]
                chunk_text = ' '.join(chunk_words)
                
                # Add context prefix for better retrieval
                context_prefix = ""
                if chunk_index > 0:
                    context_prefix = f"[Continued from {processed_doc['title']}] "
                
                chunk = {
                    "chunk_id": f"{processed_doc['id']}_chunk_{chunk_index}",
                    "doc_id": processed_doc['id'],
                    "chunk_index": chunk_index,
                    "text": context_prefix + chunk_text,
                    "citation": processed_doc['citation'],
                    "metadata": {
                        "chunk_words": len(chunk_words),
                        "total_chunks": -1,  # Will update after all chunks created
                        "slug": processed_doc['slug'],
                        "title": processed_doc['title'],
                        "position": "beginning" if chunk_index == 0 else "middle"
                    }
                }
                chunks.append(chunk)
                
                chunk_start = chunk_start + chunk_size - chunk_overlap
                chunk_index += 1
            
            # Update total chunks and mark last chunk
            for chunk in chunks:
                chunk['metadata']['total_chunks'] = len(chunks)
            chunks[-1]['metadata']['position'] = 'end'
        
        return chunks
    
    def download_all_documents(self, product: Optional[str] = None, 
                             max_documents: Optional[int] = None):
        """
        Download all documents from SUMO.
        
        Args:
            product: Optional product filter (e.g., 'firefox')
            max_documents: Maximum number of documents to download (for testing)
        """
        print(f"\n{'='*60}")
        print(f"Starting SUMO Knowledge Base Download")
        print(f"Locale: {self.locale}")
        if product:
            print(f"Product filter: {product}")
        print(f"Output directory: {self.output_dir}")
        print(f"{'='*60}\n")
        
        # Collect all document slugs
        all_slugs = []
        downloaded_set = set(self.progress.get('downloaded_slugs', []))
        page = max(1, self.progress.get('last_page', 0))
        
        print("Phase 1: Collecting document list...")
        print("-" * 40)
        
        while True:
            if max_documents and len(all_slugs) >= max_documents:
                break
                
            print(f"Fetching page {page}...", end=" ")
            data = self.fetch_document_list(page, product)
            
            if not data or not data.get('results'):
                print("No more results")
                break
            
            results = data.get('results', [])
            for doc in results:
                if doc['slug'] not in downloaded_set:
                    all_slugs.append(doc['slug'])
            
            print(f"Found {len(results)} documents (Total unique: {len(all_slugs)})")
            
            if not data.get('next'):
                break
            
            page += 1
            self.progress['last_page'] = page
            sleep(0.3)  # Be nice to the API
        
        # Download full content for each document
        print(f"\nPhase 2: Downloading {len(all_slugs)} documents...")
        print("-" * 40)
        
        all_chunks = []
        master_index = []
        
        for i, slug in enumerate(all_slugs):
            if max_documents and i >= max_documents:
                break
            
            print(f"[{i+1}/{min(len(all_slugs), max_documents or len(all_slugs))}] Downloading: {slug}...", end=" ")
            
            # Fetch document details
            doc = self.fetch_document_detail(slug)
            if not doc:
                print("FAILED")
                self.progress['failed_slugs'].append(slug)
                continue
            
            # Save raw HTML
            raw_file = self.output_dir / "raw_html" / f"{slug}.json"
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            
            # Process for chatbot
            processed_doc = self.process_document_for_chatbot(doc)
            
            # Save processed document
            processed_file = self.output_dir / "processed" / f"{slug}.json"
            with open(processed_file, 'w', encoding='utf-8') as f:
                json.dump(processed_doc, f, ensure_ascii=False, indent=2)
            
            # Create chunks for vector storage
            chunks = self.chunk_document(processed_doc)
            all_chunks.extend(chunks)
            
            # Save chunks
            chunks_file = self.output_dir / "chunks" / f"{slug}_chunks.json"
            with open(chunks_file, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)
            
            # Add to master index
            master_index.append({
                "slug": slug,
                "title": processed_doc['title'],
                "url": processed_doc['citation']['url'],
                "products": processed_doc['products'],
                "topics": processed_doc['topics'],
                "summary": processed_doc['summary'],
                "chunk_count": len(chunks),
                "word_count": processed_doc['metadata']['word_count']
            })
            
            print(f"OK ({len(chunks)} chunks)")
            
            # Update progress
            self.progress['downloaded_slugs'].append(slug)
            self.progress['total_documents'] = len(self.progress['downloaded_slugs'])
            
            # Save progress periodically
            if (i + 1) % 10 == 0:
                self.save_progress()
            
            sleep(0.5)  # Rate limiting
        
        # Save master index
        print("\nPhase 3: Creating master index...")
        print("-" * 40)
        
        master_index_file = self.output_dir / "master_index.json"
        with open(master_index_file, 'w', encoding='utf-8') as f:
            json.dump({
                "locale": self.locale,
                "total_documents": len(master_index),
                "total_chunks": len(all_chunks),
                "download_date": datetime.utcnow().isoformat(),
                "documents": master_index
            }, f, ensure_ascii=False, indent=2)
        
        # Save all chunks in a single file for easy loading
        all_chunks_file = self.output_dir / "all_chunks.json"
        with open(all_chunks_file, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        
        # Create a simple CSV for quick reference
        import csv
        csv_file = self.output_dir / "document_citations.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['title', 'url', 'products', 'topics', 'summary'])
            writer.writeheader()
            for doc in master_index:
                writer.writerow({
                    'title': doc['title'],
                    'url': doc['url'],
                    'products': ', '.join(doc['products']),
                    'topics': ', '.join(doc['topics']),
                    'summary': doc['summary']
                })
        
        # Save final progress
        self.save_progress()
        
        # Print summary
        print(f"\n{'='*60}")
        print("Download Complete!")
        print(f"{'='*60}")
        print(f"Documents downloaded: {len(self.progress['downloaded_slugs'])}")
        print(f"Failed downloads: {len(self.progress.get('failed_slugs', []))}")
        print(f"Total chunks created: {len(all_chunks)}")
        print(f"\nOutput files:")
        print(f"  - Raw HTML: {self.output_dir}/raw_html/")
        print(f"  - Processed docs: {self.output_dir}/processed/")
        print(f"  - Document chunks: {self.output_dir}/chunks/")
        print(f"  - Master index: {master_index_file}")
        print(f"  - All chunks: {all_chunks_file}")
        print(f"  - Citations CSV: {csv_file}")
        print(f"\nReady for use in RAG chatbot system!")
    
    def create_sample_chatbot_response(self, chunk_id: str) -> str:
        """
        Generate a sample chatbot response with proper citation.
        
        Args:
            chunk_id: ID of the chunk used to answer
        
        Returns:
            Sample response with citation
        """
        # Load the chunk
        all_chunks_file = self.output_dir / "all_chunks.json"
        if not all_chunks_file.exists():
            return "Chunks file not found"
        
        with open(all_chunks_file, 'r') as f:
            all_chunks = json.load(f)
        
        chunk = next((c for c in all_chunks if c['chunk_id'] == chunk_id), None)
        if not chunk:
            return "Chunk not found"
        
        citation = chunk['citation']
        response = f"""Based on Mozilla Support documentation:

{chunk['text'][:200]}...

**Source:** [{citation['title']}]({citation['url']})
**Products:** {citation['products']}
**Topics:** {citation['topics']}

For more details, please visit the full article at:
{citation['url']}
"""
        return response


def main():
    """Main function to run the downloader."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download SUMO KB for chatbot use')
    parser.add_argument('--locale', default='en-US', help='Locale to download (default: en-US)')
    parser.add_argument('--product', help='Filter by product (e.g., firefox)')
    parser.add_argument('--max-docs', type=int, help='Maximum documents to download (for testing)')
    parser.add_argument('--output-dir', default='sumo_knowledge_base', help='Output directory')
    parser.add_argument('--resume', action='store_true', help='Resume previous download')
    
    args = parser.parse_args()
    
    # Initialize downloader
    downloader = SUMOKnowledgeBaseDownloader(
        output_dir=args.output_dir,
        locale=args.locale
    )
    
    # Clear progress if not resuming
    if not args.resume:
        downloader.progress = {
            "downloaded_slugs": [],
            "failed_slugs": [],
            "last_page": 0,
            "total_documents": 0
        }
    
    # Start download
    downloader.download_all_documents(
        product=args.product,
        max_documents=args.max_docs
    )
    
    # Show sample citation
    print("\n" + "="*60)
    print("Sample Chatbot Response with Citation:")
    print("="*60)
    
    # Get a sample chunk ID
    all_chunks_file = Path(args.output_dir) / "all_chunks.json"
    if all_chunks_file.exists():
        with open(all_chunks_file, 'r') as f:
            chunks = json.load(f)
            if chunks:
                sample_response = downloader.create_sample_chatbot_response(chunks[0]['chunk_id'])
                print(sample_response)


if __name__ == "__main__":
    main()