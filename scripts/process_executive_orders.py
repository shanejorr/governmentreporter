#!/usr/bin/env python3
"""
Bulk Processing Script for US Executive Orders from the Federal Register API.

This script serves as the command-line interface for downloading and processing Executive Orders
in bulk from the Federal Register API. It orchestrates the complete document processing pipeline
for presidential executive orders, implementing hierarchical chunking, AI-powered metadata
extraction, embedding generation, and storage in ChromaDB.

Key Features:
    - Fetches Executive Orders from Federal Register API by date range
    - Implements hierarchical chunking (header, sections, subsections, tail)
    - Extracts rich policy metadata using Google Gemini 2.5 Flash-Lite AI
    - Generates semantic embeddings for intelligent search
    - Stores processed chunks in ChromaDB vector database
    - Provides resumable operations with progress tracking
    - Detects and skips duplicate documents already in database
    - Handles errors gracefully with detailed logging

The script works in conjunction with:
    - ExecutiveOrderBulkProcessor: Manages bulk processing workflow (src/governmentreporter/processors/executive_order_bulk.py)
    - ExecutiveOrderProcessor: Processes individual orders (src/governmentreporter/processors/executive_order_chunker.py)
    - FederalRegisterClient: Interfaces with Federal Register API (src/governmentreporter/apis/federal_register.py)
    - ChromaDBClient: Manages vector database storage (src/governmentreporter/database/chroma_client.py)

Usage Examples:
    # Process all Executive Orders from 2024
    uv run python scripts/process_executive_orders.py 2024-01-01 2024-12-31

    # Process orders from first half of 2024
    uv run python scripts/process_executive_orders.py 2024-01-01 2024-06-30

    # Process with custom output directory for logs
    uv run python scripts/process_executive_orders.py 2024-01-01 2024-06-30 --output-dir my_data

    # Process only first 10 orders (useful for testing)
    uv run python scripts/process_executive_orders.py 2024-01-01 2024-12-31 --max-orders 10

    # Show statistics without processing
    uv run python scripts/process_executive_orders.py 2024-01-01 2024-06-30 --stats

Arguments:
    start_date: Start date in YYYY-MM-DD format (required)
    end_date: End date in YYYY-MM-DD format (required)

Options:
    --output-dir: Output directory for progress and error logs (default: raw-data/executive_orders_data)
    --max-orders: Maximum number of orders to process (default: all)
    --collection-name: ChromaDB collection name (default: federal-executive-orders)
    --stats: Show current processing statistics without processing

Environment Requirements:
    - GOOGLE_GEMINI_API_KEY: Required for metadata generation
    - Python 3.11+ with uv package manager
    - No API key required for Federal Register API (public access)

Python Learning Notes:
    - argparse: Standard library for parsing command-line arguments
    - pathlib.Path: Modern object-oriented filesystem path handling
    - re.match(): Regular expression pattern matching for date validation
    - sys.exit(): Provides proper exit codes (0=success, 1=error, 130=Ctrl+C)
    - try/except blocks: Comprehensive error handling with specific exceptions
    - Type hints: Improves code clarity and enables better IDE support
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from governmentreporter.processors import ExecutiveOrderBulkProcessor
from governmentreporter.utils import get_logger


def validate_date_format(date_str: str) -> bool:
    """
    Validate that a date string follows the YYYY-MM-DD format.
    
    This function uses regular expressions to check if the provided date string
    matches the exact pattern required by the Federal Register API. It only validates
    the format, not whether the date is actually valid (e.g., it would accept 2024-13-45).
    
    Args:
        date_str (str): Date string to validate. Should be in YYYY-MM-DD format.
                       Examples: "2024-01-01", "2024-12-31"
    
    Returns:
        bool: True if the string matches YYYY-MM-DD format, False otherwise.
              Returns False for None, empty strings, or incorrectly formatted dates.
    
    Examples:
        >>> validate_date_format("2024-01-15")
        True
        >>> validate_date_format("01/15/2024")
        False
        >>> validate_date_format("2024-1-15")  # Missing leading zeros
        False
    
    Integration Notes:
        - Used by main() to validate command-line arguments before processing
        - Ensures API compatibility with Federal Register date requirements
        - Works in conjunction with date range validation in main()
    
    Python Learning Notes:
        - Regular expressions (re module): Pattern matching for string validation
        - r"" prefix: Raw string literal, treats backslashes literally
        - \d{4}: Matches exactly 4 digits (the year)
        - \d{2}: Matches exactly 2 digits (month and day)
        - ^ and $: Anchors ensuring the entire string matches (not just part)
        - bool(): Explicitly converts match object to boolean
    """
    import re

    pattern = r"^\d{4}-\d{2}-\d{2}$"
    return bool(re.match(pattern, date_str))


def main() -> None:
    """
    Main entry point for the Executive Orders bulk processing script.
    
    This function orchestrates the entire bulk processing workflow for Executive Orders.
    It handles command-line argument parsing, validates input parameters, initializes
    the bulk processor, and executes the requested operation (stats or full processing).
    
    The function follows this workflow:
        1. Parse command-line arguments using argparse
        2. Validate date format and date range logic
        3. Initialize ExecutiveOrderBulkProcessor with configuration
        4. Execute requested operation (stats display or full processing)
        5. Display results and handle various error conditions
    
    Command-line Arguments:
        start_date: Start date for order retrieval (YYYY-MM-DD format, required)
        end_date: End date for order retrieval (YYYY-MM-DD format, required)
        --output-dir: Directory for storing progress files and error logs
        --max-orders: Limit on number of orders to process (for testing)
        --collection-name: Name of ChromaDB collection for storage
        --stats: Flag to display current processing statistics only
    
    Exit Codes:
        0: Successful completion
        1: Error during processing or validation
        130: User interrupted with Ctrl+C (SIGINT)
    
    Error Handling:
        - Validates date formats before processing
        - Ensures start_date is before end_date
        - Catches KeyboardInterrupt for graceful shutdown
        - Logs all errors with full traceback for debugging
    
    Integration Points:
        - Uses ExecutiveOrderBulkProcessor from processors module
        - Relies on environment variables loaded via dotenv
        - Uses centralized logging from utils module
        - Outputs progress to specified directory for resumable operations
    
    Python Learning Notes:
        - argparse.RawDescriptionHelpFormatter: Preserves formatting in help text
        - epilog=__doc__: Uses module docstring as additional help text
        - KeyboardInterrupt: Special exception raised when user presses Ctrl+C
        - traceback.print_exc(): Prints full exception traceback for debugging
        - Multiple exit codes: Different codes indicate different failure modes
        - f-strings with formatting: {value:,} adds thousand separators
        - Conditional logic: Validates inputs before expensive operations
    """
    parser = argparse.ArgumentParser(
        description="Process Executive Orders from Federal Register API using hierarchical chunking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Positional arguments
    parser.add_argument(
        "start_date",
        help="Start date for executive order retrieval in YYYY-MM-DD format",
        type=str,
    )
    parser.add_argument(
        "end_date",
        help="End date for executive order retrieval in YYYY-MM-DD format",
        type=str,
    )

    # Optional arguments
    parser.add_argument(
        "--output-dir",
        default="raw-data/executive_orders_data",
        help="Output directory for progress and error logs (default: raw-data/executive_orders_data)",
    )
    parser.add_argument(
        "--max-orders",
        type=int,
        help="Maximum number of executive orders to process (default: all)",
    )
    parser.add_argument(
        "--collection-name",
        default="federal-executive-orders",
        help="ChromaDB collection name (default: federal-executive-orders)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show current processing statistics without processing",
    )

    args = parser.parse_args()

    # Initialize logger
    logger = get_logger(__name__)

    # Validate date formats
    if not validate_date_format(args.start_date):
        logger.error(
            f"Invalid start_date format: {args.start_date}. Use YYYY-MM-DD format."
        )
        sys.exit(1)

    if not validate_date_format(args.end_date):
        logger.error(
            f"Invalid end_date format: {args.end_date}. Use YYYY-MM-DD format."
        )
        sys.exit(1)

    # Validate date range
    if args.start_date > args.end_date:
        logger.error(
            f"Start date ({args.start_date}) must be before end date ({args.end_date})"
        )
        sys.exit(1)

    try:
        # Initialize the bulk processor
        processor = ExecutiveOrderBulkProcessor(
            output_dir=args.output_dir,
            collection_name=args.collection_name,
        )

        if args.stats:
            # Show statistics only
            stats = processor.get_processing_stats(args.start_date, args.end_date)
            print("\nCurrent Processing Statistics:")
            print(f"  Date range: {stats['date_range']}")
            print(f"  Total available: {stats['total_available']:,}")
            print(f"  Already processed: {stats['processed_count']:,}")
            print(f"  Remaining: {stats['remaining_count']:,}")
            print(f"  Progress: {stats['progress_percentage']:.1f}%")
            print(f"  Collection: {stats['collection_name']}")
            print(f"  Output directory: {stats['output_dir']}")
            return

        # Run the bulk processing
        logger.info(
            f"Starting to process Executive Orders from {args.start_date} to {args.end_date}"
        )

        results = processor.process_executive_orders(
            start_date=args.start_date,
            end_date=args.end_date,
            max_orders=args.max_orders,
        )

        # Print final results
        print(f"\n🎉 Executive Order processing completed!")
        print(f"Date range: {args.start_date} to {args.end_date}")
        print(f"Processed: {results['processed_count']:,} orders")
        print(f"Failed: {results['failed_count']:,} orders")
        print(f"Skipped (already in DB): {results['skipped_count']:,} orders")
        print(f"Success rate: {results['success_rate']:.1%}")
        print(f"Total time: {results['elapsed_time']/60:.1f} minutes")

        # Exit with appropriate code
        if results["failed_count"] > 0:
            sys.exit(1)  # Exit with error if any failures

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Processing interrupted by user")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
