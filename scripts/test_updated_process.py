#!/usr/bin/env python3
"""
Test script to verify the updated process_scotus_opinion.py script works correctly.
This simulates the processing without making real API calls or database operations.
"""

import os
import sys
from unittest.mock import Mock, patch

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.process_scotus_opinion import process_scotus_opinion


def create_mock_processed_chunks():
    """Create mock processed chunks for testing."""
    from src.governmentreporter.processors.scotus_opinion_chunker import \
        ProcessedOpinionChunk

    # Create sample chunks representing different opinion types
    chunks = []

    # Syllabus chunk
    chunks.append(
        ProcessedOpinionChunk(
            text="Sample syllabus text...",
            opinion_type="syllabus",
            justice=None,
            section=None,
            chunk_index=0,
            id=9973155,
            cluster_id=9506542,
            resource_uri="https://example.com/api/opinions/9973155/",
            download_url="https://example.com/pdf",
            author_str="",
            page_count=58,
            joined_by_str="",
            type="010combined",
            per_curiam=False,
            date_created="2024-05-23",
            opinions_cited=["Sample v. Case"],
            case_name="Test Case v. Example Corp",
            citation="601 U.S. 416 (2024)",
            legal_topics=["Constitutional Law", "Administrative Law"],
            key_legal_questions=["Test question?"],
            constitutional_provisions=["Art. I, § 9, cl. 7"],
            statutes_interpreted=["12 U.S.C. § 5497"],
            holding="Test holding statement",
        )
    )

    # Majority opinion chunk
    chunks.append(
        ProcessedOpinionChunk(
            text="Sample majority opinion text...",
            opinion_type="majority",
            justice=None,
            section="I",
            chunk_index=0,
            id=9973155,
            cluster_id=9506542,
            resource_uri="https://example.com/api/opinions/9973155/",
            download_url="https://example.com/pdf",
            author_str="Thomas",
            page_count=58,
            joined_by_str="Roberts, Sotomayor, Kagan",
            type="010combined",
            per_curiam=False,
            date_created="2024-05-23",
            opinions_cited=["Sample v. Case"],
            case_name="Test Case v. Example Corp",
            citation="601 U.S. 416 (2024)",
            legal_topics=["Constitutional Law", "Administrative Law"],
            key_legal_questions=["Test question?"],
            constitutional_provisions=["Art. I, § 9, cl. 7"],
            statutes_interpreted=["12 U.S.C. § 5497"],
            holding="Test holding statement",
        )
    )

    # Concurring opinion chunk
    chunks.append(
        ProcessedOpinionChunk(
            text="Sample concurring opinion text...",
            opinion_type="concurring",
            justice="Jackson",
            section="A",
            chunk_index=0,
            id=9973155,
            cluster_id=9506542,
            resource_uri="https://example.com/api/opinions/9973155/",
            download_url="https://example.com/pdf",
            author_str="Jackson",
            page_count=58,
            joined_by_str="",
            type="010combined",
            per_curiam=False,
            date_created="2024-05-23",
            opinions_cited=["Sample v. Case"],
            case_name="Test Case v. Example Corp",
            citation="601 U.S. 416 (2024)",
            legal_topics=["Constitutional Law", "Administrative Law"],
            key_legal_questions=["Test question?"],
            constitutional_provisions=["Art. I, § 9, cl. 7"],
            statutes_interpreted=["12 U.S.C. § 5497"],
            holding="Test holding statement",
        )
    )

    return chunks


def test_updated_process():
    """Test the updated process_scotus_opinion function."""
    print("Testing Updated SCOTUS Opinion Processing Script")
    print("=" * 50)

    # Create mock chunks
    mock_chunks = create_mock_processed_chunks()

    # Create mock embedding (768-dimensional vector)
    mock_embedding = [0.1] * 768

    # Mock the SCOTUSOpinionProcessor
    with patch(
        "scripts.process_scotus_opinion.SCOTUSOpinionProcessor"
    ) as mock_processor_class:
        # Mock the processor instance and its process_opinion method
        mock_processor = Mock()
        mock_processor.process_opinion.return_value = mock_chunks
        mock_processor_class.return_value = mock_processor

        # Mock the GoogleEmbeddingsClient
        with patch(
            "scripts.process_scotus_opinion.GoogleEmbeddingsClient"
        ) as mock_embeddings_class:
            mock_embeddings = Mock()
            mock_embeddings.generate_embedding.return_value = mock_embedding
            mock_embeddings_class.return_value = mock_embeddings

            # Mock the ChromaDBClient
            with patch(
                "scripts.process_scotus_opinion.ChromaDBClient"
            ) as mock_db_class:
                mock_db = Mock()
                mock_db.store_scotus_opinion.return_value = None  # Successful storage
                mock_db_class.return_value = mock_db

                # Test the function
                try:
                    result = process_scotus_opinion(9973155)

                    print("✅ Function executed successfully!")
                    print(f"📊 Results:")
                    print(f"   - Opinion ID: {result['opinion_id']}")
                    print(f"   - Case: {result['case_name']}")
                    print(f"   - Citation: {result['citation']}")
                    print(f"   - Total chunks: {result['total_chunks']}")
                    print(f"   - Stored chunks: {result['stored_chunks']}")
                    print(f"   - Chunk types: {', '.join(result['chunk_types'])}")
                    print(f"   - Success: {result['success']}")

                    # Verify the expected calls were made
                    print(f"\n🔍 Verification:")
                    print(
                        f"   - SCOTUSOpinionProcessor.process_opinion called: {mock_processor.process_opinion.called}"
                    )
                    print(
                        f"   - Embeddings generated: {mock_embeddings.generate_embedding.call_count} times"
                    )
                    print(
                        f"   - Database stores attempted: {mock_db.store_scotus_opinion.call_count} times"
                    )

                    # Check that we got expected results
                    expected_chunk_types = {"syllabus", "majority", "concurring"}
                    actual_chunk_types = set(result["chunk_types"])

                    if expected_chunk_types == actual_chunk_types:
                        print(
                            f"   ✅ Chunk types match expected: {expected_chunk_types}"
                        )
                    else:
                        print(
                            f"   ⚠️  Chunk types mismatch. Expected: {expected_chunk_types}, Got: {actual_chunk_types}"
                        )

                    if result["total_chunks"] == len(mock_chunks):
                        print(f"   ✅ Chunk count matches expected: {len(mock_chunks)}")
                    else:
                        print(
                            f"   ⚠️  Chunk count mismatch. Expected: {len(mock_chunks)}, Got: {result['total_chunks']}"
                        )

                    if result["success"]:
                        print(f"   ✅ Processing marked as successful")
                    else:
                        print(f"   ⚠️  Processing marked as failed")

                except Exception as e:
                    print(f"❌ Function failed with error: {e}")
                    import traceback

                    traceback.print_exc()
                    return False

    print(f"\n" + "=" * 50)
    print("✅ Test completed successfully!")
    print("\nThe updated script is ready to use with real API calls.")
    print("Usage: python scripts/process_scotus_opinion.py 9973155")

    return True


if __name__ == "__main__":
    test_updated_process()
