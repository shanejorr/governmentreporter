"""
Main orchestration module for building Qdrant payloads from government documents.

This module provides the primary interface for transforming Document objects from
government API clients into chunk payloads ready for Qdrant storage. It orchestrates
the metadata extraction, chunking, and payload assembly process.

The module integrates:
    - Document objects from CourtListener and Federal Register APIs
    - LLM-based metadata extraction using GPT-5-nano
    - Section-aware chunking algorithms
    - Pydantic schemas for validation
    - Qdrant payload formatting

Process Flow:
    1. Receive Document from API client
    2. Extract document-level metadata from API fields
    3. Detect document type and route to appropriate chunker
    4. Generate LLM fields using GPT-5-nano
    5. Combine metadata at chunk level
    6. Return list of Qdrant-ready payloads

Python Learning Notes:
    - Pure functions with no side effects
    - Type hints for clear interfaces
    - Exception handling for robustness
    - Defensive programming with validation
"""

import re
from datetime import datetime
from typing import Any, Dict, List

from ..apis.base import Document
from ..utils import get_logger
from ..utils.citations import build_bluebook_citation
from .chunking import chunk_executive_order, chunk_supreme_court_opinion
from .llm_extraction import generate_eo_llm_fields, generate_scotus_llm_fields
from .schema import (ChunkMetadata, ExecutiveOrderMetadata, QdrantPayload,
                     SupremeCourtMetadata)

logger = get_logger(__name__)


def extract_year_from_date(date_str: str) -> int:
    """
    Extract the year from a date string in YYYY-MM-DD format.

    This helper function safely extracts the year from standardized
    date strings, with fallback to current year on parse errors.

    Args:
        date_str (str): Date in YYYY-MM-DD format

    Returns:
        int: Four-digit year

    Python Learning Notes:
        - String slicing for simple extraction
        - Exception handling for robustness
        - datetime.now() for current date
    """
    try:
        # Try simple extraction first (faster)
        if len(date_str) >= 4 and date_str[4] in ["-", "/"]:
            return int(date_str[:4])
        # Fallback to datetime parsing
        return datetime.strptime(date_str, "%Y-%m-%d").year
    except (ValueError, AttributeError):
        logger.warning("Failed to parse date '%s', using current year", date_str)
        return datetime.now().year


def normalize_scotus_metadata(doc: Document) -> Dict[str, Any]:
    """
    Extract and normalize Supreme Court opinion metadata from Document.

    This function maps Document fields and metadata to the standardized
    schema for Supreme Court opinions. It handles the complexity of
    CourtListener's data structure and ensures consistent field naming.

    Normalization includes:
        - Extracting case name from metadata
        - Building Bluebook citations
        - Standardizing dates
        - Setting document type and source

    Args:
        doc (Document): Document object from CourtListenerClient

    Returns:
        Dict[str, Any]: Normalized metadata matching SupremeCourtMetadata fields

    Python Learning Notes:
        - Dictionary get() method with defaults
        - Nested dictionary access with safety
        - Type preservation during normalization
    """
    metadata = doc.metadata or {}

    # Extract case name (may be in metadata from cluster)
    case_name = metadata.get("case_name", doc.title)

    # Build Bluebook citation - multiple strategies
    citation_bluebook = metadata.get("citation")  # May already be built

    if not citation_bluebook:
        if "cluster_data" in metadata:
            citation_bluebook = build_bluebook_citation(metadata["cluster_data"])
        elif "citations" in metadata:
            # Try to build from citations list
            citations = metadata.get("citations", [])
            if citations and isinstance(citations, list):
                # Find official U.S. reporter citation
                for cite in citations:
                    if isinstance(cite, dict) and cite.get("type") == 1:
                        volume = cite.get("volume", "")
                        reporter = cite.get("reporter", "")
                        page = cite.get("page", "")
                        if volume and reporter and page:
                            year = extract_year_from_date(doc.date)
                            citation_bluebook = f"{volume} {reporter} {page} ({year})"
                            break

    # Extract opinion type if available
    opinion_type = metadata.get("type", None)
    if opinion_type:
        # Map CourtListener types to our schema
        type_mapping = {
            "010combined": "majority",
            "020lead": "majority",
            "030concurrence": "concurrence",
            "040dissent": "dissent",
            "050concurrence_dissent": "concurrence_dissent",
        }
        opinion_type = type_mapping.get(opinion_type, opinion_type)

    # Use absolute_url if available, otherwise download_url
    url = doc.url or metadata.get("absolute_url", metadata.get("download_url", ""))

    return {
        "document_id": doc.id,
        "title": doc.title,
        "publication_date": doc.date,
        "year": extract_year_from_date(doc.date),
        "source": doc.source,  # Should be "CourtListener"
        "type": doc.type,  # Should be "Supreme Court Opinion"
        "url": url,
        "citation_bluebook": citation_bluebook,
        "case_name": case_name,
        "opinion_type": opinion_type,
        "judges": metadata.get("judges", ""),
        "author_str": metadata.get("author_str", ""),
        "per_curiam": metadata.get("per_curiam", False),
        "joined_by_str": metadata.get("joined_by_str", ""),
    }


