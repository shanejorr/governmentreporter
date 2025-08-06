#!/usr/bin/env python3
"""
MCP Server for GovernmentReporter

This module provides a Model Context Protocol server that enables LLMs to access
US federal government publications through semantic search and real-time retrieval.

The server exposes tools for:
- Searching Supreme Court opinions by topic, case name, or legal concepts
- Retrieving full text of government documents from authoritative sources
- Querying legal metadata (citations, constitutional provisions, statutes)
- Processing new documents through the hierarchical chunking pipeline

Usage:
    python -m governmentreporter.server
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence

from mcp.server.fastmcp import FastMCP
from mcp.server.models import InitializationOptions
from mcp.types import (EmbeddedResource, ImageContent, Resource, TextContent,
                       Tool)

from .database import ChromaDBClient
from .processors import SCOTUSOpinionProcessor
from .utils import GoogleEmbeddingsClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("GovernmentReporter")

# Initialize clients
db_client = ChromaDBClient()
embeddings_client = GoogleEmbeddingsClient()
opinion_processor = SCOTUSOpinionProcessor()


@mcp.tool()
def search_scotus_opinions(
    query: str, limit: int = 5, opinion_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search Supreme Court opinions using semantic search.

    Args:
        query: Search query (e.g., "environmental regulation", "free speech")
        limit: Maximum number of results to return (default: 5)
        opinion_type: Filter by opinion type (syllabus, majority, concurring, dissenting)

    Returns:
        List of matching opinion chunks with metadata
    """
    try:
        # Generate embedding for the query
        query_embedding = embeddings_client.generate_embedding(query)

        # Get the collection
        collection = db_client.get_or_create_collection("federal_court_scotus_opinions")

        # Prepare where clause for filtering
        where_clause = {}
        if opinion_type:
            where_clause["opinion_type"] = opinion_type

        # Perform semantic search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_clause if where_clause else None,
            include=["metadatas", "documents", "distances"],
        )

        # Format results
        formatted_results = []
        if results["metadatas"] and results["metadatas"][0]:
            for i, metadata in enumerate(results["metadatas"][0]):
                result = {
                    "case_name": metadata.get("case_name", "Unknown"),
                    "citation": metadata.get("citation", "Unknown"),
                    "opinion_type": metadata.get("opinion_type", "Unknown"),
                    "justice": metadata.get("justice"),
                    "section": metadata.get("section"),
                    "legal_topics": metadata.get("legal_topics", []),
                    "constitutional_provisions": metadata.get(
                        "constitutional_provisions", []
                    ),
                    "statutes_interpreted": metadata.get("statutes_interpreted", []),
                    "holding": metadata.get("holding"),
                    "similarity_score": 1
                    - results["distances"][0][i],  # Convert distance to similarity
                    "text_preview": (
                        results["documents"][0][i][:200] + "..."
                        if results["documents"][0][i]
                        else ""
                    ),
                }
                formatted_results.append(result)

        return formatted_results

    except Exception as e:
        logger.error(f"Error searching SCOTUS opinions: {e}")
        return [{"error": str(e)}]


@mcp.tool()
def get_opinion_full_text(case_name: str, citation: str) -> Dict[str, Any]:
    """Retrieve the full text of a Supreme Court opinion.

    Args:
        case_name: Name of the case
        citation: Bluebook citation (e.g., "601 U.S. 416 (2024)")

    Returns:
        Dictionary with full case information and text
    """
    try:
        # Search for the case in the database
        collection = db_client.get_or_create_collection("federal_court_scotus_opinions")

        # Query by case name and citation
        results = collection.query(
            query_texts=[case_name],
            where={
                "$and": [
                    {"case_name": {"$contains": case_name.split("v.")[0].strip()}},
                    {"citation": citation},
                ]
            },
            n_results=20,  # Get all chunks for this case
            include=["metadatas", "documents"],
        )

        if not results["metadatas"] or not results["metadatas"][0]:
            return {"error": f"Case not found: {case_name} {citation}"}

        # Organize chunks by opinion type
        organized_chunks: Dict[str, List[Dict[str, Any]]] = {}
        for i, metadata in enumerate(results["metadatas"][0]):
            opinion_type = metadata.get("opinion_type", "unknown")
            if opinion_type not in organized_chunks:
                organized_chunks[opinion_type] = []

            organized_chunks[opinion_type].append(
                {
                    "text": results["documents"][0][i],
                    "section": metadata.get("section"),
                    "justice": metadata.get("justice"),
                    "chunk_index": metadata.get("chunk_index", 0),
                }
            )

        # Sort chunks within each opinion type
        for opinion_type in organized_chunks:
            organized_chunks[opinion_type].sort(key=lambda x: x["chunk_index"])

        # Get case metadata from first chunk
        first_metadata = results["metadatas"][0][0]

        return {
            "case_name": first_metadata.get("case_name"),
            "citation": first_metadata.get("citation"),
            "date_created": first_metadata.get("date_created"),
            "legal_topics": first_metadata.get("legal_topics", []),
            "constitutional_provisions": first_metadata.get(
                "constitutional_provisions", []
            ),
            "statutes_interpreted": first_metadata.get("statutes_interpreted", []),
            "holding": first_metadata.get("holding"),
            "organized_text": organized_chunks,
        }

    except Exception as e:
        logger.error(f"Error retrieving full text: {e}")
        return {"error": str(e)}


