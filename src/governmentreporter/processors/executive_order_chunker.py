"""
Executive Order Hierarchical Chunking and Metadata Extraction

This module implements sophisticated hierarchical chunking for Presidential Executive
Orders, recognizing the standardized structure of federal regulatory documents and
extracting comprehensive policy metadata for enhanced search and analysis.

Core Components:
    - ExecutiveOrderChunk: Data structure for chunks with regulatory structure
    - ProcessedExecutiveOrderChunk: Complete chunk with policy metadata for database storage
    - ExecutiveOrderChunker: Hierarchical chunking algorithm for regulatory documents
    - ExecutiveOrderMetadataGenerator: AI-powered policy metadata extraction
    - ExecutiveOrderProcessor: Complete processing pipeline coordination

Hierarchical Chunking Strategy:
    Executive Orders follow a standardized regulatory document structure that
    enables sophisticated semantic chunking:
    
    1. **Document Level Structure**:
       - Header Block: Title, EO number, date, president, legal authority
       - Main Content: Policy sections with numbered directives
       - Tail Block: Signature, filing information, billing codes
    
    2. **Section Level Structure**:
       - Major sections (Section 1., Sec. 2., etc.)
       - Subsections with letter designations (a), (b), (c)
       - Numbered items within subsections (1), (2), (3)
    
    3. **Chunk Level Processing**:
       - Paragraph-based chunking within sections
       - Token-aware splitting (target ~300 tokens per chunk)
       - Sentence-level overlap between chunks for context continuity
       - Preservation of regulatory citation and cross-reference integrity

Policy Metadata Extraction:
    Using Google's Gemini 2.5 Flash-Lite API to extract comprehensive policy data:
    - Executive summary and policy objectives
    - Federal agencies impacted or tasked with implementation
    - Legal authorities and statutory citations (USC, CFR)
    - Referenced, amended, or revoked Executive Orders
    - Economic sectors and policy domains affected
    - Implementation requirements and timelines

Processing Pipeline:
    1. **Document Retrieval**: Fetch Executive Order data from Federal Register API
    2. **Structure Analysis**: Identify header, sections, subsections, and tail blocks
    3. **Hierarchical Chunking**: Create chunks preserving regulatory structure
    4. **Policy Analysis**: Extract metadata using AI analysis of policy content
    5. **Citation Processing**: Identify legal authorities and EO cross-references
    6. **Embedding Generation**: Create vector embeddings for semantic search
    7. **Database Storage**: Store in ChromaDB with comprehensive policy metadata

Executive Order Format:
    Presidential Executive Orders follow Title 3 Code of Federal Regulations format:
    - Standardized header with OMB control information
    - "By the authority vested in me..." legal basis statement
    - "It is hereby ordered:" directive introduction
    - Numbered sections with specific policy directives
    - Signature block with date and presidential signature
    - Federal Register filing and billing information

Python Learning Notes:
    - @dataclass for structured data with automatic method generation
    - Regular expressions for complex regulatory text pattern matching
    - Token counting integration with Google's Gemini API
    - Overlap algorithms for maintaining context between chunks
    - AI prompt engineering for policy metadata extraction
    - Exception handling for robust processing of varied document formats
    - File I/O patterns for progress tracking and error logging

Example Usage:
    ```python
    processor = ExecutiveOrderProcessor()
    result = processor.process_and_store(
        document_id="2024-12345",  # Federal Register document number
        collection_name="executive_orders_2024"
    )
    
    print(f"Created {result['chunks_processed']} chunks")
    print(f"Stored {result['chunks_stored']} chunks in database")
    ```

Key Features:
    - Preserves regulatory document structure and hierarchy
    - Extracts comprehensive policy metadata using AI analysis
    - Handles varied Executive Order formats and edge cases
    - Optimizes chunk size for Executive Orders (shorter than court opinions)
    - Provides sentence-level overlap for improved context
    - Integrates with Federal Register API and Google AI services
    - Supports multiple presidencies and administrative styles
"""

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai

from ..apis.federal_register import FederalRegisterClient
from ..database.chroma_client import ChromaDBClient
from ..metadata.gemini_generator import GeminiMetadataGenerator
from ..utils import get_logger
from ..utils.embeddings import GoogleEmbeddingsClient
from .base import BaseDocumentProcessor, ProcessedChunk


