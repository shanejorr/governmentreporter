"""
MCP tool handlers for GovernmentReporter.

This module contains the handler functions for each MCP tool exposed by the server.
Each handler processes tool arguments, performs the requested operation (usually
involving Qdrant searches), and formats the response for LLM consumption.

Functions:
    handle_search_government_documents: Main semantic search across all collections
    handle_search_scotus_opinions: Specialized search for Supreme Court opinions
    handle_search_executive_orders: Specialized search for Executive Orders
    handle_get_document_by_id: Retrieve specific document by ID
    handle_list_collections: List available collections and statistics

Each handler follows the pattern:
1. Validate and parse arguments
2. Generate query embedding if needed
3. Perform Qdrant search with filters
4. Format results for LLM context
"""

import logging
from typing import Any, Dict

from ..database.qdrant import QdrantDBClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny, Range
from ..processors.embeddings import generate_embedding
from ..apis.court_listener import CourtListenerClient
from ..apis.federal_register import FederalRegisterClient
from .query_processor import QueryProcessor

logger = logging.getLogger(__name__)


async def handle_search_government_documents(
    qdrant_client: QdrantDBClient, arguments: Dict[str, Any]
) -> str:
    """
    Handle the search_government_documents tool call.

    This is the primary search tool that searches across all government document
    collections. It performs semantic search using query embeddings and returns
    relevant document chunks with metadata.

    Args:
        qdrant_client: The Qdrant database client for vector searches.
        arguments: Tool arguments containing:
            - query (str): The search query
            - document_types (List[str], optional): Types to search ["scotus", "executive_orders"]
            - limit (int, optional): Maximum results (default: 10)

    Returns:
        Formatted string containing search results with document chunks and metadata
        suitable for LLM context.

    Example Return Format:
        ## Search Results for: "environmental regulation"

        ### 1. Supreme Court Opinion - West Virginia v. EPA (2022)
        **Majority Opinion by Chief Justice Roberts (Section II.A)**
        [Chunk text about major questions doctrine...]

        **Metadata:**
        - Legal Topics: Environmental Law, Administrative Law
        - Relevance Score: 0.89

        ### 2. Executive Order 14008 - Climate Crisis (2021)
        **Section 2: Domestic Climate Policy**
        [Chunk text about climate policy...]

        **Metadata:**
        - President: Biden
        - Date: January 27, 2021
        - Agencies: EPA, DOE, DOI
        - Relevance Score: 0.87
    """
    query = arguments.get("query")
    document_types = arguments.get("document_types", ["scotus", "executive_orders"])
    limit = arguments.get("limit", 10)

    if not query:
        return "Error: Query parameter is required"

    processor = QueryProcessor()

    try:
        # Generate query embedding
        logger.info(f"Processing search query: {query}")
        query_embedding = generate_embedding(query)

        results = []

        # Search each requested document type
        if "scotus" in document_types:
            collection = "supreme_court_opinions"
            scotus_results = qdrant_client.semantic_search(
                collection_name=collection, query_vector=query_embedding, limit=limit
            )
            for result in scotus_results:
                # SearchResult has document attribute, not payload
                # Flatten document text and metadata into single payload dict
                payload = {
                    "text": result.document.text,
                    **result.document.metadata,  # Flatten metadata into payload
                }
                results.append(
                    {"type": "scotus", "score": result.score, "payload": payload}
                )

        if "executive_orders" in document_types:
            collection = "executive_orders"
            eo_results = qdrant_client.semantic_search(
                collection_name=collection, query_vector=query_embedding, limit=limit
            )
            for result in eo_results:
                # SearchResult has document attribute, not payload
                # Flatten document text and metadata into single payload dict
                payload = {
                    "text": result.document.text,
                    **result.document.metadata,  # Flatten metadata into payload
                }
                results.append(
                    {
                        "type": "executive_order",
                        "score": result.score,
                        "payload": payload,
                    }
                )

        # Sort all results by relevance score
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:limit]

        # Format results for LLM
        formatted_response = processor.format_search_results(query, results)
        return formatted_response

    except Exception as e:
        logger.error(f"Error in search_government_documents: {e}")
        return f"Error performing search: {str(e)}"


