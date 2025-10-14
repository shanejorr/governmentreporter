"""
Supreme Court opinion chunking with section awareness.

This module provides intelligent chunking specifically for Supreme Court opinions,
respecting the legal structure of SCOTUS documents including:
- Syllabus (official court summary)
- Majority opinions
- Concurring opinions
- Dissenting opinions
- Roman numeral subsections (I., II., III.)

The chunker uses pattern matching to identify opinion types and subsections,
then applies the sliding window chunking algorithm while respecting these
structural boundaries.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from ...utils import get_logger
from .base import SCOTUS_CFG, chunk_text_with_tokens, overlap_tokens

logger = get_logger(__name__)


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
        - Syllabus: Standalone "Syllabus" heading
        - Majority: "Justice X delivered the opinion of the Court" or "Per Curiam" or
          "Opinion of the Court" header
        - Concurrence/Dissent: "Justice X, concurring/dissenting"

    Text Format:
        - Input text is plain text (HTML already stripped by court_listener.py)
        - Patterns match against plain text with normalized whitespace
        - Original HTML with citations was already processed before chunking

    Special Handling:
        - Syllabus is extracted separately for LLM analysis
        - Roman numeral subheadings (I, II, III) create boundaries
        - Overlap is applied within sections but not across boundaries

    Args:
        text (str): Full text of the Supreme Court opinion (plain text, HTML already stripped)

    Returns:
        Tuple containing:
            - List[Tuple[str, Dict]]: List of (chunk_text, metadata) tuples
            - Optional[str]: The Syllabus text if found (for LLM use)

    Example:
        opinion_text = '''
        SYLLABUS
        The Court held that...

        Justice Roberts delivered the opinion of the Court.
        [Main opinion text...]
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

    # Section detection patterns for plain text (HTML already stripped)
    patterns = {
        # Syllabus appears as a heading after case citation info
        # In plain text: "... OCTOBER TERM, 2023 Syllabus CONSUMER FINANCIAL..."
        "syllabus": re.compile(r"\bSyllabus\b", re.IGNORECASE),
        # Majority opinion markers
        # "Justice Thomas delivered the opinion of the Court."
        # Also matches "Per Curiam" or "Opinion of the Court" headers
        "majority": re.compile(
            r"(?:Justice\s+\w+\s+delivered\s+the\s+opinion\s+of\s+the\s+Court\.?|"
            r"Per\s+Curiam\.?)",
            re.IGNORECASE,
        ),
        # Concurring opinions - "Justice X, concurring"
        # May include "with whom Justice Y joins"
        # Uses negative lookahead to exclude "concurring in part and dissenting"
        "concurring": re.compile(
            r"Justice\s+\w+,\s+(?:with\s+whom.*?joins?,\s+)?concurring"
            r"(?!\s+in\s+part\s+and\s+dissenting)",
            re.IGNORECASE,
        ),
        # Dissenting opinions - "Justice X, dissenting"
        # Uses negative lookahead to exclude "dissenting in part"
        "dissenting": re.compile(
            r"Justice\s+\w+,\s+(?:with\s+whom.*?joins?,\s+)?dissenting"
            r"(?!\s+in\s+part)",
            re.IGNORECASE,
        ),
        # Concurring in part and dissenting in part
        "concur_dissent": re.compile(
            r"Justice\s+\w+,\s+(?:with\s+whom.*?joins?,\s+)?concurring\s+"
            r"in\s+part\s+and\s+dissenting\s+in\s+part",
            re.IGNORECASE,
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
            # Skip header line and get content
            syllabus_content = "\n".join(syllabus_lines[1:]).strip()
            if syllabus_content:
                syllabus_text = syllabus_content

        # Handle hierarchical subsections within opinions
        # In plain text after HTML stripping, sections appear inline:
        # - Roman numerals (I, II, III, IV, V, etc.) = Level 1 sections
        # - Capital letters (A, B, C) = Level 2 subsections
        # - Arabic numerals (1, 2, 3) = Level 3 sub-subsections
        #
        # Pattern matches section markers that appear with surrounding whitespace
        # Examples: "...text. I A Page Proof..." or "...reverse. II Under the..."
        # Match Roman numerals or single capital letters with word boundaries
        section_pattern = re.compile(r"\s+([IVX]+|[A-Z])\s+(?=[A-Z]|\w)", re.MULTILINE)
        subsections = list(section_pattern.finditer(section_text))

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

                # Create section label with section marker
                # (Roman numeral, letter, or number)
                section_marker = match.group(1).strip()
                subsection_label = f"{section_label} - Part {section_marker}"

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
