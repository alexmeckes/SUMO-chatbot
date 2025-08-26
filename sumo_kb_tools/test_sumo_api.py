#!/usr/bin/env python3
"""
Script to test SUMO API and count available documentation.
This script queries the Mozilla Support (SUMO) API to count and analyze
the available documentation articles.
"""

import requests
import json
from time import sleep
from typing import Dict, List, Optional

def fetch_documents_page(page: int = 1, locale: str = "en-US", product: Optional[str] = None) -> Dict:
    """
    Fetch a single page of documents from the SUMO API.
    
    Args:
        page: Page number to fetch
        locale: Locale/language code
        product: Optional product filter (e.g., "firefox", "thunderbird")
    
    Returns:
        API response as dictionary
    """
    base_url = "https://support.mozilla.org/api/1/kb/"
    params = {
        "page": page,
        "locale": locale
    }
    
    if product:
        params["product"] = product
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {page}: {e}")
        return {}

def count_all_documents(locale: str = "en-US", product: Optional[str] = None) -> Dict:
    """
    Count all documents available in the SUMO API.
    
    Args:
        locale: Locale/language code
        product: Optional product filter
    
    Returns:
        Dictionary with statistics about the documents
    """
    stats = {
        "total_documents": 0,
        "pages_fetched": 0,
        "products": set(),
        "sample_titles": [],
        "locale": locale,
        "filtered_by_product": product
    }
    
    page = 1
    has_more = True
    
    print(f"\nCounting documents for locale: {locale}")
    if product:
        print(f"Filtering by product: {product}")
    print("-" * 50)
    
    while has_more:
        print(f"Fetching page {page}...", end=" ")
        data = fetch_documents_page(page, locale, product)
        
        if not data:
            print("Failed to fetch data")
            break
        
        results = data.get("results", [])
        
        if not results:
            print("No more results")
            has_more = False
            break
        
        # Count documents on this page
        page_count = len(results)
        stats["total_documents"] += page_count
        stats["pages_fetched"] = page
        
        # Collect sample titles from first page
        if page == 1 and results:
            stats["sample_titles"] = [doc.get("title", "No title") for doc in results[:5]]
        
        print(f"Found {page_count} documents")
        
        # Check if there's a next page
        if data.get("next"):
            page += 1
            # Small delay to be respectful to the API
            sleep(0.5)
        else:
            has_more = False
    
    return stats

def test_single_document(slug: str, locale: str = "en-US") -> Dict:
    """
    Test fetching a single document's details.
    
    Args:
        slug: Document slug/identifier
        locale: Locale/language code
    
    Returns:
        Document details
    """
    url = f"https://support.mozilla.org/api/1/kb/{slug}"
    params = {"locale": locale}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching document {slug}: {e}")
        return {}

def main():
    """Main function to run API tests."""
    print("=" * 60)
    print("SUMO API Documentation Counter")
    print("=" * 60)
    
    # Test 1: Count all English documents
    en_stats = count_all_documents(locale="en-US")
    
    print("\n" + "=" * 60)
    print("RESULTS - English (en-US) Documentation")
    print("=" * 60)
    print(f"Total documents: {en_stats['total_documents']}")
    print(f"Pages fetched: {en_stats['pages_fetched']}")
    print(f"Documents per page: ~{en_stats['total_documents'] // max(1, en_stats['pages_fetched'])}")
    
    if en_stats["sample_titles"]:
        print("\nSample document titles:")
        for i, title in enumerate(en_stats["sample_titles"], 1):
            print(f"  {i}. {title}")
    
    # Test 2: Count Firefox-specific documents
    print("\n" + "-" * 60)
    firefox_stats = count_all_documents(locale="en-US", product="firefox")
    
    print("\n" + "=" * 60)
    print("RESULTS - Firefox-specific Documentation (en-US)")
    print("=" * 60)
    print(f"Total Firefox documents: {firefox_stats['total_documents']}")
    print(f"Pages fetched: {firefox_stats['pages_fetched']}")
    
    # Test 3: Try fetching a single document's details
    if en_stats["total_documents"] > 0:
        print("\n" + "=" * 60)
        print("TEST: Fetching Single Document Details")
        print("=" * 60)
        
        # Get the first document from our list
        first_page = fetch_documents_page(1, "en-US")
        if first_page and first_page.get("results"):
            first_doc = first_page["results"][0]
            slug = first_doc.get("slug", "")
            
            if slug:
                print(f"Fetching details for: {slug}")
                doc_details = test_single_document(slug, "en-US")
                
                if doc_details:
                    print(f"Title: {doc_details.get('title', 'N/A')}")
                    print(f"Has HTML content: {'html' in doc_details}")
                    print(f"Products: {', '.join(doc_details.get('products', []))}")
                    print(f"Topics: {', '.join(doc_details.get('topics', []))}")
                    
                    if doc_details.get("html"):
                        html_length = len(doc_details["html"])
                        print(f"HTML content length: {html_length:,} characters")
    
    # Test 4: Count documents in other locales
    print("\n" + "=" * 60)
    print("TESTING OTHER LOCALES")
    print("=" * 60)
    
    test_locales = ["es", "de", "fr", "ja", "zh-CN"]
    locale_counts = {}
    
    for locale in test_locales:
        print(f"\nChecking {locale}...", end=" ")
        # Just fetch first page to get a count estimate
        data = fetch_documents_page(1, locale)
        if data and data.get("count"):
            locale_counts[locale] = data["count"]
            print(f"approximately {data['count']} documents")
        else:
            print("no count available")
        sleep(0.5)  # Be nice to the API
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total English (en-US) documents: {en_stats['total_documents']}")
    print(f"Firefox-specific documents: {firefox_stats['total_documents']}")
    print(f"Other products: {en_stats['total_documents'] - firefox_stats['total_documents']}")
    
    if locale_counts:
        print("\nEstimated counts for other locales:")
        for locale, count in locale_counts.items():
            print(f"  {locale}: ~{count} documents")
    
    print("\nNOTE: The API uses pagination (20 items per page by default)")
    print("To download all content, you would need to:")
    print(f"1. Make ~{en_stats['pages_fetched']} requests to list all en-US documents")
    print(f"2. Make {en_stats['total_documents']} individual requests to get full content")
    print(f"3. Total API calls needed: ~{en_stats['pages_fetched'] + en_stats['total_documents']}")

if __name__ == "__main__":
    main()