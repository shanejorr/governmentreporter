"""
Executive Order ingester.

This module provides batch ingestion of Executive Orders from the
Federal Register API into the Qdrant vector database.

The ingester:
- Fetches Executive Order metadata from Federal Register
- Retrieves raw text for each order
- Processes documents through chunking and metadata extraction
- Generates embeddings using OpenAI
- Stores in Qdrant with progress tracking
- Handles errors and provides resumability
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List

from ..apis.base import Document
from ..apis.federal_register import FederalRegisterClient
from ..processors.build_payloads import build_payloads_from_document
from .base import DocumentIngester

logger = logging.getLogger(__name__)


class ExecutiveOrderIngester(DocumentIngester):
    """
    Handles batch ingestion of Executive Orders into Qdrant.

    This class extends DocumentIngester with Executive Order-specific logic
    for fetching orders from the Federal Register API and processing them.

    The ingester:
    - Fetches all Executive Order metadata for the date range
    - Stores metadata for lookup during processing
    - Fetches raw text for each order
    - Caches text URLs to avoid duplicate fetches
    - Processes through standard chunking pipeline

    Example:
        ingester = ExecutiveOrderIngester(
            start_date="2021-01-20",
            end_date="2024-12-31",
            batch_size=25,
        )
        ingester.run()
    """

    def __init__(
        self,
        start_date: str,
        end_date: str,
        batch_size: int = 25,
        dry_run: bool = False,
        progress_db: str = "executive_orders_ingestion.db",
        qdrant_db_path: str = "./data/qdrant/qdrant_db",
        shared_db_client=None,
    ):
        """
        Initialize the Executive Order ingester.

        Args:
            start_date: Start date for order range (YYYY-MM-DD)
            end_date: End date for order range (YYYY-MM-DD)
            batch_size: Number of orders to process in each batch
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
            document_type="executive_order",
            shared_db_client=shared_db_client,
        )

        # Initialize EO-specific API client
        self.api_client = FederalRegisterClient()

        # Cache for raw text URLs to avoid duplicate fetches
        self.text_url_cache = {}

        # Store metadata for lookup during processing
        self.orders_metadata = {}

    def _get_collection_name(self) -> str:
        """Get the Qdrant collection name for Executive Orders."""
        return "executive_orders"

    def _fetch_document_ids(self) -> List[str]:
        """
        Fetch all Executive Order document numbers in the date range.

        This method fetches all Executive Order metadata from the Federal
        Register API and stores it for later use during processing. It returns
        the list of document numbers.

        Returns:
            List of document numbers (IDs) to process
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

            # Store metadata for later lookup and add to progress tracker
            for order in all_orders:
                doc_id = order.get("document_number", "")
                if doc_id:
                    self.orders_metadata[doc_id] = order

                    # Add to progress tracker with metadata
                    self.progress_tracker.add_document(
                        doc_id,
                        metadata={
                            "title": order.get("title", ""),
                            "executive_order_number": order.get(
                                "executive_order_number", ""
                            ),
                            "signing_date": order.get("signing_date", ""),
                            "publication_date": order.get("publication_date", ""),
                        },
                    )

            # Return list of document IDs
            return [
                order.get("document_number")
                for order in all_orders
                if order.get("document_number")
            ]

        except Exception as e:
            logger.error(f"Error fetching Executive Orders: {e}")
            return []

    def _process_single_document(
        self,
        doc_id: str,
        batch_documents: List[Dict[str, Any]],
        batch_embeddings: List[List[float]],
    ) -> bool:
        """
        Process a single Executive Order.

        This method:
        1. Looks up the order metadata
        2. Fetches the raw text (with caching)
        3. Creates a Document object
        4. Builds payloads (chunking + metadata extraction)
        5. Generates embeddings
        6. Adds to batch lists

        Args:
            doc_id: Document number to process
            batch_documents: List to append document payloads to
            batch_embeddings: List to append embeddings to

        Returns:
            True if successful, False if failed
        """
        start_time = time.time()

        try:
            # Mark as processing
            self.progress_tracker.mark_processing(doc_id)

            # Get order metadata
            order_metadata = self.orders_metadata.get(doc_id)
            if not order_metadata:
                raise ValueError(f"No metadata found for order {doc_id}")

            # Log the document being ingested
            html_url = order_metadata.get("html_url", f"Document Number: {doc_id}")
            eo_number = order_metadata.get("executive_order_number", "N/A")
            logger.info(f"Ingesting Executive Order {eo_number}: {html_url}")

            # Get raw text URL
            raw_text_url = order_metadata.get("raw_text_url")
            if not raw_text_url:
                raise ValueError(f"No raw text URL for order {doc_id}")

            # Fetch raw text (with caching)
            if raw_text_url in self.text_url_cache:
                raw_text = self.text_url_cache[raw_text_url]
                logger.debug(f"Using cached text for order {doc_id}")
            else:
                logger.debug(f"Fetching raw text for order {doc_id}")
                raw_text = self.api_client.get_executive_order_text(raw_text_url)
                self.text_url_cache[raw_text_url] = raw_text

            if not raw_text:
                raise ValueError(f"Could not fetch raw text for order {doc_id}")

            # Create Document object for processing
            document = Document(
                id=doc_id,
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
                    "document_number": doc_id,
                    "agencies": order_metadata.get("agencies", []),
                    "topics": order_metadata.get("topics", []),
                },
                url=order_metadata.get("html_url", ""),
            )

            # Process through the pipeline
            logger.debug(f"Building payloads for order {doc_id}")
            payloads = build_payloads_from_document(document)

            if not payloads:
                raise ValueError(f"No payloads generated for order {doc_id}")

            logger.debug(f"Generated {len(payloads)} chunks for order {doc_id}")

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
            logger.error(f"Error processing order {doc_id}: {e}")
            self.progress_tracker.mark_failed(doc_id, str(e))
            return False

    def _print_final_statistics(self) -> None:
        """Print final ingestion statistics with cache info."""
        # Call parent method for standard statistics
        super()._print_final_statistics()

        # Add EO-specific statistics
        print(f"\nText URL Cache Hits: {len(self.text_url_cache)} unique URLs cached")