@dataclass
class ExecutiveOrderChunk:
    """
    Represents a semantically coherent chunk of Executive Order text with regulatory structure.
    
    This data class captures a single chunk of regulatory text along with its
    structural position within the Executive Order document. The metadata preserves
    the hierarchical structure that is essential for regulatory analysis, compliance
    tracking, and legal citation.
    
    Executive Orders have a more standardized structure than court opinions,
    following federal regulatory document conventions with numbered sections,
    lettered subsections, and standardized header/tail blocks.
    
    Attributes:
        text (str): The actual text content of the chunk. Typically includes
                   complete regulatory directives, policy statements, or
                   administrative instructions. Usually 200-600 words
                   (300-900 tokens) depending on section complexity.
                   
        chunk_type (str): The type of content this chunk represents:
                         - 'header': Title, EO number, authority statement, preamble
                         - 'section': Main policy directive or administrative section
                         - 'tail': Signature block, filing info, billing codes
                         
        section_title (Optional[str]): Full section heading including number and title.
                                      Examples:
                                      - 'Sec. 1. Policy'
                                      - 'Section 3. Agency Coordination'
                                      - 'Sec. 4. Implementation Timeline'
                                      None for header and tail chunks.
                                      
        subsection (Optional[str]): Subsection identifier within major sections.
                                   Examples: '(a)', '(b)', '(i)', '(1)'
                                   Follows federal regulatory citation format.
                                   None if chunk spans multiple subsections.
                                   
        chunk_index (int): Zero-based position of this chunk within the entire
                          Executive Order. Used for maintaining document order
                          and creating unique identifiers. Essential for proper
                          document reconstruction and regulatory citation.
    
    Python Learning Notes:
        - @dataclass automatically generates __init__, __repr__, __eq__ methods
        - Type hints improve code clarity and enable IDE assistance
        - Optional[str] indicates the field can be None for some chunk types
        - Multi-line string in section_title comment shows example formatting
        - Dataclass fields are ordered and used for string representation
    
    Example:
        ```python
        chunk = ExecutiveOrderChunk(
            text="The Secretary of Transportation shall, within 60 days...",
            chunk_type="section",
            section_title="Sec. 2. Agency Implementation Requirements",
            subsection="(a)",
            chunk_index=3
        )
        
        print(f"Chunk {chunk.chunk_index}: {chunk.section_title}")
        print(f"Type: {chunk.chunk_type}, Subsection: {chunk.subsection}")
        ```
    
    Regulatory Structure Context:
        Executive Orders follow standard federal document conventions:
        - Header: Authority statement, background, policy declaration
        - Sections: Numbered policy directives (Sec. 1, Sec. 2, etc.)
        - Subsections: Lettered subdivisions ((a), (b), (c), etc.)
        - Items: Numbered items within subsections ((1), (2), (3), etc.)
        - Tail: Signature, effective date, Federal Register information
    """

    text: str
    chunk_type: str  # 'header', 'section', 'tail'
    section_title: Optional[
        str
    ]  # e.g., 'Sec. 2. Regulatory Reform for Supersonic Flight'
    subsection: Optional[str]  # e.g., '(a)', '(i)'
    chunk_index: int  # Index within the document


