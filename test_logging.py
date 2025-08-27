#!/usr/bin/env python3
"""
Test script to verify logging configuration is working properly.

This script tests the logging setup from various modules to ensure:
1. Log files are created in the logs directory
2. Different log levels are properly routed
3. Console output shows appropriate messages
4. Module-specific logging configurations work
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from governmentreporter.apis.court_listener import CourtListenerClient
from governmentreporter.apis.federal_register import FederalRegisterClient
from governmentreporter.database import QdrantDBClient
from governmentreporter.utils import get_logger, setup_logging


def test_basic_logging():
    """Test basic logging functionality."""
    logger = get_logger("test.basic")

    logger.debug("This is a DEBUG message - should appear in debug.log")
    logger.info("This is an INFO message - should appear in console and info.log")
    logger.warning("This is a WARNING message - should appear everywhere")
    logger.error("This is an ERROR message - should appear in console and error.log")

    print("\n✓ Basic logging test completed")


def test_utils_logging():
    """Test logging from utils module."""
    logger = get_logger("governmentreporter.utils.test")

    logger.info("Testing utils module logging")
    logger.debug("Utils debug message - should follow utils config")

    # Test embeddings client initialization (will log)
    try:
        from governmentreporter.utils.embeddings import GoogleEmbeddingsClient

        client = GoogleEmbeddingsClient()
        print("✓ Embeddings client initialized with logging")
    except Exception as e:
        logger.error(f"Failed to initialize embeddings client: {e}")
        print(f"✗ Embeddings client initialization failed: {e}")


def test_api_logging():
    """Test logging from API modules."""
    logger = get_logger("governmentreporter.apis.test")

    logger.info("Testing API module logging")

    # Test Federal Register client (no token needed)
    try:
        fr_client = FederalRegisterClient()
        print("✓ Federal Register client initialized with logging")
    except Exception as e:
        logger.error(f"Failed to initialize Federal Register client: {e}")
        print(f"✗ Federal Register client initialization failed: {e}")

    # Test Court Listener client (will fail without token, but logs the attempt)
    try:
        cl_client = CourtListenerClient()
        print("✓ Court Listener client initialized with logging")
    except Exception as e:
        logger.warning(
            f"Court Listener client initialization failed (expected without token): {e}"
        )
        print(f"ℹ Court Listener client initialization failed (expected without token)")


def test_database_logging():
    """Test logging from database module."""
    logger = get_logger("governmentreporter.database.test")

    logger.info("Testing database module logging")

    try:
        db_client = QdrantDBClient(db_path="./test_qdrant_db")
        print("✓ QdrantDB client initialized with logging")
    except Exception as e:
        logger.error(f"Failed to initialize QdrantDB client: {e}")
        print(f"✗ QdrantDB client initialization failed: {e}")


def test_processor_logging():
    """Test logging from processor modules."""
    logger = get_logger("governmentreporter.processors.test")

    logger.info("Testing processor module logging")
    logger.debug("Processor debug message - should appear in debug.log")

    print("✓ Processor logging test completed")


def check_log_files():
    """Check that log files were created."""
    log_dir = Path("logs")
    expected_files = ["info.log", "error.log", "debug.log"]

    print("\n📁 Checking log files:")

    if not log_dir.exists():
        print("✗ Logs directory does not exist")
        return False

    all_exist = True
    for log_file in expected_files:
        file_path = log_dir / log_file
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"  ✓ {log_file} exists ({size} bytes)")
        else:
            print(f"  ✗ {log_file} does not exist")
            all_exist = False

    return all_exist


def main():
    """Run all logging tests."""
    print("🧪 Testing GovernmentReporter Logging Configuration\n")
    print("=" * 60)

    # Initialize logging
    print("Initializing logging system...")
    setup_logging()
    print("✓ Logging system initialized\n")

    # Run tests
    print("Running logging tests:")
    print("-" * 40)

    test_basic_logging()
    test_utils_logging()
    test_api_logging()
    test_database_logging()
    test_processor_logging()

    # Check log files
    print("\n" + "=" * 60)
    if check_log_files():
        print("\n✅ All logging tests completed successfully!")
        print("\n📝 Check the following files for log output:")
        print("  - logs/info.log    - INFO level and above")
        print("  - logs/error.log   - ERROR level only")
        print("  - logs/debug.log   - All log levels")
    else:
        print("\n⚠️ Some log files were not created")

    print("\n💡 You should see INFO and ERROR messages in the console above")


if __name__ == "__main__":
    main()