def normalize_eo_metadata(doc: Document) -> Dict[str, Any]:
    """
    Extract and normalize Executive Order metadata from Document.

    This function maps Document fields and metadata to the standardized
    schema for Executive Orders. It handles Federal Register API data
    structure and ensures consistent field naming.

    Normalization includes:
        - Extracting EO number
        - Building FR citation
        - Standardizing dates
        - Setting document type and source

    Args:
        doc (Document): Document object from FederalRegisterClient

    Returns:
        Dict[str, Any]: Normalized metadata matching ExecutiveOrderMetadata fields

    Python Learning Notes:
        - Safe dictionary access with get()
        - String formatting for citations
        - Conditional logic for optional fields
    """
    metadata = doc.metadata or {}

    # Extract EO number - check multiple possible field names
    eo_number = (
        metadata.get("executive_order_number")
        or metadata.get("presidential_document_number")
        or ""
    )

    # Build Federal Register citation
    citation_bluebook = metadata.get("citation")
    if not citation_bluebook:
        # Try to build from volume and page
        volume = metadata.get("volume")
        start_page = metadata.get("start_page")
        if volume and start_page:
            citation_bluebook = f"{volume} FR {start_page}"

    # Get the HTML URL (preferred) or PDF URL
    url = doc.url or metadata.get("html_url", metadata.get("pdf_url", ""))

    # Extract president info if available
    president_info = metadata.get("president", "")
    if isinstance(president_info, dict):
        president_name = president_info.get("name", "")
    else:
        president_name = str(president_info) if president_info else ""

    return {
        "document_id": doc.id,
        "title": doc.title,
        "publication_date": doc.date,
        "year": extract_year_from_date(doc.date),
        "source": doc.source,  # Should be "Federal Register"
        "type": doc.type,  # Should be "Executive Order"
        "url": url,
        "citation_bluebook": citation_bluebook,
        "eo_number": eo_number,
        "president": president_name,
        "agencies": metadata.get("agencies", []),
        "signing_date": metadata.get("signing_date", doc.date),
    }


