"""
Document Processing Module for Government Publications

This module provides a comprehensive document processing system for US federal government
publications, implementing hierarchical chunking, metadata extraction, and embedding
generation for RAG (Retrieval-Augmented Generation) applications.

Core Architecture:
    The processors module implements a three-layer architecture:

    1. **Base Layer** (base.py, base_bulk.py):
       - Abstract base classes defining common interfaces
       - Shared functionality for document processing and bulk operations
       - Progress tracking, error handling, and database integration

    2. **Document-Specific Chunkers** (scotus_opinion_chunker.py, executive_order_chunker.py):
       - Specialized hierarchical chunking algorithms for each document type
       - Metadata extraction using Gemini AI
       - Integration with government APIs for data retrieval

    3. **Bulk Processing Layer** (scotus_bulk.py, executive_order_bulk.py):
       - Large-scale document processing workflows
       - Rate limiting and API management
       - Resume capability and progress tracking

Processing Workflow:
    1. **Document Retrieval**: Fetch documents from government APIs
    2. **Hierarchical Chunking**: Break documents into semantic chunks based on structure
    3. **Metadata Generation**: Extract legal metadata using Gemini 2.5 Flash-Lite
    4. **Embedding Creation**: Generate vector embeddings using Google's text embeddings
    5. **Database Storage**: Store chunks and metadata in ChromaDB for retrieval

Document Types Supported:
    - Supreme Court Opinions: Full-text opinions with syllabus, majority, concurring, and dissenting sections
    - Executive Orders: Presidential directives with hierarchical section structure

Integration Points:
    - APIs: CourtListener, Federal Register
    - Database: ChromaDB for vector storage
    - AI Services: Google Gemini for metadata, Google text embeddings for vectors
    - Utils: Citation formatting, embeddings client, logging utilities

Python Learning Notes:
    - Uses dataclasses for structured data representation
    - Implements ABC (Abstract Base Class) pattern for extensible design
    - Leverages async/await patterns for API operations
    - Demonstrates factory pattern through processor initialization
    - Shows composition over inheritance through client dependency injection

Example Usage:
    ```python
    from governmentreporter.processors import SCOTUSOpinionProcessor

    # Process a single Supreme Court opinion
    processor = SCOTUSOpinionProcessor()
    result = processor.process_and_store(
        document_id="123456",
        collection_name="scotus_opinions"
    )
    logger = get_logger(__name__)
    logger.info(f"Created {result['chunks_processed']} chunks")
    ```

Dependencies:
    - chromadb: Vector database for embeddings storage
    - google.generativeai: Gemini API for metadata extraction
    - dataclasses: Python's structured data classes
    - abc: Abstract base class functionality
    - logging: Comprehensive logging system
"""

from .executive_order_bulk import ExecutiveOrderBulkProcessor
from .executive_order_chunker import ExecutiveOrderProcessor
from .scotus_bulk import SCOTUSBulkProcessor
from .scotus_opinion_chunker import SCOTUSOpinionProcessor

__all__ = [
    "SCOTUSBulkProcessor",
    "SCOTUSOpinionProcessor",
    "ExecutiveOrderBulkProcessor",
    "ExecutiveOrderProcessor",
]
