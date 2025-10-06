"""
Shared chunking utilities and configuration for government documents.

This module provides the foundation for document chunking across different
document types. It contains:
- ChunkingConfig dataclass for per-document-type configuration
- Token counting using OpenAI's tiktoken
- Text normalization utilities
- Core sliding window chunking algorithm

The module is document-type agnostic and provides building blocks that
specific chunkers (SCOTUS, Executive Orders) build upon.
"""

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Tuple

import tiktoken

from ...utils import get_logger

logger = get_logger(__name__)


@dataclass
class ChunkingConfig:
    """
    Configuration for document chunking.

    This dataclass encapsulates the chunking parameters for different document types,
    allowing flexible configuration while maintaining type safety.

    Attributes:
        min_tokens: Minimum tokens per chunk (avoid tiny chunks)
        target_tokens: Target window size for sliding window
        max_tokens: Maximum tokens per chunk (hard limit)
        overlap_ratio: Fraction of target_tokens to overlap (0.0 to 1.0)

    """

    min_tokens: int
    target_tokens: int
    max_tokens: int
    overlap_ratio: float

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.min_tokens <= 0 or self.target_tokens <= 0 or self.max_tokens <= 0:
            raise ValueError("Token counts must be positive")
        if self.min_tokens > self.max_tokens:
            raise ValueError("min_tokens cannot exceed max_tokens")
        if self.overlap_ratio < 0 or self.overlap_ratio >= 1:
            raise ValueError("overlap_ratio must be between 0 and 1 (exclusive)")


def _load_config(prefix: str, defaults: Dict[str, Any]) -> ChunkingConfig:
    """
    Load configuration with environment variable overrides.

    Args:
        prefix: Environment variable prefix (e.g., "RAG_SCOTUS")
        defaults: Default configuration values

    Returns:
        ChunkingConfig with environment overrides applied

    """
    min_tokens = int(os.environ.get(f"{prefix}_MIN_TOKENS", defaults["min_tokens"]))
    target_tokens = int(
        os.environ.get(f"{prefix}_TARGET_TOKENS", defaults["target_tokens"])
    )
    max_tokens = int(os.environ.get(f"{prefix}_MAX_TOKENS", defaults["max_tokens"]))
    overlap_ratio = float(
        os.environ.get(f"{prefix}_OVERLAP_RATIO", defaults["overlap_ratio"])
    )

    return ChunkingConfig(
        min_tokens=min_tokens,
        target_tokens=target_tokens,
        max_tokens=max_tokens,
        overlap_ratio=overlap_ratio,
    )


# Module-level configurations
SCOTUS_CFG = _load_config(
    "RAG_SCOTUS",
    {"min_tokens": 500, "target_tokens": 600, "max_tokens": 800, "overlap_ratio": 0.15},
)

EO_CFG = _load_config(
    "RAG_EO",
    {"min_tokens": 240, "target_tokens": 340, "max_tokens": 400, "overlap_ratio": 0.10},
)

# Log configurations at module load
logger.debug("SCOTUS chunking config: %s", SCOTUS_CFG)
logger.debug("EO chunking config: %s", EO_CFG)


def overlap_tokens(cfg: ChunkingConfig) -> int:
    """
    Calculate the number of overlap tokens from configuration.

    Args:
        cfg: Chunking configuration

    Returns:
        Number of tokens to overlap between chunks

    """
    return max(0, int(cfg.target_tokens * cfg.overlap_ratio))


def get_chunking_config(doc_type: Literal["scotus", "eo"]) -> ChunkingConfig:
    """
    Get the chunking configuration for a document type.

    Args:
        doc_type: Document type identifier

    Returns:
        Appropriate ChunkingConfig for the document type

    Raises:
        ValueError: If doc_type is not recognized

    Example:
        config = get_chunking_config("scotus")
        print(f"SCOTUS uses {config.target_tokens} target tokens")
    """
    if doc_type == "scotus":
        return SCOTUS_CFG
    elif doc_type == "eo":
        return EO_CFG
    else:
        raise ValueError(f"Unknown document type: {doc_type}")


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """
    Count the number of tokens in text using OpenAI's tiktoken.

    Uses the cl100k_base encoding (GPT-3.5-turbo and GPT-4 models).
    Falls back to 4 chars/token approximation if tiktoken fails.

    Args:
        text: The text to count tokens for
        encoding_name: The tiktoken encoding to use (default: cl100k_base)

    Returns:
        Number of tokens in the text
    """
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning("Failed to use tiktoken, falling back to approximation: %s", e)
        # Fallback: approximate 4 characters per token
        return len(text) // 4


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text while preserving paragraph structure.

    - Strips leading/trailing whitespace
    - Reduces multiple blank lines to double newlines (paragraph breaks)
    - Preserves single paragraph breaks

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    # Strip leading/trailing whitespace
    text = text.strip()

    # Reduce multiple blank lines to double newline (paragraph break)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    return text


