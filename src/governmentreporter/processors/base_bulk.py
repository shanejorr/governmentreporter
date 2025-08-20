"""
Base Bulk Processing Framework for Large-Scale Document Processing

This module provides the foundational infrastructure for processing thousands of
government documents in batch operations. It implements a robust framework for
handling large-scale document processing with progress tracking, error recovery,
and performance monitoring.

Core Features:
    - Progress persistence across interruptions and restarts
    - Comprehensive error logging with document-specific details
    - Performance metrics and rate limiting
    - Automatic resume capability for long-running operations
    - Memory-efficient processing with configurable batch sizes

Design Patterns:
    - Abstract Base Class: Defines common bulk processing interface
    - Template Method: Provides processing workflow framework
    - Strategy Pattern: Allows different document processing strategies
    - Observer Pattern: Progress tracking and reporting system

Key Components:
    - BaseBulkProcessor: Abstract base class for all bulk processors
    - Progress tracking: JSON-based persistence for resume capability
    - Error logging: JSONL format for structured error analysis
    - Rate limiting: Configurable delays to respect API limits

Python Learning Notes:
    - ABC (Abstract Base Class) enforces implementation of required methods
    - Set data structure provides O(1) lookup for processed document tracking
    - Path class from pathlib provides modern file system operations
    - Context managers (with statements) ensure proper file handling
    - Exception handling prevents single failures from stopping entire process
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set
from abc import ABC, abstractmethod


class BaseBulkProcessor(ABC):
    """Base class for bulk document processing with common functionality.

    This abstract base class provides shared functionality for:
    - Progress tracking and persistence
    - Error logging
    - Performance metrics
    - Database duplicate checking

    Subclasses must implement:
    - _process_single_document: Process one document
    - get_documents_iterator: Iterate through documents
    - get_total_count: Get total document count
    """

    def __init__(
        self,
        output_dir: str,
        collection_name: str,
        rate_limit_delay: float = 0.75,
    ):
        """Initialize the base bulk processor.

        Args:
            output_dir: Directory to store progress and error logs
            collection_name: ChromaDB collection name for storage
            rate_limit_delay: Delay between API requests in seconds
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.collection_name = collection_name
        self.rate_limit_delay = rate_limit_delay

        # Progress tracking files
        self.progress_file = self.output_dir / "processing_progress.json"
        self.error_log_file = self.output_dir / "error_log.jsonl"
        self.processed_ids: Set[str] = set()

        # Load existing progress
        self._load_progress()

    def _load_progress(self) -> None:
        """Load previously processed document IDs from progress file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r") as f:
                    progress_data = json.load(f)
                    self.processed_ids = set(progress_data.get("processed_ids", []))
                    print(
                        f"Loaded progress: {len(self.processed_ids)} documents already processed"
                    )
            except Exception as e:
                print(f"Warning: Could not load progress file: {e}")
                self.processed_ids = set()

    def _save_progress(self) -> None:
        """Save current progress to file."""
        progress_data = {
            "processed_ids": list(self.processed_ids),
            "last_updated": datetime.now().isoformat(),
            "total_processed": len(self.processed_ids),
            "collection_name": self.collection_name,
        }

        # Add any subclass-specific data
        progress_data.update(self._get_additional_progress_data())

        with open(self.progress_file, "w") as f:
            json.dump(progress_data, f, indent=2)

    def _log_error(
        self, document_id: str, error: str, document_data: Optional[Dict] = None
    ) -> None:
        """Log errors to error log file."""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "document_id": document_id,
            "error": error,
            "document_data": document_data,
        }

        with open(self.error_log_file, "a") as f:
            f.write(json.dumps(error_entry) + "\n")

    def process_documents(
        self, max_documents: Optional[int] = None, **kwargs
    ) -> Dict[str, Any]:
        """Process documents through the pipeline.

        Args:
            max_documents: Maximum number of documents to process (None for all)
            **kwargs: Additional arguments passed to get_documents_iterator

        Returns:
            Dictionary with processing statistics
        """
        print(f"Starting document processing")
        print(f"Output directory: {self.output_dir}")
        print(f"Collection: {self.collection_name}")

        # Get total count if available
        total_count = self.get_total_count(**kwargs)
        if total_count > 0:
            print(f"Total documents available: {total_count:,}")
            remaining = total_count - len(self.processed_ids)
            print(f"Remaining to process: {remaining:,}")

        start_time = time.time()
        processed_count = 0
        failed_count = 0
        skipped_count = 0

        try:
            # Iterate through all documents
            for document_summary in self.get_documents_iterator(
                max_results=max_documents, **kwargs
            ):
                document_id = self._extract_document_id(document_summary)

                # Check if already processed
                if document_id in self.processed_ids:
                    skipped_count += 1
                    continue

                # Process the document
                success = self._process_single_document(document_summary)

                if success:
                    processed_count += 1
                    self.processed_ids.add(document_id)
                else:
                    failed_count += 1

                # Save progress periodically
                if (processed_count + failed_count) % self._get_save_interval() == 0:
                    self._save_progress()

                # Show progress
                elapsed = time.time() - start_time
                if elapsed > 0 and (processed_count + failed_count) % 10 == 0:
                    rate = processed_count / elapsed if processed_count > 0 else 0
                    print(
                        f"Progress: {processed_count} processed, {failed_count} failed, "
                        f"{skipped_count} skipped, {rate:.2f} docs/sec"
                    )

                # Respect rate limits
                if self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)

        except KeyboardInterrupt:
            print("\n⚠️  Processing interrupted by user")
        except Exception as e:
            print(f"\n❌ Processing failed with error: {e}")
        finally:
            # Save final progress
            self._save_progress()

            # Print summary
            elapsed = time.time() - start_time
            print(f"\n{'='*60}")
            print(f"Processing Summary:")
            print(f"  Total processed: {processed_count}")
            print(f"  Total failed: {failed_count}")
            print(f"  Total skipped: {skipped_count}")
            print(f"  Time elapsed: {elapsed/60:.1f} minutes")
            print(
                f"  Average rate: {processed_count/elapsed:.2f} docs/sec"
                if elapsed > 0
                else ""
            )
            print(f"  Progress saved to: {self.progress_file}")
            if failed_count > 0:
                print(f"  Error log: {self.error_log_file}")

        return {
            "processed_count": processed_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "elapsed_time": elapsed,
            "total_available": total_count,
            "success_rate": (
                processed_count / (processed_count + failed_count)
                if (processed_count + failed_count) > 0
                else 0
            ),
        }

    # Abstract methods that subclasses must implement

    @abstractmethod
    def _process_single_document(self, document_summary: Dict[str, Any]) -> bool:
        """Process a single document through the pipeline.

        Args:
            document_summary: Document metadata from the listing API

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_documents_iterator(self, **kwargs):
        """Return an iterator over documents to process.

        Args:
            **kwargs: Arguments specific to the document type

        Yields:
            Document summaries
        """
        pass

    @abstractmethod
    def get_total_count(self, **kwargs) -> int:
        """Get total count of documents to process.

        Args:
            **kwargs: Arguments specific to the document type

        Returns:
            Total number of documents matching the criteria
        """
        pass

    @abstractmethod
    def _extract_document_id(self, document_summary: Dict[str, Any]) -> str:
        """Extract the document ID from a document summary.

        Args:
            document_summary: Document metadata

        Returns:
            Document ID as string
        """
        pass

    # Optional methods that subclasses can override

    def _get_additional_progress_data(self) -> Dict[str, Any]:
        """Get additional data to save in progress file.

        Subclasses can override this to add custom progress data.

        Returns:
            Dictionary of additional progress data
        """
        return {}

    def _get_save_interval(self) -> int:
        """Get the interval for saving progress.

        Returns:
            Number of documents between progress saves
        """
        return 10
