#!/usr/bin/env python3
"""
Improved HTML extractor that preserves structure better without needing an LLM.
No external dependencies required.
"""

import re
from html.parser import HTMLParser
from html import unescape

class ImprovedHTMLExtractor(HTMLParser):
    """
    Enhanced HTML to text extractor that preserves document structure.
    Better for vector search and RAG applications.
    """
    
    def __init__(self):
        super().__init__()
        self.output = []
        self.current_text = []
        self.skip_tags = {'script', 'style', 'meta', 'link', 'noscript'}
        self.in_skip = False
        self.in_code = False
        self.in_pre = False
        self.list_depth = 0
        self.in_heading = False
        self.last_tag = None
    
    def handle_starttag(self, tag, attrs):
        self.last_tag = tag
        
        # Skip unwanted content
        if tag in self.skip_tags:
            self.in_skip = True
            return
        
        if self.in_skip:
            return
        
        # Handle different tags
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self._flush_text()
            self.in_heading = True
            level = int(tag[1])
            self.output.append('\n\n' + '#' * level + ' ')
            
        elif tag == 'p':
            self._flush_text()
            if self.output and not self.output[-1].endswith('\n\n'):
                self.output.append('\n\n')
                
        elif tag == 'br':
            self.output.append('\n')
            
        elif tag in ['ul', 'ol']:
            self._flush_text()
            self.list_depth += 1
            if self.output and not self.output[-1].endswith('\n'):
                self.output.append('\n')
                
        elif tag == 'li':
            self._flush_text()
            indent = '  ' * (self.list_depth - 1)
            self.output.append(f"\n{indent}• ")
            
        elif tag in ['code', 'tt']:
            self._flush_text()
            self.in_code = True
            self.output.append('`')
            
        elif tag == 'pre':
            self._flush_text()
            self.in_pre = True
            self.output.append('\n```\n')
            
        elif tag == 'blockquote':
            self._flush_text()
            self.output.append('\n> ')
            
        elif tag in ['strong', 'b']:
            self._flush_text()
            self.output.append('**')
            
        elif tag in ['em', 'i']:
            self._flush_text()
            self.output.append('*')
            
        elif tag == 'hr':
            self._flush_text()
            self.output.append('\n---\n')
            
        elif tag == 'a':
            self._flush_text()
            # Extract href for context
            href = None
            for attr_name, attr_value in attrs:
                if attr_name == 'href':
                    href = attr_value
                    break
            if href and not href.startswith('#'):
                self.output.append('[')
            
        elif tag == 'img':
            # Extract alt text
            alt = None
            for attr_name, attr_value in attrs:
                if attr_name == 'alt':
                    alt = attr_value
                    break
            if alt:
                self.output.append(f'[{alt}]')
                
        elif tag == 'table':
            self._flush_text()
            self.output.append('\n[Table]\n')
            
        elif tag == 'div':
            # Check for special div classes that might indicate warnings/notes
            classes = []
            for attr_name, attr_value in attrs:
                if attr_name == 'class':
                    classes = attr_value.split()
                    break
            
            if any(cls in ['warning', 'note', 'tip', 'caution'] for cls in classes):
                self._flush_text()
                self.output.append('\n**Note:** ')
    
    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.in_skip = False
            return
            
        if self.in_skip:
            return
        
        self._flush_text()
        
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.in_heading = False
            self.output.append('\n')
            
        elif tag in ['ul', 'ol']:
            self.list_depth = max(0, self.list_depth - 1)
            if self.list_depth == 0:
                self.output.append('\n')
                
        elif tag in ['code', 'tt']:
            self.in_code = False
            self.output.append('`')
            
        elif tag == 'pre':
            self.in_pre = False
            self.output.append('\n```\n')
            
        elif tag in ['strong', 'b']:
            self.output.append('**')
            
        elif tag in ['em', 'i']:
            self.output.append('*')
            
        elif tag == 'a':
            if self.last_tag == 'a':
                self.output.append(']')
    
    def handle_data(self, data):
        if self.in_skip:
            return
        
        if self.in_pre:
            # Preserve formatting in pre blocks
            self.output.append(data)
        else:
            # Clean up whitespace for normal text
            text = data.strip()
            if text:
                if self.in_code:
                    self.current_text.append(text)
                else:
                    self.current_text.append(text)
    
    def _flush_text(self):
        """Flush accumulated text to output."""
        if self.current_text:
            text = ' '.join(self.current_text)
            if text:
                self.output.append(text)
            self.current_text = []
    
    def get_text(self):
        """Get the final extracted text."""
        self._flush_text()
        
        # Join output
        text = ''.join(self.output)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n{4,}', '\n\n\n', text)  # Max 3 newlines
        text = re.sub(r' {2,}', ' ', text)  # Remove multiple spaces
        text = re.sub(r'\n +', '\n', text)  # Remove leading spaces on lines
        
        # Unescape HTML entities
        text = unescape(text)
        
        return text.strip()


