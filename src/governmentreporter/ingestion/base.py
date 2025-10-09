"""
Abstract base class for document ingesters.

This module provides the shared foundation for all document ingestion
pipelines. It defines the common interface and shared logic that all
concrete ingesters (SCOTUS, Executive Orders, etc.) must implement.

The base class handles:
- Progress tracking setup
- Performance monitoring
- Error handling patterns
- Batch processing framework
- Statistics reporting

Python Learning Notes:
    - Abstract Base Classes (ABC) enforce implementation of required methods
    - Template Method pattern: base class defines structure, subclasses fill in details
    - Shared logic reduces duplication across ingester implementations
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..database.ingestion import QdrantIngestionClient
from ..database.qdrant import QdrantDBClient
from ..processors.embeddings import EmbeddingGenerator
from ..utils.monitoring import PerformanceMonitor
from .progress import ProgressTracker

logger = logging.getLogger(__name__)


class DocumentIngester(ABC):
    """
    Abstract base class for document ingesters.

    This class provides the template for all document ingestion pipelines.
    Subclasses must implement abstract methods for document-specific logic
    while inheriting common functionality like progress tracking, monitoring,
    and batch processing.

    The ingestion pipeline follows these steps:
    1. Fetch document IDs from source API
    2. Filter out already-processed documents
    3. Process documents in batches:
       a. Fetch document content
       b. Build payloads (chunking + metadata extraction)
       c. Generate embeddings
       d. Store in Qdrant
    4. Track progress and report statistics

    Attributes:
        start_date: Start date for document range (YYYY-MM-DD)
        end_date: End date for document range (YYYY-MM-DD)
        batch_size: Number of documents to process per batch
        dry_run: If True, don't actually store in Qdrant
        progress_tracker: SQLite-based progress tracking
        embedding_generator: OpenAI embedding generator
        qdrant_client: Qdrant ingestion client
        performance_monitor: Performance tracking and statistics

    Example:
        # Concrete implementation
        class MyIngester(DocumentIngester):
            def _get_collection_name(self):
                return "my_collection"

            def _fetch_document_ids(self):
                return ["doc1", "doc2", "doc3"]

            def _process_single_document(self, doc_id, batch_docs, batch_embeds):
                # Implementation here
                return True

        # Usage
        ingester = MyIngester(
            start_date="2020-01-01",
            end_date="2024-12-31"
        )
        ingester.run()
    """

    def __init__(
        self,
        start_date: str,
        end_date: str,
        batch_size: int = 50,
        dry_run: bool = False,
        progress_db: str = "ingestion.db",
        qdrant_db_path: str = "./data/qdrant/qdrant_db",
        document_type: str = "generic",
        shared_db_client: Optional[QdrantDBClient] = None,
    ):
        """
        Initialize the document ingester.

        Args:
            start_date: Start date for document range (YYYY-MM-DD)
            end_date: End date for document range (YYYY-MM-DD)
            batch_size: Number of documents to process in each batch
            dry_run: If True, don't actually store documents
            progress_db: Path to SQLite database for progress tracking
            qdrant_db_path: Path to Qdrant database directory
            document_type: Type identifier for progress tracking
            shared_db_client: Optional pre-initialized QdrantDBClient for shared access.
                            When provided, multiple ingesters can share the same database
                            connection, which is required for local Qdrant storage.
        """
        self.start_date = start_date
        self.end_date = end_date
        self.batch_size = batch_size
        self.dry_run = dry_run

        # Initialize tracking and monitoring
        self.progress_tracker = ProgressTracker(progress_db, document_type)
        self.embedding_generator = EmbeddingGenerator()

        # Create QdrantIngestionClient for this collection
        # If a shared_db_client is provided, use it; otherwise create a new connection
        # This allows multiple ingesters to share the same underlying database client,
        # which is necessary because Qdrant local storage only allows one client
        # at a time to access the same database path
        self.qdrant_client = QdrantIngestionClient(
            collection_name=self._get_collection_name(),
            db_path=qdrant_db_path,
            db_client=shared_db_client,
        )

        self.performance_monitor = PerformanceMonitor()

        # Reset any stuck documents from previous runs
        self.progress_tracker.reset_processing_status()

    @abstractmethod
    def _get_collection_name(self) -> str:
        """
        Get the Qdrant collection name for this document type.

        Returns:
            Collection name (e.g., "supreme_court_opinions")
        """
        pass

    @abstractmethod
    def _fetch_document_ids(self) -> List[str]:
        """
        Fetch all document IDs to process from the source API.

        This method should query the government API and return a list
        of document IDs within the date range.

        Returns:
            List of document IDs to process
        """
        pass

    @abstractmethod
    def _process_single_document(
        self,
        doc_id: str,
        batch_documents: List[Dict[str, Any]],
        batch_embeddings: List[List[float]],
    ) -> bool:
        """
        Process a single document and add to batch.

        This method should:
        1. Fetch the document from the API
        2. Build payloads (chunking + metadata)
        3. Generate embeddings
        4. Add to batch lists

        Args:
            doc_id: Document identifier to process
            batch_documents: List to append document payloads to
            batch_embeddings: List to append embeddings to

        Returns:
            True if successful, False if failed
        """
        pass

    def run(self) -> None:
        """
        Execute the main ingestion pipeline.

        This method orchestrates the entire ingestion process:
        1. Fetches all document IDs
        2. Filters out already-processed documents
        3. Processes remaining documents in batches
        4. Reports final statistics
        """
        logger.info(
            f"Starting ingestion for date range: {self.start_date} to {self.end_date}"
        )

        if self.dry_run:
            logger.info("DRY RUN MODE - No documents will be stored")

        # Start a new ingestion run
        run_id = self.progress_tracker.start_run(
            self.start_date,
            self.end_date,
            {"batch_size": self.batch_size, "dry_run": self.dry_run},
        )

        try:
            # Fetch document IDs
            doc_ids = self._fetch_document_ids()

            if not doc_ids:
                logger.warning("No documents found in the specified date range")
                return

            logger.info(f"Found {len(doc_ids)} total documents")

            # Add all documents to tracker (will ignore duplicates)
            for doc_id in doc_ids:
                self.progress_tracker.add_document(doc_id)

            # Get pending documents
            pending_ids = self.progress_tracker.get_pending_documents()
            logger.info(f"Processing {len(pending_ids)} pending documents")

            if not pending_ids:
                logger.info("All documents have already been processed")
                return

            # Process in batches
            self.performance_monitor.start()
            self._process_documents_batch(pending_ids)

            # Print final statistics
            self._print_final_statistics()

        finally:
            # Mark run as completed
            self.progress_tracker.end_run(run_id)
            self.progress_tracker.close()

    def _process_documents_batch(self, doc_ids: List[str]) -> None:
        """
        Process documents in batches.

        Args:
            doc_ids: List of document IDs to process
        """
        total = len(doc_ids)
        processed = 0

        for i in range(0, total, self.batch_size):
            batch_ids = doc_ids[i : i + self.batch_size]
            logger.info(
                f"Processing batch {i // self.batch_size + 1} ({len(batch_ids)} documents)"
            )

            batch_documents = []
            batch_embeddings = []

            for doc_id in batch_ids:
                processed += 1

                # Update progress bar
                self.performance_monitor.print_progress(
                    processed, total, "Processing documents"
                )

                # Process individual document
                success = self._process_single_document(
                    doc_id, batch_documents, batch_embeddings
                )

                if success:
                    self.performance_monitor.record_document()
                else:
                    self.performance_monitor.record_document(failed=True)

            # Store batch in Qdrant
            if batch_documents and not self.dry_run:
                self._store_batch(batch_documents, batch_embeddings)

    def _store_batch(
        self, documents: List[Dict[str, Any]], embeddings: List[List[float]]
    ) -> None:
        """
        Store a batch of documents in Qdrant.

        Args:
            documents: List of document payloads
            embeddings: Corresponding embedding vectors
        """
        try:
            logger.info(f"Storing batch of {len(documents)} chunks in Qdrant")

            successful, failed = self.qdrant_client.batch_upsert_documents(
                documents, embeddings, batch_size=100
            )

            logger.info(f"Stored {successful} chunks, {failed} failed")

        except Exception as e:
            logger.error(f"Error storing batch in Qdrant: {e}")

    def _print_final_statistics(self) -> None:
        """Print final ingestion statistics."""
        print("\n" + "=" * 60)
        print("INGESTION COMPLETE")
        print("=" * 60)

        # Get statistics from progress tracker
        stats = self.progress_tracker.get_statistics()

        print(f"Document Type: {stats['document_type']}")
        print(f"Total Documents: {stats['total']}")
        print(f"Completed: {stats['completed']}")
        print(f"Failed: {stats['failed']}")
        print(f"Pending: {stats['pending']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")

        if stats["avg_processing_time_ms"]:
            print(f"Avg Processing Time: {stats['avg_processing_time_ms']:.0f}ms")

        # Get performance statistics
        perf_stats = self.performance_monitor.get_statistics()
        print(f"\nTotal Time: {perf_stats['elapsed_time_formatted']}")
        print(f"Throughput: {perf_stats['throughput_per_minute']:.1f} docs/minute")

        # Get Qdrant statistics
        qdrant_stats = self.qdrant_client.get_collection_stats()
        print(f"\nQdrant Collection: {qdrant_stats.get('collection_name')}")
        print(f"Total Chunks in Collection: {qdrant_stats.get('total_documents', 0)}")

        # Show failed documents if any
        if stats["failed"] > 0:
            print("\n" + "=" * 60)
            print("FAILED DOCUMENTS (showing up to 10):")
            print("-" * 60)
            for failed_doc in stats["failed_documents"]:
                print(f"ID: {failed_doc['document_id']}")
                print(f"Error: {failed_doc['error']}")
                print(f"Failed At: {failed_doc['failed_at']}")
                print("-" * 40)
