#!/usr/bin/env python3
"""
Batch ingestion script for Executive Orders from Federal Register API.

This script fetches Executive Orders within a specified date range,
processes them through the document chunking and metadata extraction pipeline,
generates embeddings, and stores them in Qdrant for semantic search.

The script supports:
- Date range filtering for targeted ingestion
- Batch processing for efficient API usage
- Comprehensive error handling and logging
- Performance monitoring and ETA calculation
- Text caching to avoid duplicate fetches

Usage:
    python ingest_executive_orders.py --start-date 2021-01-20 --end-date 2024-12-31
    python ingest_executive_orders.py --start-date 2017-01-20 --end-date 2021-01-20 --batch-size 50
    python ingest_executive_orders.py --start-date 2021-01-20 --end-date 2024-12-31 --dry-run
"""

import argparse
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Handle both module and script execution
try:
    from .progress_tracker import ProgressTracker
except ImportError:
    from progress_tracker import ProgressTracker

from governmentreporter.apis.base import Document
from governmentreporter.apis.federal_register import FederalRegisterClient
from governmentreporter.database.ingestion import QdrantIngestionClient
from governmentreporter.processors.build_payloads import build_payloads_from_document
from governmentreporter.processors.embeddings import EmbeddingGenerator
from governmentreporter.utils.monitoring import PerformanceMonitor, setup_logging

logger = logging.getLogger(__name__)


