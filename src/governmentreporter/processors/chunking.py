"""
Section-aware document chunking for Supreme Court opinions and Executive Orders.

This module provides intelligent chunking algorithms that respect document structure
while maintaining semantic coherence. It implements section-aware splitting with
configurable token limits and overlap strategies.

Key Features:
    - Per-document-type chunking configurations
    - Token-based splitting using OpenAI's tiktoken library
    - Sliding window with configurable overlap ratios
    - Special handling for Supreme Court opinion sections (Syllabus, opinions)
    - Executive Order section detection (Sec. 1, Sec. 2, etc.)
    - Preservation of legal citations and references
    - No overlap across section boundaries for Executive Orders

Chunking Configurations:
    Supreme Court Opinions:
        - MIN_TOKENS: 500
        - TARGET_TOKENS: 600
        - MAX_TOKENS: 800
        - OVERLAP_RATIO: 0.15 (15%)

    Executive Orders:
        - MIN_TOKENS: 240
        - TARGET_TOKENS: 340
        - MAX_TOKENS: 400
        - OVERLAP_RATIO: 0.10 (10%)

"""

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

import tiktoken

from ..utils import get_logger

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


# Load configurations with environment variable overrides
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


def chunk_supreme_court_opinion(
    text: str,
) -> Tuple[List[Tuple[str, Dict[str, Any]]], Optional[str]]:
    """
    Chunk a Supreme Court opinion with section awareness.

    This function identifies and preserves the structure of Supreme Court opinions:
        - Syllabus (official summary)
        - Majority Opinion
        - Concurring Opinions
        - Dissenting Opinions

    Uses SCOTUS_CFG configuration:
        - MIN_TOKENS: 500
        - TARGET_TOKENS: 600
        - MAX_TOKENS: 800
        - OVERLAP_RATIO: 0.15 (15%)

    Section Detection:
        The function uses regex patterns to identify section boundaries:
        - Syllabus: ^SYLLABUS or ^Syllabus
        - Majority: "delivered the opinion of the Court" or "Per Curiam"
        - Concurrence/Dissent: "JUSTICE X, concurring/dissenting"

    Special Handling:
        - Syllabus is extracted separately for LLM analysis
        - Roman numeral subheadings (I., II., III.) create boundaries
        - Overlap is applied within sections but not across boundaries

    Args:
        text (str): Full text of the Supreme Court opinion

    Returns:
        Tuple containing:
            - List[Tuple[str, Dict]]: List of (chunk_text, metadata) tuples
            - Optional[str]: The Syllabus text if found (for LLM use)

    Example:
        opinion_text = '''
        SYLLABUS
        The Court held that...

        JUSTICE ROBERTS delivered the opinion of the Court.
        [Main opinion text...]

        JUSTICE THOMAS, concurring.
        [Concurring opinion...]
        '''

        chunks, syllabus = chunk_supreme_court_opinion(opinion_text)
        print(f"Found {len(chunks)} chunks")
        print(f"Syllabus: {syllabus[:100]}...")

    """
    chunks = []
    syllabus_text = None

    # Calculate overlap for SCOTUS documents
    ov = overlap_tokens(SCOTUS_CFG)

    logger.debug(
        "Chunking SCOTUS opinion with config: min=%d, target=%d, max=%d, overlap=%d",
        SCOTUS_CFG.min_tokens,
        SCOTUS_CFG.target_tokens,
        SCOTUS_CFG.max_tokens,
        ov,
    )

    # Section detection patterns
    patterns = {
        "syllabus": re.compile(r"^\s*SYLLABUS\s*$", re.MULTILINE | re.IGNORECASE),
        "majority": re.compile(
            r"^(?:(?:Per Curiam\.)|"
            r"(?:JUSTICE\s+[A-Z][A-Za-z\-]+,?\s+delivered the opinion of the Court\.?)|"
            r"(?:Opinion of the Court))",
            re.MULTILINE | re.IGNORECASE,
        ),
        "concurring": re.compile(
            r"^JUSTICE\s+[A-Z][A-Za-z\-]+,\s+(?:with whom.*?join,\s+)?concurring",
            re.MULTILINE,
        ),
        "dissenting": re.compile(
            r"^JUSTICE\s+[A-Z][A-Za-z\-]+,\s+(?:with whom.*?join,\s+)?dissenting",
            re.MULTILINE,
        ),
        "concur_dissent": re.compile(
            r"^JUSTICE\s+[A-Z][A-Za-z\-]+,\s+(?:with whom.*?join,\s+)?"
            r"concurring in part and dissenting in part",
            re.MULTILINE,
        ),
    }

    # Find all section boundaries
    sections = []

    # Check for Syllabus
    syllabus_match = patterns["syllabus"].search(text)
    if syllabus_match:
        sections.append(("syllabus", syllabus_match.start(), "Syllabus"))

    # Check for majority opinion
    majority_match = patterns["majority"].search(text)
    if majority_match:
        sections.append(("majority", majority_match.start(), "Majority Opinion"))

    # Check for concurring opinions
    for match in patterns["concurring"].finditer(text):
        sections.append(("concurring", match.start(), "Concurring Opinion"))

    # Check for dissenting opinions
    for match in patterns["dissenting"].finditer(text):
        sections.append(("dissenting", match.start(), "Dissenting Opinion"))

    # Check for concurring and dissenting opinions
    for match in patterns["concur_dissent"].finditer(text):
        sections.append(
            ("concur_dissent", match.start(), "Concurring in Part, Dissenting in Part")
        )

    # Sort sections by position in text
    sections.sort(key=lambda x: x[1])

    # If no sections found, treat entire text as one section
    if not sections:
        logger.warning("No section markers found in Supreme Court opinion")
        chunk_results = chunk_text_with_tokens(
            text,
            "Opinion",
            min_tokens=SCOTUS_CFG.min_tokens,
            target_tokens=SCOTUS_CFG.target_tokens,
            max_tokens=SCOTUS_CFG.max_tokens,
            overlap_tokens=ov,
        )
        for chunk_text, metadata in chunk_results:
            chunks.append((chunk_text, metadata))
        return chunks, None

    # Process each section
    for i, (section_type, start_pos, section_label) in enumerate(sections):
        # Determine end position (start of next section or end of text)
        end_pos = sections[i + 1][1] if i + 1 < len(sections) else len(text)
        section_text = text[start_pos:end_pos].strip()

        # Extract Syllabus for separate LLM processing
        if section_type == "syllabus":
            # Find the actual Syllabus content (after the header)
            syllabus_lines = section_text.split("\n")
            syllabus_content = "\n".join(syllabus_lines[1:]).strip()  # Skip header line
            if syllabus_content:
                syllabus_text = syllabus_content

        # Handle Roman numeral subsections within opinions
        roman_pattern = re.compile(r"^\s*[IVX]+\.\s*$", re.MULTILINE)
        subsections = list(roman_pattern.finditer(section_text))

        if subsections and len(subsections) > 1:
            # Process each subsection separately
            for j, match in enumerate(subsections):
                subsection_start = match.start()
                subsection_end = (
                    subsections[j + 1].start()
                    if j + 1 < len(subsections)
                    else len(section_text)
                )
                subsection_text = section_text[subsection_start:subsection_end].strip()

                # Create section label with Roman numeral
                roman_numeral = match.group().strip().rstrip(".")
                subsection_label = f"{section_label} - Part {roman_numeral}"

                # Chunk the subsection with SCOTUS config
                chunk_results = chunk_text_with_tokens(
                    subsection_text,
                    subsection_label,
                    min_tokens=SCOTUS_CFG.min_tokens,
                    target_tokens=SCOTUS_CFG.target_tokens,
                    max_tokens=SCOTUS_CFG.max_tokens,
                    overlap_tokens=ov,
                )
                for chunk_text, metadata in chunk_results:
                    chunks.append((chunk_text, metadata))
        else:
            # No subsections, chunk the entire section
            chunk_results = chunk_text_with_tokens(
                section_text,
                section_label,
                min_tokens=SCOTUS_CFG.min_tokens,
                target_tokens=SCOTUS_CFG.target_tokens,
                max_tokens=SCOTUS_CFG.max_tokens,
                overlap_tokens=ov,
            )
            for chunk_text, metadata in chunk_results:
                chunks.append((chunk_text, metadata))

    logger.info(
        "Chunked Supreme Court opinion into %d chunks across %d sections",
        len(chunks),
        len(sections),
    )

    return chunks, syllabus_text


