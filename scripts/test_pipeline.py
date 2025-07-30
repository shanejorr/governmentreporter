#!/usr/bin/env python3
"""
Test script to verify the pipeline works with the provided SCOTUS opinion data.
This uses the pre-fetched JSON data instead of making live API calls.
"""

import json

from src.governmentreporter.apis.court_listener import CourtListenerClient
from src.governmentreporter.database import ChromaDBClient
from src.governmentreporter.metadata import GeminiMetadataGenerator
from src.governmentreporter.utils import GoogleEmbeddingsClient


def load_test_data():
    """Load the test data from the scratch directory."""
    try:
        # Load opinion data
        with open("scratch/opinions_endpoint.json", "r") as f:
            opinion_content = f.read()
            # Find the start of the actual JSON data (skip any initial content)
            json_start = opinion_content.find("{")
            if json_start != -1:
                opinion_data = json.loads(opinion_content[json_start:])
            else:
                raise ValueError("No JSON data found in opinions_endpoint.json")

        # Load cluster data
        with open("scratch/cluster_endpoint.json", "r") as f:
            cluster_data = json.load(f)

        return opinion_data, cluster_data

    except Exception as e:
        print(f"Error loading test data: {e}")
        return None, None


def test_pipeline():
    """Test the complete pipeline with the sample data."""
    print("Testing SCOTUS Opinion Processing Pipeline")
    print("=" * 50)

    # Load test data from scratch files
    opinion_data, cluster_data = load_test_data()
    if not opinion_data:
        print("❌ Cannot run test - failed to load test data from scratch files")
        return

    # Step 1: Extract basic metadata using CourtListenerClient
    print("1. Testing basic metadata extraction...")
    # Use dummy token for testing since we're not making API calls
    court_client = CourtListenerClient(token="dummy_token_for_testing")
    basic_metadata = court_client.extract_basic_metadata(opinion_data)

    print(f"   ✅ Opinion ID: {basic_metadata['id']}")
    print(f"   ✅ Date: {basic_metadata['date']}")
    print(f"   ✅ Text length: {len(basic_metadata['plain_text'])} characters")
    print(f"   ✅ Author ID: {basic_metadata['author_id']}")

    # Step 2: Test Gemini metadata generation (truncated text for testing)
    print("\n2. Testing Gemini metadata generation...")
    try:
        metadata_generator = GeminiMetadataGenerator(api_key="dummy_key_for_testing")

        # Use a shorter excerpt for testing to avoid API costs
        test_text = basic_metadata["plain_text"][:3000] + "..."
        ai_metadata = metadata_generator.extract_legal_metadata(test_text)

        print(f"   ✅ Summary: {ai_metadata.get('summary', 'N/A')[:100]}...")
        print(f"   ✅ Topics: {ai_metadata.get('topics', [])}")
        print(f"   ✅ Author: {ai_metadata.get('author', 'N/A')}")
        print(f"   ✅ Majority: {ai_metadata.get('majority', [])}")
        print(f"   ✅ Minority: {ai_metadata.get('minority', [])}")

    except Exception as e:
        print(f"   ❌ Gemini metadata generation failed: {e}")
        # Use mock data for testing
        ai_metadata = {
            "summary": "Mock summary for testing pipeline",
            "topics": [
                "constitutional law",
                "appropriations clause",
                "federal agencies",
            ],
            "author": "Thomas",
            "majority": [
                "Roberts",
                "Thomas",
                "Sotomayor",
                "Kagan",
                "Kavanaugh",
                "Barrett",
                "Jackson",
            ],
            "minority": ["Alito", "Gorsuch"],
        }
        print("   ℹ️  Using mock metadata for pipeline testing")

    # Step 3: Test embeddings generation
    print("\n3. Testing embeddings generation...")
    try:
        embeddings_client = GoogleEmbeddingsClient(api_key="dummy_key_for_testing")

        # Use shorter text for testing
        test_text = basic_metadata["plain_text"][:1000]
        embedding = embeddings_client.generate_embedding(test_text)

        print(f"   ✅ Generated embedding with {len(embedding)} dimensions")

    except Exception as e:
        print(f"   ❌ Embeddings generation failed: {e}")
        # Use mock embedding for testing
        embedding = [0.1] * 768  # Mock 768-dimensional embedding
        print("   ℹ️  Using mock embedding for pipeline testing")

    # Step 4: Test ChromaDB storage
    print("\n4. Testing ChromaDB storage...")
    try:
        db_client = ChromaDBClient()

        # Combine metadata
        combined_metadata = {**basic_metadata, **ai_metadata}
        final_metadata = {
            k: v for k, v in combined_metadata.items() if k != "plain_text"
        }

        # Store in database
        db_client.store_scotus_opinion(
            opinion_id=str(basic_metadata["id"]),
            plain_text=basic_metadata["plain_text"],
            embedding=embedding,
            metadata=final_metadata,
        )

        print("   ✅ Successfully stored in ChromaDB")

        # Test retrieval
        retrieved = db_client.get_opinion_by_id(str(basic_metadata["id"]))
        if retrieved:
            print("   ✅ Successfully retrieved from ChromaDB")
            print(f"      - Retrieved ID: {retrieved['id']}")
            print(f"      - Document length: {len(retrieved['document'])} characters")
            print(f"      - Metadata keys: {list(retrieved['metadata'].keys())}")
        else:
            print("   ❌ Failed to retrieve from ChromaDB")

    except Exception as e:
        print(f"   ❌ ChromaDB storage failed: {e}")

    print("\n" + "=" * 50)
    print("Pipeline test completed!")


if __name__ == "__main__":
    test_pipeline()
