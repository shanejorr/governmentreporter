#!/usr/bin/env python3
"""
Script to process a Supreme Court opinion using the complete pipeline:
1. Fetch opinion data from CourtListener API
2. Extract basic metadata
3. Generate AI-powered metadata using Gemini
4. Create embeddings using Google's embedding model
5. Store in ChromaDB
"""

import sys
import os
from typing import Dict, Any
from dotenv import load_dotenv

# opinion_id = 9973155

# Load environment variables from .env file
load_dotenv()

from src.governmentreporter.apis import CourtListenerClient
from src.governmentreporter.database import ChromaDBClient
from src.governmentreporter.metadata import GeminiMetadataGenerator
from src.governmentreporter.utils import GoogleEmbeddingsClient


def process_scotus_opinion(opinion_id: int) -> Dict[str, Any]:
    """Process a Supreme Court opinion through the complete pipeline.
    
    Args:
        opinion_id: CourtListener opinion ID
        
    Returns:
        Dict containing all processed data
    """
    print(f"Processing Supreme Court opinion ID: {opinion_id}")
    
    # Step 1: Fetch opinion data from CourtListener API
    print("1. Fetching opinion data from CourtListener API...")
    court_client = CourtListenerClient()
    raw_opinion_data = court_client.get_opinion(opinion_id)
    basic_metadata = court_client.extract_basic_metadata(raw_opinion_data)
    
    print(f"   - Retrieved opinion: {basic_metadata.get('id')}")
    print(f"   - Date: {basic_metadata.get('date')}")
    print(f"   - Text length: {len(basic_metadata.get('plain_text', ''))} characters")
    
    # Step 2: Generate AI metadata using Gemini
    print("2. Generating metadata using Gemini 2.5 Flash-Lite...")
    metadata_generator = GeminiMetadataGenerator()
    ai_metadata = metadata_generator.generate_scotus_metadata(basic_metadata['plain_text'])
    
    print(f"   - Generated summary: {ai_metadata.get('summary', '')[:100]}...")
    print(f"   - Topics: {ai_metadata.get('topics', [])}")
    print(f"   - Author: {ai_metadata.get('author')}")
    print(f"   - Majority: {ai_metadata.get('majority', [])}")
    print(f"   - Minority: {ai_metadata.get('minority', [])}")
    
    # Step 3: Generate embeddings
    print("3. Generating embeddings using Google's embedding model...")
    embeddings_client = GoogleEmbeddingsClient()
    embedding = embeddings_client.generate_embedding(basic_metadata['plain_text'])
    
    print(f"   - Generated embedding with {len(embedding)} dimensions")
    
    # Step 4: Combine all metadata
    combined_metadata = {
        **basic_metadata,  # Basic metadata from API
        **ai_metadata      # AI-generated metadata
    }
    
    # Remove plain_text from metadata as it's stored separately
    final_metadata = {k: v for k, v in combined_metadata.items() if k != 'plain_text'}
    
    # Step 5: Store in ChromaDB
    print("4. Storing in ChromaDB...")
    db_client = ChromaDBClient()
    
    db_client.store_scotus_opinion(
        opinion_id=str(opinion_id),
        plain_text=basic_metadata['plain_text'],
        embedding=embedding,
        metadata=final_metadata
    )
    
    print("   - Successfully stored in ChromaDB collection 'federal_court_scotus_opinions'")
    
    # Return all processed data for verification
    return {
        "opinion_id": opinion_id,
        "metadata": final_metadata,
        "embedding_dimensions": len(embedding),
        "text_length": len(basic_metadata['plain_text']),
        "success": True
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
        print("\n✅ Processing completed successfully!")
        print(f"Opinion ID: {result['opinion_id']}")
        print(f"Embedding dimensions: {result['embedding_dimensions']}")
        print(f"Text length: {result['text_length']} characters")
        
    except Exception as e:
        print(f"\n❌ Processing failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()