"""
Section-aware document chunking for Supreme Court opinions and Executive Orders.

This module provides intelligent chunking algorithms that respect document structure
while maintaining semantic coherence. It implements section-aware splitting with
configurable token limits and overlap strategies.

Key Features:
    - Section-aware chunking that preserves document structure
    - Token-based splitting using OpenAI's tiktoken library
    - Minimal overlap only when necessary to preserve sentences
    - Special handling for Supreme Court opinion sections (Syllabus, opinions)
    - Executive Order section detection (Sec. 1, Sec. 2, etc.)
    - Preservation of legal citations and references

Chunking Strategy:
    - Target: 220-320 tokens per chunk
    - Overlap: 12-15% only when splitting mid-sentence
    - No overlap across semantic boundaries (sections)
    - Whole sentence preservation when possible

Python Learning Notes:
    - Regular expressions for pattern matching in text
    - Generator functions for memory-efficient processing
    - Type hints with Tuple for complex return types
    - List comprehensions for efficient data transformation
"""

import re
from typing import Dict, List, Optional, Tuple, Any
import tiktoken

from ..utils import get_logger


logger = get_logger(__name__)

# Token limits for chunking
MIN_TOKENS = 220
TARGET_TOKENS = 270  # Middle of the 220-320 range
MAX_TOKENS = 320
OVERLAP_RATIO = 0.12  # 12% overlap when needed


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """
    Count the number of tokens in text using OpenAI's tiktoken.

    This function uses the same tokenizer as OpenAI's models to ensure
    accurate token counting for chunking purposes. The cl100k_base encoding
    is used by GPT-3.5-turbo and GPT-4 models.

    Args:
        text (str): The text to count tokens for
        encoding_name (str): The tiktoken encoding to use (default: cl100k_base)

    Returns:
        int: Number of tokens in the text

    Python Learning Notes:
        - tiktoken is OpenAI's fast tokenizer library
        - Encoding determines how text is split into tokens
        - Different models may use different encodings
    """
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning("Failed to use tiktoken, falling back to approximation: %s", e)
        # Fallback: approximate 4 characters per token
        return len(text) // 4


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences while preserving legal citations.

    This function intelligently splits text into sentences, handling the
    complexities of legal text including citations, abbreviations, and
    special formatting.

    Legal Text Challenges:
        - Citations like "347 U.S. 483" shouldn't be split
        - Abbreviations like "U.S.C." shouldn't end sentences
        - Section references like "Sec. 2(a)" should stay together

    Args:
        text (str): The text to split into sentences

    Returns:
        List[str]: List of sentences

    Python Learning Notes:
        - Regular expressions handle complex pattern matching
        - Negative lookbehind (?<!) prevents false matches
        - re.split() splits text while preserving delimiters
    """
    # Protect common legal abbreviations from being sentence endings
    abbreviations = [
        r"U\.S\.C\.",
        r"C\.F\.R\.",
        r"U\.S\.",
        r"v\.",
        r"Fed\.",
        r"F\.",
        r"Sec\.",
        r"§",
        r"cl\.",
        r"art\.",
        r"amend\.",
        r"Inc\.",
        r"Corp\.",
        r"Co\.",
        r"Ltd\.",
        r"No\.",
        r"Id\.",
        r"Ibid\.",
        r"et al\.",
        r"e\.g\.",
        r"i\.e\.",
        r"cf\.",
        r"App\.",
        r"Cir\.",
        r"Dist\.",
    ]

    # Build pattern to protect abbreviations
    abbrev_pattern = "|".join(f"(?<={abbr})" for abbr in abbreviations)

    # Split on sentence endings, but not after abbreviations
    # This regex looks for periods, exclamation marks, or question marks
    # followed by whitespace and a capital letter (start of new sentence)
    sentence_pattern = r"(?<=[.!?])\s+(?=[A-Z])"

    # First, protect abbreviations by replacing their periods temporarily
    protected_text = text
    for i, abbr in enumerate(abbreviations):
        protected_text = re.sub(abbr, f"__ABBR_{i}__", protected_text)

    # Split into sentences
    sentences = re.split(sentence_pattern, protected_text)

    # Restore abbreviations
    result_sentences = []
    for sentence in sentences:
        for i, abbr in enumerate(abbreviations):
            sentence = sentence.replace(f"__ABBR_{i}__", abbr.replace("\\", ""))
        if sentence.strip():  # Only add non-empty sentences
            result_sentences.append(sentence.strip())

    return result_sentences if result_sentences else [text]


def chunk_text_with_tokens(
    text: str, section_label: str, max_tokens: int = MAX_TOKENS, overlap_tokens: int = 0
) -> List[Tuple[str, str]]:
    """
    Chunk text respecting token limits and sentence boundaries.

    This function splits text into chunks while:
        - Respecting token limits
        - Preserving sentence boundaries
        - Adding overlap only when necessary
        - Maintaining section labels

    The function tries to pack whole sentences into chunks up to the
    token limit. If a sentence would exceed the limit, it starts a
    new chunk. Overlap is only added when a sentence is split.

    Args:
        text (str): The text to chunk
        section_label (str): Label for this section (e.g., "Syllabus", "Sec. 2")
        max_tokens (int): Maximum tokens per chunk
        overlap_tokens (int): Number of overlap tokens between chunks

    Returns:
        List[Tuple[str, str]]: List of (chunk_text, section_label) tuples

    Python Learning Notes:
        - Tuple return type for structured data
        - List comprehensions for efficient processing
        - Token counting for precise chunking
    """
    chunks = []
    sentences = split_into_sentences(text)

    current_chunk = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)

        # If this sentence alone exceeds max tokens, we need to split it
        if sentence_tokens > max_tokens:
            # First, finish current chunk if it has content
            if current_chunk:
                chunks.append((" ".join(current_chunk), section_label))
                current_chunk = []
                current_tokens = 0

            # Split the long sentence by tokens (rare case)
            words = sentence.split()
            temp_chunk = []
            temp_tokens = 0

            for word in words:
                word_tokens = count_tokens(word + " ")
                if temp_tokens + word_tokens > max_tokens:
                    if temp_chunk:
                        chunks.append((" ".join(temp_chunk), section_label))
                    temp_chunk = (
                        [word]
                        if overlap_tokens == 0
                        else temp_chunk[-overlap_tokens:] + [word]
                    )
                    temp_tokens = count_tokens(" ".join(temp_chunk))
                else:
                    temp_chunk.append(word)
                    temp_tokens += word_tokens

            if temp_chunk:
                chunks.append((" ".join(temp_chunk), section_label))

        # Normal case: sentence fits within limits
        elif current_tokens + sentence_tokens <= max_tokens:
            current_chunk.append(sentence)
            current_tokens += sentence_tokens

        # Need to start a new chunk
        else:
            chunks.append((" ".join(current_chunk), section_label))

            # Add overlap if specified (take last few tokens from previous chunk)
            if overlap_tokens > 0 and current_chunk:
                overlap_text = " ".join(current_chunk)
                overlap_words = overlap_text.split()[-overlap_tokens:]
                current_chunk = overlap_words + [sentence]
                current_tokens = count_tokens(" ".join(current_chunk))
            else:
                current_chunk = [sentence]
                current_tokens = sentence_tokens

    # Add the last chunk if it has content
    if current_chunk:
        chunks.append((" ".join(current_chunk), section_label))

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

    Section Detection:
        The function uses regex patterns to identify section boundaries:
        - Syllabus: ^SYLLABUS or ^Syllabus
        - Majority: "delivered the opinion of the Court" or "Per Curiam"
        - Concurrence/Dissent: "JUSTICE X, concurring/dissenting"

    Special Handling:
        - Syllabus is extracted separately for LLM analysis
        - Roman numeral subheadings (I., II., III.) create boundaries
        - No overlap across section boundaries

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

    Python Learning Notes:
        - re.MULTILINE flag makes ^ match line starts
        - re.IGNORECASE makes pattern case-insensitive
        - Named groups in regex improve readability
        - Tuple unpacking for multiple return values
    """
    chunks = []
    syllabus_text = None

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
        chunk_results = chunk_text_with_tokens(text, "Opinion", TARGET_TOKENS)
        for chunk_text, section_label in chunk_results:
            chunk_metadata = {"section_label": section_label}
            chunks.append((chunk_text, chunk_metadata))
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

                # Chunk the subsection
                chunk_results = chunk_text_with_tokens(
                    subsection_text, subsection_label, TARGET_TOKENS
                )
                for chunk_text, chunk_section_label in chunk_results:
                    chunk_metadata = {"section_label": chunk_section_label}
                    chunks.append((chunk_text, chunk_metadata))
        else:
            # No subsections, chunk the entire section
            chunk_results = chunk_text_with_tokens(
                section_text, section_label, TARGET_TOKENS
            )
            for chunk_text, chunk_section_label in chunk_results:
                chunk_metadata = {"section_label": chunk_section_label}
                chunks.append((chunk_text, chunk_metadata))

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

    Section Detection:
        The function uses regex patterns to identify:
        - Section headers: "Sec. 1.", "Sec. 2(a).", etc.
        - Subsection markers: (a), (b), (c), etc.
        - Subparagraphs: (i), (ii), (iii), etc.

    Chunking Strategy:
        - Preserve section boundaries (no overlap across sections)
        - Prefer breaking at subsection boundaries
        - Maintain whole paragraphs when possible

    Args:
        text (str): Full text of the Executive Order

    Returns:
        List[Tuple[str, Dict]]: List of (chunk_text, metadata) tuples where
            metadata contains section_label

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
            print(f"Text preview: {chunk_text[:100]}...")

    Python Learning Notes:
        - re.finditer() returns an iterator of match objects
        - match.group(1) gets the first captured group
        - List slicing for extracting text portions
    """
    chunks = []

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
            # Chunk the preamble
            chunk_results = chunk_text_with_tokens(
                preamble_text, "Preamble", TARGET_TOKENS
            )
            for chunk_text, section_label in chunk_results:
                chunk_metadata = {"section_label": section_label}
                chunks.append((chunk_text, chunk_metadata))

    # Process each section
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

                        # Chunk the subparagraph
                        chunk_results = chunk_text_with_tokens(
                            subpara_text, subsection_label, TARGET_TOKENS
                        )
                        for chunk_text, chunk_label in chunk_results:
                            chunk_metadata = {"section_label": chunk_label}
                            chunks.append((chunk_text, chunk_metadata))
                else:
                    # No subparagraphs, chunk the subsection
                    chunk_results = chunk_text_with_tokens(
                        subsection_text, subsection_label, TARGET_TOKENS
                    )
                    for chunk_text, chunk_label in chunk_results:
                        chunk_metadata = {"section_label": chunk_label}
                        chunks.append((chunk_text, chunk_metadata))
        else:
            # No subsections, chunk the entire section
            chunk_results = chunk_text_with_tokens(
                section_text, section_label, TARGET_TOKENS
            )
            for chunk_text, chunk_label in chunk_results:
                chunk_metadata = {"section_label": chunk_label}
                chunks.append((chunk_text, chunk_metadata))

    # If no sections were found, treat as single document
    if not chunks:
        logger.warning("No section markers found in Executive Order")
        chunk_results = chunk_text_with_tokens(text, "Executive Order", TARGET_TOKENS)
        for chunk_text, section_label in chunk_results:
            chunk_metadata = {"section_label": section_label}
            chunks.append((chunk_text, chunk_metadata))

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
    chunks, syllabus = chunk_supreme_court_opinion(sample_scotus)
    print(f"Generated {len(chunks)} chunks")
    if syllabus:
        print(f"Syllabus extracted: {syllabus[:50]}...")
    for i, (chunk_text, metadata) in enumerate(chunks[:3]):
        print(f"Chunk {i}: {metadata['section_label']} - {len(chunk_text)} chars")

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
    chunks = chunk_executive_order(sample_eo)
    print(f"Generated {len(chunks)} chunks")
    for i, (chunk_text, metadata) in enumerate(chunks):
        print(f"Chunk {i}: {metadata['section_label']} - {len(chunk_text)} chars")
