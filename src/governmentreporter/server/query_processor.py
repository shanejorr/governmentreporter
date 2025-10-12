"""
Query processor for formatting search results for LLM consumption.

This module handles the formatting of search results from Qdrant into
human-readable and LLM-friendly text formats. It provides specialized
formatting for different document types and ensures consistent, informative
output that maximizes the utility of retrieved chunks in LLM context windows.

Classes:
    QueryProcessor: Main class for processing and formatting query results.

The processor ensures that:
- Chunk text is presented with proper context
- Metadata is formatted clearly and consistently
- References are properly formatted
- Results are ranked and numbered for clarity
- Document structure is preserved in the output
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def format_timestamp_to_date(
    timestamp: Union[int, None], format_str: str = "%B %d, %Y"
) -> str:
    """
    Convert a Unix timestamp to a human-readable date string.

    Args:
        timestamp: Unix timestamp (seconds since epoch) or None
        format_str: strftime format string for output (default: "Month DD, YYYY")

    Returns:
        Formatted date string, or empty string if timestamp is None

    Example:
        >>> format_timestamp_to_date(1704067200)
        "January 1, 2024"
        >>> format_timestamp_to_date(1704067200, "%Y-%m-%d")
        "2024-01-01"

    Python Learning Notes:
        - datetime.fromtimestamp() creates datetime from Unix timestamp
        - strftime() formats datetime as string using format codes
        - Gracefully handles None values for optional date fields
    """
    if timestamp is None:
        return ""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime(format_str)
    except (ValueError, OSError, OverflowError) as e:
        logger.warning("Failed to format timestamp %s: %s", timestamp, e)
        return ""


class QueryProcessor:
    """
    Process and format query results for LLM consumption.

    This class provides methods to format search results from Qdrant into
    structured, readable text that provides maximum context for LLMs. It
    handles different document types (SCOTUS opinions, Executive Orders)
    with type-specific formatting while maintaining consistency.

    Methods:
        format_search_results: Format general search results
        format_scotus_results: Format SCOTUS-specific results
        format_eo_results: Format Executive Order results
        format_document_chunk: Format a single document chunk
        format_full_document: Format a complete document
        format_collections_list: Format collection information

    Example:
        >>> processor = QueryProcessor()
        >>> formatted = processor.format_search_results(query, results)
    """

    def __init__(self, max_chunk_length: int = 1000):
        """
        Initialize the QueryProcessor.

        Args:
            max_chunk_length: Maximum length for chunk text before truncation.
                             Defaults to 1000 characters.

        Raises:
            ValueError: If max_chunk_length is less than or equal to 0.
        """
        if max_chunk_length <= 0:
            raise ValueError("max_chunk_length must be greater than 0")
        self.max_chunk_length = max_chunk_length

    def format_search_results(self, query: str, results: List[Dict[str, Any]]) -> str:
        """
        Format general search results from multiple document types.

        Args:
            query: The original search query.
            results: List of search results with type, score, and payload.

        Returns:
            Formatted string with numbered results, chunk text, and metadata.
        """
        if not results:
            return f"No results found for query: '{query}'"

        output = [f'## Search Results for: "{query}"\n']
        output.append(f"Found {len(results)} relevant document chunks.\n")

        for i, result in enumerate(results, 1):
            doc_type = result.get("type")
            score = result.get("score", 0)
            payload = result.get("payload", {})

            # Auto-detect document type from payload if not explicitly set
            if not doc_type:
                if "case_name" in payload or "opinion_type" in payload:
                    doc_type = "scotus"
                elif "executive_order_number" in payload or "president" in payload:
                    doc_type = "executive_order"

            if doc_type == "scotus":
                output.append(self._format_scotus_chunk(i, payload, score))
            elif doc_type == "executive_order":
                output.append(self._format_eo_chunk(i, payload, score))
            else:
                output.append(self._format_generic_chunk(i, payload, score))

            output.append("")  # Add blank line between results

        # Add full document access hint if appropriate
        hint = self._generate_full_document_hint(results)
        if hint:
            output.append(hint)

        return "\n".join(output)

    def format_scotus_results(self, query: str, results: List[Dict[str, Any]]) -> str:
        """
        Format Supreme Court opinion search results with legal context.

        Args:
            query: The original search query.
            results: List of SCOTUS search results.

        Returns:
            Formatted string with legal metadata emphasized.
        """
        if not results:
            return f"No Supreme Court opinions found for query: '{query}'"

        output = [f"## Supreme Court Opinion Search Results\n"]
        output.append(f'Query: "{query}"')
        output.append(f"Found {len(results)} relevant opinion chunks.\n")

        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            payload = result.get("payload", {})
            output.append(self._format_scotus_chunk(i, payload, score, detailed=True))
            output.append("")

        # Add full document access hint if appropriate
        hint = self._generate_full_document_hint(results)
        if hint:
            output.append(hint)

        return "\n".join(output)

    def format_eo_results(self, query: str, results: List[Dict[str, Any]]) -> str:
        """
        Format Executive Order search results with policy context.

        Args:
            query: The original search query.
            results: List of Executive Order search results.

        Returns:
            Formatted string with policy metadata emphasized.
        """
        if not results:
            return f"No Executive Orders found for query: '{query}'"

        output = [f"## Executive Order Search Results\n"]
        output.append(f'Query: "{query}"')
        output.append(f"Found {len(results)} relevant order chunks.\n")

        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            payload = result.get("payload", {})
            output.append(self._format_eo_chunk(i, payload, score, detailed=True))
            output.append("")

        # Add full document access hint if appropriate
        hint = self._generate_full_document_hint(results)
        if hint:
            output.append(hint)

        return "\n".join(output)

    def format_document_chunk(
        self, collection: str, document_id: str, payload: Dict[str, Any]
    ) -> str:
        """
        Format a single document chunk with its metadata.

        Args:
            collection: The collection name.
            document_id: The document/chunk ID.
            payload: The document payload with text and metadata.

        Returns:
            Formatted string with chunk content and metadata.
        """
        output = [f"## Document Retrieved\n"]
        output.append(f"**Collection:** {collection}")
        output.append(f"**Document ID:** {document_id}\n")

        # Add document-specific header
        if collection == "supreme_court_opinions":
            case_name = payload.get("case_name", "Unknown Case")
            output.append(f"### {case_name}")
        elif collection == "executive_orders":
            title = payload.get("title", "Unknown Order")
            eo_number = payload.get("executive_order_number", "")
            output.append(f"### {title}")
            if eo_number:
                output.append(f"**EO Number:** {eo_number}")

        # Add the chunk text
        output.append("\n### Document Content:")
        text = payload.get("text") or payload.get("chunk_text", "No text available")
        output.append(text)

        # Add metadata section
        output.append("\n### Metadata:")
        metadata_items = self._extract_relevant_metadata(collection, payload)
        for key, value in metadata_items.items():
            output.append(f"- **{key}:** {value}")

        return "\n".join(output)

    def format_full_document(
        self, doc_type: str, full_document: Any, chunk_metadata: Dict[str, Any]
    ) -> str:
        """
        Format a complete document retrieved from government API.

        Args:
            doc_type: Type of document ("scotus" or "executive_order").
            full_document: The complete document from the API.
            chunk_metadata: Original chunk metadata for context.

        Returns:
            Formatted string with full document content.
        """
        output = [f"## Full Document Retrieved\n"]

        metadata: Dict[str, Any] = dict(chunk_metadata or {})

        # Merge metadata from the full document when available.
        if hasattr(full_document, "metadata"):
            doc_metadata = getattr(full_document, "metadata")
            if isinstance(doc_metadata, dict):
                metadata = {**metadata, **doc_metadata}
        elif isinstance(full_document, dict):
            metadata = {**metadata, **full_document}

        # Resolve the full document text with sensible fallbacks.
        if hasattr(full_document, "content"):
            document_text = getattr(full_document, "content")
        elif isinstance(full_document, dict):
            document_text = (
                full_document.get("plain_text")
                or full_document.get("content")
                or full_document.get("text")
            )
        elif isinstance(full_document, str):
            document_text = full_document
        else:
            document_text = None

        if document_text is None and full_document is not None:
            document_text = str(full_document)

        if doc_type == "scotus":
            case_name = (
                metadata.get("case_name")
                or chunk_metadata.get("case_name")
                or "Supreme Court Opinion"
            )
            opinion_date_timestamp = (
                metadata.get("publication_date")
                or metadata.get("decided_date")
                or chunk_metadata.get("publication_date")
            )
            opinion_date = format_timestamp_to_date(opinion_date_timestamp)
            opinion_type = (
                metadata.get("opinion_type") or chunk_metadata.get("opinion_type") or ""
            )
            justice = (
                metadata.get("justice")
                or metadata.get("author")
                or chunk_metadata.get("justice")
            )

            output.append(f"### {case_name}")
            if opinion_date:
                output.append(f"**Date:** {opinion_date}")
            if opinion_type:
                descriptor = f"**Opinion Type:** {str(opinion_type).title()}"
                if justice:
                    descriptor = f"{descriptor} by {justice}"
                output.append(descriptor)
            output.append("\n### Full Opinion Text:")
            output.append(document_text or "Full opinion text unavailable.")

            additional_metadata = self._extract_relevant_metadata(
                "supreme_court_opinions", metadata
            )
        elif doc_type == "executive_order":
            title = (
                metadata.get("title")
                or chunk_metadata.get("title")
                or "Executive Order"
            )
            eo_number = metadata.get("executive_order_number") or chunk_metadata.get(
                "executive_order_number", ""
            )
            signing_date_timestamp = (
                metadata.get("signing_date")
                or metadata.get("publication_date")
                or chunk_metadata.get("signing_date")
            )
            signing_date = format_timestamp_to_date(signing_date_timestamp)

            president_value = metadata.get("president") or chunk_metadata.get(
                "president"
            )
            if isinstance(president_value, dict):
                president = (
                    president_value.get("name")
                    or president_value.get("full_name")
                    or president_value.get("title")
                )
            else:
                president = president_value

            output.append(f"### {title}")
            if eo_number:
                output.append(f"**EO Number:** {eo_number}")
            if president:
                output.append(f"**President:** {president}")
            if signing_date:
                output.append(f"**Date:** {signing_date}")
            output.append("\n### Full Order Text:")
            output.append(document_text or "Full executive order text unavailable.")

            additional_metadata = self._extract_relevant_metadata(
                "executive_orders", metadata
            )
        else:
            output.append("### Document")
            output.append(document_text or "Full document text unavailable.")
            additional_metadata = {}

        if additional_metadata:
            output.append("\n### Metadata:")
            for key, value in additional_metadata.items():
                output.append(f"- **{key}:** {value}")

        return "\n".join(output)

    def format_collections_list(self, collections: List[Dict[str, Any]]) -> str:
        """
        Format the list of available collections with statistics.

        Args:
            collections: List of collection information dictionaries.

        Returns:
            Formatted string describing available collections.
        """
        output = ["## Available Document Collections\n"]

        for i, collection in enumerate(collections, 1):
            name = collection.get("name", "Unknown")
            output.append(f"### {i}. {name}")

            if "error" in collection:
                output.append(
                    f"*Error retrieving collection info: {collection['error']}*"
                )
            else:
                vectors_count = collection.get("vectors_count", 0)
                points_count = collection.get("points_count", 0)

                output.append(f"- **Total Chunks:** {points_count:,}")
                output.append(f"- **Vector Count:** {vectors_count:,}")

                # Add sample metadata fields if available
                sample_metadata = collection.get("sample_metadata", {})
                if sample_metadata:
                    output.append("- **Available Metadata Fields:**")
                    fields = list(sample_metadata.keys())[:10]  # First 10 fields
                    for field in fields:
                        output.append(f"  - {field}")

            output.append("")

        # Add general information
        output.append("### Collection Features:")
        output.append("- Hierarchical chunking preserves document structure")
        output.append("- Rich metadata enables advanced filtering")
        output.append("- Semantic search with OpenAI text-embedding-3-small")
        output.append("- Real-time document retrieval from government APIs")

        return "\n".join(output)

    def _format_scotus_chunk(
        self, index: int, payload: Dict[str, Any], score: float, detailed: bool = False
    ) -> str:
        """
        Format a Supreme Court opinion chunk.

        Args:
            index: Result number.
            payload: Chunk payload with text and metadata.
            score: Relevance score.
            detailed: Whether to include detailed metadata.

        Returns:
            Formatted string for the SCOTUS chunk.
        """
        lines = []

        # Header with case name
        case_name = payload.get("case_name", "Unknown Case")
        lines.append(f"### {index}. {case_name}")

        # Citation if available
        citation = payload.get("citation", "")
        if citation:
            lines.append(f"*{citation}*")

        # Opinion type and justice
        opinion_type = payload.get("opinion_type", "").title()
        justice = payload.get("justice", "")
        section = payload.get("section", "")

        if opinion_type:
            header_parts = [f"**{opinion_type} Opinion**"]
            if justice:
                header_parts.append(f"by Justice {justice}")
            if section:
                header_parts.append(f"(Section {section})")
            lines.append(" ".join(header_parts))

        # Chunk text
        lines.append("\n**Excerpt:**")
        text = payload.get("text") or payload.get("chunk_text", "No text available")
        # Truncate very long chunks for display
        if len(text) > self.max_chunk_length:
            text = text[: self.max_chunk_length] + "..."
        lines.append(text)

        # Metadata section
        if detailed:
            lines.append("\n**Legal Context:**")

            # Legal topics
            legal_topics = payload.get("legal_topics", [])
            if legal_topics:
                lines.append(f"- **Legal Topics:** {', '.join(legal_topics)}")

            # Constitutional provisions
            constitutional = payload.get("constitutional_provisions", [])
            if constitutional:
                lines.append(
                    f"- **Constitutional Provisions:** {', '.join(constitutional)}"
                )

            # Statutes
            statutes = payload.get("statutes_interpreted", [])
            if statutes:
                lines.append(f"- **Statutes:** {', '.join(statutes)}")

            # Vote breakdown
            vote = payload.get("vote_breakdown", "")
            if vote:
                lines.append(f"- **Vote:** {vote}")

            # Holding
            holding = payload.get("holding", "")
            if holding:
                lines.append(f"- **Key Holding:** {holding[:200]}...")

        # Relevance score
        lines.append(f"\n*Relevance Score: {score:.3f}*")

        return "\n".join(lines)

    def _format_eo_chunk(
        self, index: int, payload: Dict[str, Any], score: float, detailed: bool = False
    ) -> str:
        """
        Format an Executive Order chunk.

        Args:
            index: Result number.
            payload: Chunk payload with text and metadata.
            score: Relevance score.
            detailed: Whether to include detailed metadata.

        Returns:
            Formatted string for the Executive Order chunk.
        """
        lines = []

        # Header with title and EO number
        title = payload.get("title", "Unknown Executive Order")
        eo_number = payload.get("executive_order_number", "")
        lines.append(f"### {index}. {title}")
        if eo_number:
            lines.append(f"**EO Number:** {eo_number}")

        # President and date
        president = payload.get("president", "")
        signing_date_timestamp = payload.get("signing_date")
        signing_date = format_timestamp_to_date(signing_date_timestamp)
        if president or signing_date:
            info_parts = []
            if president:
                info_parts.append(f"President {president}")
            if signing_date:
                info_parts.append(f"Signed {signing_date}")
            lines.append(f"**{' | '.join(info_parts)}**")

        # Section information
        chunk_type = payload.get("chunk_type", "")
        section_title = payload.get("section_title", "")
        if section_title:
            lines.append(f"\n**{section_title}**")
        elif chunk_type:
            lines.append(f"\n**Document Part: {chunk_type.title()}**")

        # Chunk text
        lines.append("\n**Excerpt:**")
        text = payload.get("text") or payload.get("chunk_text", "No text available")
        # Truncate very long chunks for display
        if len(text) > self.max_chunk_length:
            text = text[: self.max_chunk_length] + "..."
        lines.append(text)

        # Metadata section
        if detailed:
            lines.append("\n**Policy Context:**")

            # Summary
            summary = payload.get("summary", "")
            if summary:
                lines.append(f"- **Summary:** {summary[:200]}...")

            # Policy topics
            topics = payload.get("policy_topics", [])
            if topics:
                lines.append(f"- **Policy Topics:** {', '.join(topics)}")

            # Impacted agencies
            agencies = payload.get("impacted_agencies", [])
            if agencies:
                lines.append(f"- **Agencies:** {', '.join(agencies)}")

            # Legal authorities
            authorities = payload.get("legal_authorities", [])
            if authorities:
                lines.append(f"- **Legal Authorities:** {', '.join(authorities[:3])}")

            # Economic sectors
            sectors = payload.get("economic_sectors", [])
            if sectors:
                lines.append(f"- **Economic Sectors:** {', '.join(sectors)}")

        # Relevance score
        lines.append(f"\n*Relevance Score: {score:.3f}*")

        return "\n".join(lines)

    def _format_generic_chunk(
        self, index: int, payload: Dict[str, Any], score: float
    ) -> str:
        """
        Format a generic document chunk (fallback formatter).

        Args:
            index: Result number.
            payload: Chunk payload.
            score: Relevance score.

        Returns:
            Formatted string for the chunk.
        """
        lines = []
        lines.append(f"### {index}. Document Chunk")

        # Try to extract any identifying information
        for key in ["title", "name", "document_id", "id"]:
            if key in payload:
                lines.append(f"**{key.title()}:** {payload[key]}")
                break

        # Add text
        text = payload.get("text") or payload.get("chunk_text", "No text available")
        if len(text) > self.max_chunk_length:
            text = text[: self.max_chunk_length] + "..."
        lines.append(f"\n**Content:**\n{text}")

        # Relevance score
        lines.append(f"\n*Relevance Score: {score:.3f}*")

        return "\n".join(lines)

    def _extract_relevant_metadata(
        self, collection: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract relevant metadata fields based on collection type.

        Args:
            collection: The collection name.
            payload: The document payload.

        Returns:
            Dictionary of relevant metadata fields.
        """
        metadata = {}

        # Define date fields that need timestamp-to-string conversion
        date_fields = {
            "publication_date",
            "signing_date",
            "argued_date",
            "decided_date",
            "effective_date",
        }

        if collection == "supreme_court_opinions":
            fields = [
                "opinion_type",
                "justice",
                "section",
                "publication_date",
                "legal_topics",
                "constitutional_provisions",
                "statutes_interpreted",
                "vote_breakdown",
            ]
        elif collection == "executive_orders":
            fields = [
                "president",
                "signing_date",
                "chunk_type",
                "section_title",
                "policy_topics",
                "impacted_agencies",
                "legal_authorities",
                "economic_sectors",
            ]
        else:
            # For unknown collections, take first 10 non-text fields
            fields = [k for k in payload.keys() if k != "text"][:10]

        for field in fields:
            if field in payload and payload[field]:
                value = payload[field]
                # Convert timestamps to readable dates
                if field in date_fields and isinstance(value, int):
                    value = format_timestamp_to_date(value)
                # Format lists nicely
                elif isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                elif isinstance(value, dict):
                    if "name" in value:
                        value = value["name"]
                    else:
                        value = json.dumps(value, ensure_ascii=False)
                metadata[field.replace("_", " ").title()] = value

        return metadata

    def _generate_full_document_hint(
        self,
        results: List[Dict[str, Any]],
        max_results: int = 3,
        min_score: float = 0.4,
    ) -> str:
        """
        Generate a hint suggesting full document retrieval when appropriate.

        This method analyzes search results and provides explicit guidance to the LLM
        about when and how to fetch full documents for detailed analysis. Hints are
        only generated when results are focused enough that full document context
        would be beneficial without overwhelming the context window.

        The hint includes specific document IDs and tool invocation examples,
        making it easy for the LLM to perform follow-up actions.

        Args:
            results: List of search results with type, score, and payload
            max_results: Maximum number of results to trigger hint (default: 3)
            min_score: Minimum relevance score to trigger hint (default: 0.4)

        Returns:
            String containing full document access hint, or empty string if
            conditions aren't met for hint generation.

        Conditions for hint generation:
            1. Number of results <= max_results (focused search)
            2. Highest relevance score >= min_score (relevant matches)
            3. Results contain document_id in metadata

        Example Output:
            ## 📄 Full Document Access

            For detailed analysis of these 2 cases, you can load the complete opinion text:

            **Trump v. CASA, Inc.:**
            ```
            get_document_by_id(
                document_id="11085138_chunk_0",
                collection="supreme_court_opinions",
                full_document=true
            )
            ```

            This loads the full opinion into context for comprehensive follow-up questions.
        """
        # Don't generate hints if too many results (would overwhelm context)
        if not results or len(results) > max_results:
            return ""

        # Check if any result meets minimum relevance threshold
        max_score = max(r.get("score", 0) for r in results)
        if max_score < min_score:
            return ""

        # Group results by document to avoid duplicate hints
        seen_docs = set()
        doc_hints = []

        for result in results:
            payload = result.get("payload", {})
            doc_type = result.get("type")

            # Extract document ID (opinion ID for SCOTUS, document number for EO)
            document_id = payload.get("document_id")
            if not document_id or document_id in seen_docs:
                continue

            seen_docs.add(document_id)

            # Determine collection name
            if doc_type == "scotus" or "case_name" in payload:
                collection = "supreme_court_opinions"
                doc_title = payload.get("case_name", payload.get("title", "Document"))
            elif doc_type == "executive_order" or "executive_order_number" in payload:
                collection = "executive_orders"
                eo_number = payload.get("executive_order_number", "")
                doc_title = payload.get("title", f"Executive Order {eo_number}")
            else:
                continue

            # Generate hint for this document
            # Use first chunk ID for document retrieval
            chunk_id = payload.get("chunk_id", f"{document_id}_chunk_0")

            hint = f"""**{doc_title}:**
```
get_document_by_id(
    document_id="{chunk_id}",
    collection="{collection}",
    full_document=true
)
```"""
            doc_hints.append(hint)

        # Only generate section if we have hints
        if not doc_hints:
            return ""

        doc_count = len(doc_hints)
        intro = f"For detailed analysis of {'this case' if doc_count == 1 else f'these {doc_count} documents'}, you can load the complete {'opinion' if results[0].get('type') == 'scotus' else 'document'} text:"

        output = ["\n---\n", "## 📄 Full Document Access\n", intro, ""]
        output.extend(doc_hints)
        output.append(
            "\nLoading the full document enables comprehensive follow-up questions without additional searches."
        )

        return "\n".join(output)
