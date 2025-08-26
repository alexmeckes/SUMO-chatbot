#!/usr/bin/env python3
"""
Complete SUMO Knowledge Base Downloader
Downloads documents with ALL data: raw HTML, clean text, and structured text.
Gives you maximum flexibility for processing later.
"""

import requests
import json
import re
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Dict, List, Optional
from html.parser import HTMLParser
from html import unescape

class BasicHTMLCleaner(HTMLParser):
    """Basic HTML to text conversion."""
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip = False
        self.skip_tags = {'script', 'style', 'meta', 'link'}
    
    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.skip = True
    
    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.skip = False
    
    def handle_data(self, data):
        if not self.skip and data.strip():
            self.text.append(data.strip())
    
    def get_text(self):
        return ' '.join(self.text)


class CompleteSUMODownloader:
    """Download SUMO docs with complete data including raw HTML."""
    
    def __init__(self, output_dir: str = "sumo_kb_complete", locale: str = "en-US"):
        self.base_url = "https://support.mozilla.org"
        self.api_base = f"{self.base_url}/api/1/kb"
        self.output_dir = Path(output_dir)
        self.locale = locale
        
        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "raw").mkdir(exist_ok=True)
        (self.output_dir / "processed").mkdir(exist_ok=True)
        
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
        """Fetch a page of document listings."""
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
        """Fetch full document including HTML."""
        url = f"{self.api_base}/{slug}"
        params = {"locale": self.locale}
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching document {slug}: {e}")
            return None
    
    def clean_text_basic(self, html: str) -> str:
        """Basic HTML to text conversion."""
        cleaner = BasicHTMLCleaner()
        cleaner.feed(html)
        text = cleaner.get_text()
        # Basic cleanup
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def process_document(self, doc: Dict) -> Dict:
        """Process document with multiple extraction methods."""
        html = doc.get('html', '')
        
        # Build the canonical URL
        article_url = f"{self.base_url}/{self.locale}/kb/{doc.get('slug', '')}"
        
        # Basic text extraction
        clean_text = self.clean_text_basic(html)
        
        # Complete document with everything
        complete_doc = {
            # Original API response fields
            "id": doc.get('id'),
            "slug": doc.get('slug', ''),
            "title": doc.get('title', ''),
            "summary": doc.get('summary', ''),
            "locale": doc.get('locale', self.locale),
            
            # Products and topics for filtering
            "products": doc.get('products', []),
            "topics": doc.get('topics', []),
            
            # Content in different formats
            "content": {
                "raw_html": html,  # Complete HTML for custom processing
                "clean_text": clean_text,  # Basic cleaned text
                "api_html": doc.get('html', ''),  # Original from API
            },
            
            # Citation information
            "citation": {
                "title": doc.get('title', ''),
                "url": article_url,
                "api_url": doc.get('url', ''),
                "source": "Mozilla Support (SUMO)",
                "locale": self.locale,
                "products": ", ".join(doc.get('products', [])),
                "topics": ", ".join(doc.get('topics', []))
            },
            
            # Metadata
            "metadata": {
                "html_size": len(html),
                "text_size": len(clean_text),
                "word_count": len(clean_text.split()),
                "has_images": '<img' in html,
                "has_videos": any(x in html for x in ['<video', 'youtube.com', 'vimeo.com']),
                "has_code": '<code' in html or '<pre' in html,
                "downloaded_at": datetime.now().isoformat()
            }
        }
        
        return complete_doc
    
    def download_all(self, product: Optional[str] = None, max_docs: Optional[int] = None):
        """Download all documents with complete data."""
        print(f"\n{'='*60}")
        print(f"Complete SUMO Knowledge Base Downloader")
        print(f"{'='*60}")
        print(f"Locale: {self.locale}")
        if product:
            print(f"Product: {product}")
        print(f"Output: {self.output_dir}/")
        print(f"Saving: Raw HTML + Clean Text + Metadata")
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
        
        print(f"\nPhase 2: Downloading {len(all_slugs)} documents with HTML...")
        
        documents = []
        for i, slug in enumerate(all_slugs):
            if max_docs and i >= max_docs:
                break
            
            print(f"  [{i+1}/{min(len(all_slugs), max_docs or len(all_slugs))}] {slug[:40]}...", end=" ")
            
            # Fetch complete document
            doc = self.fetch_document(slug)
            if not doc:
                print("FAILED")
                self.progress['failed'].append(slug)
                continue
            
            # Process document
            complete_doc = self.process_document(doc)
            documents.append(complete_doc)
            
            # Save raw API response
            raw_file = self.output_dir / "raw" / f"{slug}.json"
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
            
            # Save processed version
            processed_file = self.output_dir / "processed" / f"{slug}.json"
            with open(processed_file, 'w', encoding='utf-8') as f:
                json.dump(complete_doc, f, ensure_ascii=False, indent=2)
            
            html_size = complete_doc['metadata']['html_size']
            text_size = complete_doc['metadata']['text_size']
            print(f"OK (HTML: {html_size:,} bytes, Text: {text_size:,} bytes)")
            
            # Update progress
            self.progress['downloaded'].append(slug)
            if (i + 1) % 10 == 0:
                self.save_progress()
            
            sleep(0.5)
        
        # Save complete dataset
        complete_file = self.output_dir / "complete_dataset.json"
        with open(complete_file, 'w', encoding='utf-8') as f:
            json.dump({
                "locale": self.locale,
                "total_documents": len(documents),
                "download_date": datetime.now().isoformat(),
                "documents": documents
            }, f, ensure_ascii=False, indent=2)
        
        # Save lightweight version (without HTML)
        lightweight_docs = []
        for doc in documents:
            light_doc = doc.copy()
            light_doc['content'] = {
                "text": doc['content']['clean_text'],
                "html_available": True
            }
            lightweight_docs.append(light_doc)
        
        lightweight_file = self.output_dir / "lightweight_dataset.json"
        with open(lightweight_file, 'w', encoding='utf-8') as f:
            json.dump(lightweight_docs, f, ensure_ascii=False, indent=2)
        
        # Create index CSV
        import csv
        csv_file = self.output_dir / "index.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['slug', 'title', 'url', 'products', 'topics', 'html_size', 'text_size', 'word_count'])
            for doc in documents:
                writer.writerow([
                    doc['slug'],
                    doc['title'],
                    doc['citation']['url'],
                    ', '.join(doc['products']),
                    ', '.join(doc['topics']),
                    doc['metadata']['html_size'],
                    doc['metadata']['text_size'],
                    doc['metadata']['word_count']
                ])
        
        # Save progress
        self.save_progress()
        
        # Summary
        print(f"\n{'='*60}")
        print("Download Complete!")
        print(f"{'='*60}")
        print(f"Documents: {len(documents)}")
        print(f"Failed: {len(self.progress.get('failed', []))}")
        
        total_html = sum(d['metadata']['html_size'] for d in documents)
        total_text = sum(d['metadata']['text_size'] for d in documents)
        
        print(f"\nData sizes:")
        print(f"  Total HTML: {total_html / 1024 / 1024:.1f} MB")
        print(f"  Total Text: {total_text / 1024:.1f} KB")
        
        print(f"\nOutput files:")
        print(f"  - Raw API responses: {self.output_dir}/raw/*.json")
        print(f"  - Processed docs: {self.output_dir}/processed/*.json")
        print(f"  - Complete dataset: {complete_file} (includes HTML)")
        print(f"  - Lightweight dataset: {lightweight_file} (no HTML)")
        print(f"  - Index CSV: {csv_file}")
        
        print(f"\nYou now have:")
        print("  ✓ Raw HTML for custom processing")
        print("  ✓ Clean text for immediate use")
        print("  ✓ All metadata for citations")
        print("  ✓ Flexibility to process HTML any way you want!")
        
        return documents


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Complete SUMO KB downloader with raw HTML')
    parser.add_argument('--locale', default='en-US', help='Locale (default: en-US)')
    parser.add_argument('--product', help='Filter by product (e.g., firefox)')
    parser.add_argument('--max-docs', type=int, help='Max documents (for testing)')
    parser.add_argument('--output-dir', default='sumo_kb_complete', help='Output directory')
    
    args = parser.parse_args()
    
    downloader = CompleteSUMODownloader(
        output_dir=args.output_dir,
        locale=args.locale
    )
    
    documents = downloader.download_all(
        product=args.product,
        max_docs=args.max_docs
    )
    
    if documents:
        print(f"\nSample document structure:")
        print(f"  - slug: {documents[0]['slug']}")
        print(f"  - title: {documents[0]['title']}")
        print(f"  - content.raw_html: {len(documents[0]['content']['raw_html'])} bytes")
        print(f"  - content.clean_text: {len(documents[0]['content']['clean_text'])} bytes")
        print(f"  - citation.url: {documents[0]['citation']['url']}")


if __name__ == "__main__":
    main()