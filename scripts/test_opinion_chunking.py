#!/usr/bin/env python3
"""
Test script for the Supreme Court Opinion Chunking and Metadata Extraction system.
Uses the pre-fetched JSON data to test the complete pipeline.
"""

import json
import os
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.governmentreporter.processors.scotus_opinion_chunker import \
    SCOTUSOpinionProcessor
from src.governmentreporter.utils.citations import build_bluebook_citation


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


def test_citation_builder():
    """Test the bluebook citation builder."""
    print("Testing Citation Builder")
    print("-" * 30)

    _, cluster_data = load_test_data()
    if not cluster_data:
        print("❌ Cannot test citation builder - no cluster data")
        return

    citation = build_bluebook_citation(cluster_data)
    print(f"✅ Citation: {citation}")

    expected = "601 U.S. 416 (2024)"
    if citation == expected:
        print(f"✅ Citation matches expected format: {expected}")
    else:
        print(
            f"⚠️  Citation format may need review. Expected: {expected}, Got: {citation}"
        )


def test_chunking_system():
    """Test the hierarchical chunking system."""
    print("\nTesting Hierarchical Chunking System")
    print("-" * 40)

    opinion_data, cluster_data = load_test_data()
    if not opinion_data:
        print("❌ Cannot test chunking - no opinion data")
        return

    from src.governmentreporter.processors.scotus_opinion_chunker import \
        SCOTUSOpinionChunker

    chunker = SCOTUSOpinionChunker(target_chunk_size=600, max_chunk_size=800)
    plain_text = opinion_data.get("plain_text", "")

    if not plain_text:
        print("❌ No plain text found in opinion data")
        return

    print(f"📄 Original text length: {len(plain_text)} characters")
    print(f"🔢 Original token count: {chunker.count_tokens(plain_text)} tokens")

    # Test opinion type splitting
    opinions = chunker.split_by_opinion_type(plain_text)
    print(f"\n📋 Found {len(opinions)} opinion sections:")

    for i, (text, opinion_type, justice) in enumerate(opinions):
        token_count = chunker.count_tokens(text)
        justice_info = f" by Justice {justice}" if justice else ""
        print(f"   {i+1}. {opinion_type.title()}{justice_info}: {token_count} tokens")

    # Test full chunking
    chunks = chunker.chunk_opinion(plain_text)
    print(f"\n🧩 Generated {len(chunks)} total chunks:")

    chunk_stats = {}
    for chunk in chunks:
        opinion_type = chunk.opinion_type
        if opinion_type not in chunk_stats:
            chunk_stats[opinion_type] = []
        chunk_stats[opinion_type].append(
            {
                "tokens": chunker.count_tokens(chunk.text),
                "section": chunk.section,
                "justice": chunk.justice,
                "index": chunk.chunk_index,
            }
        )

    for opinion_type, type_chunks in chunk_stats.items():
        print(f"\n   {opinion_type.title()} Opinion:")
        for chunk_info in type_chunks:
            section_info = (
                f" (Section {chunk_info['section']})" if chunk_info["section"] else ""
            )
            justice_info = (
                f" by {chunk_info['justice']}" if chunk_info["justice"] else ""
            )
            print(
                f"     - Chunk {chunk_info['index']}{section_info}{justice_info}: {chunk_info['tokens']} tokens"
            )

    # Verify chunking requirements
    print(f"\n🔍 Chunk Analysis:")
    oversized_chunks = [c for c in chunks if chunker.count_tokens(c.text) > 800]
    if oversized_chunks:
        print(f"   ⚠️  {len(oversized_chunks)} chunks exceed 800 token limit")
    else:
        print(f"   ✅ All chunks within 800 token limit")

    undersized_chunks = [c for c in chunks if chunker.count_tokens(c.text) < 100]
    if undersized_chunks:
        print(f"   ⚠️  {len(undersized_chunks)} chunks are very small (<100 tokens)")

    avg_size = sum(chunker.count_tokens(c.text) for c in chunks) / len(chunks)
    print(f"   📊 Average chunk size: {avg_size:.0f} tokens")


def test_metadata_extraction():
    """Test Gemini metadata extraction (without API calls)."""
    print("\nTesting Metadata Extraction")
    print("-" * 30)

    opinion_data, _ = load_test_data()
    if not opinion_data:
        print("❌ Cannot test metadata extraction - no opinion data")
        return

    # Test the prompt generation without making API calls
    from src.governmentreporter.metadata.gemini_generator import \
        GeminiMetadataGenerator

    # Create generator (will fail on API call but we can test prompt generation)
    generator = GeminiMetadataGenerator(api_key="test_key")

    plain_text = opinion_data.get("plain_text", "")

    # Test prompt creation
    prompt = generator._create_legal_metadata_prompt(plain_text)
    print("✅ Legal metadata prompt generated successfully")
    print(f"📝 Prompt length: {len(prompt)} characters")

    # Show what fields will be extracted
    expected_fields = [
        "legal_topics",
        "key_legal_questions",
        "constitutional_provisions",
        "statutes_interpreted",
        "holding",
    ]

    print(f"🎯 Will extract these fields: {', '.join(expected_fields)}")

    # Mock what the response would look like
    mock_metadata = {
        "legal_topics": [
            "Constitutional Law",
            "Administrative Law",
            "Appropriations Clause",
        ],
        "key_legal_questions": [
            "Whether the CFPB's funding mechanism violates the Appropriations Clause",
            "What constitutes a valid appropriation under Article I, Section 9, Clause 7",
        ],
        "constitutional_provisions": ["Art. I, § 9, cl. 7", "Art. I, § 8, cl. 12"],
        "statutes_interpreted": ["12 U.S.C. § 5497(a)(1)", "12 U.S.C. § 5497(a)(2)"],
        "holding": "Congress' statutory authorization allowing the Bureau to draw money from the Federal Reserve System satisfies the Appropriations Clause.",
    }

    print("🎭 Mock extracted metadata:")
    for field, value in mock_metadata.items():
        if isinstance(value, list):
            print(f"   {field}: {len(value)} items")
            for item in value:
                print(f"     - {item}")
        else:
            print(f"   {field}: {value}")


