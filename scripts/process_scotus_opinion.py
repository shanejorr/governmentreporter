#!/usr/bin/env python3
"""
Script to process a Supreme Court opinion through the hierarchical chunking pipeline.

This script fetches Supreme Court opinions from CourtListener, processes them into
semanticly meaningful chunks, enriches them with AI-generated metadata, and stores
them in ChromaDB for retrieval.

Pipeline Overview:
1. Fetch opinion data from CourtListener API
2. Fetch cluster data for case metadata
3. Hierarchically chunk the opinion by type and sections
4. Generate AI-powered legal metadata using Gemini 2.5 Flash-Lite
5. Create embeddings for each chunk
6. Store all chunks with complete metadata in ChromaDB
"""

import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# opinion_id = 9973155

from governmentreporter.processors.scotus_opinion_chunker import SCOTUSOpinionProcessor


def process_scotus_opinion(opinion_id: int) -> Dict[str, Any]:
    """Process a Supreme Court opinion through the hierarchical chunking pipeline.

    Args:
        opinion_id: CourtListener opinion ID (unique identifier for the opinion)

    Returns:
        Dict containing processing results and statistics including:
            - opinion_id: The processed opinion ID
            - total_chunks: Number of chunks created
            - stored_chunks: Number of chunks successfully stored in ChromaDB
            - chunk_types: List of opinion types found (majority, dissenting, etc.)
            - case_name: Name of the case
            - citation: Bluebook citation for the case
            - success: Boolean indicating if processing succeeded
            - error: Error message if processing failed (None if successful)
    """
    print(f"Processing Supreme Court opinion ID: {opinion_id}")

    # Step 1: Initialize the opinion processor
    # What: Creates an instance of SCOTUSOpinionProcessor with default configuration
    # Why: This processor contains all necessary clients (CourtListener API, ChromaDB,
    #      Gemini AI, embeddings) and the chunking logic for processing opinions
    # Output: Configured processor instance ready to fetch and process opinions
    print("1. Initializing SCOTUS opinion processor...")
    processor = SCOTUSOpinionProcessor()

    # Step 2: Process the opinion into chunks with complete metadata and store in ChromaDB
    # What: Executes the complete processing pipeline using process_and_store method
    # Why: This single method handles the entire workflow from fetching to storage,
    #      ensuring all steps are properly coordinated and errors are handled consistently
    # Output: Dict with success status, chunk counts, and any error messages
    #
    # The process_and_store method internally performs these operations:
    #   a. Fetches opinion text and metadata from CourtListener API
    #   b. Fetches cluster data for additional case information (case name, court, date)
    #   c. Splits opinion into logical chunks based on opinion type (majority, dissenting, etc.)
    #      and sections (I, II.A, etc.) while maintaining semantic coherence
    #   d. Sends full opinion text to Gemini 2.5 Flash-Lite to extract legal metadata:
    #      legal topics, key questions, constitutional provisions, statutes, and holdings
    #   e. Constructs proper Bluebook citations from cluster metadata
    #   f. Generates semantic embeddings for each chunk using Google's embedding model
    #   g. Stores chunks with all metadata in ChromaDB collection for vector search
    print("2. Processing opinion through hierarchical chunking pipeline...")
    print("   - Fetching opinion data from CourtListener API")
    print("   - Fetching cluster data for case metadata")
    print("   - Hierarchically chunking by opinion type and sections")
    print("   - Extracting legal metadata using Gemini 2.5 Flash-Lite")
    print("   - Building bluebook citations")
    print("   - Generating embeddings for each chunk")

    result = processor.process_and_store(
        document_id=str(opinion_id), collection_name="scotus_opinions"
    )

    if not result["success"]:
        print(f"   ❌ Failed to process opinion: {result['error']}")
        return {
            "opinion_id": opinion_id,
            "total_chunks": 0,
            "stored_chunks": 0,
            "success": False,
            "error": result["error"],
        }

    print(f"   ✅ Generated and stored {result['chunks_stored']} chunks")

    # Step 3: Get processed chunks for display and statistics
    # What: Fetches the same chunks but without embeddings (for memory efficiency)
    # Why: We need the chunk objects to display statistics and sample metadata to the user,
    #      but don't need the large embedding vectors for display purposes
    # Output: List of ProcessedOpinionChunk objects containing all metadata but no embeddings
    processed_chunks = processor.process_opinion(opinion_id)

    # Calculate chunk statistics for user feedback
    # What: Aggregates chunks by opinion type and tracks authoring justices
    # Why: Provides a quick overview of how the opinion was chunked, showing the
    #      distribution of content across different opinion types and authors
    # Output: Dictionary mapping opinion types to counts and justice names
    chunk_stats = {}
    for chunk in processed_chunks:
        opinion_type = chunk.opinion_type
        if opinion_type not in chunk_stats:
            chunk_stats[opinion_type] = {"count": 0, "justices": set()}
        chunk_stats[opinion_type]["count"] += 1
        if chunk.justice:
            chunk_stats[opinion_type]["justices"].add(chunk.justice)

    print("   📊 Chunk breakdown:")
    for opinion_type, stats in chunk_stats.items():
        justice_info = (
            f" (by {', '.join(stats['justices'])})" if stats["justices"] else ""
        )
        print(f"      - {opinion_type.title()}: {stats['count']} chunks{justice_info}")

    # Step 4: Display sample metadata from the first chunk
    # What: Shows a preview of the metadata extracted and stored for each chunk
    # Why: Allows users to verify that metadata extraction worked correctly and
    #      understand what information is available for retrieval
    # Output: Console display of key metadata fields from the first chunk
    if processed_chunks:
        sample_chunk = processed_chunks[0]
        print("\n📋 Sample metadata from first chunk:")
        print(f"   - Case: {sample_chunk.case_name}")
        print(f"   - Citation: {sample_chunk.citation}")
        print(f"   - Opinion type: {sample_chunk.opinion_type}")
        print(f"   - Legal topics: {sample_chunk.legal_topics[:3]}...")  # Show first 3
        print(
            f"   - Constitutional provisions: {sample_chunk.constitutional_provisions}"
        )
        print(
            f"   - Holding: {sample_chunk.holding[:100] if sample_chunk.holding else 'N/A'}..."
        )

    # Compile and return processing results
    # What: Aggregates all processing statistics and metadata into a single dict
    # Why: Provides a comprehensive summary for logging, error handling, and user feedback
    # Output: Dictionary with success status, counts, and key metadata
    return {
        "opinion_id": opinion_id,
        "total_chunks": result["chunks_processed"],
        "stored_chunks": result["chunks_stored"],
        "chunk_types": list(chunk_stats.keys()),
        "case_name": processed_chunks[0].case_name if processed_chunks else "Unknown",
        "citation": processed_chunks[0].citation if processed_chunks else "Unknown",
        "success": result["success"],
    }


def main():
    """Main function to run the processing pipeline."""
    if len(sys.argv) != 2:
        print("Usage: python process_scotus_opinion.py <opinion_id>")
        print("Example: python process_scotus_opinion.py 9973155")
        sys.exit(1)

    try:
        opinion_id = int(sys.argv[1])
    except ValueError:
        print("Error: opinion_id must be an integer")
        sys.exit(1)

    try:
        result = process_scotus_opinion(opinion_id)
        print(f"\n{'✅' if result['success'] else '❌'} Processing completed!")
        print(f"Opinion ID: {result['opinion_id']}")

        if result["success"]:
            print(f"Case: {result['case_name']}")
            print(f"Citation: {result['citation']}")
            print(f"Total chunks: {result['total_chunks']}")
            print(f"Stored chunks: {result['stored_chunks']}")
            print(f"Chunk types: {', '.join(result['chunk_types'])}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            print("⚠️  Processing failed - check the output above for details")

    except Exception as e:
        print(f"\n❌ Processing failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
