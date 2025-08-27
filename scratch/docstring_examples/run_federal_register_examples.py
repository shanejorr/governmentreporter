#!/usr/bin/env python
"""
Script to run all docstring examples from federal_register.py

This script demonstrates the usage of Federal Register API methods by running
the examples from the module docstrings using real API calls.

#  uv run python scratch/docstring_examples/run_federal_register_examples.py > federal_register_results.txt
"""

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parents[2]))

# Load environment variables from .env file (for consistency)
from dotenv import load_dotenv
load_dotenv()

from src.governmentreporter.apis.federal_register import FederalRegisterClient


def truncate_text(text: str, max_chars: int = 100) -> str:
    """Truncate text to specified number of characters."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def run_examples():
    """Run docstring examples from FederalRegisterClient."""

    # Initialize client
    print("=" * 80)
    print("FederalRegisterClient Examples")
    print("=" * 80)

    # No token needed for Federal Register API
    client = FederalRegisterClient()
    print("✓ Client initialized (no authentication required)")
    print()

    # Example 1: Get a specific executive order
    print("-" * 80)
    print("Example 1: get_executive_order(document_number)")
    print("-" * 80)
    document_number = "2025-10800"  # From scratch/executive_order_metadata.json
    try:
        order = client.get_executive_order(document_number)
        print(f"Title: {order.get('title', 'N/A')}")
        print(f"EO Number: {order.get('executive_order_number', 'N/A')}")
        print(
            f"Signed: {order.get('signing_date', 'N/A')} by {order.get('president', {}).get('name', 'N/A')}"
        )
        print(f"Citation: {order.get('citation', 'N/A')}")

        # Access different format URLs
        print(
            f"PDF URL: {order.get('pdf_url', 'N/A')[:50]}..."
            if order.get("pdf_url")
            else "PDF URL: N/A"
        )
        print(
            f"Text URL: {order.get('raw_text_url', 'N/A')[:50]}..."
            if order.get("raw_text_url")
            else "Text URL: N/A"
        )
        print(
            f"Web URL: {order.get('html_url', 'N/A')[:50]}..."
            if order.get("html_url")
            else "Web URL: N/A"
        )
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 2: Get executive order text
    print("-" * 80)
    print("Example 2: get_executive_order_text(raw_text_url)")
    print("-" * 80)
    try:
        order_data = client.get_executive_order(document_number)
        raw_url = order_data.get("raw_text_url")
        if raw_url:
            text = client.get_executive_order_text(raw_url)
            print(f"Order text preview: {truncate_text(text)}")
        else:
            print("No raw text URL found")
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 3: List executive orders
    print("-" * 80)
    print("Example 3: list_executive_orders(start_date, end_date)")
    print("-" * 80)
    try:
        count = 0
        for order in client.list_executive_orders(
            "2024-01-01", "2024-12-31", max_results=2
        ):
            count += 1
            print(f"Order {count}:")
            print(
                f"  EO {order.get('executive_order_number', 'N/A')}: {order.get('title', 'N/A')}"
            )
            print(f"  Document: {order.get('document_number', 'N/A')}")
            print(f"  President: {order.get('president', {}).get('name', 'N/A')}")
            print()
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 4: Search documents
    print("-" * 80)
    print("Example 4: search_documents(query, limit=2)")
    print("-" * 80)
    try:
        climate_orders = client.search_documents(
            "climate change renewable energy", start_date="2021-01-01", limit=2
        )
        for doc in climate_orders:
            print(f"Title: {doc.title}")
            print(f"Date: {doc.date}")
            print(f"Content preview: {truncate_text(doc.content)}")
            print()
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 5: Get document with full content
    print("-" * 80)
    print("Example 5: get_document(document_id)")
    print("-" * 80)
    try:
        doc = client.get_document(document_number)
        print(f"Title: {doc.title}")
        print(f"Signed: {doc.date}")
        print(f"President: {doc.metadata.get('president', {}).get('name', 'N/A')}")
        print(f"EO Number: {doc.metadata.get('executive_order_number', 'N/A')}")
        print(f"Content preview: {truncate_text(doc.content)}")
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 6: Get document text only
    print("-" * 80)
    print("Example 6: get_document_text(document_id)")
    print("-" * 80)
    try:
        text = client.get_document_text(document_number)
        word_count = len(text.split())
        print(f"Executive order contains {word_count} words")
        print(f"Text preview: {truncate_text(text)}")

        # Search for specific terms
        if "national security" in text.lower():
            print("✓ Order relates to national security")
        else:
            print("✗ Order does not mention national security")

        # Extract key phrases (first sentence)
        sentences = text.split(". ")
        if sentences:
            print(f"First sentence: {truncate_text(sentences[0].strip())}")
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 7: Extract basic metadata
    print("-" * 80)
    print("Example 7: extract_basic_metadata(order_data)")
    print("-" * 80)
    try:
        raw_data = client.get_executive_order(document_number)
        metadata = client.extract_basic_metadata(raw_data)
        print(f"Document Number: {metadata['document_number']}")
        print(f"Title: {metadata['title']}")
        print(f"EO Number: {metadata['executive_order_number']}")
        print(f"Signed: {metadata['signing_date']} by {metadata['president']}")
        print(f"Citation: {metadata['citation']}")
        print(
            f"Agencies: {', '.join(metadata['agencies']) if metadata['agencies'] else 'None'}"
        )
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 8: Search with all filters
    print("-" * 80)
    print("Example 8: search_documents with all filters")
    print("-" * 80)
    try:
        security_orders = client.search_documents(
            "national security", start_date="2023-01-01", end_date="2023-12-31", limit=2
        )
        print(f"Found {len(security_orders)} national security orders in 2023")
        for doc in security_orders:
            print(f"  - {doc.title} ({doc.date})")
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 9: Search for specific executive order
    print("-" * 80)
    print("Example 9: search_documents for specific EO")
    print("-" * 80)
    try:
        results = client.search_documents("Executive Order 14019", limit=2)
        if results:
            order = results[0]
            print(f"Found: {order.title}")
            print(
                f"Signed: {order.date} by {order.metadata.get('president', {}).get('name', 'N/A')}"
            )
        else:
            print("No results found for Executive Order 14019")
    except Exception as e:
        print(f"Error: {e}")
    print()

    print("=" * 80)
    print("All Federal Register examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    run_examples()