async def handle_search_scotus_opinions(
    qdrant_client: QdrantDBClient, arguments: Dict[str, Any]
) -> str:
    """
    Handle the search_scotus_opinions tool call with specialized filters.

    This tool provides advanced search capabilities specifically for Supreme Court
    opinions, allowing filtering by opinion type, justice, date range, and more.

    Args:
        qdrant_client: The Qdrant database client.
        arguments: Tool arguments containing:
            - query (str): The search query
            - opinion_type (str, optional): Filter by opinion type
            - justice (str, optional): Filter by authoring justice
            - start_date (str, optional): Start date filter (YYYY-MM-DD)
            - end_date (str, optional): End date filter (YYYY-MM-DD)
            - limit (int, optional): Maximum results (default: 10)

    Returns:
        Formatted string containing SCOTUS-specific search results with legal
        metadata.

    Example Return Format:
        ## Supreme Court Opinion Search Results

        ### 1. Dobbs v. Jackson Women's Health Organization (2022)
        **Majority Opinion by Justice Alito (Section III.B)**
        [Chunk text about constitutional interpretation...]

        **Legal Context:**
        - Vote: 6-3
        - Constitutional Provisions: Fourteenth Amendment
        - Key Holding: No constitutional right to abortion
        - Relevance Score: 0.92
    """
    query = arguments.get("query")
    opinion_type = arguments.get("opinion_type")
    justice = arguments.get("justice")
    start_date = arguments.get("start_date")
    end_date = arguments.get("end_date")
    limit = arguments.get("limit", 10)

    if not query:
        return "Error: Query parameter is required"

    processor = QueryProcessor()

    try:
        # Generate query embedding
        logger.info(f"Processing SCOTUS search query: {query}")
        query_embedding = generate_embedding(query)

        # Build proper Qdrant filter conditions
        filter_conditions = []

        if opinion_type:
            filter_conditions.append(
                FieldCondition(key="opinion_type", match=MatchValue(value=opinion_type))
            )

        if justice:
            filter_conditions.append(
                FieldCondition(key="justice", match=MatchValue(value=justice))
            )

        if start_date or end_date:
            # Build range condition for dates
            range_params = {}
            if start_date:
                range_params["gte"] = start_date
            if end_date:
                range_params["lte"] = end_date

            filter_conditions.append(
                FieldCondition(key="date", range=Range(**range_params))
            )

        # Create proper Qdrant Filter object
        search_filter = Filter(must=filter_conditions) if filter_conditions else None

        results = qdrant_client.semantic_search(
            collection_name="supreme_court_opinions",
            query_vector=query_embedding,
            limit=limit,
            query_filter=search_filter,
        )

        # Format results with SCOTUS-specific formatting
        formatted_results = []
        for result in results:
            # SearchResult has document attribute, not payload
            payload = {"text": result.document.text, **result.document.metadata}
            formatted_results.append(
                {"type": "scotus", "score": result.score, "payload": payload}
            )

        formatted_response = processor.format_scotus_results(query, formatted_results)
        return formatted_response

    except Exception as e:
        logger.error(f"Error in search_scotus_opinions: {e}")
        return f"Error performing SCOTUS search: {str(e)}"


