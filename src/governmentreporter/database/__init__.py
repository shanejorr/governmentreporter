"""
Database module for managing document embeddings and metadata.

This module provides a clean, unified interface for storing and retrieving
document embeddings using Qdrant vector database. It handles document storage,
retrieval, and semantic search with a simple, maintainable API.

Key Components:
    - QdrantClient: Unified client for all Qdrant operations
    - Document: Data structure for documents with embeddings
    - SearchResult: Data structure for search results

Architecture Overview:
    The database module implements a streamlined approach where:
    1. Documents are stored with embeddings for semantic search
    2. Metadata enables filtering and contextual retrieval
    3. Text content is stored alongside embeddings

    This design ensures:
    - Simple, predictable API
    - Fast semantic search capabilities
    - Easy maintenance and debugging

Integration Points:
    - APIs Module: Provides document content for storage
    - Metadata Module: Generates rich metadata using AI
    - Utils Module: Shared utilities for data processing

Python Learning Notes:
    - __init__.py files make directories into Python packages
    - The __all__ list controls what gets imported with "from package import *"
    - This file acts as the public interface for the database module
    - Dataclasses provide clean data structures with automatic methods

Example Usage:
    from governmentreporter.database import QdrantClient, Document

    # Initialize client
    client = QdrantClient(db_path="./qdrant_db")

    # Store a document
    doc = Document(
        id="scotus_2024_001",
        text="Supreme Court opinion text...",
        embedding=[0.1, 0.2, ...],  # 1536-dimensional vector
        metadata={"case": "Sample v. Example", "year": 2024}
    )
    client.store_document(doc, "scotus_opinions")

    # Search for similar documents
    results = client.search(query_embedding, "scotus_opinions", limit=5)
    for result in results:
        print(f"Score: {result.score:.3f} - {result.document.id}")
"""

from .qdrant import Document, QdrantDBClient, SearchResult

__all__ = ["QdrantDBClient", "Document", "SearchResult"]
