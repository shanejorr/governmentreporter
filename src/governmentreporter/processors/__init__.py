"""
Document processing modules for GovernmentReporter.

This package provides functionality for transforming government documents
into structured, searchable chunks with rich metadata for RAG retrieval.

The processors package includes:
    - schema: Pydantic models for metadata validation
    - llm_extraction: GPT-5-nano powered metadata generation
    - chunking: Section-aware text chunking algorithms
    - build_payloads: Main orchestration for document processing

Primary Interface:
    The main entry point is build_payloads_from_document() which accepts
    a Document object and returns Qdrant-ready payloads.

Example Usage:
    from governmentreporter.apis.court_listener import CourtListenerClient
    from governmentreporter.processors import build_payloads_from_document

    # Get document from API
    client = CourtListenerClient()
    doc = client.get_document("12345")

    # Process into chunks
    payloads = build_payloads_from_document(doc)

    # Ready for Qdrant storage
    # qdrant_client.batch_upsert(payloads, embeddings, "collection")

Python Learning Notes:
    - __all__ controls what's exported with "from processors import *"
    - Relative imports (.) reference modules in the same package
    - This file makes the directory a Python package
"""

from .build_payloads import build_payloads_from_document
from .schema import (
    SupremeCourtMetadata,
    ExecutiveOrderMetadata,
    ChunkMetadata,
    QdrantPayload,
)
from .llm_extraction import generate_scotus_llm_fields, generate_eo_llm_fields
from .chunking import chunk_supreme_court_opinion, chunk_executive_order

__all__ = [
    # Main interface
    "build_payloads_from_document",
    # Schemas
    "SupremeCourtMetadata",
    "ExecutiveOrderMetadata",
    "ChunkMetadata",
    "QdrantPayload",
    # LLM extraction
    "generate_scotus_llm_fields",
    "generate_eo_llm_fields",
    # Chunking
    "chunk_supreme_court_opinion",
    "chunk_executive_order",
]
