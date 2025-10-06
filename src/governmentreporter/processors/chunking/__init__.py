"""
Document chunking module for government documents.

This module provides intelligent chunking algorithms that respect document
structure while maintaining semantic coherence. It supports:
- Supreme Court opinions with section awareness
- Executive Orders with regulatory structure preservation
- Configurable token limits and overlap strategies

The module is organized into:
- base.py: Shared utilities and core chunking algorithm
- scotus.py: Supreme Court opinion-specific chunking
- executive_orders.py: Executive Order-specific chunking

Usage:
    from governmentreporter.processors.chunking import chunk_supreme_court_opinion
    from governmentreporter.processors.chunking import chunk_executive_order
    from governmentreporter.processors.chunking import get_chunking_config

    # Chunk SCOTUS opinion
    chunks, syllabus = chunk_supreme_court_opinion(opinion_text)

    # Chunk Executive Order
    chunks = chunk_executive_order(order_text)

    # Get configuration
    scotus_cfg = get_chunking_config("scotus")
"""

# Import tiktoken for tests that mock it
import tiktoken

# Import shared utilities from base
from .base import (
    EO_CFG,
    SCOTUS_CFG,
    ChunkingConfig,
    _load_config,
    chunk_text_with_tokens,
    count_tokens,
    get_chunking_config,
    normalize_whitespace,
    overlap_tokens,
)
from .executive_orders import chunk_executive_order

# Import document-specific chunkers
from .scotus import chunk_supreme_court_opinion

__all__ = [
    # Configuration
    "ChunkingConfig",
    "SCOTUS_CFG",
    "EO_CFG",
    "_load_config",
    "get_chunking_config",
    # Utilities
    "count_tokens",
    "normalize_whitespace",
    "chunk_text_with_tokens",
    "overlap_tokens",
    # Document-specific chunkers
    "chunk_supreme_court_opinion",
    "chunk_executive_order",
]
