"""
Database integrations for storing document embeddings and metadata.

This module provides the database layer for the GovernmentReporter application,
specifically focused on vector database operations using ChromaDB. The module
handles the storage and retrieval of document embeddings, metadata, and full
text content for government documents.

Key Components:
    ChromaDBClient: Main client class for ChromaDB operations

Architecture Overview:
    The database module implements a metadata-only storage approach where:
    1. Document embeddings are stored for semantic search
    2. Metadata is stored for filtering and context
    3. Full document text is retrieved on-demand from government APIs

    This approach ensures:
    - Fresh, up-to-date document content
    - Efficient storage usage
    - Fast semantic search capabilities
    - Scalable document management

Integration Points:
    - APIs Module: Provides fresh document content during retrieval
    - Metadata Module: Generates rich metadata using Gemini 2.5 Flash-Lite
    - Utils Module: Shared utilities for data processing

Python Learning Notes:
    - __init__.py files make directories into Python packages
    - The __all__ list controls what gets imported with "from package import *"
    - This file acts as the public interface for the database module
    - Importing classes here allows users to do "from database import ChromaDBClient"
      instead of "from database.chroma_client import ChromaDBClient"

Example Usage:
    from governmentreporter.database import ChromaDBClient

    # Create database client
    db = ChromaDBClient(db_path="./my_chroma_db")

    # Store a document with embeddings
    db.store_scotus_opinion(
        opinion_id="scotus_2024_001",
        plain_text="Supreme Court opinion text...",
        embedding=[0.1, 0.2, 0.3, ...],  # 768-dimensional vector
        metadata={"case_name": "Sample v. Example", "year": 2024}
    )
"""

from .chroma_client import ChromaDBClient

__all__ = ["ChromaDBClient"]
