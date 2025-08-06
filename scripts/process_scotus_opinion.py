#!/usr/bin/env python3
"""
Script to process a single SCOTUS opinion with verbose logging support.

This script provides a simple interface for processing individual Supreme Court
opinions through the complete pipeline with optional verbose output.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.governmentreporter.processors import SCOTUSOpinionProcessor


def setup_logger(opinion_id: str, verbose: bool) -> logging.Logger:
    """Set up logger with optional verbose output."""
    logger = logging.getLogger("scotus_processor")

    if verbose:
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"scotus_opinion_{opinion_id}_{timestamp}.log"

        # Set up file handler for verbose output
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Also add console handler for INFO level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        logger.setLevel(logging.DEBUG)
        logger.info(f"Verbose logging enabled. Log file: {log_file}")
    else:
        # Only console output for normal mode
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)

    return logger


def process_opinion(opinion_id: str, verbose: bool = False) -> bool:
    """Process a single SCOTUS opinion.

    Args:
        opinion_id: The Court Listener opinion ID
        verbose: Whether to enable verbose logging

    Returns:
        True if successful, False otherwise
    """
    # Load environment variables
    load_dotenv()

    # Set up logger
    logger = setup_logger(opinion_id, verbose)

    try:
        logger.info(f"Processing SCOTUS opinion {opinion_id}...")

        # Create processor with logger if verbose
        processor = SCOTUSOpinionProcessor(logger=logger if verbose else None)

        # Process and store the opinion
        result = processor.process_and_store(
            document_id=str(opinion_id), collection_name="federal_court_scotus_opinions"
        )

        if result["success"]:
            logger.info(f"✅ Successfully processed opinion {opinion_id}")
            logger.info(f"   Chunks processed: {result['chunks_processed']}")
            logger.info(f"   Chunks stored: {result['chunks_stored']}")

            if verbose:
                logger.debug(f"Processing result: {result}")

            return True
        else:
            logger.error(f"❌ Failed to process opinion: {result['error']}")
            return False

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if verbose:
            logger.exception("Full exception details:")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process a single SCOTUS opinion with hierarchical chunking"
    )
    parser.add_argument("opinion_id", help="The Court Listener opinion ID to process")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging to file and console",
    )

    args = parser.parse_args()

    # Process the opinion
    success = process_opinion(args.opinion_id, args.verbose)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