def build_payloads_from_document(doc: Document) -> List[Dict[str, Any]]:
    """
    Transform a Document into Qdrant-ready chunk payloads.

    This is the main orchestration function that coordinates the entire
    document processing pipeline. It detects document type, extracts metadata,
    performs chunking, generates LLM fields, and assembles final payloads.

    The function is pure (no side effects) and handles both Supreme Court
    opinions and Executive Orders, automatically detecting type from the
    Document's type and source fields.

    Process:
        1. Validate input document
        2. Detect document type from doc.type/doc.source
        3. Extract and normalize API metadata
        4. Route to appropriate chunker
        5. Generate LLM metadata fields
        6. Combine all metadata at chunk level
        7. Format as Qdrant payloads

    Args:
        doc (Document): Document object from a government API client
                       Must have non-empty content and valid type/source

    Returns:
        List[Dict[str, Any]]: List of chunk payloads ready for conversion to
                             QdrantClient Document objects. Each dict contains:
                             - id: Unique chunk identifier
                             - text: Chunk text content
                             - embedding: Empty list (to be filled by caller after generation)
                             - metadata: Combined metadata dictionary

    Raises:
        ValueError: If document is invalid (empty content, unknown type)

    Example:
        from governmentreporter.apis.court_listener import CourtListenerClient

        # Get a document from the API
        client = CourtListenerClient()
        doc = client.get_document("12345")

        # Build payloads for Qdrant
        payloads = build_payloads_from_document(doc)

        # Ready for Qdrant storage
        for payload in payloads:
            print(f"Chunk ID: {payload['id']}")
            print(f"Text preview: {payload['text'][:100]}...")
            print(f"Metadata keys: {payload['metadata'].keys()}")

        # Pass to Qdrant (with embeddings)
        # from governmentreporter.database.qdrant import QdrantClient, Document
        # client = QdrantClient(db_path="./qdrant_db")
        #
        # # Convert payloads to Document objects with embeddings
        # documents = []
        # for payload, embedding in zip(payloads, embeddings):
        #     doc = Document(
        #         id=payload["id"],
        #         text=payload["text"],
        #         embedding=embedding,
        #         metadata=payload["metadata"]
        #     )
        #     documents.append(doc)
        #
        # # Store documents in batch
        # success_count, failed_ids = client.store_documents_batch(documents, "scotus_opinions")

    Python Learning Notes:
        - Early validation with clear error messages
        - Pattern matching for document type detection
        - List comprehension for efficient processing
        - Dictionary merging with ** operator
        - Exception handling with logging
    """
    # Validate input
    if not doc:
        raise ValueError("Document cannot be None")

    if not doc.content:
        raise ValueError(f"Document {doc.id} has no content to process")

    # Detect document type - handle both with and without space in source names
    is_scotus = (
        doc.type == "Supreme Court Opinion"
        or doc.source == "CourtListener"
        or "scotus" in doc.type.lower()
        or "court" in doc.source.lower()
    )

    is_eo = (
        doc.type == "Executive Order"
        or doc.source == "FederalRegister"
        or doc.source == "Federal Register"  # Handle both formats
        or "executive" in doc.type.lower()
        or "federal" in doc.source.lower()
    )

    if not (is_scotus or is_eo):
        raise ValueError(f"Unknown document type: {doc.type} from {doc.source}")

    logger.info("Processing document %s (%s)", doc.id, doc.type)

    try:
        if is_scotus:
            # Process Supreme Court Opinion

            # 1. Extract document-level metadata
            doc_metadata = normalize_scotus_metadata(doc)

            # 2. Chunk the opinion (with section detection)
            chunks, syllabus = chunk_supreme_court_opinion(doc.content)

            if not chunks:
                logger.warning("No chunks generated for document %s", doc.id)
                return []

            # 3. Generate LLM metadata fields (optional - non-blocking)
            llm_extraction_successful = True
            try:
                llm_fields = generate_scotus_llm_fields(doc.content, syllabus)
            except Exception as e:
                logger.warning("Failed to generate LLM fields for %s: %s", doc.id, str(e))
                llm_extraction_successful = False

                # Use standardized fallback messages
                llm_fields = {
                    "plain_language_summary": "Unable to generate summary.",
                    "constitution_cited": [],
                    "federal_statutes_cited": [],
                    "federal_regulations_cited": [],
                    "cases_cited": [],
                    "topics_or_policy_areas": ["supreme court", "legal opinion", "court decision"],
                    "holding_plain": "Unable to extract holding.",
                    "outcome_simple": "Unable to extract outcome.",
                    "issue_plain": "Unable to extract issue.",
                    "reasoning": "Unable to extract reasoning.",
                }

            # 4. Merge document and LLM metadata
            full_doc_metadata = {**doc_metadata, **llm_fields}

            # Add failure tracking if LLM extraction failed
            if not llm_extraction_successful:
                full_doc_metadata["llm_extraction_failed"] = True
                full_doc_metadata["requires_reprocessing"] = True

            # 5. Create payload for each chunk
            payloads = []
            for chunk_index, (chunk_text, chunk_meta) in enumerate(chunks):
                # Generate unique chunk ID
                chunk_id = f"{doc.id}_chunk_{chunk_index}"

                # Create chunk metadata
                chunk_metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    section_label=chunk_meta.get("section_label", "Unknown"),
                )

                # Combine all metadata
                combined_metadata = {**full_doc_metadata, **chunk_metadata.model_dump()}

                # Create Qdrant Document-compatible payload
                # Note: embedding will be added by the caller after generation
                payload = {
                    "id": chunk_id,
                    "text": chunk_text,
                    "embedding": [],  # Placeholder - will be filled by caller
                    "metadata": combined_metadata,
                }

                payloads.append(payload)

            logger.info(
                "Generated %d payloads for SCOTUS opinion %s", len(payloads), doc.id
            )
            return payloads

        else:  # Executive Order
            # 1. Extract document-level metadata
            doc_metadata = normalize_eo_metadata(doc)

            # 2. Chunk the executive order
            chunks = chunk_executive_order(doc.content)

            if not chunks:
                logger.warning("No chunks generated for document %s", doc.id)
                return []

            # 3. Generate LLM metadata fields (optional - non-blocking)
            llm_extraction_successful = True
            try:
                llm_fields = generate_eo_llm_fields(doc.content)
            except Exception as e:
                logger.warning("Failed to generate LLM fields for %s: %s", doc.id, str(e))
                llm_extraction_successful = False

                # Use standardized fallback messages
                llm_fields = {
                    "plain_language_summary": "Unable to generate summary.",
                    "agencies_impacted": [],
                    "constitution_cited": [],
                    "federal_statutes_cited": [],
                    "federal_regulations_cited": [],
                    "cases_cited": [],
                    "topics_or_policy_areas": ["executive order", "federal policy", "presidential action"],
                }

            # 4. Merge document and LLM metadata
            full_doc_metadata = {**doc_metadata, **llm_fields}

            # Add failure tracking if LLM extraction failed
            if not llm_extraction_successful:
                full_doc_metadata["llm_extraction_failed"] = True
                full_doc_metadata["requires_reprocessing"] = True

            # 5. Create payload for each chunk
            payloads = []
            for chunk_index, (chunk_text, chunk_meta) in enumerate(chunks):
                # Generate unique chunk ID
                chunk_id = f"{doc.id}_chunk_{chunk_index}"

                # Create chunk metadata
                chunk_metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    chunk_index=chunk_index,
                    section_label=chunk_meta.get("section_label", "Unknown"),
                )

                # Combine all metadata
                combined_metadata = {**full_doc_metadata, **chunk_metadata.model_dump()}

                # Create Qdrant Document-compatible payload
                # Note: embedding will be added by the caller after generation
                payload = {
                    "id": chunk_id,
                    "text": chunk_text,
                    "embedding": [],  # Placeholder - will be filled by caller
                    "metadata": combined_metadata,
                }

                payloads.append(payload)

            logger.info(
                "Generated %d payloads for Executive Order %s", len(payloads), doc.id
            )
            return payloads

    except Exception as e:
        logger.error("Failed to build payloads for document %s: %s", doc.id, str(e))
        raise


