#!/usr/bin/env python3
"""Integration test for the SCOTUS opinion processing pipeline."""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.governmentreporter.processors import SCOTUSOpinionProcessor


def test_scotus_pipeline():
    """Test the complete SCOTUS opinion processing pipeline."""
    load_dotenv()

    # Test opinion ID (a real SCOTUS opinion)
    opinion_id = "9973155"

    print("=" * 60)
    print("Testing SCOTUS Opinion Processing Pipeline")
    print("=" * 60)

    print(f"\nProcessing opinion ID: {opinion_id}")
    print("-" * 40)

    try:
        # Initialize processor
        processor = SCOTUSOpinionProcessor()

        # Process and store the opinion
        result = processor.process_and_store(
            document_id=str(opinion_id), collection_name="test_scotus_opinions"
        )

        if result["success"]:
            print(f"✅ Successfully processed opinion {opinion_id}")
            print(f"   Chunks processed: {result['chunks_processed']}")
            print(f"   Chunks stored: {result['chunks_stored']}")

            # Verify the chunks were stored
            if result["chunks_stored"] > 0:
                print(f"✅ All {result['chunks_stored']} chunks stored in database")
            else:
                print("❌ No chunks were stored")
                return False

        else:
            print(f"❌ Failed to process opinion: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_scotus_pipeline()
    sys.exit(0 if success else 1)
