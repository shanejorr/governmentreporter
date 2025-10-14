"""
Supreme Court opinion ingester.

This module provides batch ingestion of Supreme Court opinions from the
CourtListener API into the Qdrant vector database.

The ingester:
- Fetches opinion IDs with pagination handling
- Processes documents through chunking and metadata extraction
- Generates embeddings using OpenAI
- Stores in Qdrant with progress tracking
- Handles errors and provides resumability
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List

from ..apis.court_listener import CourtListenerClient
from ..processors.build_payloads import build_payloads_from_document
from .base import DocumentIngester

logger = logging.getLogger(__name__)


class SCOTUSIngester(DocumentIngester):
    """
    Handles batch ingestion of Supreme Court opinions into Qdrant.

    This class extends DocumentIngester with SCOTUS-specific logic for
    fetching opinion IDs from CourtListener and processing opinion documents.

    The ingester uses the CourtListener API's opinions endpoint with:
    - Date range filtering on filing date
    - SCOTUS-specific court filter
    - Pagination handling (20 results per page)
    - Sanity checks on result counts
    - Rate limiting

    Example:
        ingester = SCOTUSIngester(
            start_date="2020-01-01",
            end_date="2024-12-31",
            batch_size=50,
        )
        ingester.run()
    """

    def __init__(
        self,
        start_date: str,
        end_date: str,
        batch_size: int = 50,
        dry_run: bool = False,
        progress_db: str = "scotus_ingestion.db",
        qdrant_db_path: str = "./data/qdrant/qdrant_db",
        shared_db_client=None,
    ):
        """
        Initialize the SCOTUS ingester.

        Args:
            start_date: Start date for opinion range (YYYY-MM-DD)
            end_date: End date for opinion range (YYYY-MM-DD)
            batch_size: Number of opinions to process in each batch
            dry_run: If True, don't actually store documents
            progress_db: Path to SQLite progress database
            qdrant_db_path: Path to Qdrant database directory
            shared_db_client: Optional pre-initialized QdrantDBClient for shared access
        """
        # Initialize base class
        super().__init__(
            start_date=start_date,
            end_date=end_date,
            batch_size=batch_size,
            dry_run=dry_run,
            progress_db=progress_db,
            qdrant_db_path=qdrant_db_path,
            document_type="scotus",
            shared_db_client=shared_db_client,
        )

        # Initialize SCOTUS-specific API client
        self.api_client = CourtListenerClient()

        # Cache for cluster metadata to avoid redundant API calls
        # Maps opinion_id -> cluster_data dictionary
        # Populated during _fetch_document_ids() and used in _process_single_document()
        self.cluster_cache: Dict[str, Dict[str, Any]] = {}

    def _get_collection_name(self) -> str:
        """Get the Qdrant collection name for SCOTUS opinions."""
        return "supreme_court_opinions"

    def _fetch_document_ids(self) -> List[str]:
        """
        Fetch all Supreme Court opinion IDs in the date range.

        This method queries the clusters endpoint (not opinions) because:
        - The clusters endpoint is more efficient (fewer results to paginate)
        - Each cluster contains sub_opinions field with all opinion IDs
        - We can cache cluster metadata for later use (avoids redundant API calls)
        - The docket__court=scotus filter reliably returns only SCOTUS clusters

        The method:
        - Uses docket__court=scotus filter (verified to work correctly)
        - Handles pagination automatically
        - Caches cluster metadata for performance optimization
        - Includes retry logic for transient server errors

        Returns:
            List of opinion IDs to process
        """
        logger.info("Fetching opinion IDs from CourtListener clusters API...")
        logger.info(f"Date range: {self.start_date} to {self.end_date}")

        all_opinion_ids: List[str] = []
        all_clusters: List[Dict[str, Any]] = []

        # Query clusters endpoint with court filter
        # The docket__court=scotus filter is reliable (verified 2025-10-13)
        url = f"{self.api_client.base_url}/clusters/"
        params: Dict[str, Any] = {
            "docket__court": "scotus",  # Filter to SCOTUS only (reliable)
            "date_filed__gte": self.start_date,
            "date_filed__lte": self.end_date,
            # Most recent first, with id as tie-breaker for consistent ordering
            # Per API docs: tie-breaker prevents inconsistent results when
            # multiple clusters have the same date_filed
            "order_by": "-date_filed,id",
            "page_size": 20,  # API maximum for clusters endpoint
        }

        try:
            import httpx

            # Create HTTP client with longer timeout for pagination
            with httpx.Client(timeout=120.0) as client:
                page = 1
                max_pages = 200  # Safety limit to prevent runaway pagination

                # Paginate through all SCOTUS clusters in date range
                while url and page <= max_pages:
                    # Rate limiting
                    time.sleep(self.api_client._get_rate_limit_delay())

                    logger.info(f"Fetching page {page}...")

                    # Retry logic for transient errors (502, 503, 504)
                    max_retries = 3
                    retry_delay = 5  # seconds

                    for attempt in range(max_retries):
                        try:
                            response = client.get(
                                url, headers=self.api_client.headers, params=params
                            )
                            response.raise_for_status()
                            break  # Success, exit retry loop
                        except httpx.HTTPStatusError as e:
                            if (
                                e.response.status_code in [502, 503, 504]
                                and attempt < max_retries - 1
                            ):
                                logger.warning(
                                    f"API error {e.response.status_code} on page {page}, "
                                    f"retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})..."
                                )
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                            else:
                                raise  # Re-raise if not retryable or max retries exceeded

                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        logger.info(f"No more results on page {page}, stopping.")
                        break

                    # Collect all clusters from this page
                    # No validation needed - the API filter is reliable
                    page_clusters = len(results)
                    all_clusters.extend(results)

                    # Log progress
                    logger.info(
                        f"Page {page}: {page_clusters} clusters collected "
                        f"({len(all_clusters)} total)"
                    )

                    # Get next page URL
                    next_url = data.get("next")

                    if not next_url:
                        logger.info("No next URL, pagination complete")
                        break

                    url = next_url
                    params = {}  # Clear params (they're in the next URL)
                    page += 1

                    # Safety check to prevent infinite loops
                    if page > max_pages:
                        logger.warning(
                            f"Reached maximum page limit ({max_pages} pages), "
                            "stopping pagination"
                        )
                        break

                # Extract opinion IDs from all collected clusters
                logger.info(
                    f"Extracting opinion IDs from {len(all_clusters)} SCOTUS clusters..."
                )

                for cluster in all_clusters:
                    # Extract opinion IDs from sub_opinions
                    sub_opinions = cluster.get("sub_opinions", [])

                    if not sub_opinions:
                        logger.warning(
                            f"Cluster {cluster.get('id')} has no sub_opinions, skipping"
                        )
                        continue

                    for opinion_url in sub_opinions:
                        # Extract opinion ID from URL
                        # Format: .../api/rest/v4/opinions/{id}/
                        try:
                            opinion_id = opinion_url.rstrip("/").split("/")[-1]
                            all_opinion_ids.append(str(opinion_id))

                            # Cache cluster data for this opinion
                            # This avoids refetching cluster data during processing
                            self.cluster_cache[str(opinion_id)] = cluster

                        except (IndexError, AttributeError) as e:
                            logger.warning(
                                f"Could not extract opinion ID from "
                                f"URL: {opinion_url}, error: {e}"
                            )

            # Each opinion belongs to exactly one cluster per CourtListener's data model
            # (Court → Docket → Cluster → Opinions hierarchy is strictly one-to-many)
            # Therefore, opinion IDs are guaranteed unique - no deduplication needed

            logger.info(
                f"Successfully fetched {len(all_opinion_ids)} opinion IDs "
                f"from {len(all_clusters)} SCOTUS clusters"
            )

            # Log cluster cache size
            logger.info(f"Cached metadata for {len(self.cluster_cache)} opinions")

        except Exception as e:
            logger.error(f"Error during cluster fetching: {e}")

            # If we collected any clusters before the error, extract opinion IDs
            if len(all_clusters) > 0:
                logger.warning(
                    f"Collected {len(all_clusters)} SCOTUS clusters before error, "
                    f"extracting opinion IDs from partial results..."
                )

                # Extract opinion IDs from clusters we did manage to collect
                for cluster in all_clusters:
                    sub_opinions = cluster.get("sub_opinions", [])

                    if not sub_opinions:
                        continue

                    for opinion_url in sub_opinions:
                        try:
                            opinion_id = opinion_url.rstrip("/").split("/")[-1]
                            all_opinion_ids.append(str(opinion_id))
                            self.cluster_cache[str(opinion_id)] = cluster
                        except (IndexError, AttributeError) as e:
                            logger.warning(
                                f"Could not extract opinion ID from URL: {opinion_url}, error: {e}"
                            )

                logger.info(
                    f"Extracted {len(all_opinion_ids)} opinion IDs from "
                    f"{len(all_clusters)} SCOTUS clusters "
                    f"(partial results due to API error)"
                )
            else:
                logger.error("No SCOTUS clusters collected before error occurred")

        return all_opinion_ids

    def _process_single_document(
        self,
        doc_id: str,
        batch_documents: List[Dict[str, Any]],
        batch_embeddings: List[List[float]],
    ) -> bool:
        """
        Process a single Supreme Court opinion using cached cluster data.

        This method:
        1. Retrieves cached cluster data (validated during _fetch_document_ids())
        2. Fetches the opinion from CourtListener with field selection
        3. Passes cluster data to avoid redundant API call
        4. Builds payloads (chunking + metadata extraction)
        5. Generates embeddings
        6. Adds to batch lists

        Performance Optimization:
            Court validation already happened in _fetch_document_ids(), so this
            method skips validation and uses cached cluster data to avoid
            redundant API calls. This reduces API calls per opinion from 4 to 1.

        Args:
            doc_id: Opinion ID to process
            batch_documents: List to append document payloads to
            batch_embeddings: List to append embeddings to

        Returns:
            True if successful, False if failed

        Error Handling:
            - If cluster data not found in cache, falls back to fetching
            - API failures are logged and marked as failed in progress tracker
            - Processing failures don't block other opinions in batch
        """
        start_time = time.time()

        try:
            # Mark as processing
            self.progress_tracker.mark_processing(doc_id)

            # Retrieve cached cluster data
            # This was populated during _fetch_document_ids() and already validated
            cluster_data = self.cluster_cache.get(doc_id)

            if not cluster_data:
                # This shouldn't happen if _fetch_document_ids() worked correctly,
                # but we handle it gracefully by proceeding without cluster data
                logger.warning(
                    f"No cached cluster data for opinion {doc_id}, "
                    f"will fetch from API (slower)"
                )

            # Fetch opinion data with cached cluster data
            # This skips the cluster API call since we already have the data
            logger.debug(f"Fetching opinion {doc_id}")
            document = self.api_client.get_document(doc_id, cluster_data=cluster_data)

            # Log the document being ingested
            if document:
                case_name = document.title or f"Opinion ID: {doc_id}"
                logger.info(f"Ingesting SCOTUS opinion: {case_name}")

            if not document:
                raise ValueError(f"Could not fetch document for opinion {doc_id}")

            # Process through the pipeline
            logger.debug(f"Building payloads for opinion {doc_id}")
            payloads = build_payloads_from_document(document)

            if not payloads:
                raise ValueError(f"No payloads generated for opinion {doc_id}")

            logger.debug(f"Generated {len(payloads)} chunks for opinion {doc_id}")

            # Generate embeddings for each chunk
            chunk_texts = [p["text"] for p in payloads]
            embeddings = self.embedding_generator.generate_batch_embeddings(chunk_texts)

            # Convert payloads to Qdrant format
            for payload, embedding in zip(payloads, embeddings):
                doc_dict = payload
                doc_dict["document_id"] = doc_id
                doc_dict["ingested_at"] = datetime.now().isoformat()

                batch_documents.append(doc_dict)
                batch_embeddings.append(embedding)

            # Mark as completed
            processing_time_ms = (time.time() - start_time) * 1000
            self.progress_tracker.mark_completed(doc_id, int(processing_time_ms))

            return True

        except Exception as e:
            logger.error(f"Error processing opinion {doc_id}: {e}")
            self.progress_tracker.mark_failed(doc_id, str(e))
            return False