def validate_payload(payload: Dict[str, Any]) -> bool:
    """
    Validate that a payload meets Qdrant requirements.

    This helper function ensures payloads have the required structure
    and fields for QdrantClient's Document dataclass.

    Validation checks:
        - Required fields: id, text, metadata
        - Non-empty id and text
        - Metadata is a dictionary
        - All metadata values are JSON-serializable

    Args:
        payload (Dict[str, Any]): Payload to validate

    Returns:
        bool: True if valid, False otherwise

    Python Learning Notes:
        - isinstance() for type checking
        - all() for checking multiple conditions
        - Dictionary iteration with items()
    """
    # Check required fields
    if not all(key in payload for key in ["id", "text", "embedding", "metadata"]):
        return False

    # Check id and text are non-empty strings
    if not isinstance(payload["id"], str) or not payload["id"]:
        return False

    if not isinstance(payload["text"], str) or not payload["text"]:
        return False

    # Check metadata is a dictionary
    if not isinstance(payload["metadata"], dict):
        return False

    # Check embedding is a list (can be empty initially)
    if not isinstance(payload["embedding"], list):
        return False

    # Check metadata values are JSON-serializable
    for key, value in payload["metadata"].items():
        if not isinstance(key, str):
            return False
        # Basic JSON-serializable types
        if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
            return False

    return True