@mcp.tool()
def process_new_opinion(opinion_id: int) -> Dict[str, Any]:
    """Process a new Supreme Court opinion through the hierarchical chunking pipeline.

    DEPRECATED: Use the bulk processor (download_scotus_bulk.py) instead.
    This function duplicates functionality now in SCOTUSOpinionProcessor.process_and_store().

    Args:
        opinion_id: CourtListener opinion ID

    Returns:
        Processing results and statistics
    """
    try:
        # Use the integrated process_and_store method
        result = opinion_processor.process_and_store(
            document_id=str(opinion_id), collection_name="federal_court_scotus_opinions"
        )

        if not result["success"]:
            return {"error": result.get("error", "Processing failed")}

        # Get chunks for metadata (without embeddings)
        chunks = opinion_processor.process_opinion(opinion_id)

        # Generate statistics
        chunk_stats: Dict[str, int] = {}
        for chunk in chunks:
            opinion_type = chunk.opinion_type
            chunk_stats[opinion_type] = chunk_stats.get(opinion_type, 0) + 1

        return {
            "opinion_id": opinion_id,
            "case_name": chunks[0].case_name if chunks else "Unknown",
            "citation": chunks[0].citation if chunks else "Unknown",
            "total_chunks": result["chunks_processed"],
            "stored_chunks": result["chunks_stored"],
            "chunk_breakdown": chunk_stats,
            "success": result["success"],
        }

    except Exception as e:
        logger.error(f"Error processing new opinion: {e}")
        return {"error": str(e)}


@mcp.tool()
def get_legal_topics(limit: int = 100) -> List[str]:
    """Get a list of common legal topics found in the database.

    Args:
        limit: Maximum number of topics to return (default: 100)

    Returns:
        List of unique legal topics across sampled documents
    """
    try:
        collection = db_client.get_or_create_collection("federal_court_scotus_opinions")

        # Sample a subset of documents instead of loading all
        # This is much more efficient for large collections
        results = collection.query(
            query_texts=[""],  # Empty query to get random sample
            n_results=min(limit, 500),  # Sample up to 500 documents
            include=["metadatas"],
        )

        topics = set()
        if results["metadatas"] and len(results["metadatas"]) > 0:
            for metadata_list in results["metadatas"]:
                for metadata in metadata_list:
                    legal_topics = metadata.get("legal_topics", [])
                    if isinstance(legal_topics, list):
                        topics.update(legal_topics)

        # Return sorted list, limited to requested number
        sorted_topics = sorted(list(topics))
        return sorted_topics[:limit]

    except Exception as e:
        logger.error(f"Error getting legal topics: {e}")
        return []


@mcp.resource("government://scotus/search")
async def scotus_search_resource(uri: str) -> str:
    """Resource for SCOTUS opinion search functionality."""
    return """
    Supreme Court Opinion Search Resource
    
    This resource provides access to hierarchically chunked Supreme Court opinions
    with semantic search capabilities. Each opinion is broken down into:
    
    - Syllabus: Court's summary of the case and holding
    - Majority Opinion: Main opinion of the court  
    - Concurring Opinions: Additional opinions agreeing with the result
    - Dissenting Opinions: Opinions disagreeing with the majority
    
    Each chunk includes rich metadata:
    - Legal topics and key questions
    - Constitutional provisions cited
    - Statutes interpreted (in bluebook format)
    - Case citations and court holdings
    - Justice attribution for concurring/dissenting opinions
    
    Use the search_scotus_opinions tool to find relevant cases.
    """


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    logger.info("Starting GovernmentReporter MCP Server...")
    logger.info(
        "Available tools: search_scotus_opinions, get_opinion_full_text, process_new_opinion, get_legal_topics"
    )

    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="governmentreporter",
                server_version="0.1.0",
                capabilities=mcp.get_capabilities(
                    notification_options=None, experimental_capabilities={}
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
