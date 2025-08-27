#!/usr/bin/env python
"""
Script to run all docstring examples from court_listener.py

This script demonstrates the usage of Court Listener API methods by running
the examples from the module docstrings using real API calls.

uv run python scratch/docstring_examples/run_court_listener_examples.py > court_listener_results.txt
"""

import os
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parents[2]))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.governmentreporter.apis.court_listener import CourtListenerClient
from src.governmentreporter.utils.config import get_court_listener_token


def truncate_text(text: str, max_chars: int = 100) -> str:
    """Truncate text to specified number of characters."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def run_examples():
    """Run docstring examples from CourtListenerClient."""

    # Initialize client
    print("=" * 80)
    print("CourtListenerClient Examples")
    print("=" * 80)

    # Get token (will raise error if not found)
    token = get_court_listener_token()
    client = CourtListenerClient(token=token)
    print(f"✓ Client initialized with token")
    print()

    # Example 1: Get a specific opinion
    print("-" * 80)
    print("Example 1: get_opinion(opinion_id)")
    print("-" * 80)
    opinion_id = 9973155  # From scratch/opinions_endpoint.json
    try:
        opinion = client.get_opinion(opinion_id)
        print(f"Opinion ID: {opinion['id']}")
        print(f"Author ID: {opinion.get('author_id', 'N/A')}")
        print(f"Text preview: {truncate_text(opinion.get('plain_text', ''))}")
        print(f"Opinion type: {opinion.get('type', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 2: Search documents with limit
    print("-" * 80)
    print("Example 2: search_documents(query, limit=2)")
    print("-" * 80)
    try:
        docs = client.search_documents("freedom of speech", limit=2)
        for i, doc in enumerate(docs, 1):
            print(f"Document {i}:")
            print(f"  Title: {doc.title}")
            print(f"  Citation: {doc.metadata.get('citation', 'N/A')}")
            print(f"  Content preview: {truncate_text(doc.content)}")
            print()
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 3: Get document with full metadata
    print("-" * 80)
    print("Example 3: get_document(document_id)")
    print("-" * 80)
    document_id = "9973155"
    try:
        doc = client.get_document(document_id)
        print(f"Case: {doc.title}")
        print(f"Decided: {doc.date}")
        print(f"Citation: {doc.metadata.get('citation', 'N/A')}")
        print(f"Content preview: {truncate_text(doc.content)}")
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 4: Get document text only
    print("-" * 80)
    print("Example 4: get_document_text(document_id)")
    print("-" * 80)
    try:
        text = client.get_document_text(document_id)
        print(f"Plain text preview: {truncate_text(text)}")
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 5: Extract basic metadata
    print("-" * 80)
    print("Example 5: extract_basic_metadata(opinion_data)")
    print("-" * 80)
    try:
        opinion_data = client.get_opinion(opinion_id)
        metadata = client.extract_basic_metadata(opinion_data)
        print(f"ID: {metadata['id']}")
        print(f"Date: {metadata['date']}")
        print(f"Author ID: {metadata['author_id']}")
        print(f"Type: {metadata['type']}")
        print(f"Page count: {metadata['page_count']}")
        print(f"Text preview: {truncate_text(metadata['plain_text'])}")
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 6: Get opinion cluster
    print("-" * 80)
    print("Example 6: get_opinion_cluster(cluster_url)")
    print("-" * 80)
    try:
        opinion = client.get_opinion(opinion_id)
        cluster_url = opinion.get("cluster")
        if cluster_url:
            cluster = client.get_opinion_cluster(cluster_url)
            print(f"Case: {cluster.get('case_name', 'N/A')}")
            print(f"Filed: {cluster.get('date_filed', 'N/A')}")

            # Extract citation information
            citations = cluster.get("citations", [])
            if citations:
                primary = citations[0]
                print(
                    f"Citation: {primary.get('volume', '')} {primary.get('reporter', '')} {primary.get('page', '')}"
                )
        else:
            print("No cluster URL found")
    except Exception as e:
        print(f"Error: {e}")
    print()

    # Example 7: Search with date range
    print("-" * 80)
    print("Example 7: search_documents with date filters")
    print("-" * 80)
    try:
        docs = client.search_documents(
            query="constitutional", start_date="2020-01-01", limit=2
        )
        print(f"Found {len(docs)} documents")
        for doc in docs:
            print(f"  {doc.title} ({doc.date})")
            print(f"    Content preview: {truncate_text(doc.content)}")
    except Exception as e:
        print(f"Error: {e}")
    print()

    print("=" * 80)
    print("All Court Listener examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    run_examples()
