#!/usr/bin/env python3
"""
Test different HTML extraction methods to compare quality.
"""

import json
import re
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from html.parser import HTMLParser

# Sample HTML from SUMO
sample_html = """
<p>This article explains how to <strong>fix problems</strong> with images on websites.</p>
<h2>Clear cookies and cache</h2>
<p>Sometimes problems loading websites can be fixed by clearing the cookies and cache.</p>
<ol>
<li>Click the menu button <img src="menu.png" alt="menu"> to open the menu panel.</li>
<li>Click <strong>History</strong> and select <em>Clear recent history...</em></li>
<li>In the <code>Time range to clear:</code> drop-down, select <strong>Everything</strong>.</li>
</ol>
<div class="warning">
<p><strong>Warning:</strong> These instructions are for experienced users only!</p>
</div>
<pre><code>about:config</code></pre>
<p>For more info, see <a href="/kb/other-article">this article</a>.</p>
"""

class SimpleHTMLParser(HTMLParser):
    """Current simple parser."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'meta', 'link'}
        self.in_skip = False
    
    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.in_skip = True
        elif tag in {'p', 'h1', 'h2', 'h3', 'li', 'br', 'div'}:
            self.text_parts.append('\n')
    
    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.in_skip = False
    
    def handle_data(self, data):
        if not self.in_skip and data.strip():
            self.text_parts.append(data.strip())
    
    def get_text(self):
        text = ' '.join(self.text_parts)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        return text.strip()

def extract_with_beautifulsoup(html):
    """Extract text using BeautifulSoup."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove script and style elements
    for script in soup(['script', 'style']):
        script.decompose()
    
    # Get text with better formatting
    text = soup.get_text(separator=' ', strip=True)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    return text

def extract_with_beautifulsoup_structured(html):
    """Extract with BeautifulSoup preserving structure."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove unwanted elements
    for element in soup(['script', 'style', 'meta', 'link']):
        element.decompose()
    
    # Process different elements
    output = []
    
    for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'pre', 'code', 'div']):
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            # Headers get extra spacing
            output.append(f"\n\n{element.get_text(strip=True)}\n")
        elif element.name == 'li':
            # List items with bullets
            output.append(f"• {element.get_text(strip=True)}\n")
        elif element.name in ['pre', 'code']:
            # Code blocks preserved
            output.append(f"\n`{element.get_text(strip=True)}`\n")
        else:
            # Regular paragraphs
            text = element.get_text(strip=True)
            if text:
                output.append(f"{text}\n")
    
    return '\n'.join(output)

def extract_as_markdown(html):
    """Convert HTML to Markdown for better structure preservation."""
    # Configure markdown conversion
    text = md(html, 
              heading_style="ATX",
              bullets="•",
              code_language="",
              strip=['img'])  # Remove images
    
    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def compare_methods(html):
    """Compare different extraction methods."""
    print("="*60)
    print("HTML EXTRACTION COMPARISON")
    print("="*60)
    
    # Simple parser
    print("\n1. SIMPLE HTML PARSER:")
    print("-"*40)
    simple_parser = SimpleHTMLParser()
    simple_parser.feed(html)
    simple_text = simple_parser.get_text()
    print(simple_text)
    
    # BeautifulSoup basic
    print("\n2. BEAUTIFULSOUP (BASIC):")
    print("-"*40)
    bs_text = extract_with_beautifulsoup(html)
    print(bs_text)
    
    # BeautifulSoup structured
    print("\n3. BEAUTIFULSOUP (STRUCTURED):")
    print("-"*40)
    bs_structured = extract_with_beautifulsoup_structured(html)
    print(bs_structured)
    
    # Markdown conversion
    print("\n4. MARKDOWN CONVERSION:")
    print("-"*40)
    md_text = extract_as_markdown(html)
    print(md_text)
    
    # Compare lengths
    print("\n" + "="*60)
    print("COMPARISON METRICS:")
    print("-"*40)
    print(f"Simple Parser: {len(simple_text)} chars")
    print(f"BeautifulSoup Basic: {len(bs_text)} chars")
    print(f"BeautifulSoup Structured: {len(bs_structured)} chars")
    print(f"Markdown: {len(md_text)} chars")
    
    # Best for vector search
    print("\n" + "="*60)
    print("RECOMMENDATION FOR VECTOR SEARCH:")
    print("-"*40)
    print("Markdown conversion preserves the most structure while")
    print("remaining readable. This helps with:")
    print("• Better semantic chunking by the vector DB")
    print("• Preserved lists, headers, and code blocks")
    print("• Clean text without losing context")
    print("\nNo LLM needed - just better parsing!")

if __name__ == "__main__":
    compare_methods(sample_html)