@dataclass
class ProcessedExecutiveOrderChunk:
    """
    Complete processed Executive Order chunk ready for database storage with full metadata.
    
    This comprehensive data class combines the chunk content with all available
    metadata from multiple sources: the chunk's regulatory structure, the Federal
    Register API data, and AI-extracted policy metadata from Gemini analysis.
    
    The class represents the final form of a processed chunk before database
    storage, containing everything needed for policy search, regulatory analysis,
    and document reconstruction.
    
    Data Sources:
    1. **Chunk Structure**: From hierarchical chunking of regulatory text
    2. **Federal Register API**: Official government metadata and document info
    3. **AI Policy Analysis**: Policy metadata extracted by Gemini 2.5 Flash-Lite
    
    Attributes:
        # === Chunk Content and Regulatory Structure ===
        text (str): The actual chunk text content
        chunk_type (str): Type of content (header, section, tail)
        section_title (Optional[str]): Full section heading with number
        subsection (Optional[str]): Subsection identifier ((a), (b), etc.)
        chunk_index (int): Position of chunk within the document
        
        # === Federal Register API Metadata ===
        document_number (str): Federal Register document number (e.g., "2024-12345")
        title (str): Full title of the Executive Order
        executive_order_number (str): EO number (e.g., "14123")
        signing_date (str): Date the president signed the order
        president (str): Name of the president who issued the order
        citation (str): Federal Register citation (e.g., "89 FR 12345")
        html_url (str): URL to HTML version on Federal Register
        raw_text_url (str): URL to plain text version
        
        # === Gemini AI Extracted Policy Metadata ===
        summary (str): AI-generated executive summary of the order
        policy_topics (List[str]): Policy areas and subject matter tags
        impacted_agencies (List[str]): Federal agencies affected or tasked
        legal_authorities (List[str]): Legal authorities cited (USC, CFR references)
        executive_orders_referenced (List[str]): Other EOs referenced in text
        executive_orders_revoked (List[str]): EOs explicitly revoked by this order
        executive_orders_amended (List[str]): EOs explicitly amended by this order
        economic_sectors (List[str]): Economic/societal sectors impacted
    
    Python Learning Notes:
        - Comprehensive dataclass with 16+ fields from multiple data sources
        - Mix of primitive types (str, int) and collections (List[str])
        - Optional types handle cases where regulatory structure varies
        - Comments organize fields by data source for code clarity
        - @dataclass handles complex constructor and representation automatically
    
    Database Storage:
        The to_dict() method converts this structure for ChromaDB storage,
        handling JSON serialization of list fields and None value conversion.
    
    Policy Analysis Applications:
        The rich metadata enables sophisticated policy analysis:
        - Track which agencies are mentioned across presidencies
        - Identify patterns in legal authorities cited
        - Analyze EO cross-references and revocation patterns
        - Search by policy topics and economic sectors
        - Monitor implementation timelines and requirements
    
    Example Usage:
        ```python
        processed_chunk = ProcessedExecutiveOrderChunk(
            text="The Secretary of Energy shall establish...",
            chunk_type="section",
            section_title="Sec. 3. Implementation Requirements",
            subsection="(a)",
            chunk_index=5,
            document_number="2024-12345",
            title="Executive Order on Clean Energy",
            executive_order_number="14150",
            president="Biden",
            policy_topics=["energy", "climate", "regulation"],
            impacted_agencies=["DOE", "EPA"],
            # ... other fields
        )
        
        # Convert for database storage
        db_data = processed_chunk.to_dict()
        ```
    
    Regulatory Compliance:
        The comprehensive metadata supports regulatory compliance analysis:
        - Track implementation deadlines and requirements
        - Identify affected regulations and statutes
        - Monitor agency responsibilities and authorities
        - Analyze policy continuity across administrations
    """

    # Chunk content and structure
    text: str
    chunk_type: str
    section_title: Optional[str]
    subsection: Optional[str]
    chunk_index: int

    # API metadata (applies to all chunks of same executive order)
    document_number: str
    title: str
    executive_order_number: str
    signing_date: str
    president: str
    citation: str
    html_url: str
    raw_text_url: str

    # Gemini extracted metadata (applies to all chunks of same executive order)
    summary: str
    policy_topics: List[str]
    impacted_agencies: List[str]
    legal_authorities: List[str]
    executive_orders_referenced: List[str]
    executive_orders_revoked: List[str]
    executive_orders_amended: List[str]
    economic_sectors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = asdict(self)

        # Convert list fields to JSON strings for ChromaDB compatibility
        list_fields = [
            "policy_topics",
            "impacted_agencies",
            "legal_authorities",
            "executive_orders_referenced",
            "executive_orders_revoked",
            "executive_orders_amended",
            "economic_sectors",
        ]

        # Process all fields to ensure ChromaDB compatibility
        processed_data = {}
        for field, value in data.items():
            if value is None:
                # Convert None to empty string
                processed_data[field] = ""
            elif field in list_fields and isinstance(value, list):
                # Convert list to JSON string
                processed_data[field] = json.dumps(value)
            else:
                processed_data[field] = value

        return processed_data


