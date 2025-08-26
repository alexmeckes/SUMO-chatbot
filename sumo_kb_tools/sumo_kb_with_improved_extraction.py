#!/usr/bin/env python3
"""
SUMO Downloader with Improved HTML Extraction
Downloads and processes SUMO docs with better text extraction.
"""

import requests
import json
from pathlib import Path
from time import sleep
from improved_html_extractor import ImprovedHTMLExtractor

class SUMODownloaderImproved:
    """Download SUMO docs with improved extraction."""
    
    def __init__(self, output_dir="sumo_kb_improved", locale="en-US"):
        self.base_url = "https://support.mozilla.org"
        self.api_base = f"{self.base_url}/api/1/kb"
        self.output_dir = Path(output_dir)
        self.locale = locale
        self.output_dir.mkdir(exist_ok=True)
    
    def fetch_document(self, slug):
        """Fetch a document with HTML content."""
        url = f"{self.api_base}/{slug}"
        params = {"locale": self.locale}
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def process_document(self, doc):
        """Process with improved extraction."""
        # Use improved extractor on HTML
        html = doc.get('html', '')
        extractor = ImprovedHTMLExtractor()
        extractor.feed(html)
        clean_text = extractor.get_text()
        
        # Build processed document
        article_url = f"{self.base_url}/{self.locale}/kb/{doc.get('slug', '')}"
        
        return {
            # Better extracted content
            "content": clean_text,
            "title": doc.get('title', ''),
            "summary": doc.get('summary', ''),
            
            # Citation info
            "url": article_url,
            "slug": doc.get('slug', ''),
            "source": "Mozilla Support (SUMO)",
            
            # Metadata
            "products": doc.get('products', []),
            "topics": doc.get('topics', []),
            "locale": self.locale,
            
            "metadata": {
                "extraction_method": "ImprovedHTMLExtractor",
                "char_count": len(clean_text),
                "word_count": len(clean_text.split()),
                "has_structure": '##' in clean_text or '•' in clean_text
            }
        }
    
    def download_sample(self, slugs):
        """Download sample documents to test."""
        print("Downloading with IMPROVED extraction...")
        print("="*60)
        
        docs = []
        for slug in slugs:
            print(f"Fetching {slug}...", end=" ")
            doc = self.fetch_document(slug)
            if doc:
                processed = self.process_document(doc)
                docs.append(processed)
                
                # Save individual file
                out_file = self.output_dir / f"{slug}.json"
                with open(out_file, 'w', encoding='utf-8') as f:
                    json.dump(processed, f, ensure_ascii=False, indent=2)
                
                print(f"OK ({len(processed['content'])} chars)")
            else:
                print("FAILED")
            
            sleep(0.5)
        
        # Save all docs
        all_file = self.output_dir / "all_documents.json"
        with open(all_file, 'w', encoding='utf-8') as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*60)
        print(f"Saved to: {self.output_dir}/")
        print("With improved structure for better RAG performance!")
        
        return docs


def compare_extraction_methods():
    """Show the difference in a sample."""
    
    slug = "fix-common-audio-and-video-issues"
    
    # Simple extraction (what we had before)
    simple_dir = Path("sumo_kb")
    simple_file = simple_dir / "all_documents.json"
    
    # Improved extraction
    improved = SUMODownloaderImproved()
    improved.download_sample([slug])
    
    # Load both
    with open(simple_file, 'r') as f:
        simple_docs = json.load(f)
        simple_content = simple_docs[0]['content'][:500]
    
    improved_file = improved.output_dir / f"{slug}.json"
    with open(improved_file, 'r') as f:
        improved_doc = json.load(f)
        improved_content = improved_doc['content'][:500]
    
    print("\n" + "="*60)
    print("EXTRACTION COMPARISON")
    print("="*60)
    
    print("\nSIMPLE (Original):")
    print("-"*40)
    print(simple_content)
    
    print("\n\nIMPROVED (With Structure):")
    print("-"*40)
    print(improved_content)
    
    print("\n" + "="*60)
    print("The improved version is better for:")
    print("• Vector search (sections are clear)")
    print("• Chatbot responses (formatted text)")
    print("• Citations (clean excerpts)")


if __name__ == "__main__":
    # Test with one document
    downloader = SUMODownloaderImproved()
    slugs = ["fix-common-audio-and-video-issues"]
    downloader.download_sample(slugs)
    
    # Compare methods
    compare_extraction_methods()