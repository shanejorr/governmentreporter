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

    def _fetch_document_ids(self) -> List[str]:
        """
        Fetch all Supreme Court opinion IDs in the date range.

        This method fetches opinion IDs in batches using pagination
        to handle large date ranges that may contain thousands of opinions.

        The method includes:
        - Count validation (SCOTUS typically issues 60-80 opinions per term)
        - Pagination handling (20 results per page)
        - Rate limiting between requests
        - Safety checks to prevent runaway API calls

        Returns:
            List of opinion IDs to process
        """
        logger.info("Fetching opinion IDs from CourtListener API...")
        logger.info(f"Date range: {self.start_date} to {self.end_date}")

        all_opinion_ids = []

        # Build initial API URL and parameters
        # IMPORTANT: The CourtListener API limits page_size to 20 for opinions endpoint
        url = f"{self.api_client.base_url}/opinions/"
        params = {
            "cluster__docket__court": "scotus",  # Supreme Court only
            "order_by": "-cluster__date_filed",  # Most recent first
            "cluster__date_filed__gte": self.start_date,
            "cluster__date_filed__lte": self.end_date,
            "page_size": 20,  # API maximum for opinions endpoint
        }

        try:
            import httpx

            # Create HTTP client with longer timeout for pagination
            with httpx.Client(timeout=60.0) as client:
                # Get total count first
                count_params = params.copy()
                count_params["count"] = "on"
                count_params["page_size"] = 1

                logger.debug(f"Fetching count with params: {count_params}")
                count_response = client.get(
                    url, headers=self.api_client.headers, params=count_params
                )
                count_response.raise_for_status()
                count_data = count_response.json()

                total_count = count_data.get("count", 0)
                if isinstance(total_count, str):
                    # If it's a URL string, fetch it
                    try:
                        actual_count_response = client.get(
                            total_count, headers=self.api_client.headers
                        )
                        count_json = actual_count_response.json()
                        total_count = count_json.get("count", 0)
                    except Exception as e:
                        logger.warning(f"Could not fetch count from URL: {e}")
                        total_count = None

                if total_count:
                    logger.info(
                        f"Total SCOTUS opinions available in date range: {total_count}"
                    )

                    # Sanity check - SCOTUS typically issues 60-80 opinions per term
                    years_in_range = (
                        datetime.strptime(self.end_date, "%Y-%m-%d")
                        - datetime.strptime(self.start_date, "%Y-%m-%d")
                    ).days / 365
                    expected_max = int(years_in_range * 100)  # ~100 opinions per year max

                    if total_count > max(1000, expected_max * 2):
                        logger.error(
                            f"ERROR: Found {total_count} opinions, which is far more than expected for SCOTUS."
                        )
                        logger.error(
                            "The filter may not be working correctly. Aborting to prevent excessive API calls."
                        )
                        return all_opinion_ids

                    max_opinions = total_count
                else:
                    logger.warning("Could not determine total count, proceeding with caution")
                    max_opinions = 1000  # Conservative default

                # Paginate through results
                page = 1
                while url and len(all_opinion_ids) < max_opinions:
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

                    # Process each opinion in the current page
                    for opinion_summary in results:
                        opinion_id = opinion_summary.get("id")
                        if opinion_id:
                            all_opinion_ids.append(str(opinion_id))

                            if len(all_opinion_ids) >= max_opinions:
                                logger.info(
                                    f"Reached maximum opinion limit ({max_opinions}), stopping."
                                )
                                break

                    # Log progress
                    logger.info(
                        f"Fetched page {page}: {len(results)} opinions (total: {len(all_opinion_ids)}/{total_count or 'unknown'})"
                    )

                    # Get next page URL
                    url = data.get("next")
                    params = {}  # Clear params (they're in the next URL)
                    page += 1

                    # Safety check to prevent infinite loops
                    if page > 100:  # Maximum 100 pages
                        logger.warning("Reached maximum page limit (100 pages), stopping pagination")
                        break

            logger.info(f"Successfully fetched {len(all_opinion_ids)} opinion IDs")

        except Exception as e:
            logger.error(f"Error fetching opinion IDs: {e}")
            if len(all_opinion_ids) > 0:
                logger.info(f"Partial results: fetched {len(all_opinion_ids)} opinion IDs before error")

        return all_opinion_ids

    def _process_single_document(
        self,
        doc_id: str,
        batch_documents: List[Dict[str, Any]],
        batch_embeddings: List[List[float]],
    ) -> bool:
        """
        Process a single Supreme Court opinion.

        This method:
        1. Fetches the opinion from CourtListener
        2. Builds payloads (chunking + metadata extraction)
        3. Generates embeddings
        4. Adds to batch lists

        Args:
            doc_id: Opinion ID to process
            batch_documents: List to append document payloads to
            batch_embeddings: List to append embeddings to

        Returns:
            True if successful, False if failed
        """
        start_time = time.time()

        try:
            # Mark as processing
            self.progress_tracker.mark_processing(doc_id)

            # Fetch opinion data
            logger.debug(f"Fetching opinion {doc_id}")
            document = self.api_client.get_document(doc_id)

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