#!/usr/bin/env python3
"""
GovernmentReporter Main Entry Point

This is the main entry point for GovernmentReporter. You can use this to:
- Process individual Supreme Court opinions
- Run bulk processing operations
- Test the chunking system
- Start various data processing pipelines

For more specific operations, use the scripts in the scripts/ directory.
"""

import sys

from dotenv import load_dotenv

from src.governmentreporter.processors import SCOTUSOpinionProcessor


def show_usage():
    print("GovernmentReporter - US Federal Government Document Processing")
    print("=" * 60)
    print("\nUsage:")
    print("  python main.py <command> [arguments]")
    print("\nCommands:")
    print("  process <opinion_id>     - Process a single SCOTUS opinion with chunking")
    print("  help                     - Show this help message")
    print("\nExamples:")
    print("  python main.py process 9973155")
    print("\nFor bulk operations, use:")
    print("  python scripts/download_scotus_bulk.py")


def process_opinion(opinion_id: int):
    """Process a single Supreme Court opinion."""
    print(f"Processing SCOTUS opinion {opinion_id} with hierarchical chunking...")

    try:
        processor = SCOTUSOpinionProcessor()
        chunks = processor.process_opinion(opinion_id)

        print(f"✅ Successfully processed {len(chunks)} chunks")

        # Show summary
        chunk_types = {}
        for chunk in chunks:
            chunk_types[chunk.opinion_type] = chunk_types.get(chunk.opinion_type, 0) + 1

        print("📊 Chunk breakdown:")
        for opinion_type, count in chunk_types.items():
            print(f"  - {opinion_type.title()}: {count} chunks")

        if chunks:
            print(f"\n📋 Case: {chunks[0].case_name}")
            print(f"📄 Citation: {chunks[0].citation}")

    except Exception as e:
        print(f"❌ Error processing opinion: {e}")
        return False

    return True


def main():
    load_dotenv()

    if len(sys.argv) < 2:
        show_usage()
        return

    command = sys.argv[1].lower()

    if command == "help" or command == "-h" or command == "--help":
        show_usage()
    elif command == "process":
        if len(sys.argv) < 3:
            print("❌ Error: opinion_id required for process command")
            print("Usage: python main.py process <opinion_id>")
            return

        try:
            opinion_id = int(sys.argv[2])
            process_opinion(opinion_id)
        except ValueError:
            print("❌ Error: opinion_id must be an integer")
    else:
        print(f"❌ Unknown command: {command}")
        show_usage()


if __name__ == "__main__":
    main()
