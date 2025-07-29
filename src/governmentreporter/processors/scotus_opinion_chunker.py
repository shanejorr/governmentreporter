"""Supreme Court Opinion Hierarchical Chunking and Metadata Extraction."""

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import tiktoken

from ..apis.court_listener import CourtListenerClient
from ..metadata.gemini_generator import GeminiMetadataGenerator
from ..utils.citations import build_bluebook_citation, extract_cited_cases


@dataclass
class OpinionChunk:
    """Represents a chunk of Supreme Court opinion text with metadata."""

    text: str
    opinion_type: str  # 'syllabus', 'majority', 'concurring', 'dissenting'
    justice: Optional[str]  # Name of the justice (for concurring/dissenting opinions)
    section: Optional[str]  # Section identifier (e.g., 'II.A')
    chunk_index: int  # Index within the opinion type


@dataclass
class ProcessedOpinionChunk:
    """Represents a processed chunk with complete metadata for database storage."""

    # Chunk content and structure
    text: str
    opinion_type: str
    justice: Optional[str]
    section: Optional[str]
    chunk_index: int

    # Opinion endpoint metadata
    id: int
    cluster_id: int
    resource_uri: str
    download_url: Optional[str]
    author_str: str
    page_count: Optional[int]
    joined_by_str: str
    type: str
    per_curiam: bool
    date_created: str
    opinions_cited: List[str]

    # Cluster endpoint metadata
    case_name: str
    citation: Optional[str]

    # Gemini extracted metadata
    legal_topics: List[str]
    key_legal_questions: List[str]
    constitutional_provisions: List[str]
    statutes_interpreted: List[str]
    holding: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return asdict(self)