class ExecutiveOrderChunker:
    """Hierarchical chunker for Executive Orders."""

    def __init__(
        self,
        target_chunk_size: int = 300,
        max_chunk_size: int = 400,
        api_key: Optional[str] = None,
    ):
        """Initialize the chunker.

        Args:
            target_chunk_size: Target size for chunks in tokens (≈225 words)
            max_chunk_size: Maximum allowed chunk size in tokens (≈300 words)
            api_key: Google Gemini API key for token counting
        """
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.logger = get_logger(__name__)
        self._token_cache: Dict[str, int] = {}

        # Initialize Google API for token counting
        self.api_key = api_key
        self.model_name = "gemini-2.0-flash-001"  # Model for token counting
        self.model = None
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.model_name)

        # Regex patterns for structure detection
        # Top-level sections (case-insensitive, line-start anchored)
        self.section_pattern = re.compile(
            r"^\s*(Section\s+\d+\.|Sec\.\s*\d+\.)\s*(.*?)(?:\.\s*)?$",
            re.IGNORECASE | re.MULTILINE,
        )

        # Subsections and paragraphs
        self.subsection_pattern = re.compile(r"^\s*\(([a-z])\)\s*", re.MULTILINE)

        self.numbered_item_pattern = re.compile(r"^\s*\((\d+)\)\s*", re.MULTILINE)

        # Header detection (Federal Register format)
        self.header_end_pattern = re.compile(
            r"(it is hereby ordered:?|I hereby order:?)", re.IGNORECASE
        )

        # Tail detection (signature block)
        self.tail_start_patterns = [
            re.compile(r"^\s*\(Presidential Sig\.\)", re.MULTILINE),
            re.compile(r"^\s*THE WHITE HOUSE", re.MULTILINE),
            re.compile(r"^\s*\[FR Doc\.", re.MULTILINE),
            re.compile(r"^\s*Billing code", re.MULTILINE | re.IGNORECASE),
        ]

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using Google's tokenization with limited caching."""
        cache_key = str(hash(text))

        if cache_key not in self._token_cache:
            try:
                if self.model:
                    response = self.model.count_tokens(text)
                    self._token_cache[cache_key] = response.total_tokens
                else:
                    # Fallback to rough estimation (4 chars per token)
                    self._token_cache[cache_key] = len(text) // 4
            except Exception as e:
                # Fallback to rough estimation (4 chars per token)
                self.logger.warning(
                    f"Failed to count tokens using Google API: {e}. Using fallback estimation."
                )
                self._token_cache[cache_key] = len(text) // 4

            # Limit cache size to prevent memory issues
            if len(self._token_cache) > 500:
                # Clear half of the cache
                keys_to_remove = list(self._token_cache.keys())[:250]
                for key in keys_to_remove:
                    del self._token_cache[key]

        return self._token_cache[cache_key]

    def extract_header_block(self, text: str) -> Tuple[str, int]:
        """Extract the header/metadata block from the executive order.

        Returns:
            Tuple of (header_text, end_position)
        """
        # Find where the header ends (usually at "it is hereby ordered:")
        header_match = self.header_end_pattern.search(text)

        if header_match:
            # Include the "it is hereby ordered" phrase in the header
            end_pos = header_match.end()
            header_text = text[:end_pos].strip()
            return header_text, end_pos
        else:
            # If no clear header end, look for first section
            section_match = self.section_pattern.search(text)
            if section_match:
                header_text = text[: section_match.start()].strip()
                return header_text, section_match.start()
            else:
                # Default: take first 500 characters as header
                header_text = text[:500].strip()
                return header_text, 500

    def extract_tail_block(self, text: str) -> Tuple[str, int]:
        """Extract the tail/signature block from the executive order.

        Returns:
            Tuple of (tail_text, start_position)
        """
        tail_start = len(text)

        for pattern in self.tail_start_patterns:
            match = pattern.search(text)
            if match and match.start() < tail_start:
                tail_start = match.start()

        if tail_start < len(text):
            tail_text = text[tail_start:].strip()
            return tail_text, tail_start
        else:
            return "", len(text)

    def detect_sections(self, text: str) -> List[Tuple[int, int, str, str]]:
        """Detect section boundaries in text.

        Returns:
            List of tuples: (start_pos, end_pos, section_id, section_title)
        """
        sections = []

        for match in self.section_pattern.finditer(text):
            section_id = match.group(1).strip()
            section_title = match.group(2).strip() if match.group(2) else ""
            full_title = f"{section_id} {section_title}"
            sections.append((match.start(), match.end(), section_id, full_title))

        return sections

    def split_by_paragraphs(self, text: str) -> List[str]:
        """Split text by paragraphs, preserving structure."""
        # Split by double newlines
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def add_overlap(self, chunks: List[str]) -> List[str]:
        """Add one-sentence overlap between consecutive chunks.

        Args:
            chunks: List of text chunks

        Returns:
            List of chunks with overlap added
        """
        if len(chunks) <= 1:
            return chunks

        overlapped_chunks = []

        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk: no prefix needed
                overlapped_chunks.append(chunk)
            else:
                # Add last sentence of previous chunk as prefix
                prev_chunk = chunks[i - 1]
                # Find last sentence (simple heuristic)
                sentences = re.split(r"(?<=[.!?])\s+", prev_chunk)
                if sentences:
                    last_sentence = sentences[-1]
                    # Only add if it doesn't make chunk too long
                    test_chunk = f"{last_sentence} {chunk}"
                    if self.count_tokens(test_chunk) <= self.max_chunk_size + 50:
                        overlapped_chunks.append(test_chunk)
                    else:
                        overlapped_chunks.append(chunk)
                else:
                    overlapped_chunks.append(chunk)

        return overlapped_chunks

    def chunk_section(
        self, text: str, section_title: Optional[str] = None
    ) -> List[Tuple[str, Optional[str]]]:
        """Chunk a section of text, detecting subsections.

        Returns:
            List of tuples: (chunk_text, subsection_label)
        """
        chunks = []

        # Detect subsections
        subsection_matches = list(self.subsection_pattern.finditer(text))
        numbered_matches = list(self.numbered_item_pattern.finditer(text))

        # Combine and sort all matches
        all_matches = []
        for match in subsection_matches:
            all_matches.append((match.start(), match.group(1), "subsection"))
        for match in numbered_matches:
            all_matches.append((match.start(), match.group(1), "numbered"))

        all_matches.sort(key=lambda x: x[0])

        if not all_matches:
            # No subsections, chunk the entire section
            paragraphs = self.split_by_paragraphs(text)
            current_chunk_parts = []

            for para in paragraphs:
                test_parts = current_chunk_parts + [para]
                test_text = "\n\n".join(test_parts)

                if self.count_tokens(test_text) <= self.max_chunk_size:
                    current_chunk_parts.append(para)
                else:
                    if current_chunk_parts:
                        chunks.append(("\n\n".join(current_chunk_parts), None))
                    current_chunk_parts = [para]

            if current_chunk_parts:
                chunks.append(("\n\n".join(current_chunk_parts), None))
        else:
            # Process subsections
            current_text = ""
            current_subsection = None

            for i, (pos, label, match_type) in enumerate(all_matches):
                # Get text for this subsection
                if i < len(all_matches) - 1:
                    next_pos = all_matches[i + 1][0]
                    subsection_text = text[pos:next_pos]
                else:
                    subsection_text = text[pos:]

                # Check if adding this subsection would exceed limit
                test_text = (
                    current_text + "\n\n" + subsection_text
                    if current_text
                    else subsection_text
                )

                if self.count_tokens(test_text) <= self.max_chunk_size:
                    current_text = test_text
                    if not current_subsection:
                        current_subsection = f"({label})"
                else:
                    # Save current chunk and start new one
                    if current_text:
                        chunks.append((current_text.strip(), current_subsection))
                    current_text = subsection_text
                    current_subsection = f"({label})"

            # Add final chunk
            if current_text:
                chunks.append((current_text.strip(), current_subsection))

        return chunks

    def chunk_executive_order(self, text: str) -> List[ExecutiveOrderChunk]:
        """Hierarchically chunk an Executive Order.

        Args:
            text: The full text of the Executive Order

        Returns:
            List of ExecutiveOrderChunk objects with metadata
        """
        chunks = []
        chunk_index = 0

        # Step 1: Extract header block
        header_text, header_end = self.extract_header_block(text)
        if header_text and self.count_tokens(header_text) > 50:
            # Check if header needs to be split
            if self.count_tokens(header_text) <= self.max_chunk_size:
                chunks.append(
                    ExecutiveOrderChunk(
                        text=header_text,
                        chunk_type="header",
                        section_title=None,
                        subsection=None,
                        chunk_index=chunk_index,
                    )
                )
                chunk_index += 1
            else:
                # Split header into smaller chunks
                header_parts = self.split_by_paragraphs(header_text)
                current_parts = []

                for part in header_parts:
                    test_parts = current_parts + [part]
                    test_text = "\n\n".join(test_parts)

                    if self.count_tokens(test_text) <= self.max_chunk_size:
                        current_parts.append(part)
                    else:
                        if current_parts:
                            chunks.append(
                                ExecutiveOrderChunk(
                                    text="\n\n".join(current_parts),
                                    chunk_type="header",
                                    section_title=None,
                                    subsection=None,
                                    chunk_index=chunk_index,
                                )
                            )
                            chunk_index += 1
                        current_parts = [part]

                if current_parts:
                    chunks.append(
                        ExecutiveOrderChunk(
                            text="\n\n".join(current_parts),
                            chunk_type="header",
                            section_title=None,
                            subsection=None,
                            chunk_index=chunk_index,
                        )
                    )
                    chunk_index += 1

        # Step 2: Extract tail block
        tail_text, tail_start = self.extract_tail_block(text)

        # Step 3: Process main content (between header and tail)
        main_content = text[header_end:tail_start].strip()

        if main_content:
            # Detect sections
            sections = self.detect_sections(main_content)

            if not sections:
                # No sections detected, chunk the entire content
                section_chunks = self.chunk_section(main_content)
                for chunk_text, subsection in section_chunks:
                    chunks.append(
                        ExecutiveOrderChunk(
                            text=chunk_text,
                            chunk_type="section",
                            section_title=None,
                            subsection=subsection,
                            chunk_index=chunk_index,
                        )
                    )
                    chunk_index += 1
            else:
                # Process each section
                for i, (start, end, section_id, section_title) in enumerate(sections):
                    # Get text for this section
                    if i < len(sections) - 1:
                        next_start = sections[i + 1][0]
                        section_text = main_content[start:next_start].strip()
                    else:
                        section_text = main_content[start:].strip()

                    # Skip if section text is too short
                    if len(section_text) < 50:
                        continue

                    # Chunk this section
                    section_chunks = self.chunk_section(section_text, section_title)

                    for chunk_text, subsection in section_chunks:
                        chunks.append(
                            ExecutiveOrderChunk(
                                text=chunk_text,
                                chunk_type="section",
                                section_title=section_title,
                                subsection=subsection,
                                chunk_index=chunk_index,
                            )
                        )
                        chunk_index += 1

        # Step 4: Add tail block if present
        if tail_text and len(tail_text) > 20:
            chunks.append(
                ExecutiveOrderChunk(
                    text=tail_text,
                    chunk_type="tail",
                    section_title=None,
                    subsection=None,
                    chunk_index=chunk_index,
                )
            )

        # Step 5: Add overlap between chunks
        # Extract just the text from chunks
        chunk_texts = [chunk.text for chunk in chunks]
        overlapped_texts = self.add_overlap(chunk_texts)

        # Update chunks with overlapped text
        for i, chunk in enumerate(chunks):
            chunk.text = overlapped_texts[i]

        return chunks


