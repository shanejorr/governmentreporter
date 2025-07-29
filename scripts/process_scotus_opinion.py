#!/usr/bin/env python3
"""
Script to process a Supreme Court opinion using the new hierarchical chunking pipeline:
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

from src.governmentreporter.database import ChromaDBClient
from src.governmentreporter.processors.scotus_opinion_chunker import \
    SCOTUSOpinionProcessor
from src.governmentreporter.utils import GoogleEmbeddingsClient


def process_scotus_opinion(opinion_id: int) -> Dict[str, Any]:
    """Process a Supreme Court opinion through the new hierarchical chunking pipeline.

    Args:
        opinion_id: CourtListener opinion ID

    Returns:
        Dict containing processing results and statistics
    """
    print(f"Processing Supreme Court opinion ID: {opinion_id}")

    # Step 1: Initialize the opinion processor
    print("1. Initializing SCOTUS opinion processor...")
    processor = SCOTUSOpinionProcessor()

    # Step 2: Process the opinion into chunks with complete metadata
    print("2. Processing opinion through hierarchical chunking pipeline...")
    print("   - Fetching opinion data from CourtListener API")
    print("   - Fetching cluster data for case metadata")
    print("   - Hierarchically chunking by opinion type and sections")
    print("   - Extracting legal metadata using Gemini 2.5 Flash-Lite")
    print("   - Building bluebook citations")

    processed_chunks = processor.process_opinion(opinion_id)

    print(f"   ✅ Generated {len(processed_chunks)} chunks")

    # Step 3: Show chunk breakdown
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

    # Step 4: Generate embeddings for each chunk
    print("3. Generating embeddings for each chunk...")
    embeddings_client = GoogleEmbeddingsClient()

    chunk_data_for_storage = []
    for i, chunk in enumerate(processed_chunks):
        # Generate embedding for this chunk
        embedding = embeddings_client.generate_embedding(chunk.text)

        # Prepare data for storage
        chunk_data = {
            "chunk_id": f"{opinion_id}_chunk_{i}",
            "text": chunk.text,
            "embedding": embedding,
            "metadata": chunk.to_dict(),
        }

        # Remove text from metadata to avoid duplication
        chunk_data["metadata"].pop("text", None)

        chunk_data_for_storage.append(chunk_data)

        if (i + 1) % 10 == 0 or i == len(processed_chunks) - 1:
            print(
                f"   - Generated embeddings for {i + 1}/{len(processed_chunks)} chunks"
            )

    # Step 5: Store all chunks in ChromaDB
    print("4. Storing chunks in ChromaDB...")
    db_client = ChromaDBClient()

    stored_count = 0
    for chunk_data in chunk_data_for_storage:
        try:
            # Store each chunk individually
            db_client.store_scotus_opinion(
                opinion_id=chunk_data["chunk_id"],
                plain_text=chunk_data["text"],
                embedding=chunk_data["embedding"],
                metadata=chunk_data["metadata"],
            )
            stored_count += 1
        except Exception as e:
            print(f"   ⚠️  Failed to store chunk {chunk_data['chunk_id']}: {e}")

    print(f"   ✅ Successfully stored {stored_count}/{len(processed_chunks)} chunks")

    # Step 6: Display sample metadata
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

    # Return processing results
    return {
        "opinion_id": opinion_id,
        "total_chunks": len(processed_chunks),
        "stored_chunks": stored_count,
        "chunk_types": list(chunk_stats.keys()),
        "case_name": processed_chunks[0].case_name if processed_chunks else "Unknown",
        "citation": processed_chunks[0].citation if processed_chunks else "Unknown",
        "success": stored_count == len(processed_chunks),
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
        print(f"\n{'✅' if result['success'] else '⚠️'} Processing completed!")
        print(f"Opinion ID: {result['opinion_id']}")
        print(f"Case: {result['case_name']}")
        print(f"Citation: {result['citation']}")
        print(f"Total chunks: {result['total_chunks']}")
        print(f"Stored chunks: {result['stored_chunks']}")
        print(f"Chunk types: {', '.join(result['chunk_types'])}")

        if not result["success"]:
            print("⚠️  Some chunks failed to store - check the output above for details")

    except Exception as e:
        print(f"\n❌ Processing failed with error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
