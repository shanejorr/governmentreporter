"""
Pydantic schemas for document metadata in GovernmentReporter RAG system.

This module defines the metadata schemas for Supreme Court opinions and Executive Orders
using Pydantic for validation and type safety. These schemas ensure consistent metadata
structure across document types for improved retrieval and filtering capabilities.

The schemas are designed to support:
    - Lay user understanding of legal documents
    - Consistent field naming across document types
    - Rich metadata for filtering and faceted search
    - LLM-generated fields for enhanced retrieval
    - Section-aware chunking with chunk-level metadata

Python Learning Notes:
    - Pydantic validates data at runtime and provides type hints
    - Optional fields use Optional[Type] or default values
    - List fields can be validated for content and length
    - Field(...) allows adding descriptions and constraints
    - BaseModel provides automatic JSON serialization/deserialization
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class SharedMetadata(BaseModel):
    """
    Shared metadata fields present on every chunk across all document types.

    This base class contains fields that are common to both Supreme Court opinions
    and Executive Orders, ensuring consistent retrieval and filtering capabilities
    across different document types.

    The metadata is designed to support:
        - Basic document identification and retrieval
        - Date-based filtering and sorting
        - Source tracking for provenance
        - Natural language search through LLM-generated summaries

    Python Learning Notes:
        - Inheritance allows subclasses to extend this base schema
        - Field descriptions are used for documentation and validation messages
        - Optional fields can be None but required fields must have values
    """

    # Document/API-extracted fields
    document_id: str = Field(
        description="Stable identifier from the source API (e.g., CL opinion ID or FR document number)"
    )
    title: str = Field(
        description="Human-readable document name (case name for SCOTUS, title for EOs)"
    )
    publication_date: str = Field(
        description="Date in YYYY-MM-DD format when the document was published/filed"
    )
    year: int = Field(
        description="Four-digit year extracted from publication_date for efficient filtering"
    )
    source: str = Field(
        description="Data source identifier: 'CourtListener' or 'Federal Register'"
    )
    type: str = Field(
        description="Document type: 'Supreme Court Opinion' or 'Executive Order'"
    )
    url: str = Field(description="Canonical web URL for the full document")

    # LLM-generated fields (populated by GPT-5-nano)
    document_summary: str = Field(
        description="Document-level technical summary (1-2 dense sentences) optimized for RAG retrieval and LLM comprehension"
    )
    constitution_cited: List[str] = Field(
        default_factory=list,
        description="U.S. Constitution citations in Bluebook format (e.g., 'U.S. Const. amend. XIV, § 1')",
    )
    federal_statutes_cited: List[str] = Field(
        default_factory=list,
        description="U.S. Code citations in Bluebook format (e.g., '8 U.S.C. § 1182(f)')",
    )
    federal_regulations_cited: List[str] = Field(
        default_factory=list,
        description="CFR citations in Bluebook format (e.g., '14 C.F.R. § 91.819')",
    )
    cases_cited: List[str] = Field(
        default_factory=list,
        description="Case citations in Bluebook format (e.g., 'Brown v. Bd. of Educ., 347 U.S. 483 (1954)')",
    )
    topics_or_policy_areas: List[str] = Field(
        default_factory=list,
        min_length=5,
        max_length=8,
        description="Plain-language tags for policy domains and legal areas (5-8 tags)",
    )


class ChunkMetadata(BaseModel):
    """
    Chunk-specific metadata added to each text chunk.

    This metadata helps track the position and context of each chunk within
    the source document, enabling reconstruction of document structure and
    providing context for retrieval.

    Python Learning Notes:
        - This is typically combined with document-level metadata
        - chunk_id should be unique across the entire collection
        - section_label provides semantic context for the chunk
    """

    chunk_id: str = Field(
        description="Unique identifier for this specific chunk (e.g., 'doc123_chunk_0')"
    )
    chunk_index: int = Field(
        description="Zero-based index of this chunk within the document"
    )
    section_label: str = Field(
        description="Section identifier (e.g., 'Syllabus', 'Majority Opinion', 'Sec. 2')"
    )


class SupremeCourtMetadata(SharedMetadata):
    """
    Metadata specific to Supreme Court opinions from CourtListener.

    Extends the shared metadata with fields specific to judicial opinions,
    including case details, holdings, and opinion types. These fields support
    specialized retrieval for legal research and lay user understanding.

    The Supreme Court-specific fields enable:
        - Distinction between majority, concurring, and dissenting opinions
        - Clear understanding of case outcomes and holdings
        - Tracking of judicial authorship
        - Plain-language explanations of complex legal concepts

    Python Learning Notes:
        - Inherits all fields from SharedMetadata
        - Additional fields are specific to court opinions
        - Optional fields handle cases where data may not be available
    """

    # Document/API-extracted fields specific to SCOTUS
    case_name: str = Field(
        description="Full case name from CourtListener (e.g., 'Brown v. Board of Education')"
    )
    case_name_short: Optional[str] = Field(
        default=None,
        description="Shortened case name (e.g., 'Miranda')",
    )
    docket_number: Optional[str] = Field(
        default=None,
        description="Docket number for the case",
    )
    opinion_type: Optional[str] = Field(
        default=None,
        description="Type of opinion: 'majority', 'concurrence', or 'dissent'",
    )
    majority_author: Optional[str] = Field(
        default=None,
        description="Justice who authored the majority opinion",
    )
    vote_majority: Optional[int] = Field(
        default=None,
        description="Number of justices in the majority",
    )
    vote_minority: Optional[int] = Field(
        default=None,
        description="Number of justices in the minority",
    )
    argued_date: Optional[str] = Field(
        default=None,
        description="Date the case was argued (YYYY-MM-DD format)",
    )
    decided_date: Optional[str] = Field(
        default=None,
        description="Date the case was decided (YYYY-MM-DD format)",
    )

    # LLM-generated fields specific to SCOTUS
    holding_plain: str = Field(
        description="One-sentence statement of the Court's holding in plain English"
    )
    outcome_simple: str = Field(
        description="Simple outcome description (e.g., 'Petitioner won', 'Vacated & remanded')"
    )
    issue_plain: str = Field(
        description="Central question addressed by the Court in plain English"
    )
    reasoning: str = Field(
        description="Court's reasoning in plain English (one paragraph maximum)"
    )


class ExecutiveOrderMetadata(SharedMetadata):
    """
    Metadata specific to Executive Orders from the Federal Register.

    Extends the shared metadata with fields specific to presidential executive
    orders, including order numbers and affected agencies. These fields support
    retrieval for policy research and regulatory compliance.

    The Executive Order-specific fields enable:
        - Tracking by presidential order number
        - Identification of impacted federal agencies
        - Understanding of regulatory changes
        - Policy area classification

    Python Learning Notes:
        - Inherits all fields from SharedMetadata
        - executive_order_number is the primary identifier used in citations
        - agencies_or_entities helps with regulatory research
    """

    # Document/API-extracted fields specific to Executive Orders
    executive_order_number: Optional[str] = Field(
        default=None,
        description="Presidential Executive Order number (e.g., '14304')",
    )
    president: Optional[str] = Field(
        default=None,
        description="Name of the president who signed the order",
    )
    signing_date: Optional[str] = Field(
        default=None,
        description="Date the order was signed (YYYY-MM-DD format)",
    )
    effective_date: Optional[str] = Field(
        default=None,
        description="Date the order becomes effective (YYYY-MM-DD format)",
    )
    federal_register_number: Optional[str] = Field(
        default=None,
        description="Federal Register document number",
    )

    # LLM-generated fields specific to Executive Orders
    plain_summary: str = Field(description="Brief plain-language summary of the order")
    action_plain: str = Field(
        description="Plain-language description of the primary action or directive"
    )
    impact_simple: str = Field(description="Simple description of the order's impact")
    implementation_requirements: str = Field(
        description="Key implementation requirements in plain language"
    )
    agencies_or_entities: List[str] = Field(
        default_factory=list,
        description="Federal agencies or entities materially affected by the order",
    )
    revokes: List[str] = Field(
        default_factory=list,
        description="List of prior executive orders revoked by this order",
    )


class QdrantPayload(BaseModel):
    """
    Complete payload structure for Qdrant vector database storage.

    This schema represents the final structure that gets stored in Qdrant.
    It combines the chunk text with all relevant metadata for retrieval.

    The payload structure is designed to work with QdrantClient's Document dataclass.
    After adding embeddings, these payloads can be converted to Document objects
    for storage. The metadata gets stored in Qdrant's payload for filtering and retrieval.

    Usage:
        payload = QdrantPayload(
            id="scotus_2024_001_chunk_0",
            text="The Court held that...",
            embedding=[],  # Will be filled after generation
            metadata={...}  # All metadata fields as a dictionary
        )

    Python Learning Notes:
        - Generic dict type for metadata allows flexibility
        - The id field becomes the unique identifier in Qdrant
        - text field is used for display and context
        - metadata dict gets stored as Qdrant payload fields
    """

    id: str = Field(
        description="Unique identifier for the chunk (used as Qdrant point ID)"
    )
    text: str = Field(description="The actual text content of the chunk")
    embedding: list = Field(
        default_factory=list,
        description="Vector embedding (initially empty, filled after generation)",
    )
    metadata: dict = Field(
        description="Combined metadata including document-level, LLM-generated, and chunk-level fields"
    )


# Type aliases for clearer function signatures
SupremeCourtChunkMetadata = dict  # Combination of SupremeCourtMetadata + ChunkMetadata
ExecutiveOrderChunkMetadata = (
    dict  # Combination of ExecutiveOrderMetadata + ChunkMetadata
)


def create_scotus_chunk_metadata(
    doc_metadata: SupremeCourtMetadata, chunk_metadata: ChunkMetadata
) -> dict:
    """
    Combine Supreme Court document metadata with chunk-specific metadata.

    This helper function merges document-level metadata with chunk-specific
    metadata to create the complete metadata dictionary for a single chunk.
    This combined metadata is what gets stored in Qdrant for each chunk.

    The function ensures all metadata is available at the chunk level,
    enabling consistent filtering and retrieval regardless of which chunk
    is returned by the vector search.

    Args:
        doc_metadata: Document-level Supreme Court opinion metadata
        chunk_metadata: Chunk-specific metadata (id, index, section)

    Returns:
        dict: Combined metadata ready for Qdrant storage

    Example:
        doc_meta = SupremeCourtMetadata(
            document_id="12345",
            title="Brown v. Board of Education",
            ...
        )
        chunk_meta = ChunkMetadata(
            chunk_id="12345_chunk_0",
            chunk_index=0,
            section_label="Syllabus"
        )
        combined = create_scotus_chunk_metadata(doc_meta, chunk_meta)
    """
    return {**doc_metadata.model_dump(), **chunk_metadata.model_dump()}


def create_eo_chunk_metadata(
    doc_metadata: ExecutiveOrderMetadata, chunk_metadata: ChunkMetadata
) -> dict:
    """
    Combine Executive Order document metadata with chunk-specific metadata.

    This helper function merges document-level metadata with chunk-specific
    metadata to create the complete metadata dictionary for a single chunk.
    This combined metadata is what gets stored in Qdrant for each chunk.

    The function ensures all metadata is available at the chunk level,
    enabling consistent filtering and retrieval regardless of which chunk
    is returned by the vector search.

    Args:
        doc_metadata: Document-level Executive Order metadata
        chunk_metadata: Chunk-specific metadata (id, index, section)

    Returns:
        dict: Combined metadata ready for Qdrant storage

    Example:
        doc_meta = ExecutiveOrderMetadata(
            document_id="2025-10800",
            title="Leading the World in Supersonic Flight",
            ...
        )
        chunk_meta = ChunkMetadata(
            chunk_id="2025-10800_chunk_0",
            chunk_index=0,
            section_label="Preamble"
        )
        combined = create_eo_chunk_metadata(doc_meta, chunk_meta)
    """
    return {**doc_metadata.model_dump(), **chunk_metadata.model_dump()}