async def handle_search_executive_orders(
    qdrant_client: QdrantDBClient, arguments: Dict[str, Any]
) -> str:
    """
    Handle the search_executive_orders tool call with specialized filters.

    This tool provides advanced search capabilities specifically for Executive
    Orders, allowing filtering by president, agencies, policy topics, and date.

    Args:
        qdrant_client: The Qdrant database client.
        arguments: Tool arguments containing:
            - query (str): The search query
            - president (str, optional): Filter by president name
            - agencies (List[str], optional): Filter by agency codes
            - policy_topics (List[str], optional): Filter by policy topics
            - start_date (str, optional): Start date filter (YYYY-MM-DD)
            - end_date (str, optional): End date filter (YYYY-MM-DD)
            - limit (int, optional): Maximum results (default: 10)

    Returns:
        Formatted string containing Executive Order search results with policy
        metadata and agency impacts.

    Example Return Format:
        ## Executive Order Search Results

        ### 1. Executive Order 14067 - Digital Assets (2022)
        **Section 3: Policy and Actions**
        [Chunk text about cryptocurrency regulation...]

        **Policy Context:**
        - EO Number: 14067
        - President: Biden
        - Date: March 9, 2022
        - Agencies: Treasury, SEC, CFTC
        - Policy Topics: cryptocurrency, financial regulation
        - Relevance Score: 0.88
    """
    query = arguments.get("query")
    president = arguments.get("president")
    agencies = arguments.get("agencies", [])
    policy_topics = arguments.get("policy_topics", [])
    start_date = arguments.get("start_date")
    end_date = arguments.get("end_date")
    limit = arguments.get("limit", 10)

    if not query:
        return "Error: Query parameter is required"

    processor = QueryProcessor()

    try:
        # Generate query embedding
        logger.info(f"Processing Executive Order search query: {query}")
        query_embedding = generate_embedding(query)

        # Build proper Qdrant filter conditions
        filter_conditions = []

        if president:
            filter_conditions.append(
                FieldCondition(key="president", match=MatchValue(value=president))
            )

        if agencies:
            # Agencies are stored as an array, match any of them
            filter_conditions.append(
                FieldCondition(key="impacted_agencies", match=MatchAny(any=agencies))
            )

        if policy_topics:
            # Policy topics are stored as an array, match any of them
            filter_conditions.append(
                FieldCondition(key="policy_topics", match=MatchAny(any=policy_topics))
            )

        if start_date or end_date:
            # Build range condition for dates
            range_params = {}
            if start_date:
                range_params["gte"] = start_date
            if end_date:
                range_params["lte"] = end_date

            filter_conditions.append(
                FieldCondition(key="signing_date", range=Range(**range_params))
            )

        # Create proper Qdrant Filter object
        search_filter = Filter(must=filter_conditions) if filter_conditions else None

        results = qdrant_client.semantic_search(
            collection_name="executive_orders",
            query_vector=query_embedding,
            limit=limit,
            query_filter=search_filter,
        )

        # Format results with EO-specific formatting
        formatted_results = []
        for result in results:
            # SearchResult has document attribute, not payload
            payload = {"text": result.document.text, **result.document.metadata}
            formatted_results.append(
                {"type": "executive_order", "score": result.score, "payload": payload}
            )

        formatted_response = processor.format_eo_results(query, formatted_results)
        return formatted_response

    except Exception as e:
        logger.error(f"Error in search_executive_orders: {e}")
        return f"Error performing Executive Order search: {str(e)}"


