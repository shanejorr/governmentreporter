#!/usr/bin/env python3
"""
Batch ingestion script for Supreme Court opinions from CourtListener API.

This script fetches Supreme Court opinions within a specified date range,
processes them through the document chunking and metadata extraction pipeline,
generates embeddings, and stores them in Qdrant for semantic search.

The script supports:
- Date range filtering for targeted ingestion
- Resume capability through SQLite progress tracking
- Batch processing for efficient API usage
- Comprehensive error handling and logging
- Performance monitoring and ETA calculation

Usage:
    python ingest_scotus.py --start-date 2020-01-01 --end-date 2024-12-31
    python ingest_scotus.py --start-date 2020-01-01 --end-date 2024-12-31 --batch-size 100
    python ingest_scotus.py --start-date 2020-01-01 --end-date 2024-12-31 --dry-run
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

# Handle both module and script execution
try:
    from .progress_tracker import ProgressTracker
except ImportError:
    from progress_tracker import ProgressTracker

from governmentreporter.apis.court_listener import CourtListenerClient
from governmentreporter.database.ingestion import QdrantIngestionClient
from governmentreporter.processors.build_payloads import build_payloads_from_document
from governmentreporter.processors.embeddings import EmbeddingGenerator
from governmentreporter.utils.monitoring import PerformanceMonitor, setup_logging

logger = logging.getLogger(__name__)


class SCOTUSIngester:
    """
    Handles batch ingestion of Supreme Court opinions into Qdrant.

    This class orchestrates the complete ingestion pipeline:
    1. Fetches opinion IDs from CourtListener API
    2. Tracks progress using SQLite
    3. Processes documents through chunking and metadata extraction
    4. Generates embeddings for semantic search
    5. Stores everything in Qdrant vector database
    """

    def __init__(
        self,
        start_date: str,
        end_date: str,
        batch_size: int = 100,
        dry_run: bool = False,
        progress_db: str = "scotus_ingestion.db",
        qdrant_db_path: str = "./qdrant_db",
    ):
        """
        Initialize the SCOTUS ingester.

        Args:
            start_date: Start date for opinion range (YYYY-MM-DD)
            end_date: End date for opinion range (YYYY-MM-DD)
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
        self.api_client = CourtListenerClient()
        self.progress_tracker = ProgressTracker(progress_db, "scotus")
        self.embedding_generator = EmbeddingGenerator()
        self.qdrant_client = QdrantIngestionClient(
            "supreme_court_opinions", qdrant_db_path
        )
        self.performance_monitor = PerformanceMonitor()

        # Reset any stuck documents from previous runs
        self.progress_tracker.reset_processing_status()

    def run(self) -> None:
        """
        Execute the main ingestion pipeline.

        This method:
        1. Fetches all opinion IDs in the date range
        2. Filters out already-processed documents
        3. Processes remaining documents in batches
        4. Reports final statistics
        """
        logger.info(
            "Starting SCOTUS ingestion for date range: %s to %s",
            self.start_date,
            self.end_date,
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
            # Fetch opinion IDs
            opinion_ids = self._fetch_opinion_ids()

            if not opinion_ids:
                logger.warning("No opinions found in the specified date range")
                return

            logger.info("Found %d total opinions", len(opinion_ids))

            # Add all opinions to tracker (will ignore duplicates)
            for opinion_id in opinion_ids:
                self.progress_tracker.add_document(opinion_id)

            # Get pending documents
            pending_ids = self.progress_tracker.get_pending_documents()
            logger.info("Processing %d pending opinions", len(pending_ids))

            if not pending_ids:
                logger.info("All opinions have already been processed")
                return

            # Process in batches
            self.performance_monitor.start()
            self._process_opinions_batch(pending_ids)

            # Print final statistics
            self._print_final_statistics()

        finally:
            # Mark run as completed
            self.progress_tracker.end_run(run_id)
            self.progress_tracker.close()

    def _fetch_opinion_ids(self) -> List[str]:
        """
        Fetch all Supreme Court opinion IDs in the date range.

        This method fetches opinion IDs in batches to avoid timeout issues.
        It directly accesses the CourtListener API with pagination support
        to handle large date ranges that may contain thousands of opinions.

        Returns:
            List of opinion IDs to process
        """
        logger.info("Fetching opinion IDs from CourtListener API...")
        logger.info("Date range: %s to %s", self.start_date, self.end_date)

        all_opinion_ids = []

        # Build initial API URL and parameters
        # IMPORTANT: The CourtListener API limits page_size to 20 for opinions endpoint
        url = f"{self.api_client.base_url}/opinions/"
        params = {
            "cluster__docket__court": "scotus",  # Supreme Court only - this is the correct filter
            "order_by": "-cluster__date_filed",  # Most recent first by filing date
            "cluster__date_filed__gte": self.start_date,  # Use filing date, not creation date
            "cluster__date_filed__lte": self.end_date,  # Use filing date, not creation date
            "page_size": 20,  # API maximum for opinions endpoint is 20
        }

        try:
            import httpx
            import time
            from datetime import datetime

            # Create HTTP client with longer timeout for pagination
            with httpx.Client(timeout=60.0) as client:
                # First, get the total count to know what we're dealing with
                # Use the count API endpoint directly
                count_params = params.copy()
                count_params['count'] = 'on'
                count_params['page_size'] = 1

                logger.debug("Fetching count with params: %s", count_params)
                count_response = client.get(url, headers=self.api_client.headers, params=count_params)
                count_response.raise_for_status()
                count_data = count_response.json()

                # The count field directly contains the count for this endpoint
                total_count = count_data.get('count', 0)
                if isinstance(total_count, str):
                    # If it's a URL string, fetch it
                    try:
                        actual_count_response = client.get(total_count, headers=self.api_client.headers)
                        count_json = actual_count_response.json()
                        total_count = count_json.get('count', 0)
                    except Exception as e:
                        logger.warning("Could not fetch count from URL: %s", e)
                        total_count = None

                if total_count:
                    logger.info(
                        "Total SCOTUS opinions available in date range: %d",
                        total_count,
                    )

                    # Sanity check - SCOTUS typically issues 60-80 opinions per term
                    # If we're getting thousands, something is wrong
                    years_in_range = (
                        datetime.strptime(self.end_date, "%Y-%m-%d")
                        - datetime.strptime(self.start_date, "%Y-%m-%d")
                    ).days / 365
                    expected_max = int(years_in_range * 100)  # ~100 opinions per year max

                    if total_count > max(1000, expected_max * 2):
                        logger.error(
                            "ERROR: Found %d opinions, which is far more than expected "
                            "for SCOTUS.",
                            total_count,
                        )
                        logger.error(
                            "The filter may not be working correctly. Aborting to "
                            "prevent excessive API calls."
                        )
                        return all_opinion_ids

                    max_opinions = total_count
                else:
                    logger.warning(
                        "Could not determine total count, proceeding with caution"
                    )
                    max_opinions = 1000  # Conservative default

                page = 1
                while url and len(all_opinion_ids) < max_opinions:
                    # Add rate limiting
                    time.sleep(self.api_client._get_rate_limit_delay())

                    logger.debug("Fetching page %d from: %s", page, url)
                    response = client.get(url, headers=self.api_client.headers, params=params)
                    response.raise_for_status()

                    data = response.json()
                    results = data.get("results", [])

                    # If we get no results, we're done
                    if not results:
                        logger.info("No more results on page %d, stopping.", page)
                        break

                    # Process each opinion in the current page
                    for opinion_summary in results:
                        opinion_id = opinion_summary.get("id")
                        if opinion_id:
                            all_opinion_ids.append(str(opinion_id))

                            # Stop if we've reached the maximum
                            if len(all_opinion_ids) >= max_opinions:
                                logger.info(
                                    "Reached maximum opinion limit (%d), stopping.",
                                    max_opinions,
                                )
                                break

                    # Log progress
                    logger.info(
                        "Fetched page %d: %d opinions (total: %d/%s)",
                        page,
                        len(results),
                        len(all_opinion_ids),
                        total_count or "unknown",
                    )

                    # Get next page URL
                    url = data.get("next")
                    # Clear params for subsequent requests (they're included in the next URL)
                    params = {}
                    page += 1

                    # Safety check to prevent infinite loops
                    if page > 100:  # Maximum 100 pages (10,000 opinions at 100 per page)
                        logger.warning(
                            "Reached maximum page limit (100 pages), stopping pagination"
                        )
                        break

            logger.info("Successfully fetched %d opinion IDs", len(all_opinion_ids))

        except httpx.TimeoutException as e:
            logger.error("Request timed out while fetching opinion IDs: %s", e)
            logger.info(
                "Partial results: fetched %d opinion IDs before timeout",
                len(all_opinion_ids),
            )
        except httpx.HTTPError as e:
            logger.error("HTTP error while fetching opinion IDs: %s", e)
            if hasattr(e, "response") and e.response:
                logger.error("Response status: %s", e.response.status_code)
                logger.error("Response content: %s", e.response.text[:500])
        except Exception as e:
            logger.error(
                "Unexpected error fetching opinion IDs: %s: %s",
                type(e).__name__,
                e,
            )

        return all_opinion_ids

    def _process_opinions_batch(self, opinion_ids: List[str]) -> None:
        """
        Process opinions in batches.

        Args:
            opinion_ids: List of opinion IDs to process
        """
        total = len(opinion_ids)
        processed = 0

        for i in range(0, total, self.batch_size):
            batch_ids = opinion_ids[i : i + self.batch_size]
            logger.info(
                "Processing batch %d (%d opinions)",
                i // self.batch_size + 1,
                len(batch_ids),
            )

            batch_documents = []
            batch_embeddings = []

            for opinion_id in batch_ids:
                processed += 1

                # Update progress bar
                self.performance_monitor.print_progress(
                    processed, total, "Processing opinions"
                )

                # Process individual opinion
                success = self._process_single_opinion(
                    opinion_id, batch_documents, batch_embeddings
                )

                if success:
                    self.performance_monitor.record_document()
                else:
                    self.performance_monitor.record_document(failed=True)

            # Store batch in Qdrant
            if batch_documents and not self.dry_run:
                self._store_batch(batch_documents, batch_embeddings)

    def _process_single_opinion(
        self,
        opinion_id: str,
        batch_documents: List[Dict[str, Any]],
        batch_embeddings: List[List[float]],
    ) -> bool:
        """
        Process a single Supreme Court opinion.

        Args:
            opinion_id: ID of the opinion to process
            batch_documents: List to append document chunks to
            batch_embeddings: List to append embeddings to

        Returns:
            True if processing succeeded, False otherwise
        """
        start_time = time.time()

        try:
            # Mark as processing
            self.progress_tracker.mark_processing(opinion_id)

            # Fetch opinion data
            logger.debug(f"Fetching opinion {opinion_id}")
            document = self.api_client.get_document(opinion_id)

            if not document:
                raise ValueError(f"Could not fetch document for opinion {opinion_id}")

            # Process through the pipeline
            logger.debug(f"Building payloads for opinion {opinion_id}")
            payloads = build_payloads_from_document(document)

            if not payloads:
                raise ValueError(f"No payloads generated for opinion {opinion_id}")

            logger.debug(f"Generated {len(payloads)} chunks for opinion {opinion_id}")

            # Generate embeddings for each chunk
            chunk_texts = [p["text"] for p in payloads]
            embeddings = self.embedding_generator.generate_batch_embeddings(chunk_texts)

            # Convert payloads to Qdrant format
            for payload, embedding in zip(payloads, embeddings):
                # Payload is already a dict
                doc_dict = payload
                doc_dict["document_id"] = opinion_id
                doc_dict["ingested_at"] = datetime.now().isoformat()

                batch_documents.append(doc_dict)
                batch_embeddings.append(embedding)

            # Mark as completed
            processing_time_ms = (time.time() - start_time) * 1000
            self.progress_tracker.mark_completed(opinion_id, int(processing_time_ms))

            return True

        except Exception as e:
            logger.error(f"Error processing opinion {opinion_id}: {e}")
            self.progress_tracker.mark_failed(opinion_id, str(e))
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
            logger.info("Storing batch of %d chunks in Qdrant", len(documents))

            successful, failed = self.qdrant_client.batch_upsert_documents(
                documents, embeddings, batch_size=100
            )

            logger.info("Stored %d chunks, %d failed", successful, failed)

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


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Batch ingestion of Supreme Court opinions from CourtListener"
    )

    parser.add_argument(
        "--start-date", required=True, help="Start date for opinion range (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--end-date", required=True, help="End date for opinion range (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of opinions to process in each batch (default: 50)",
    )

    parser.add_argument(
        "--progress-db",
        default="scotus_ingestion.db",
        help="Path to SQLite progress database (default: scotus_ingestion.db)",
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
        datetime.strptime(args.start_date, "%Y-%m-%d")
        datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format")
        sys.exit(1)

    # Setup logging
    setup_logging(args.verbose)

    # Run ingestion
    ingester = SCOTUSIngester(
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
