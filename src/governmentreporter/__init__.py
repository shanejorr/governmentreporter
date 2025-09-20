"""
GovernmentReporter: US Federal Government Document Retrieval and RAG Database System.

This is the main package initialization file for GovernmentReporter, a comprehensive Python
library designed for retrieving, processing, and storing US federal government publications
in a Qdrant vector database for retrieval augmented generation (RAG) applications.

The GovernmentReporter system provides:
    - Hierarchical document chunking for complex legal documents
    - AI-powered metadata extraction using Google Gemini 2.5 Flash-Lite
    - Semantic embedding generation for intelligent search
    - Qdrant integration for vector storage and retrieval
    - Support for multiple government data sources (SCOTUS opinions, Executive Orders)
    - Resumable bulk processing with progress tracking
    - Rich legal and policy metadata extraction

Package Structure:
    - apis/: Government API client implementations (CourtListener, Federal Register)
    - database/: Qdrant vector database integration and ingestion utilities
    - processors/: Document processing, chunking, metadata extraction, and embedding generation
    - utils/: Shared utilities for configuration, legal text parsing, and monitoring

This package serves as the entry point for all GovernmentReporter functionality.
When imported, it provides access to the entire library's capabilities through
its submodules and exposes the package version for dependency management.

Integration Points:
    - Works with scripts/download_scotus_bulk.py for SCOTUS opinion processing
    - Works with scripts/process_executive_orders.py for Executive Order processing
    - Can be used programmatically as a library for custom workflows
    - Designed for integration with LLM applications via Qdrant

Environment Requirements:
    - Python 3.11+ (specified in pyproject.toml)
    - COURT_LISTENER_API_TOKEN (for SCOTUS opinions)
    - GOOGLE_GEMINI_API_KEY (for metadata and embeddings)
    - Qdrant for vector storage

Python Learning Notes:
    - __version__: Special variable that defines the package version
    - Package initialization: This file makes the directory a Python package
    - Module imports: Submodules can be imported as governmentreporter.apis, etc.
    - Docstrings: Triple-quoted strings provide package-level documentation
    - __all__ (not used here): Could control what's exported with 'from package import *'

Version History:
    - 0.1.0: Initial release with SCOTUS and Executive Order support
"""

__version__ = "0.1.0"