async def handle_get_document_by_id(
    qdrant_client: QdrantDBClient, arguments: Dict[str, Any]
) -> str:
    """
    Handle the get_document_by_id tool call.

    Retrieves a specific document or chunk by its ID. Can optionally fetch
    the full document from the government API instead of just the chunk.

    Args:
        qdrant_client: The Qdrant database client.
        arguments: Tool arguments containing:
            - document_id (str): The document/chunk ID to retrieve
            - collection (str): The collection to search in
            - full_document (bool, optional): Whether to fetch full document from API

    Returns:
        Formatted string containing the document content and metadata.

    Example Return Format:
        ## Document Retrieved: 601 U.S. 416 (2024)

        **Consumer Financial Protection Bureau v. Community Financial Services**

        ### Document Content:
        [Full chunk or document text...]

        ### Metadata:
        - Document ID: scotus_2024_cfpb_chunk_3
        - Collection: supreme_court_opinions
        - Opinion Type: majority
        - Justice: Thomas
        - Section: II.A
    """
    document_id = arguments.get("document_id")
    collection = arguments.get("collection")
    full_document = arguments.get("full_document", False)

    if not document_id or not collection:
        return "Error: document_id and collection parameters are required"

    processor = QueryProcessor()

    try:
        # First, get the chunk from Qdrant
        document = qdrant_client.get_document(
            document_id=document_id, collection_name=collection
        )

        if not document:
            return f"Document with ID {document_id} not found in {collection}"

        # Prepare payload from Document object
        payload = {
            "text": document.text,
            **document.metadata,  # Flatten metadata into payload
        }

        # If full_document is requested, fetch from API
        if full_document:
            if collection == "supreme_court_opinions":
                # Extract opinion ID from metadata
                opinion_id = payload.get("opinion_id")
                if opinion_id:
                    client = CourtListenerClient()
                    full_doc = client.get_opinion(opinion_id)
                    formatted_response = processor.format_full_document(
                        "scotus", full_doc, payload
                    )
                    return formatted_response
            elif collection == "executive_orders":
                # Extract document number from metadata
                doc_number = payload.get("document_number")
                if doc_number:
                    client = FederalRegisterClient()
                    # Note: FederalRegisterClient would need a get_document method
                    # For now, we'll just return the chunk
                    logger.debug(
                        f"Full document retrieval not implemented for EO {doc_number}"
                    )

        # Return the chunk with metadata
        formatted_response = processor.format_document_chunk(
            collection, document_id, payload
        )
        return formatted_response

    except Exception as e:
        logger.error(f"Error in get_document_by_id: {e}")
        return f"Error retrieving document: {str(e)}"


async def handle_list_collections(
    qdrant_client: QdrantDBClient, arguments: Dict[str, Any]
) -> str:
    """
    Handle the list_collections tool call.

    Lists all available document collections in the vector database with
    statistics about each collection.

    Args:
        qdrant_client: The Qdrant database client.
        arguments: Tool arguments (none required for this tool).

    Returns:
        Formatted string listing collections and their statistics.

    Example Return Format:
        ## Available Document Collections

        ### 1. supreme_court_opinions
        - Total Chunks: 45,328
        - Unique Cases: 892
        - Date Range: 1950-2024
        - Vector Dimensions: 1536
        - Distance Metric: Cosine

        ### 2. executive_orders
        - Total Chunks: 12,456
        - Unique Orders: 423
        - Date Range: 2000-2024
        - Vector Dimensions: 1536
        - Distance Metric: Cosine

        ### Collection Features:
        - Hierarchical chunking preserves document structure
        - Rich metadata enables advanced filtering
        - Semantic search with OpenAI embeddings
    """
    processor = QueryProcessor()

    try:
        # Get list of collections
        collections = qdrant_client.list_collections()

        # Get detailed info for each collection
        collection_details = []
        for collection_name in collections:
            try:
                # Get collection info from Qdrant
                info = qdrant_client.client.get_collection(collection_name)

                # Get sample point to understand metadata structure
                sample = qdrant_client.client.scroll(
                    collection_name=collection_name, limit=1
                )[0]

                details = {
                    "name": collection_name,
                    "vectors_count": info.vectors_count,
                    "points_count": info.points_count,
                    "config": info.config,
                    "sample_metadata": sample[0].payload if sample else {},
                }
                collection_details.append(details)
            except Exception as e:
                logger.warning(f"Could not get details for {collection_name}: {e}")
                collection_details.append({"name": collection_name, "error": str(e)})

        # Format the response
        formatted_response = processor.format_collections_list(collection_details)
        return formatted_response

    except Exception as e:
        logger.error(f"Error in list_collections: {e}")
        return f"Error listing collections: {str(e)}"
