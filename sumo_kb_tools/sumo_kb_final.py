#!/usr/bin/env python3
"""
Final SUMO Knowledge Base Downloader
Simple and clear: Downloads raw HTML + basic text extraction.
You can process the HTML however you want later.
"""

import requests
import json
import re
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Dict, Optional
from html.parser import HTMLParser

class BasicTextExtractor(HTMLParser):
    """Simple HTML to text conversion."""
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


class SUMODownloader:
    """Downloads SUMO docs with raw HTML and basic text extraction."""
    
    def __init__(self, output_dir: str = "sumo_kb", locale: str = "en-US"):
        self.base_url = "https://support.mozilla.org"
        self.api_base = f"{self.base_url}/api/1/kb"
        self.output_dir = Path(output_dir)
        self.locale = locale
        self.output_dir.mkdir(exist_ok=True)
    
    def fetch_document(self, slug: str) -> Optional[Dict]:
        """Fetch document from API."""
        url = f"{self.api_base}/{slug}"
        params = {"locale": self.locale}
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def process_document(self, doc: Dict) -> Dict:
        """Process document - keep it simple."""
        html = doc.get('html', '')
        
        # Basic text extraction
        extractor = BasicTextExtractor()
        extractor.feed(html)
        text = extractor.get_text()
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Build URL for citations
        article_url = f"{self.base_url}/{self.locale}/kb/{doc.get('slug', '')}"
        
        return {
            # Core fields
            "slug": doc.get('slug', ''),
            "title": doc.get('title', ''),
            "summary": doc.get('summary', ''),
            "url": article_url,
            
            # Content - ONLY TWO VERSIONS
            "html": html,  # Raw HTML for any processing you want
            "text": text,  # Basic extracted text
            
            # Metadata for filtering/search
            "products": doc.get('products', []),
            "topics": doc.get('topics', []),
            "locale": self.locale,
            
            # Stats
            "metadata": {
                "html_bytes": len(html),
                "text_bytes": len(text),
                "word_count": len(text.split()),
                "downloaded_at": datetime.now().isoformat()
            }
        }
    
    def download_documents(self, slugs: list) -> list:
        """Download a list of documents."""
        print(f"Downloading {len(slugs)} documents...")
        print("="*60)
        
        documents = []
        for i, slug in enumerate(slugs, 1):
            print(f"[{i}/{len(slugs)}] {slug}...", end=" ")
            
            doc = self.fetch_document(slug)
            if doc:
                processed = self.process_document(doc)
                documents.append(processed)
                
                # Save individual file
                out_file = self.output_dir / f"{slug}.json"
                with open(out_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, ensure_ascii=False, indent=2)
                
                print(f"OK ({processed['metadata']['html_bytes']:,} bytes HTML)")
            else:
                print("FAILED")
            
            sleep(0.5)  # Be nice to the API
        
        # Save all documents
        all_file = self.output_dir / "all_documents.json"
        with open(all_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
        
        print("="*60)
        print(f"Downloaded: {len(documents)} documents")
        print(f"Output: {self.output_dir}/")
        
        return documents


def show_what_you_get():
    """Show exactly what data is saved."""
    print("\n" + "="*60)
    print("WHAT THIS DOWNLOADER GIVES YOU:")
    print("="*60)
    print("""
Each document contains:

1. **html** - The raw HTML from SUMO
   - Use this for custom processing
   - Apply any parser you want
   - Send to LLM if needed
   
2. **text** - Basic extracted text
   - Simple, clean text
   - Good enough for most RAG systems
   - Already cleaned of HTML tags

3. **metadata** - For citations
   - title: Article title
   - url: Direct link to article
   - products: Which products it covers
   - topics: Categories

That's it! Simple and flexible.
    """)
    
    print("="*60)
    print("EXAMPLE DOCUMENT STRUCTURE:")
    print("="*60)
    
    example = {
        "slug": "fix-problems-images-not-show",
        "title": "Fix problems that cause images to not show",
        "summary": "How to fix image loading issues...",
        "url": "https://support.mozilla.org/en-US/kb/fix-problems-images-not-show",
        "html": "<p>This article explains...</p>",  # Full HTML
        "text": "This article explains...",  # Extracted text
        "products": ["firefox"],
        "topics": ["browse", "images"],
        "locale": "en-US",
        "metadata": {
            "html_bytes": 8560,
            "text_bytes": 4097,
            "word_count": 665,
            "downloaded_at": "2024-01-01T12:00:00"
        }
    }
    
    print(json.dumps(example, indent=2)[:500] + "...")


def main():
    """Demo the downloader."""
    
    # Show what you get
    show_what_you_get()
    
    # Download a few test documents
    print("\n" + "="*60)
    print("TEST DOWNLOAD:")
    print("="*60)
    
    downloader = SUMODownloader()
    
    test_slugs = [
        "fix-problems-images-not-show",
        "how-save-web-page",
        "fix-common-audio-and-video-issues"
    ]
    
    documents = downloader.download_documents(test_slugs)
    
    # Show what was saved
    if documents:
        doc = documents[0]
        print(f"\nFirst document preview:")
        print(f"  Title: {doc['title']}")
        print(f"  URL: {doc['url']}")
        print(f"  HTML: {len(doc['html'])} bytes")
        print(f"  Text: {len(doc['text'])} bytes")
        print(f"  Text preview: {doc['text'][:200]}...")
        
        print("\n✓ You now have raw HTML to process however you want!")
        print("✓ Plus basic text extraction for immediate use!")


if __name__ == "__main__":
    main()