def chunk_executive_order(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Chunk an Executive Order with section awareness.

    This function identifies and preserves the structure of Executive Orders:
        - Preamble (everything before first "Sec.")
        - Numbered sections (Sec. 1, Sec. 2, etc.)
        - Subsections and paragraphs

    Uses EO_CFG configuration:
        - MIN_TOKENS: 240
        - TARGET_TOKENS: 340
        - MAX_TOKENS: 400
        - OVERLAP_RATIO: 0.10 (10%)

    Section Detection:
        The function uses regex patterns to identify:
        - Section headers: "Sec. 1.", "Sec. 2(a).", etc.
        - Subsection markers: (a), (b), (c), etc.
        - Subparagraphs: (i), (ii), (iii), etc.

    Chunking Strategy:
        - NEVER creates overlap across section boundaries
        - Each section is chunked independently
        - Overlap only applies within the same section
        - Maintains whole paragraphs when possible

    Args:
        text (str): Full text of the Executive Order

    Returns:
        List[Tuple[str, Dict]]: List of (chunk_text, metadata) tuples where
            metadata contains section_label and chunk_token_count

    Example:
        eo_text = '''
        Executive Order 14304

        By the authority vested in me...

        Section 1. Purpose. This order establishes...

        Sec. 2. Policy. (a) It is the policy...
        (b) Federal agencies shall...
        '''

        chunks = chunk_executive_order(eo_text)
        for chunk_text, metadata in chunks:
            print(f"Section: {metadata['section_label']}")
            print(f"Tokens: {metadata['chunk_token_count']}")

    """
    chunks = []

    # Calculate overlap for EO documents
    ov = overlap_tokens(EO_CFG)

    logger.debug(
        "Chunking Executive Order with config: min=%d, target=%d, max=%d, overlap=%d",
        EO_CFG.min_tokens,
        EO_CFG.target_tokens,
        EO_CFG.max_tokens,
        ov,
    )

    # Pattern to match section headers
    # Matches: Sec. 1., Sec. 2(a)., Section 3., etc.
    section_pattern = re.compile(
        r"^\s*(Sec(?:tion)?\.?\s*\d+[A-Za-z\-]*\.)", re.MULTILINE | re.IGNORECASE
    )

    # Find all section headers
    section_matches = list(section_pattern.finditer(text))

    # Process preamble (everything before first section)
    if section_matches:
        preamble_text = text[: section_matches[0].start()].strip()
        if preamble_text:
            # Chunk the preamble with EO config
            chunk_results = chunk_text_with_tokens(
                preamble_text,
                "Preamble",
                min_tokens=EO_CFG.min_tokens,
                target_tokens=EO_CFG.target_tokens,
                max_tokens=EO_CFG.max_tokens,
                overlap_tokens=ov,
            )
            for chunk_text, metadata in chunk_results:
                chunks.append((chunk_text, metadata))

    # Process each section INDEPENDENTLY (no cross-section overlap)
    for i, match in enumerate(section_matches):
        # Extract section number and title
        section_header = match.group(1)
        section_start = match.start()

        # Find section end (start of next section or end of document)
        section_end = (
            section_matches[i + 1].start()
            if i + 1 < len(section_matches)
            else len(text)
        )
        section_text = text[section_start:section_end].strip()

        # Extract section number for label
        section_num_match = re.search(r"\d+[A-Za-z\-]*", section_header)
        section_num = section_num_match.group() if section_num_match else str(i + 1)

        # Try to extract section title (usually follows the section number)
        title_match = re.search(
            r"^Sec(?:tion)?\.?\s*\d+[A-Za-z\-]*\.\s*([^.]+)\.", section_text
        )
        section_title = title_match.group(1).strip() if title_match else ""

        # Create section label
        if section_title:
            section_label = f"Sec. {section_num} - {section_title}"
        else:
            section_label = f"Sec. {section_num}"

        # Check for subsections within this section
        subsection_pattern = re.compile(r"^\s*\([a-z]\)\s*", re.MULTILINE)
        subsection_matches = list(subsection_pattern.finditer(section_text))

        if subsection_matches and len(subsection_matches) > 1:
            # Process each subsection separately
            for j, subsec_match in enumerate(subsection_matches):
                subsec_start = subsec_match.start()
                subsec_end = (
                    subsection_matches[j + 1].start()
                    if j + 1 < len(subsection_matches)
                    else len(section_text)
                )
                subsection_text = section_text[subsec_start:subsec_end].strip()

                # Extract subsection letter
                subsec_letter = re.search(r"\(([a-z])\)", subsec_match.group()).group(1)
                subsection_label = f"{section_label}({subsec_letter})"

                # Check for subparagraphs (i), (ii), etc.
                subpara_pattern = re.compile(
                    r"^\s*\((?:i|ii|iii|iv|v|vi|vii|viii|ix|x)+\)\s*", re.MULTILINE
                )
                subpara_matches = list(subpara_pattern.finditer(subsection_text))

                if subpara_matches and len(subpara_matches) > 1:
                    # Process each subparagraph
                    for k, subpara_match in enumerate(subpara_matches):
                        subpara_start = subpara_match.start()
                        subpara_end = (
                            subpara_matches[k + 1].start()
                            if k + 1 < len(subpara_matches)
                            else len(subsection_text)
                        )
                        subpara_text = subsection_text[
                            subpara_start:subpara_end
                        ].strip()

                        # Chunk the subparagraph with EO config
                        chunk_results = chunk_text_with_tokens(
                            subpara_text,
                            subsection_label,
                            min_tokens=EO_CFG.min_tokens,
                            target_tokens=EO_CFG.target_tokens,
                            max_tokens=EO_CFG.max_tokens,
                            overlap_tokens=ov,
                        )
                        for chunk_text, metadata in chunk_results:
                            chunks.append((chunk_text, metadata))
                else:
                    # No subparagraphs, chunk the subsection
                    chunk_results = chunk_text_with_tokens(
                        subsection_text,
                        subsection_label,
                        min_tokens=EO_CFG.min_tokens,
                        target_tokens=EO_CFG.target_tokens,
                        max_tokens=EO_CFG.max_tokens,
                        overlap_tokens=ov,
                    )
                    for chunk_text, metadata in chunk_results:
                        chunks.append((chunk_text, metadata))
        else:
            # No subsections, chunk the entire section independently
            chunk_results = chunk_text_with_tokens(
                section_text,
                section_label,
                min_tokens=EO_CFG.min_tokens,
                target_tokens=EO_CFG.target_tokens,
                max_tokens=EO_CFG.max_tokens,
                overlap_tokens=ov,
            )
            for chunk_text, metadata in chunk_results:
                chunks.append((chunk_text, metadata))

    # If no sections were found, treat as single document
    if not chunks:
        logger.warning("No section markers found in Executive Order")
        chunk_results = chunk_text_with_tokens(
            text,
            "Executive Order",
            min_tokens=EO_CFG.min_tokens,
            target_tokens=EO_CFG.target_tokens,
            max_tokens=EO_CFG.max_tokens,
            overlap_tokens=ov,
        )
        for chunk_text, metadata in chunk_results:
            chunks.append((chunk_text, metadata))

    logger.info("Chunked Executive Order into %d chunks", len(chunks))

    return chunks


# Example usage for testing
if __name__ == "__main__":
    """
    Minimal examples demonstrating chunking functionality.
    """

    # Example Supreme Court opinion
    sample_scotus = """
    SYLLABUS
    
    The Court held that the Fourth Amendment requires a warrant for
    searching digital devices seized incident to arrest.
    
    JUSTICE ROBERTS delivered the opinion of the Court.
    
    I.
    
    The question presented is whether police may search digital
    information on cell phones without a warrant. We hold that they
    generally may not.
    
    II.
    
    Digital devices differ from physical objects due to their
    immense storage capacity and breadth of private information.
    
    JUSTICE ALITO, concurring.
    
    I agree with the Court's holding but write separately to
    emphasize the need for legislative action.
    """

    print("Testing Supreme Court chunking...")
    print(f"Config: {SCOTUS_CFG}")
    chunks, syllabus = chunk_supreme_court_opinion(sample_scotus)
    print(f"Generated {len(chunks)} chunks")
    if syllabus:
        print(f"Syllabus extracted: {syllabus[:50]}...")
    for i, (chunk_text, metadata) in enumerate(chunks[:3]):
        print(
            f"Chunk {i}: {metadata['section_label']} - {metadata.get('chunk_token_count', 'N/A')} tokens"
        )

    # Example Executive Order
    sample_eo = """
    Executive Order 14999
    
    By the authority vested in me as President, I hereby order:
    
    Section 1. Purpose. This order establishes new requirements
    for federal climate policy.
    
    Sec. 2. Policy. (a) All agencies shall consider climate impacts.
    (b) The EPA shall develop new standards.
        (i) Standards for emissions
        (ii) Standards for efficiency
    
    Sec. 3. Implementation. Agencies shall report progress quarterly.
    """

    print("\nTesting Executive Order chunking...")
    print(f"Config: {EO_CFG}")
    chunks = chunk_executive_order(sample_eo)
    print(f"Generated {len(chunks)} chunks")
    for i, (chunk_text, metadata) in enumerate(chunks):
        print(
            f"Chunk {i}: {metadata['section_label']} - {metadata.get('chunk_token_count', 'N/A')} tokens"
        )
