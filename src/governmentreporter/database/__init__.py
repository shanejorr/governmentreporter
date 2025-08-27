"""
Database integrations for storing document embeddings and metadata.

This module provides the database layer for the GovernmentReporter application,
specifically focused on vector database operations using Qdrant. The module
handles the storage and retrieval of document embeddings, metadata, and full
text content for government documents.

Key Components:
    QdrantDBClient: Main client class for Qdrant operations

Architecture Overview:
    The database module implements a storage approach where:
    1. Document embeddings are stored for semantic search
    2. Metadata is stored for filtering and context
    3. Text data is also stores

    This approach ensures:
    - Fresh, up-to-date document content
    - Fast semantic search capabilities
    - Scalable document management

Integration Points:
    - APIs Module: Provides fresh document content during retrieval
    - Metadata Module: Generates rich metadata using OpenAI GPT-5-nano
    - Utils Module: Shared utilities for data processing

Python Learning Notes:
    - __init__.py files make directories into Python packages
    - The __all__ list controls what gets imported with "from package import *"
    - This file acts as the public interface for the database module
    - Importing classes here allows users to do "from database import QdrantDBClient"
      instead of "from database.qdrant_client import QdrantDBClient"

Example Usage:
    from governmentreporter.database import QdrantDBClient

    # Create database client (db_path is required)
    db = QdrantDBClient(db_path="./my_qdrant_db")

    # Store a document with embeddings
    db.store_document(
        document_id="scotus_2024_001",
        text="Supreme Court opinion text...",
        embedding=[0.1, 0.2, 0.3, ...],  # 1536-dimensional vector
        metadata={"case_name": "Sample v. Example", "year": 2024},
        collection_name="federal_court_scotus_opinions"
    )
"""

from .qdrant_client import QdrantDBClient

__all__ = ["QdrantDBClient"]