# Example usage for testing
if __name__ == "__main__":
    """
    Example demonstrating the complete pipeline from Document to Qdrant payloads.
    """

    # Create a sample Supreme Court opinion Document
    scotus_doc = Document(
        id="test_scotus_001",
        title="Sample v. Test Case",
        date="2024-05-16",
        type="Supreme Court Opinion",
        source="CourtListener",
        content="""
        SYLLABUS

        Held: The Constitution requires a warrant for digital searches.

        JUSTICE ROBERTS delivered the opinion of the Court.

        The Fourth Amendment protects against unreasonable searches.
        Digital devices contain vast amounts of personal information.
        We hold that a warrant is generally required.
        """,
        metadata={
            "case_name": "Sample v. Test Case",
            "citations": [
                {"type": 1, "volume": "601", "reporter": "U.S.", "page": "100"}
            ],
        },
        url="https://example.com/opinion",
    )

    print("Processing Supreme Court opinion...")
    scotus_payloads = build_payloads_from_document(scotus_doc)
    print(f"Generated {len(scotus_payloads)} SCOTUS payloads")

    # Validate first payload
    if scotus_payloads:
        first = scotus_payloads[0]
        print(f"\nFirst payload:")
        print(f"  ID: {first['id']}")
        print(f"  Text preview: {first['text'][:50]}...")
        print(f"  Metadata fields: {list(first['metadata'].keys())[:5]}...")
        print(f"  Valid: {validate_payload(first)}")

    # Create a sample Executive Order Document
    eo_doc = Document(
        id="test_eo_001",
        title="Test Executive Order",
        date="2025-06-11",
        type="Executive Order",
        source="Federal Register",
        content="""
        Executive Order 99999

        By the authority vested in me as President, I hereby order:

        Section 1. Purpose. This order establishes test requirements.

        Sec. 2. Policy. All agencies shall implement test policies.
        """,
        metadata={"presidential_document_number": "99999", "citation": "90 FR 10000"},
        url="https://example.com/eo",
    )

    print("\n\nProcessing Executive Order...")
    eo_payloads = build_payloads_from_document(eo_doc)
    print(f"Generated {len(eo_payloads)} EO payloads")

    # Validate first payload
    if eo_payloads:
        first = eo_payloads[0]
        print(f"\nFirst payload:")
        print(f"  ID: {first['id']}")
        print(f"  Text preview: {first['text'][:50]}...")
        print(f"  Section: {first['metadata'].get('section_label')}")
        print(f"  Valid: {validate_payload(first)}")

    print("\n\nExample: Ready for Qdrant storage")
    print("# In actual usage:")
    print("# from governmentreporter.database.qdrant import QdrantClient, Document")
    print("# client = QdrantClient(db_path='./qdrant_db')")
    print("# embeddings = generate_embeddings([p['text'] for p in payloads])")
    print(
        "# documents = [Document(id=p['id'], text=p['text'], embedding=e, metadata=p['metadata'])"
    )
    print("#              for p, e in zip(payloads, embeddings)]")
    print("# client.store_documents_batch(documents, 'collection_name')")
