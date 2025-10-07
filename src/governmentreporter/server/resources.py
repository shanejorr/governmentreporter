"""
MCP resource handlers for GovernmentReporter.

This module implements MCP resources that expose full government documents
for direct access by LLMs. Resources complement the search tools by providing
complete document content when the LLM needs more context than chunks provide.

Resources use the polymorphic GovernmentAPIClient interface to fetch documents
on-demand from government APIs, ensuring fresh data without storage overhead.

Functions:
    parse_resource_uri: Parse resource URIs into document type and ID
    get_api_client: Get appropriate API client for document type
    read_resource: Fetch and format full document by URI
    format_document_resource: Format Document object for MCP response
    list_available_resources: List example resources for discovery

Resource URI Formats:
    - scotus://opinion/{opinion_id} - Supreme Court opinion by ID
    - eo://document/{document_number} - Executive Order by document number

Example:
    >>> uri = "scotus://opinion/12345678"
    >>> content = await read_resource(uri)
    >>> # Returns full opinion text with metadata
"""

import logging
from typing import Dict, List, Tuple

from mcp.types import Resource
from pydantic import AnyUrl

from ..apis.base import GovernmentAPIClient
from ..apis.court_listener import CourtListenerClient
from ..apis.federal_register import FederalRegisterClient

logger = logging.getLogger(__name__)

# Map document types to their API client classes
# This enables polymorphic document fetching
CLIENT_MAP: Dict[str, type] = {
    "scotus": CourtListenerClient,
    "executive_order": FederalRegisterClient,
}


def parse_resource_uri(uri: str) -> Tuple[str, str]:
    """
    Parse a resource URI into document type and ID.

    This function extracts the document type and identifier from a resource URI,
    enabling the system to route requests to the appropriate API client.

    Args:
        uri: Resource URI following the format:
            - "scotus://opinion/{opinion_id}"
            - "eo://document/{document_number}"

    Returns:
        Tuple of (document_type, document_id) where:
            - document_type: "scotus" or "executive_order"
            - document_id: The identifier to pass to the API client

    Raises:
        ValueError: If URI format is not recognized

    Examples:
        >>> parse_resource_uri("scotus://opinion/12345678")
        ("scotus", "12345678")

        >>> parse_resource_uri("eo://document/2024-12345")
        ("executive_order", "2024-12345")
    """
    if uri.startswith("scotus://opinion/"):
        opinion_id = uri.replace("scotus://opinion/", "")
        return ("scotus", opinion_id)

    elif uri.startswith("eo://document/"):
        document_number = uri.replace("eo://document/", "")
        return ("executive_order", document_number)

    else:
        raise ValueError(f"Unknown resource URI format: {uri}")


def get_api_client(doc_type: str) -> GovernmentAPIClient:
    """
    Get the appropriate API client for a document type.

    This function implements the factory pattern to create API clients
    polymorphically. It uses the CLIENT_MAP to determine which concrete
    client class to instantiate based on the document type.

    Args:
        doc_type: Document type identifier ("scotus" or "executive_order")

    Returns:
        Instance of GovernmentAPIClient (CourtListenerClient or FederalRegisterClient)

    Raises:
        ValueError: If no client is available for the document type

    Example:
        >>> client = get_api_client("scotus")
        >>> isinstance(client, CourtListenerClient)
        True
    """
    client_class = CLIENT_MAP.get(doc_type)
    if not client_class:
        raise ValueError(f"No client available for document type: {doc_type}")

    return client_class()