def chunk_text_with_tokens(
    text: str,
    section_label: str,
    min_tokens: int,
    target_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Chunk text using sliding window with configurable overlap.

    This function implements a sliding window chunker that:
        - Creates chunks of approximately target_tokens size
        - Maintains overlap_tokens between adjacent chunks
        - Respects min_tokens and max_tokens boundaries
        - Merges small remainder chunks when possible

    Args:
        text: The text to chunk
        section_label: Label for this section (e.g., "Syllabus", "Sec. 2")
        min_tokens: Minimum tokens per chunk
        target_tokens: Target window size for sliding window
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Number of tokens to overlap between chunks

    Returns:
        List of (chunk_text, metadata) tuples where metadata includes:
            - section_label: The section this chunk belongs to
            - chunk_token_count: Actual token count for debugging

    """

    # Ensure forward progress
    if overlap_tokens >= target_tokens:
        logger.warning(
            "overlap_tokens (%d) >= target_tokens (%d), clamping to %d",
            overlap_tokens,
            target_tokens,
            target_tokens - 1,
        )
        overlap_tokens = max(0, target_tokens - 1)

    # Normalize whitespace
    text = normalize_whitespace(text)

    # Handle short documents
    total_tokens = count_tokens(text)
    if total_tokens <= max(min_tokens, target_tokens):
        metadata = {"section_label": section_label, "chunk_token_count": total_tokens}
        return [(text, metadata)]

    # Split into tokens for sliding window
    # We'll work with character positions for simplicity
    chunks = []
    text_length = len(text)

    # Calculate step size (how much to advance the window)
    step_size = max(1, target_tokens - overlap_tokens)

    # Character approximation for efficiency (roughly 4 chars per token)
    CHARS_PER_TOKEN = 4
    window_size_chars = target_tokens * CHARS_PER_TOKEN
    step_size_chars = step_size * CHARS_PER_TOKEN

    start_pos = 0

    while start_pos < text_length:
        # Calculate end position for this chunk
        end_pos = min(start_pos + window_size_chars, text_length)

        # Extract chunk text
        chunk_text = text[start_pos:end_pos]

        # Try to end at sentence boundary if not at document end
        if end_pos < text_length:
            # Look for sentence ending near the end
            last_period = chunk_text.rfind(". ")
            last_question = chunk_text.rfind("? ")
            last_exclaim = chunk_text.rfind("! ")

            # Find the latest sentence ending
            sentence_end = max(last_period, last_question, last_exclaim)

            # If we found a sentence ending in the last 20% of the chunk, use it
            if sentence_end > len(chunk_text) * 0.8:
                chunk_text = chunk_text[
                    : sentence_end + 2
                ]  # Include punctuation and space
                end_pos = start_pos + len(chunk_text)

        # Count actual tokens
        chunk_token_count = count_tokens(chunk_text)

        # Check if this is the last potential chunk
        remaining_text = text[end_pos:].strip()
        remaining_tokens = count_tokens(remaining_text) if remaining_text else 0

        # If remainder is too small and we have chunks, merge with last chunk
        if remaining_tokens > 0 and remaining_tokens < min_tokens and chunks:
            # Merge remainder into current chunk
            chunk_text = text[start_pos:].strip()
            chunk_token_count = count_tokens(chunk_text)

            # Only add if combined size is reasonable
            if (
                chunk_token_count <= max_tokens * 1.2
            ):  # Allow 20% overflow for final chunk
                metadata = {
                    "section_label": section_label,
                    "chunk_token_count": chunk_token_count,
                }
                chunks.append((normalize_whitespace(chunk_text), metadata))
            else:
                # Too large when merged, keep as separate chunks
                metadata = {
                    "section_label": section_label,
                    "chunk_token_count": chunk_token_count,
                }
                chunks.append((normalize_whitespace(chunk_text), metadata))

                # Add remainder as final chunk despite being small
                if remaining_text:
                    metadata = {
                        "section_label": section_label,
                        "chunk_token_count": remaining_tokens,
                    }
                    chunks.append((normalize_whitespace(remaining_text), metadata))
            break

        # Add current chunk
        metadata = {
            "section_label": section_label,
            "chunk_token_count": chunk_token_count,
        }
        chunks.append((normalize_whitespace(chunk_text), metadata))

        # Advance window
        if overlap_tokens > 0 and end_pos < text_length:
            # Move back by overlap amount
            overlap_chars = overlap_tokens * CHARS_PER_TOKEN
            start_pos = max(start_pos + step_size_chars, end_pos - overlap_chars)
        else:
            start_pos = end_pos

        # Ensure we make progress
        if start_pos <= end_pos - window_size_chars:
            start_pos = end_pos

    return chunks