class ExecutiveOrderMetadataGenerator:
    """Generate metadata for Executive Orders using Gemini."""

    def __init__(self, gemini_api_key: Optional[str] = None):
        """Initialize the metadata generator."""
        self.gemini_generator = GeminiMetadataGenerator(gemini_api_key)
        self.logger = get_logger(__name__)

    def extract_executive_order_metadata(self, text: str) -> Dict[str, Any]:
        """Extract comprehensive metadata for Executive Order chunking.

        Args:
            text: The full text of the Executive Order

        Returns:
            Dict containing extracted metadata
        """
        prompt = self._create_metadata_prompt(text)

        try:
            # Use the existing Gemini generator's model
            response = self.gemini_generator.model.generate_content(prompt)

            # Strip markdown code fences if present
            response_text = response.text.strip()
            if response_text.startswith("```json") and response_text.endswith("```"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```") and response_text.endswith("```"):
                response_text = response_text[3:-3].strip()

            metadata = json.loads(response_text)

            # Validate and clean the response
            return self._validate_metadata(metadata)

        except (json.JSONDecodeError, Exception) as e:
            self.logger.warning(f"Failed to extract metadata: {str(e)}")
            # Return minimal metadata on failure
            return {
                "summary": "",
                "policy_topics": [],
                "impacted_agencies": [],
                "legal_authorities": [],
                "executive_orders_referenced": [],
                "executive_orders_revoked": [],
                "executive_orders_amended": [],
                "economic_sectors": [],
                "extraction_error": str(e),
            }

    def _create_metadata_prompt(self, text: str) -> str:
        """Create a prompt for extracting metadata from Executive Orders."""
        return f"""
You are a legal expert analyzing a US Executive Order. Extract the following metadata from the provided text and return it as a JSON object with exactly these fields:

1. "summary": A concise (≤ 60-word) abstract of the entire executive order
2. "policy_topics": Array of topical tags (e.g., ["aviation", "regulatory reform", "environment", "national security"])
3. "impacted_agencies": Array of normalized federal agency codes mentioned or impacted (e.g., ["FAA", "DOT", "EPA", "NASA"])
4. "legal_authorities": Array of U.S. Code or CFR citations in legal bluebook format (e.g., ["49 U.S.C. § 40101", "14 C.F.R. § 25.1"])
5. "executive_orders_referenced": Array of other executive order numbers mentioned (e.g., ["13771", "13777"])
6. "executive_orders_revoked": Array of executive order numbers explicitly revoked (e.g., ["12866"])
7. "executive_orders_amended": Array of executive order numbers explicitly amended (e.g., ["13563"])
8. "economic_sectors": Array of economic/societal sectors impacted (e.g., ["financial", "manufacturing", "energy", "telecommunications"])

Requirements:
- Return ONLY a valid JSON object with these exact field names
- All field names must be in lowercase
- For legal_authorities, use precise bluebook citation format
- For agencies, use standard abbreviations (FAA not "Federal Aviation Administration")
- For executive order numbers, extract just the number (not "Executive Order 13771", just "13771")
- If information cannot be determined, use empty arrays for lists or empty string for summary
- The summary should capture the main purpose and key provisions of the order

Executive Order Text:
{text[:15000]}  # Limit text to avoid token limits

Return the JSON object:
"""

    def _validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the extracted metadata."""
        validated = {
            "summary": metadata.get("summary", ""),
            "policy_topics": metadata.get("policy_topics", []),
            "impacted_agencies": metadata.get("impacted_agencies", []),
            "legal_authorities": metadata.get("legal_authorities", []),
            "executive_orders_referenced": metadata.get(
                "executive_orders_referenced", []
            ),
            "executive_orders_revoked": metadata.get("executive_orders_revoked", []),
            "executive_orders_amended": metadata.get("executive_orders_amended", []),
            "economic_sectors": metadata.get("economic_sectors", []),
        }

        # Ensure all array fields are lists
        for field in [
            "policy_topics",
            "impacted_agencies",
            "legal_authorities",
            "executive_orders_referenced",
            "executive_orders_revoked",
            "executive_orders_amended",
            "economic_sectors",
        ]:
            if not isinstance(validated[field], list):
                validated[field] = []
            else:
                # Clean up strings in arrays
                validated[field] = [
                    str(item).strip()
                    for item in validated[field]
                    if item and str(item).strip()
                ]

        # Clean up summary
        if validated["summary"] and isinstance(validated["summary"], str):
            validated["summary"] = validated["summary"].strip()
        else:
            validated["summary"] = ""

        return validated


class ExecutiveOrderProcessor(BaseDocumentProcessor):
    """Main processor for Executive Orders that combines all components."""

    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        target_chunk_size: int = 300,
        max_chunk_size: int = 400,
        embeddings_client: Optional[GoogleEmbeddingsClient] = None,
        db_client: Optional[ChromaDBClient] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the processor with API clients.

        Args:
            gemini_api_key: Google Gemini API key
            target_chunk_size: Target size for chunks in tokens
            max_chunk_size: Maximum allowed chunk size in tokens
            embeddings_client: Client for generating embeddings
            db_client: Database client for storage
            logger: Logger for verbose output
        """
        super().__init__(embeddings_client, db_client, logger)
        self.federal_register = FederalRegisterClient()
        self.metadata_generator = ExecutiveOrderMetadataGenerator(gemini_api_key)
        self.chunker = ExecutiveOrderChunker(
            target_chunk_size, max_chunk_size, gemini_api_key
        )
        self.logger = logger or get_logger(__name__)

    def process_document(self, document_id: str) -> List[ProcessedChunk]:
        """Process an Executive Order into chunks with embeddings.

        Args:
            document_id: The Federal Register document number

        Returns:
            List of ProcessedChunk objects with embeddings
        """
        order_chunks = self._process_order_chunks(document_id)

        # Convert to ProcessedChunk with embeddings
        processed_chunks = []

        self.logger.debug("=" * 80)
        self.logger.debug("GENERATING EMBEDDINGS")
        self.logger.debug("=" * 80)

        for i, chunk in enumerate(order_chunks):
            embedding = self.embeddings_client.generate_embedding(chunk.text)

            self.logger.debug(
                f"Generated embedding for chunk {i+1}/{len(order_chunks)}"
            )

            # Convert chunk metadata to dict
            metadata = chunk.to_dict()
            # Remove text from metadata to avoid duplication
            metadata.pop("text", None)

            processed_chunk = ProcessedChunk(
                text=chunk.text, embedding=embedding, metadata=metadata, chunk_index=i
            )
            processed_chunks.append(processed_chunk)

        return processed_chunks

    def _process_order_chunks(
        self, document_number: str
    ) -> List[ProcessedExecutiveOrderChunk]:
        """Process an Executive Order into chunks with complete metadata.

        Args:
            document_number: The Federal Register document number

        Returns:
            List of ProcessedExecutiveOrderChunk objects ready for database insertion
        """
        # Step 1: Fetch order data
        order_data = self.federal_register.get_executive_order(document_number)

        # Log raw API response
        self.logger.debug("=" * 80)
        self.logger.debug("RAW API RESPONSE - EXECUTIVE ORDER")
        self.logger.debug("=" * 80)
        self.logger.debug(json.dumps(order_data, indent=2, default=str))

        # Step 2: Extract plain text
        raw_text_url = order_data.get("raw_text_url")
        if not raw_text_url:
            raise ValueError(f"No raw_text_url found for document {document_number}")

        plain_text = self.federal_register.get_executive_order_text(raw_text_url)

        if not plain_text:
            raise ValueError(f"No text content found for document {document_number}")

        self.logger.info(f"Executive Order text length: {len(plain_text)} characters")

        # Step 3: Chunk the text hierarchically
        chunks = self.chunker.chunk_executive_order(plain_text)

        # Log chunk breakdown
        self.logger.debug("=" * 80)
        self.logger.debug("TEXT CHUNKS BREAKDOWN")
        self.logger.debug("=" * 80)
        self.logger.info(f"Total chunks created: {len(chunks)}")

        for i, chunk in enumerate(chunks):
            self.logger.debug(f"\n--- Chunk {i+1}/{len(chunks)} ---")
            self.logger.debug(f"Chunk Type: {chunk.chunk_type}")
            self.logger.debug(f"Section Title: {chunk.section_title or 'N/A'}")
            self.logger.debug(f"Subsection: {chunk.subsection or 'N/A'}")
            self.logger.debug(f"Chunk Index: {chunk.chunk_index}")
            self.logger.debug(f"Text Length: {len(chunk.text)} characters")
            self.logger.debug(f"Text Preview (first 200 chars):")
            self.logger.debug(f"{chunk.text[:200]}...")

        # Step 4: Extract metadata using Gemini
        try:
            eo_metadata = self.metadata_generator.extract_executive_order_metadata(
                plain_text
            )

            # Log Gemini metadata extraction result
            self.logger.debug("=" * 80)
            self.logger.debug("GEMINI METADATA EXTRACTION RESULT")
            self.logger.debug("=" * 80)
            self.logger.debug(json.dumps(eo_metadata, indent=2, default=str))

        except Exception as e:
            self.logger.warning(
                f"Failed to extract metadata for document {document_number}: {str(e)}"
            )
            eo_metadata = {
                "summary": "",
                "policy_topics": [],
                "impacted_agencies": [],
                "legal_authorities": [],
                "executive_orders_referenced": [],
                "executive_orders_revoked": [],
                "executive_orders_amended": [],
                "economic_sectors": [],
            }

        # Step 5: Extract API metadata
        api_metadata = self.federal_register.extract_basic_metadata(order_data)

        # Step 6: Combine all metadata for each chunk
        processed_chunks = []

        for chunk in chunks:
            processed_chunk = ProcessedExecutiveOrderChunk(
                # Chunk content and structure
                text=chunk.text,
                chunk_type=chunk.chunk_type,
                section_title=chunk.section_title,
                subsection=chunk.subsection,
                chunk_index=chunk.chunk_index,
                # API metadata
                document_number=api_metadata["document_number"],
                title=api_metadata["title"],
                executive_order_number=api_metadata["executive_order_number"],
                signing_date=api_metadata["signing_date"],
                president=api_metadata["president"],
                citation=api_metadata["citation"],
                html_url=api_metadata["html_url"],
                raw_text_url=api_metadata["raw_text_url"],
                # Gemini extracted metadata
                summary=eo_metadata["summary"],
                policy_topics=eo_metadata["policy_topics"],
                impacted_agencies=eo_metadata["impacted_agencies"],
                legal_authorities=eo_metadata["legal_authorities"],
                executive_orders_referenced=eo_metadata["executive_orders_referenced"],
                executive_orders_revoked=eo_metadata["executive_orders_revoked"],
                executive_orders_amended=eo_metadata["executive_orders_amended"],
                economic_sectors=eo_metadata["economic_sectors"],
            )

            processed_chunks.append(processed_chunk)

        # Log final processed chunks with metadata
        self.logger.debug("=" * 80)
        self.logger.debug("FINAL PROCESSED CHUNKS FOR DATABASE")
        self.logger.debug("=" * 80)
        self.logger.info(
            f"Total processed chunks ready for storage: {len(processed_chunks)}"
        )

        for i, chunk in enumerate(processed_chunks):
            self.logger.debug(
                f"\n--- Processed Chunk {i+1}/{len(processed_chunks)} ---"
            )
            self.logger.debug(f"Database Fields:")
            chunk_dict = chunk.to_dict()
            for key, value in chunk_dict.items():
                if key == "text":
                    self.logger.debug(f"  {key}: {len(value)} characters")
                elif isinstance(value, str) and len(value) > 100:
                    self.logger.debug(f"  {key}: {value[:100]}... (truncated)")
                else:
                    self.logger.debug(f"  {key}: {value}")

        return processed_chunks
