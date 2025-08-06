#!/usr/bin/env python3
"""
Script to process US Executive Orders from the Federal Register API.

This script fetches executive orders within a specified date range,
processes each one through the complete pipeline (chunking, metadata generation, embeddings),
and stores them in ChromaDB.

Usage:
    uv run python scripts/process_executive_orders.py 2024-01-01 2024-06-30
    
    # Process all orders in 2024
    uv run python scripts/process_executive_orders.py 2024-01-01 2024-12-31
    
    # Process with custom output directory
    uv run python scripts/process_executive_orders.py 2024-01-01 2024-06-30 --output-dir my_data
    
    # Process only first 10 orders (for testing)
    uv run python scripts/process_executive_orders.py 2024-01-01 2024-12-31 --max-orders 10
    
    # Show statistics without processing
    uv run python scripts/process_executive_orders.py 2024-01-01 2024-06-30 --stats

Arguments:
    start_date: Start date in YYYY-MM-DD format
    end_date: End date in YYYY-MM-DD format

Options:
    --output-dir: Output directory for progress and error logs (default: raw-data/executive_orders_data)
    --max-orders: Maximum number of orders to process (default: all)
    --collection-name: ChromaDB collection name (default: federal-executive-orders)
    --stats: Show current processing statistics without processing
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.governmentreporter.processors import ExecutiveOrderBulkProcessor
from src.governmentreporter.utils import get_logger


def validate_date_format(date_str: str) -> bool:
    """Validate date string is in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if valid format, False otherwise
    """
    import re
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    return bool(re.match(pattern, date_str))


def main() -> None:
    """Main entry point for the script."""
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
        logger.error(f"Invalid start_date format: {args.start_date}. Use YYYY-MM-DD format.")
        sys.exit(1)
    
    if not validate_date_format(args.end_date):
        logger.error(f"Invalid end_date format: {args.end_date}. Use YYYY-MM-DD format.")
        sys.exit(1)
    
    # Validate date range
    if args.start_date > args.end_date:
        logger.error(f"Start date ({args.start_date}) must be before end date ({args.end_date})")
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
        logger.info(f"Starting to process Executive Orders from {args.start_date} to {args.end_date}")
        
        results = processor.process_executive_orders(
            start_date=args.start_date,
            end_date=args.end_date,
            max_orders=args.max_orders
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
        if results['failed_count'] > 0:
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