def compare_extractors():
    """Compare simple vs improved extraction."""
    
    # Real SUMO HTML sample
    sample_html = """
    <h1>Fix problems with Firefox</h1>
    <p>This article describes <strong>common problems</strong> and their solutions.</p>
    
    <h2>Clear cookies and cache</h2>
    <p>Sometimes problems can be fixed by clearing cookies:</p>
    <ol>
        <li>Click the menu button</li>
        <li>Select <em>Clear recent history</em></li>
        <li>Choose <code>Everything</code> from the dropdown</li>
    </ol>
    
    <div class="warning">
        <p><strong>Warning:</strong> This will log you out of websites!</p>
    </div>
    
    <h2>Check extensions</h2>
    <p>Extensions can cause issues. Try <a href="/kb/safe-mode">Safe Mode</a>.</p>
    
    <pre><code>about:config
browser.cache.disk.enable = true</code></pre>
    
    <p>For more information, see the related articles below.</p>
    """
    
    print("="*60)
    print("HTML EXTRACTION COMPARISON")
    print("="*60)
    
    # Simple extraction (current method)
    print("\n1. SIMPLE EXTRACTION (Current):")
    print("-"*40)
    
    class SimpleExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text_parts = []
            self.skip_tags = {'script', 'style'}
            self.in_skip = False
        
        def handle_starttag(self, tag, attrs):
            if tag in self.skip_tags:
                self.in_skip = True
        
        def handle_endtag(self, tag):
            if tag in self.skip_tags:
                self.in_skip = False
        
        def handle_data(self, data):
            if not self.in_skip and data.strip():
                self.text_parts.append(data.strip())
        
        def get_text(self):
            text = ' '.join(self.text_parts)
            return re.sub(r'\s+', ' ', text)
    
    simple = SimpleExtractor()
    simple.feed(sample_html)
    simple_text = simple.get_text()
    print(simple_text[:500])
    
    # Improved extraction
    print("\n\n2. IMPROVED EXTRACTION (Proposed):")
    print("-"*40)
    
    improved = ImprovedHTMLExtractor()
    improved.feed(sample_html)
    improved_text = improved.get_text()
    print(improved_text)
    
    # Comparison
    print("\n" + "="*60)
    print("WHY THE IMPROVED VERSION IS BETTER:")
    print("-"*40)
    print("✓ Preserves document structure (headers, lists, code)")
    print("✓ Maintains semantic relationships")
    print("✓ Better for vector search (chunks align with sections)")
    print("✓ No external dependencies needed")
    print("✓ No LLM API costs")
    print("✓ Deterministic and fast")
    print(f"\nCharacter counts:")
    print(f"  Simple: {len(simple_text)} chars (loses structure)")
    print(f"  Improved: {len(improved_text)} chars (preserves structure)")


if __name__ == "__main__":
    compare_extractors()
    
    print("\n" + "="*60)
    print("RECOMMENDATION:")
    print("-"*40)
    print("Use the ImprovedHTMLExtractor class instead of an LLM.")
    print("It's free, fast, and preserves structure for better RAG performance.")
    print("No need for expensive LLM API calls!")