async def read_resource(uri: str) -> str:
    """
    Read a resource by URI using polymorphic API clients.

    This is the main entry point for resource retrieval. It:
    1. Parses the URI to determine document type and ID
    2. Gets the appropriate API client using the factory pattern
    3. Fetches the document using the standard get_document() interface
    4. Formats the Document object for MCP response

    The function uses polymorphism to handle all document types through
    the same code path, making it easy to add new document types in the future.

    Args:
        uri: Resource URI (e.g., "scotus://opinion/12345678")

    Returns:
        Formatted document content with metadata as a string suitable for
        LLM consumption. Includes title, metadata, and full document text.

    Raises:
        ValueError: If URI format is invalid or document type unsupported
        Exception: If API fetch fails or document not found

    Example:
        >>> content = await read_resource("scotus://opinion/12345678")
        >>> "Consumer Financial Protection Bureau" in content
        True
    """
    try:
        # Parse URI to get document type and ID
        logger.info(f"Reading resource: {uri}")
        doc_type, doc_id = parse_resource_uri(uri)

        # Get appropriate client using polymorphism
        client = get_api_client(doc_type)

        # Use standard interface - works for ANY document type!
        # This is the power of polymorphism via the abstract base class
        document = client.get_document(doc_id)

        # Format the document for MCP response
        formatted_content = format_document_resource(document)

        logger.info(f"Successfully retrieved resource: {uri}")
        return formatted_content

    except ValueError as e:
        logger.error(f"Invalid resource URI {uri}: {e}")
        raise

    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}")
        raise Exception(f"Failed to retrieve resource {uri}: {str(e)}")


def format_document_resource(document) -> str:
    """
    Format a Document object as a resource response.

    This function creates a human-readable and LLM-friendly representation
    of a Document object. It uses the standardized Document structure from
    the base API client, so it works for all document types.

    Args:
        document: Document object from GovernmentAPIClient.get_document()
                 Contains: id, title, date, type, source, content, metadata, url

    Returns:
        Formatted string with document title, metadata, content, and additional
        metadata fields. Structured for optimal LLM comprehension.

    Example Output:
        # Consumer Financial Protection Bureau v. Community Financial Services

        **Document ID:** scotus_12345678
        **Type:** Supreme Court Opinion
        **Source:** CourtListener API
        **Date:** 2024-05-16
        **URL:** https://www.courtlistener.com/...

        ---

        ## Document Content

        [Full opinion text here...]

        ---

        ## Metadata

        - **case_name:** Consumer Financial Protection Bureau v. Community Financial Services
        - **citation:** 601 U.S. 416 (2024)
        - **vote_breakdown:** 7-2
        ...
    """
    # Build formatted output using Document fields
    output = f"""# {document.title}

**Document ID:** {document.id}
**Type:** {document.type}
**Source:** {document.source}
**Date:** {document.date}
**URL:** {document.url}

---

## Document Content

{document.content}

---

## Metadata

"""

    # Add all metadata fields
    for key, value in document.metadata.items():
        # Handle list values (like legal_topics, agencies, etc.)
        if isinstance(value, list):
            value_str = ", ".join(str(v) for v in value)
            output += f"- **{key}:** {value_str}\n"
        else:
            output += f"- **{key}:** {value}\n"

    return output


def list_available_resources() -> List[Resource]:
    """
    List available resource types for LLM discovery.

    This function returns a list of Resource objects that describe the types
    of resources available. Since documents are fetched dynamically by ID,
    we provide example/template resources to show the LLM what's possible.

    Returns:
        List of Resource objects describing available resource types.

    Note:
        Actual document IDs must be obtained through search tools first.
        These are template resources showing the URI format.

    Example:
        >>> resources = list_available_resources()
        >>> len(resources)
        2
        >>> resources[0].uri
        'scotus://opinion/{opinion_id}'
    """
    return [
        Resource(
            uri=AnyUrl("scotus://opinion/{opinion_id}"),
            name="Supreme Court Opinion",
            description=(
                "Full text of a Supreme Court opinion. Use the opinion_id from "
                "search results. Example: scotus://opinion/12345678"
            ),
            mimeType="text/markdown",
        ),
        Resource(
            uri=AnyUrl("eo://document/{document_number}"),
            name="Executive Order",
            description=(
                "Full text of a Presidential Executive Order. Use the document_number "
                "from search results. Example: eo://document/2024-12345"
            ),
            mimeType="text/markdown",
        ),
    ]