class ExecutiveOrderIngester:
    """
    Handles batch ingestion of Executive Orders into Qdrant.

    This class orchestrates the complete ingestion pipeline:
    1. Fetches Executive Order metadata from Federal Register API
    2. Retrieves raw text for each order
    3. Tracks progress using SQLite
    4. Processes documents through chunking and metadata extraction
    5. Generates embeddings for semantic search
    6. Stores everything in Qdrant vector database
    """

    def __init__(
        self,
        start_date: str,
        end_date: str,
        batch_size: int = 50,
        dry_run: bool = False,
        progress_db: str = "executive_orders_ingestion.db",
        qdrant_db_path: str = "./qdrant_db",
    ):
        """
        Initialize the Executive Order ingester.

        Args:
            start_date: Start date for order range (YYYY-MM-DD)
            end_date: End date for order range (YYYY-MM-DD)
            batch_size: Number of documents to process in each batch
            dry_run: If True, don't actually store documents
            progress_db: Path to SQLite database for progress tracking
            qdrant_db_path: Path to Qdrant database directory
        """
        self.start_date = start_date
        self.end_date = end_date
        self.batch_size = batch_size
        self.dry_run = dry_run

        # Initialize components
        self.api_client = FederalRegisterClient()
        self.progress_tracker = ProgressTracker(progress_db, "executive_order")
        self.embedding_generator = EmbeddingGenerator()
        self.qdrant_client = QdrantIngestionClient("executive_orders", qdrant_db_path)
        self.performance_monitor = PerformanceMonitor()

        # Cache for raw text URLs to avoid duplicate fetches
        self.text_url_cache = {}

        # Reset any stuck documents from previous runs
        self.progress_tracker.reset_processing_status()

    def run(self) -> None:
        """
        Execute the main ingestion pipeline.

        This method:
        1. Fetches all Executive Orders in the date range
        2. Filters out already-processed documents
        3. Processes remaining documents in batches
        4. Reports final statistics
        """
        logger.info(
            f"Starting Executive Order ingestion for date range: {self.start_date} to {self.end_date}"
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
            # Fetch Executive Orders
            orders = self._fetch_executive_orders()

            if not orders:
                logger.warning("No Executive Orders found in the specified date range")
                return

            logger.info(f"Found {len(orders)} total Executive Orders")

            # Add all orders to tracker with metadata
            for order in orders:
                order_id = order.get("document_number", "")
                if order_id:
                    self.progress_tracker.add_document(
                        order_id,
                        metadata={
                            "title": order.get("title", ""),
                            "executive_order_number": order.get(
                                "executive_order_number", ""
                            ),
                            "signing_date": order.get("signing_date", ""),
                            "publication_date": order.get("publication_date", ""),
                        },
                    )

            # Get pending documents
            pending_ids = self.progress_tracker.get_pending_documents()
            logger.info(f"Processing {len(pending_ids)} pending Executive Orders")

            if not pending_ids:
                logger.info("All Executive Orders have already been processed")
                return

            # Build lookup for order data
            orders_lookup = {
                order["document_number"]: order
                for order in orders
                if "document_number" in order
            }

            # Process in batches
            self.performance_monitor.start()
            self._process_orders_batch(pending_ids, orders_lookup)

            # Print final statistics
            self._print_final_statistics()

        finally:
            # Mark run as completed
            self.progress_tracker.end_run(run_id)
            self.progress_tracker.close()

    def _fetch_executive_orders(self) -> List[Dict[str, Any]]:
        """
        Fetch all Executive Orders in the date range.

        Returns:
            List of Executive Order metadata dictionaries
        """
        logger.info("Fetching Executive Orders from Federal Register API...")

        all_orders = []

        try:
            # Use the list_executive_orders method with date filtering
            orders = self.api_client.list_executive_orders(
                start_date=self.start_date, end_date=self.end_date
            )

            # Process the generator and collect all orders
            for order in orders:
                all_orders.append(order)

                # Log progress every 20 orders
                if len(all_orders) % 20 == 0:
                    logger.info(f"Fetched {len(all_orders)} Executive Orders...")

            logger.info(f"Successfully fetched {len(all_orders)} Executive Orders")

        except Exception as e:
            logger.error(f"Error fetching Executive Orders: {e}")

        return all_orders

    def _process_orders_batch(
        self, order_ids: List[str], orders_lookup: Dict[str, Dict[str, Any]]
    ) -> None:
        """
        Process Executive Orders in batches.

        Args:
            order_ids: List of document numbers to process
            orders_lookup: Dictionary mapping document numbers to order metadata
        """
        total = len(order_ids)
        processed = 0

        for i in range(0, total, self.batch_size):
            batch_ids = order_ids[i : i + self.batch_size]
            logger.info(
                f"Processing batch {i//self.batch_size + 1} ({len(batch_ids)} orders)"
            )

            batch_documents = []
            batch_embeddings = []

            for order_id in batch_ids:
                processed += 1

                # Update progress bar
                self.performance_monitor.print_progress(
                    processed, total, f"Processing Executive Orders"
                )

                # Get order metadata
                order_metadata = orders_lookup.get(order_id)
                if not order_metadata:
                    logger.warning(f"No metadata found for order {order_id}")
                    self.progress_tracker.mark_failed(order_id, "Metadata not found")
                    self.performance_monitor.record_document(failed=True)
                    continue

                # Process individual order
                success = self._process_single_order(
                    order_id, order_metadata, batch_documents, batch_embeddings
                )

                if success:
                    self.performance_monitor.record_document()
                else:
                    self.performance_monitor.record_document(failed=True)

            # Store batch in Qdrant
            if batch_documents and not self.dry_run:
                self._store_batch(batch_documents, batch_embeddings)

    def _process_single_order(
        self,
        order_id: str,
        order_metadata: Dict[str, Any],
        batch_documents: List[Dict[str, Any]],
        batch_embeddings: List[List[float]],
    ) -> bool:
        """
        Process a single Executive Order.

        Args:
            order_id: Document number of the order to process
            order_metadata: Metadata about the order from API
            batch_documents: List to append document chunks to
            batch_embeddings: List to append embeddings to

        Returns:
            True if processing succeeded, False otherwise
        """
        start_time = time.time()

        try:
            # Mark as processing
            self.progress_tracker.mark_processing(order_id)

            # Get raw text URL
            raw_text_url = order_metadata.get("raw_text_url")
            if not raw_text_url:
                raise ValueError(f"No raw text URL for order {order_id}")

            # Fetch raw text (with caching)
            if raw_text_url in self.text_url_cache:
                raw_text = self.text_url_cache[raw_text_url]
                logger.debug(f"Using cached text for order {order_id}")
            else:
                logger.debug(f"Fetching raw text for order {order_id}")
                raw_text = self.api_client.get_executive_order_text(raw_text_url)
                self.text_url_cache[raw_text_url] = raw_text

            if not raw_text:
                raise ValueError(f"Could not fetch raw text for order {order_id}")

            # Create Document object for processing
            document = Document(
                id=order_id,
                title=order_metadata.get("title", ""),
                date=order_metadata.get(
                    "signing_date", order_metadata.get("publication_date", "")
                ),
                type="Executive Order",
                source="Federal Register",
                content=raw_text,
                metadata={
                    "executive_order_number": order_metadata.get(
                        "executive_order_number"
                    ),
                    "president": (
                        order_metadata.get("president", {}).get("name")
                        if "president" in order_metadata
                        else None
                    ),
                    "signing_date": order_metadata.get("signing_date"),
                    "publication_date": order_metadata.get("publication_date"),
                    "document_number": order_id,
                    "agencies": order_metadata.get("agencies", []),
                    "topics": order_metadata.get("topics", []),
                },
                url=order_metadata.get("html_url", ""),
            )

            # Process through the pipeline
            logger.debug(f"Building payloads for order {order_id}")
            payloads = build_payloads_from_document(document)

            if not payloads:
                raise ValueError(f"No payloads generated for order {order_id}")

            logger.debug(f"Generated {len(payloads)} chunks for order {order_id}")

            # Generate embeddings for each chunk
            chunk_texts = [p["text"] for p in payloads]
            embeddings = self.embedding_generator.generate_batch_embeddings(chunk_texts)

            # Convert payloads to Qdrant format
            for payload, embedding in zip(payloads, embeddings):
                # Payload is already a dict
                doc_dict = payload
                doc_dict["document_id"] = order_id
                doc_dict["ingested_at"] = datetime.now().isoformat()

                batch_documents.append(doc_dict)
                batch_embeddings.append(embedding)

            # Mark as completed
            processing_time_ms = (time.time() - start_time) * 1000
            self.progress_tracker.mark_completed(order_id, int(processing_time_ms))

            return True

        except Exception as e:
            logger.error(f"Error processing order {order_id}: {e}")
            self.progress_tracker.mark_failed(order_id, str(e))
            return False

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

        # Show cache statistics
        print(f"\nText URL Cache Hits: {len(self.text_url_cache)} unique URLs cached")

        # Show failed documents if any
        if stats["failed"] > 0:
            print("\n" + "=" * 60)
            print("FAILED DOCUMENTS (showing up to 10):")
            print("-" * 60)
            for failed_doc in stats["failed_documents"]:
                print(f"Document Number: {failed_doc['document_id']}")
                print(f"Error: {failed_doc['error']}")
                print(f"Failed At: {failed_doc['failed_at']}")
                print("-" * 40)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Batch ingestion of Executive Orders from Federal Register"
    )

    parser.add_argument(
        "--start-date", required=True, help="Start date for order range (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--end-date", required=True, help="End date for order range (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Number of orders to process in each batch (default: 25)",
    )

    parser.add_argument(
        "--progress-db",
        default="executive_orders_ingestion.db",
        help="Path to SQLite progress database (default: executive_orders_ingestion.db)",
    )

    parser.add_argument(
        "--qdrant-db-path",
        default="./qdrant_db",
        help="Path to Qdrant database directory (default: ./qdrant_db)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without actually storing documents in Qdrant",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Validate dates
    try:
        start = datetime.strptime(args.start_date, "%Y-%m-%d")
        end = datetime.strptime(args.end_date, "%Y-%m-%d")

        if start > end:
            print("Error: Start date must be before end date")
            sys.exit(1)

    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format")
        sys.exit(1)

    # Setup logging
    setup_logging(args.verbose)

    # Run ingestion
    ingester = ExecutiveOrderIngester(
        start_date=args.start_date,
        end_date=args.end_date,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        progress_db=args.progress_db,
        qdrant_db_path=args.qdrant_db_path,
    )

    try:
        ingester.run()
    except KeyboardInterrupt:
        print("\n\nIngestion interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error during ingestion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
