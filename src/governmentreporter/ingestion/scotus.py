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
        )

        # Initialize SCOTUS-specific API client
        self.api_client = CourtListenerClient()

    def _get_collection_name(self) -> str:
        """Get the Qdrant collection name for SCOTUS opinions."""
        return "supreme_court_opinions"

    def _validate_court(self, opinion_id: str) -> tuple[bool, str]:
        """
        Validate that an opinion belongs to the Supreme Court.

        This method provides defense against API index inconsistencies by directly
        fetching the docket data and verifying the court_id. It bypasses potentially
        stale search indexes and validates against the source of truth.

        Validation Process:
            1. Fetch opinion data to get cluster URL
            2. Fetch cluster data to get docket URL
            3. Fetch docket data to get court_id
            4. Verify court_id == "scotus"

        This approach catches cases where:
        - API search indexes are temporarily inconsistent
        - Bulk uploads haven't been fully indexed
        - Filter parameters don't work as expected
        - Data has been mislabeled or incorrectly tagged

        Args:
            opinion_id: Opinion ID to validate

        Returns:
            Tuple of (is_valid, error_message):
            - (True, "") if opinion belongs to SCOTUS
            - (False, error_message) if opinion belongs to different court

        Raises:
            Exception: If API calls fail (propagated to caller for handling)

        Example:
            >>> ingester = SCOTUSIngester(...)
            >>> is_valid, error = ingester._validate_court("123456")
            >>> if not is_valid:
            ...     logger.warning(f"Skipping: {error}")

        Performance Impact:
            - Adds 2 additional API calls per opinion (cluster + docket)
            - Adds ~100-200ms per opinion with rate limiting
            - Trade-off: Slower ingestion vs guaranteed data quality
            - Critical for preventing incorrect data from entering the system

        Python Learning Notes:
            - Tuple return: Returns multiple values (bool, str)
            - Early return: Returns immediately when condition met
            - Type hints: tuple[bool, str] specifies return type
            - Defensive programming: Validate assumptions before proceeding
        """
        try:
            # Fetch opinion to get cluster URL
            opinion_data = self.api_client.get_opinion(int(opinion_id))
            cluster_url = opinion_data.get("cluster")

            if not cluster_url:
                return False, f"Opinion {opinion_id} has no cluster URL"

            # Fetch cluster to get docket URL
            cluster_data = self.api_client.get_opinion_cluster(cluster_url)
            docket_url = cluster_data.get("docket")

            if not docket_url:
                return (
                    False,
                    f"Opinion {opinion_id} cluster has no docket URL",
                )

            # Fetch docket to get court_id
            docket_data = self.api_client.get_docket(docket_url)
            court_id = docket_data.get("court_id")

            if not court_id:
                return False, f"Opinion {opinion_id} docket has no court_id"

            # Validate court is SCOTUS
            if court_id != "scotus":
                case_name = cluster_data.get("case_name", "Unknown Case")
                return (
                    False,
                    f"Opinion {opinion_id} belongs to court '{court_id}' (not scotus). "
                    f"Case: {case_name}. This likely indicates an API index inconsistency.",
                )

            return True, ""

        except Exception as e:
            # Propagate exception to caller - this is a validation failure
            # but we want the caller to decide how to handle API errors
            raise

    def _fetch_document_ids(self) -> List[str]:
        """
        Fetch all Supreme Court opinion IDs in the date range.

        This method queries the clusters endpoint (not opinions) because:
        - The opinions endpoint with cluster__date_filed filters causes timeouts
        - The clusters endpoint is the recommended approach per CourtListener API docs
        - Clusters contain the sub_opinions field which provides opinion IDs

        The method includes:
        - Count validation (SCOTUS typically issues 60-80 opinions per term)
        - Pagination handling (20 results per page)
        - Rate limiting between requests
        - Safety checks to prevent runaway API calls

        Returns:
            List of opinion IDs to process
        """
        logger.info("Fetching opinion IDs from CourtListener clusters API...")
        logger.info(f"Date range: {self.start_date} to {self.end_date}")

        all_opinion_ids = []

        # Query clusters endpoint instead of opinions endpoint
        # This avoids the timeout issues with complex opinion filters
        url = f"{self.api_client.base_url}/clusters/"
        params = {
            "docket__court": "scotus",  # Supreme Court only
            # Most recent first, with id as tie-breaker for consistent ordering
            # Per API docs: tie-breaker prevents inconsistent results when
            # multiple clusters have the same date_filed
            "order_by": "-date_filed,id",
            "date_filed__gte": self.start_date,
            "date_filed__lte": self.end_date,
            "page_size": 20,  # API maximum for clusters endpoint
        }

        try:
            import httpx

            # Create HTTP client with longer timeout for pagination
            with httpx.Client(timeout=60.0) as client:
                # The CourtListener API v4 has changed its count behavior:
                # - Without count=on: Returns results + URL in count field
                # - With count=on: Returns only count, no results
                # Fetch the count first, then paginate for results

                total_count = None
                # Conservative default until we know the real count
                max_clusters = 1000

                # First, get the total count with a separate request
                logger.debug("Fetching total count...")
                count_params = params.copy()
                count_params["count"] = "on"
                count_response = client.get(
                    url, headers=self.api_client.headers, params=count_params
                )
                count_response.raise_for_status()
                total_count = count_response.json().get("count", 0)

                if total_count:
                    logger.info("Total SCOTUS clusters available: %s", total_count)

                    # Sanity check - SCOTUS typically issues
                    # 60-80 opinions per term
                    years_in_range = (
                        datetime.strptime(self.end_date, "%Y-%m-%d")
                        - datetime.strptime(self.start_date, "%Y-%m-%d")
                    ).days / 365
                    # ~100 opinions per year max
                    expected_max = int(years_in_range * 100)

                    if total_count > max(1000, expected_max * 2):
                        logger.error(
                            "ERROR: Found %s clusters, which is "
                            "far more than expected for SCOTUS.",
                            total_count,
                        )
                        logger.error(
                            "The filter may not be working correctly. "
                            "Aborting to prevent excessive API calls."
                        )
                        return all_opinion_ids

                    max_clusters = total_count
                else:
                    logger.warning("Could not determine count, proceeding with caution")

                # Rate limiting after count request
                time.sleep(self.api_client._get_rate_limit_delay())

                # Paginate through cluster results
                page = 1
                clusters_processed = 0
                while url and clusters_processed < max_clusters:
                    # Rate limiting
                    time.sleep(self.api_client._get_rate_limit_delay())

                    logger.debug(f"Fetching page {page} from: {url}")
                    response = client.get(
                        url, headers=self.api_client.headers, params=params
                    )
                    response.raise_for_status()

                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        logger.info(f"No more results on page {page}, stopping.")
                        break

                    # Process each cluster in the current page
                    for cluster in results:
                        clusters_processed += 1

                        # Each cluster has a sub_opinions field with URLs
                        sub_opinions = cluster.get("sub_opinions", [])

                        for opinion_url in sub_opinions:
                            # Extract opinion ID from URL
                            # Format: .../api/rest/v4/opinions/{id}/
                            try:
                                opinion_id = opinion_url.rstrip("/").split("/")[-1]
                                all_opinion_ids.append(str(opinion_id))
                            except (IndexError, AttributeError) as e:
                                logger.warning(
                                    f"Could not extract opinion ID from "
                                    f"URL: {opinion_url}, error: {e}"
                                )

                        if clusters_processed >= max_clusters:
                            logger.info(
                                f"Reached maximum cluster limit "
                                f"({max_clusters}), stopping."
                            )
                            break

                    # Log progress
                    logger.info(
                        f"Fetched page {page}: {len(results)} clusters, "
                        f"{len(all_opinion_ids)} total opinions "
                        f"(clusters: {clusters_processed}/"
                        f"{total_count or 'unknown'})"
                    )

                    # Get next page URL
                    url = data.get("next")
                    params = {}  # Clear params (they're in the next URL)
                    page += 1

                    # Safety check to prevent infinite loops
                    if page > 100:  # Maximum 100 pages
                        logger.warning(
                            "Reached maximum page limit (100 pages), "
                            "stopping pagination"
                        )
                        break

            logger.info(
                f"Successfully fetched {len(all_opinion_ids)} opinion IDs "
                f"from {clusters_processed} clusters"
            )

        except Exception as e:
            logger.error(f"Error fetching opinion IDs: {e}")
            if len(all_opinion_ids) > 0:
                logger.info(
                    f"Partial results: fetched {len(all_opinion_ids)} opinion IDs before error"
                )

        return all_opinion_ids

    def _process_single_document(
        self,
        doc_id: str,
        batch_documents: List[Dict[str, Any]],
        batch_embeddings: List[List[float]],
    ) -> bool:
        """
        Process a single Supreme Court opinion with court validation.

        This method:
        1. Validates the opinion belongs to SCOTUS (court_id check)
        2. Fetches the opinion from CourtListener
        3. Builds payloads (chunking + metadata extraction)
        4. Generates embeddings
        5. Adds to batch lists

        The court validation step defends against API index inconsistencies
        by directly verifying the docket's court_id before processing.

        Args:
            doc_id: Opinion ID to process
            batch_documents: List to append document payloads to
            batch_embeddings: List to append embeddings to

        Returns:
            True if successful, False if failed

        Validation Failure Handling:
            - Non-SCOTUS opinions are logged with WARNING level
            - Marked as failed in progress tracker with descriptive error
            - Not processed further (no embedding/storage overhead)
        """
        start_time = time.time()

        try:
            # Mark as processing
            self.progress_tracker.mark_processing(doc_id)

            # VALIDATION: Verify this opinion belongs to SCOTUS
            # This defends against API index inconsistencies where non-SCOTUS
            # opinions may temporarily appear in SCOTUS-filtered queries
            logger.debug(f"Validating court for opinion {doc_id}")
            is_valid, error_message = self._validate_court(doc_id)

            if not is_valid:
                logger.warning(f"Skipping opinion {doc_id}: {error_message}")
                self.progress_tracker.mark_failed(doc_id, error_message)
                return False

            # Fetch opinion data
            logger.debug(f"Fetching opinion {doc_id}")
            document = self.api_client.get_document(doc_id)

            # Log the document being ingested
            if document:
                opinion_url = document.metadata.get("url", f"Opinion ID: {doc_id}")
                logger.info(f"Ingesting SCOTUS opinion: {opinion_url}")

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