class SCOTUSOpinionChunker:
    """Hierarchical chunker for Supreme Court opinions."""

    def __init__(self, target_chunk_size: int = 600, max_chunk_size: int = 800):
        """Initialize the chunker.

        Args:
            target_chunk_size: Target size for chunks in tokens
            max_chunk_size: Maximum allowed chunk size in tokens
        """
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Regex patterns for opinion detection
        self.majority_pattern = re.compile(
            r"Justice \w+.*?delivered the opinion of the Court",
            re.IGNORECASE | re.MULTILINE,
        )
        self.concurrence_pattern = re.compile(
            r"Justice (\w+).*?concurring", re.IGNORECASE | re.MULTILINE
        )
        self.dissent_pattern = re.compile(
            r"Justice (\w+).*?dissenting", re.IGNORECASE | re.MULTILINE
        )

        # Section patterns
        self.major_section_pattern = re.compile(r"^\s*[IVX]+\.?\s*$", re.MULTILINE)
        self.subsection_pattern = re.compile(r"^\s*[A-Z]\.?\s*$", re.MULTILINE)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.tokenizer.encode(text))

    def split_by_opinion_type(
        self, plain_text: str
    ) -> List[Tuple[str, str, Optional[str]]]:
        """Split text by opinion type.

        Returns:
            List of tuples: (text, opinion_type, justice_name)
        """
        opinions: List[Tuple[str, str, Optional[str]]] = []

        # Find the start of the majority opinion
        majority_match = self.majority_pattern.search(plain_text)

        if majority_match:
            # Extract syllabus (everything before majority opinion)
            syllabus = plain_text[: majority_match.start()].strip()
            if syllabus and len(syllabus) > 100:  # Only include if substantial
                opinions.append((syllabus, "syllabus", None))

            # Start processing from majority opinion
            remaining_text = plain_text[majority_match.start() :]
        else:
            # If no clear majority opinion start, treat entire text as one opinion
            remaining_text = plain_text

        # Find all concurrences and dissents
        concurrence_matches = list(self.concurrence_pattern.finditer(remaining_text))
        dissent_matches = list(self.dissent_pattern.finditer(remaining_text))

        # Combine and sort all matches by position
        all_matches = []
        for match in concurrence_matches:
            all_matches.append(
                (match.start(), match.end(), "concurring", match.group(1))
            )
        for match in dissent_matches:
            all_matches.append(
                (match.start(), match.end(), "dissenting", match.group(1))
            )

        all_matches.sort(key=lambda x: x[0])

        # Extract majority opinion (from start to first concurrence/dissent)
        if all_matches:
            majority_text = remaining_text[: all_matches[0][0]].strip()
        else:
            majority_text = remaining_text.strip()

        if majority_text:
            opinions.append((majority_text, "majority", None))

        # Extract concurrences and dissents
        for i, (start, end, opinion_type, justice) in enumerate(all_matches):
            if i < len(all_matches) - 1:
                # Not the last opinion - extract up to next opinion
                next_start = all_matches[i + 1][0]
                opinion_text = remaining_text[start:next_start].strip()
            else:
                # Last opinion - extract to end
                opinion_text = remaining_text[start:].strip()

            if opinion_text:
                opinions.append((opinion_text, opinion_type, justice))

        return opinions

    def detect_sections(self, text: str) -> List[Tuple[int, int, str]]:
        """Detect section boundaries in text.

        Returns:
            List of tuples: (start_pos, end_pos, section_id)
        """
        sections = []

        # Find major sections (Roman numerals)
        for match in self.major_section_pattern.finditer(text):
            section_id = match.group().strip()
            sections.append((match.start(), match.end(), section_id))

        # Find subsections (Capital letters) - only if we have major sections
        if sections:
            for match in self.subsection_pattern.finditer(text):
                # Only count as subsection if it's not already a major section
                if not any(abs(match.start() - s[0]) < 10 for s in sections):
                    section_id = match.group().strip()
                    sections.append((match.start(), match.end(), section_id))

        # Sort by position
        sections.sort(key=lambda x: x[0])
        return sections

    def split_by_paragraphs(self, text: str) -> List[str]:
        """Split text by paragraphs, preserving paragraph breaks."""
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def chunk_text_within_section(
        self, text: str, section_id: Optional[str] = None
    ) -> List[str]:
        """Chunk text within a section, respecting paragraph boundaries."""
        paragraphs = self.split_by_paragraphs(text)
        if not paragraphs:
            return []

        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # Check if adding this paragraph would exceed max size
            test_chunk = (
                current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            )
            token_count = self.count_tokens(test_chunk)

            if token_count <= self.max_chunk_size:
                current_chunk = test_chunk
            else:
                # If current chunk exists and has reasonable size, save it
                if current_chunk and self.count_tokens(current_chunk) >= 100:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
                else:
                    # If paragraph is too large by itself, we need to split it
                    if self.count_tokens(paragraph) > self.max_chunk_size:
                        # Split paragraph by sentences
                        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
                        temp_chunk = current_chunk

                        for sentence in sentences:
                            test_chunk = (
                                temp_chunk + " " + sentence if temp_chunk else sentence
                            )
                            if self.count_tokens(test_chunk) <= self.max_chunk_size:
                                temp_chunk = test_chunk
                            else:
                                if temp_chunk:
                                    chunks.append(temp_chunk)
                                temp_chunk = sentence

                        current_chunk = temp_chunk
                    else:
                        current_chunk = paragraph

        # Add final chunk if it exists
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def chunk_opinion_by_sections(
        self, text: str, opinion_type: str, justice: Optional[str] = None
    ) -> List[OpinionChunk]:
        """Chunk an opinion by its sections."""
        chunks = []
        sections = self.detect_sections(text)

        if not sections:
            # No sections detected, chunk the entire text
            text_chunks = self.chunk_text_within_section(text)
            for i, chunk_text in enumerate(text_chunks):
                chunks.append(
                    OpinionChunk(
                        text=chunk_text,
                        opinion_type=opinion_type,
                        justice=justice,
                        section=None,
                        chunk_index=i,
                    )
                )
        else:
            # Process each section
            for i, (start, end, section_id) in enumerate(sections):
                # Get text for this section
                if i < len(sections) - 1:
                    next_start = sections[i + 1][0]
                    section_text = text[start:next_start].strip()
                else:
                    section_text = text[start:].strip()

                # Skip if section text is too short
                if len(section_text) < 50:
                    continue

                # Chunk this section
                section_chunks = self.chunk_text_within_section(
                    section_text, section_id
                )
                for j, chunk_text in enumerate(section_chunks):
                    chunks.append(
                        OpinionChunk(
                            text=chunk_text,
                            opinion_type=opinion_type,
                            justice=justice,
                            section=section_id,
                            chunk_index=j,
                        )
                    )

        return chunks

    def chunk_opinion(self, plain_text: str) -> List[OpinionChunk]:
        """Hierarchically chunk a Supreme Court opinion.

        Args:
            plain_text: The full text of the Supreme Court opinion

        Returns:
            List of OpinionChunk objects with metadata
        """
        all_chunks = []

        # Step 1: Split by opinion type
        opinions = self.split_by_opinion_type(plain_text)

        # Step 2: Process each opinion type
        for opinion_text, opinion_type, justice in opinions:
            if opinion_type == "syllabus":
                # Special handling for syllabus - keep as 1-2 chunks
                if self.count_tokens(opinion_text) <= self.max_chunk_size:
                    all_chunks.append(
                        OpinionChunk(
                            text=opinion_text,
                            opinion_type=opinion_type,
                            justice=None,
                            section=None,
                            chunk_index=0,
                        )
                    )
                else:
                    # Split syllabus into 2 chunks at paragraph break
                    paragraphs = self.split_by_paragraphs(opinion_text)
                    mid_point = len(paragraphs) // 2

                    chunk1 = "\n\n".join(paragraphs[:mid_point])
                    chunk2 = "\n\n".join(paragraphs[mid_point:])

                    all_chunks.append(
                        OpinionChunk(
                            text=chunk1,
                            opinion_type=opinion_type,
                            justice=None,
                            section=None,
                            chunk_index=0,
                        )
                    )
                    all_chunks.append(
                        OpinionChunk(
                            text=chunk2,
                            opinion_type=opinion_type,
                            justice=None,
                            section=None,
                            chunk_index=1,
                        )
                    )
            else:
                # Chunk by sections for other opinion types
                opinion_chunks = self.chunk_opinion_by_sections(
                    opinion_text, opinion_type, justice
                )
                all_chunks.extend(opinion_chunks)

        return all_chunks


