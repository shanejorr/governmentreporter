#!/usr/bin/env python3
"""
Script to download all US Supreme Court opinions from CourtListener API since 1900.

This script uses the CourtListener API to iterate through all SCOTUS opinions,
processes each one through the complete pipeline (metadata generation, embeddings),
and stores them in ChromaDB.
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from governmentreporter.processors import SCOTUSBulkProcessor


def main() -> None:
    """Main entry point for the script."""
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
            rate_limit_delay=args.rate_limit_delay,
            collection_name=args.collection_name,
        )

        if args.count_only:
            count = processor.get_total_count()
            print(f"Total SCOTUS opinions since {args.since_date}: {count:,}")
            return

        if args.stats:
            stats = processor.get_processing_stats()
            print("Current Processing Statistics:")
            print(f"  Total available: {stats['total_available']:,}")
            print(f"  Already processed: {stats['processed_count']:,}")
            print(f"  Remaining: {stats['remaining_count']:,}")
            print(f"  Progress: {stats['progress_percentage']:.1f}%")
            print(f"  Since date: {stats['since_date']}")
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