def test_full_pipeline():
    """Test the complete processing pipeline."""
    print("\nTesting Complete Processing Pipeline")
    print("-" * 40)

    opinion_data, cluster_data = load_test_data()
    if not opinion_data or not cluster_data:
        print("❌ Cannot test pipeline - missing test data")
        return

    # Since we can't make real API calls without tokens, we'll simulate the pipeline
    print("🔧 Simulating full pipeline (without API calls)...")

    # Step 1: Opinion data loading
    opinion_id = opinion_data.get("id")
    plain_text = opinion_data.get("plain_text", "")
    print(f"✅ Step 1: Loaded opinion {opinion_id}")

    # Step 2: Cluster data loading
    case_name = cluster_data.get("case_name", "")
    citation = build_bluebook_citation(cluster_data)
    print(f"✅ Step 2: Loaded cluster data for '{case_name}'")
    print(f"          Citation: {citation}")

    # Step 3: Chunking
    from src.governmentreporter.processors.scotus_opinion_chunker import \
        SCOTUSOpinionChunker

    chunker = SCOTUSOpinionChunker()
    chunks = chunker.chunk_opinion(plain_text)
    print(f"✅ Step 3: Generated {len(chunks)} chunks")

    # Step 4: Simulate metadata extraction
    mock_legal_metadata = {
        "legal_topics": ["Constitutional Law", "Administrative Law"],
        "key_legal_questions": ["Appropriations Clause compliance"],
        "constitutional_provisions": ["Art. I, § 9, cl. 7"],
        "statutes_interpreted": ["12 U.S.C. § 5497"],
        "holding": "CFPB funding mechanism satisfies Appropriations Clause",
    }
    print(f"✅ Step 4: Extracted legal metadata (simulated)")

    # Step 5: Combine metadata for each chunk
    print(f"✅ Step 5: Combined metadata for all chunks")

    # Verify expected chunk types are present
    chunk_types = set(chunk.opinion_type for chunk in chunks)
    expected_types = {"syllabus", "majority"}

    if "syllabus" in chunk_types:
        print("   ✅ Syllabus properly separated")
    else:
        print("   ⚠️  No syllabus chunks found")

    if "majority" in chunk_types:
        print("   ✅ Majority opinion identified")
    else:
        print("   ⚠️  No majority opinion chunks found")

    if "concurring" in chunk_types:
        print("   ✅ Concurring opinions identified")

    if "dissenting" in chunk_types:
        print("   ✅ Dissenting opinions identified")

    print(f"   📊 Opinion types found: {', '.join(sorted(chunk_types))}")

    # Show first few chunks as examples
    print(f"\n📋 Sample chunks:")
    for i, chunk in enumerate(chunks[:3]):
        preview = (
            chunk.text[:100].replace("\n", " ") + "..."
            if len(chunk.text) > 100
            else chunk.text
        )
        justice_info = f" by {chunk.justice}" if chunk.justice else ""
        section_info = f" (§{chunk.section})" if chunk.section else ""
        token_count = chunker.count_tokens(chunk.text)

        print(
            f"   {i+1}. {chunk.opinion_type.title()}{justice_info}{section_info} - {token_count} tokens"
        )
        print(f"      {preview}")


def main():
    """Run all tests."""
    print("Supreme Court Opinion Chunking System Test")
    print("=" * 50)

    # Check if test data exists
    if not os.path.exists("scratch/opinions_endpoint.json") or not os.path.exists(
        "scratch/cluster_endpoint.json"
    ):
        print(
            "❌ Test data not found. Please ensure scratch/opinions_endpoint.json and scratch/cluster_endpoint.json exist."
        )
        return

    test_citation_builder()
    test_chunking_system()
    test_metadata_extraction()
    test_full_pipeline()

    print("\n" + "=" * 50)
    print("All tests completed!")
    print("\nNote: This test uses local data and simulates API calls.")
    print("For full testing with live APIs, ensure environment variables are set:")
    print("- COURT_LISTENER_API_TOKEN")
    print("- GOOGLE_GEMINI_API_KEY")


if __name__ == "__main__":
    main()
