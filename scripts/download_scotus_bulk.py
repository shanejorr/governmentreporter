#!/usr/bin/env python3
"""
Bulk Processing Script for US Supreme Court Opinions from CourtListener API.

This script serves as the command-line interface for downloading and processing Supreme Court
opinions in bulk from the CourtListener API. It orchestrates the complete document processing
pipeline for SCOTUS opinions, from API retrieval through hierarchical chunking, metadata
extraction, embedding generation, and storage in ChromaDB.

Key Features:
    - Downloads SCOTUS opinions from CourtListener API (dating back to 1900)
    - Supports flexible date range filtering for targeted processing
    - Implements hierarchical document chunking (by opinion type, sections, paragraphs)
    - Generates rich legal metadata using Google Gemini 2.5 Flash-Lite AI
    - Creates semantic embeddings for intelligent search capabilities
    - Stores processed chunks in ChromaDB vector database
    - Provides resumable operations with progress tracking
    - Handles errors gracefully with detailed logging

The script works in conjunction with:
    - SCOTUSBulkProcessor: Manages bulk processing workflow (src/governmentreporter/processors/scotus_bulk.py)
    - SCOTUSOpinionProcessor: Processes individual opinions (src/governmentreporter/processors/scotus_opinion_chunker.py)
    - CourtListenerClient: Interfaces with CourtListener API (src/governmentreporter/apis/court_listener.py)
    - ChromaDBClient: Manages vector database storage (src/governmentreporter/database/chroma_client.py)

Example Usage:
    # Process recent opinions (last 5 years)
    python scripts/download_scotus_bulk.py --since-date 2020-01-01 --max-opinions 100

    # Process specific date range
    python scripts/download_scotus_bulk.py --since-date 2023-01-01 --until-date 2024-12-31

    # Check available opinions without processing
    python scripts/download_scotus_bulk.py --count-only --since-date 2024-01-01

    # View current processing statistics
    python scripts/download_scotus_bulk.py --stats

Environment Requirements:
    - COURT_LISTENER_API_TOKEN: Required for API authentication
    - GOOGLE_GEMINI_API_KEY: Required for metadata generation
    - Python 3.11+ with uv package manager

Python Learning Notes:
    - argparse module: Used for parsing command-line arguments in a structured way
    - sys.exit(): Provides proper exit codes for shell scripts (0=success, 1=error)
    - dotenv: Loads environment variables from .env file for secure credential management
    - Type hints (-> None): Indicates function returns nothing, helps with code clarity
"""

import argparse
import sys

from dotenv import load_dotenv

# Load environment variables from .env file
# This reads the .env file in the project root and makes all variables available
# via os.environ, allowing secure storage of API keys and tokens
load_dotenv()

from governmentreporter.processors import SCOTUSBulkProcessor


def main() -> None:
    """
    Main entry point for the SCOTUS bulk download script.

    This function orchestrates the entire bulk processing workflow for Supreme Court opinions.
    It handles command-line argument parsing, initializes the bulk processor with appropriate
    settings, and executes the requested operation (count, stats, or full processing).

    The function follows this workflow:
        1. Parse command-line arguments using argparse
        2. Initialize SCOTUSBulkProcessor with provided parameters
        3. Execute requested operation (count-only, stats, or full processing)
        4. Display results and handle errors appropriately

    Command-line Arguments:
        --output-dir: Directory for storing progress files and error logs
        --since-date: Start date for opinion retrieval (YYYY-MM-DD format)
        --until-date: Optional end date for opinion retrieval (YYYY-MM-DD format)
        --max-opinions: Limit on number of opinions to process (for testing)
        --rate-limit-delay: Delay between API requests to respect rate limits
        --collection-name: Name of ChromaDB collection for storage
        --count-only: Flag to only display count without processing
        --stats: Flag to display current processing statistics

    Returns:
        None: Function exits with appropriate status code (0 for success, 1 for error)

    Raises:
        Exception: Any unhandled exceptions are caught and displayed with error message

    Integration Points:
        - Uses SCOTUSBulkProcessor from processors module for bulk operations
        - Relies on environment variables loaded via dotenv for API credentials
        - Outputs progress to specified directory for resumable operations

    Python Learning Notes:
        - argparse.ArgumentParser: Creates a parser object for command-line arguments
        - parser.add_argument(): Defines each command-line option with type and help text
        - action="store_true": Creates boolean flags that default to False
        - try/except blocks: Handle errors gracefully and provide user-friendly messages
        - f-strings: Modern Python string formatting for clear output messages
    """
    parser = argparse.ArgumentParser(
        description="Download and process all SCOTUS opinions using hierarchical chunking from CourtListener API"
    )
    parser.add_argument(
        "--output-dir",
        default="raw-data/scotus_data",
        help="Output directory for progress and error logs (default: raw-data/scotus_data)",
    )
    parser.add_argument(
        "--since-date",
        default="1900-01-01",
        help="Start date for opinion retrieval in YYYY-MM-DD format (default: 1900-01-01)",
    )
    parser.add_argument(
        "--until-date",
        default=None,
        help="End date for opinion retrieval in YYYY-MM-DD format (optional)",
    )
    parser.add_argument(
        "--max-opinions",
        type=int,
        help="Maximum number of opinions to process (default: all)",
    )
    parser.add_argument(
        "--rate-limit-delay",
        type=float,
        default=0.75,
        help="Delay between API requests in seconds (default: 0.75)",
    )
    parser.add_argument(
        "--collection-name",
        default="federal_court_scotus_opinions",
        help="ChromaDB collection name (default: federal_court_scotus_opinions)",
    )
    parser.add_argument(
        "--count-only",
        action="store_true",
        help="Only show the count of available opinions without processing",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show current processing statistics",
    )

    args = parser.parse_args()

    try:
        processor = SCOTUSBulkProcessor(
            output_dir=args.output_dir,
            since_date=args.since_date,
            until_date=args.until_date,
            rate_limit_delay=args.rate_limit_delay,
            collection_name=args.collection_name,
        )

        if args.count_only:
            count = processor.get_total_count()
            date_range = f"since {args.since_date}"
            if args.until_date:
                date_range = f"from {args.since_date} to {args.until_date}"
            print(f"Total SCOTUS opinions {date_range}: {count:,}")
            return

        if args.stats:
            stats = processor.get_processing_stats()
            print("Current Processing Statistics:")
            print(f"  Total available: {stats['total_available']:,}")
            print(f"  Already processed: {stats['processed_count']:,}")
            print(f"  Remaining: {stats['remaining_count']:,}")
            print(f"  Progress: {stats['progress_percentage']:.1f}%")
            print(f"  Since date: {stats['since_date']}")
            if stats["until_date"]:
                print(f"  Until date: {stats['until_date']}")
            print(f"  Collection: {stats['collection_name']}")
            print(f"  Output directory: {stats['output_dir']}")
            return

        # Run the bulk processing
        results = processor.process_all_opinions(max_opinions=args.max_opinions)

        # Print final results
        print(f"\n🎉 Bulk processing completed!")
        print(f"Processed: {results['processed_count']:,} opinions")
        print(f"Failed: {results['failed_count']:,} opinions")
        print(f"Success rate: {results['success_rate']:.1%}")
        print(f"Total time: {results['elapsed_time']/60:.1f} minutes")

    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