class SCOTUSOpinionProcessor:
    """Main processor for Supreme Court opinions that combines all components."""

    def __init__(
        self,
        court_listener_token: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        target_chunk_size: int = 600,
        max_chunk_size: int = 800,
    ):
        """Initialize the processor with API clients.

        Args:
            court_listener_token: Court Listener API token
            gemini_api_key: Google Gemini API key
            target_chunk_size: Target size for chunks in tokens
            max_chunk_size: Maximum allowed chunk size in tokens
        """
        self.court_listener = CourtListenerClient(court_listener_token)
        self.gemini_generator = GeminiMetadataGenerator(gemini_api_key)
        self.chunker = SCOTUSOpinionChunker(target_chunk_size, max_chunk_size)

    def process_opinion(self, opinion_id: int) -> List[ProcessedOpinionChunk]:
        """Process a Supreme Court opinion into chunks with complete metadata.

        Args:
            opinion_id: The Court Listener opinion ID

        Returns:
            List of ProcessedOpinionChunk objects ready for database insertion
        """
        # Step 1: Fetch opinion data
        opinion_data = self.court_listener.get_opinion(opinion_id)

        # Step 2: Fetch cluster data
        cluster_url = opinion_data.get("cluster")
        if not cluster_url:
            raise ValueError(f"No cluster URL found for opinion {opinion_id}")

        cluster_data = self.court_listener.get_opinion_cluster(cluster_url)

        # Step 3: Extract plain text
        plain_text = opinion_data.get("plain_text", "")
        if not plain_text:
            raise ValueError(f"No plain text found for opinion {opinion_id}")

        # Step 4: Chunk the text hierarchically
        chunks = self.chunker.chunk_opinion(plain_text)

        # Step 5: Extract legal metadata (only once for the entire opinion)
        legal_metadata = self.gemini_generator.extract_legal_metadata(plain_text)

        # Step 6: Build citation string
        citation = build_bluebook_citation(cluster_data)

        # Step 7: Extract cited cases
        opinions_cited_data = opinion_data.get("opinions_cited", [])
        cited_cases = extract_cited_cases(opinions_cited_data)

        # Step 8: Combine all metadata for each chunk
        processed_chunks = []

        for chunk in chunks:
            processed_chunk = ProcessedOpinionChunk(
                # Chunk content and structure
                text=chunk.text,
                opinion_type=chunk.opinion_type,
                justice=chunk.justice,
                section=chunk.section,
                chunk_index=chunk.chunk_index,
                # Opinion endpoint metadata
                id=opinion_data.get("id") or 0,
                cluster_id=opinion_data.get("cluster_id") or 0,
                resource_uri=opinion_data.get("resource_uri", ""),
                download_url=opinion_data.get("download_url"),
                author_str=opinion_data.get("author_str", ""),
                page_count=opinion_data.get("page_count"),
                joined_by_str=opinion_data.get("joined_by_str", ""),
                type=opinion_data.get("type", ""),
                per_curiam=opinion_data.get("per_curiam", False),
                date_created=self._format_date(opinion_data.get("date_created")),
                opinions_cited=cited_cases,
                # Cluster endpoint metadata
                case_name=cluster_data.get("case_name", ""),
                citation=citation,
                # Gemini extracted metadata
                legal_topics=legal_metadata.get("legal_topics", []),
                key_legal_questions=legal_metadata.get("key_legal_questions", []),
                constitutional_provisions=legal_metadata.get(
                    "constitutional_provisions", []
                ),
                statutes_interpreted=legal_metadata.get("statutes_interpreted", []),
                holding=legal_metadata.get("holding"),
            )

            processed_chunks.append(processed_chunk)

        return processed_chunks

    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date string for consistent storage."""
        if not date_str:
            return ""

        try:
            # Parse ISO format date
            date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return date_obj.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            return date_str or ""
