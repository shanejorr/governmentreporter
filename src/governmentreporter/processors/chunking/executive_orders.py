"""
Executive Order chunking with section awareness.

This module provides intelligent chunking specifically for Executive Orders,
respecting the regulatory structure of EO documents including:
- Preamble (introductory text)
- Numbered sections (Sec. 1., Sec. 2., etc.)
- Lettered subsections ((a), (b), (c), etc.)
- Roman numeral subparagraphs ((i), (ii), (iii), etc.)

Important: NEVER creates overlap across section boundaries. Each section
is chunked independently to maintain legal coherence.
"""

import re
from typing import Any, Dict, List, Tuple

from ...utils import get_logger
from .base import EO_CFG, chunk_text_with_tokens, overlap_tokens

logger = get_logger(__name__)


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
