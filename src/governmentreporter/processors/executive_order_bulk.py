"""Bulk processor for Executive Orders from Federal Register API."""

from typing import Any, Dict, Optional

from ..apis.federal_register import FederalRegisterClient
from ..utils import get_logger
from .base_bulk import BaseBulkProcessor
from .executive_order_chunker import ExecutiveOrderProcessor


class ExecutiveOrderBulkProcessor(BaseBulkProcessor):
    """Processes Executive Orders through the complete hierarchical chunking pipeline.

    This class handles the systematic processing of Executive Orders
    from the Federal Register API, including:
    - API pagination and rate limiting
    - Hierarchical chunking by sections
    - Complete pipeline processing (metadata, embeddings, storage)
    - Progress tracking and error handling
    - Resumable operations
    - Duplicate checking
    """

    def __init__(
        self,
        output_dir: str = "raw-data/executive_orders_data",
        collection_name: str = "federal-executive-orders",
        rate_limit_delay: float = 0.1,
    ):
        """Initialize the bulk processor.

        Args:
            output_dir: Directory to store progress and error logs
            collection_name: ChromaDB collection name for storage
            rate_limit_delay: Delay between API requests in seconds
        """
        # Initialize base class
        super().__init__(output_dir, collection_name, rate_limit_delay)

        self.logger = get_logger(__name__)

        # Initialize clients
        self.federal_client = FederalRegisterClient()
        self.order_processor = ExecutiveOrderProcessor(logger=self.logger)

        # Use a different name for the ID set to match what's in saved files
        self.processed_document_numbers = self.processed_ids

    def _extract_document_id(self, document_summary: Dict[str, Any]) -> str:
        """Extract the document ID from an executive order summary."""
        return document_summary.get("document_number", "")

    def _get_save_interval(self) -> int:
        """Get the interval for saving progress."""
        return 5  # Save every 5 documents for executive orders

    def _check_if_exists_in_db(self, document_number: str) -> bool:
        """Check if an executive order already exists in the database.

        Args:
            document_number: The Federal Register document number

        Returns:
            True if the document exists in the database, False otherwise
        """
        try:
            # Check in ChromaDB collection
            collection = self.order_processor.db_client.get_or_create_collection(
                self.collection_name
            )

            # Query for any chunk with this document number
            results = collection.get(
                where={"document_number": document_number},
                limit=1,
            )

            return len(results["ids"]) > 0
        except Exception as e:
            self.logger.warning(
                f"Error checking if document {document_number} exists: {e}"
            )
            return False

    def _process_single_document(self, order_summary: Dict[str, Any]) -> bool:
        """Process a single executive order through the hierarchical chunking pipeline.

        Args:
            order_summary: Executive order metadata from the listing API

        Returns:
            True if successful, False otherwise
        """
        document_number = self._extract_document_id(order_summary)

        if not document_number:
            self.logger.warning("No document_number in order summary")
            return False

        # Check if exists in database
        if self._check_if_exists_in_db(document_number):
            self.logger.info(f"Skipping {document_number} - already in database")
            self.processed_document_numbers.add(document_number)
            return True

        title = order_summary.get("title", "Unknown")
        eo_number = order_summary.get("executive_order_number", "Unknown")

        self.logger.info(f"Processing EO {eo_number}: {title} ({document_number})...")

        try:
            # Process and store order using the processor's integrated method
            self.logger.info(
                "  Processing executive order with hierarchical chunking..."
            )
            result = self.order_processor.process_and_store(
                document_id=document_number, collection_name=self.collection_name
            )

            if result["success"]:
                self.logger.info(f"  Generated {result['chunks_processed']} chunks")
                self.logger.info(
                    f"  ✅ Stored {result['chunks_stored']} chunks in database"
                )
                return True
            else:
                raise Exception(result.get("error", "Unknown error during processing"))

        except Exception as e:
            error_msg = f"Failed to process executive order {document_number}: {str(e)}"
            self.logger.error(f"  ❌ {error_msg}")
            self._log_error(document_number, error_msg, order_summary)
            return False

    def get_documents_iterator(self, max_results=None, **kwargs):
        """Return an iterator over executive orders.

        Args:
            max_results: Maximum number of results
            **kwargs: Must include start_date and end_date

        Yields:
            Executive order summaries
        """
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")

        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required in kwargs")
        for order_summary in self.federal_client.list_executive_orders(
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
        ):
            # Check if exists in database before yielding
            document_number = self._extract_document_id(order_summary)
            if document_number and self._check_if_exists_in_db(document_number):
                self.logger.info(f"Skipping {document_number} - already in database")
                self.processed_ids.add(document_number)
                continue
            yield order_summary

    def get_total_count(self, **kwargs) -> int:
        """Get total count of executive orders to process.

        Args:
            **kwargs: Must include start_date and end_date

        Returns:
            Total number of orders matching the criteria
        """
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")

        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required in kwargs")
        total_count = 0
        try:
            for _ in self.federal_client.list_executive_orders(
                start_date=start_date, end_date=end_date, max_results=None
            ):
                total_count += 1
        except Exception as e:
            self.logger.warning(f"Could not count total orders: {e}")
        return total_count

    def process_executive_orders(
        self, start_date: str, end_date: str, max_orders: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process all executive orders between the specified dates.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_orders: Maximum number of orders to process (None for all)

        Returns:
            Dictionary with processing statistics
        """
        self.logger.info(
            f"Starting Executive Order processing from {start_date} to {end_date}"
        )

        # Use the base class method
        return self.process_documents(
            max_documents=max_orders, start_date=start_date, end_date=end_date
        )

    def get_processing_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get current processing statistics.

        Args:
            start_date: Start date for the range
            end_date: End date for the range

        Returns:
            Dictionary with current progress statistics
        """
        total_available = self.get_total_count(start_date=start_date, end_date=end_date)

        return {
            "total_available": total_available,
            "processed_count": len(self.processed_ids),
            "remaining_count": max(0, total_available - len(self.processed_ids)),
            "progress_percentage": (
                (len(self.processed_ids) / total_available * 100)
                if total_available > 0
                else 0
            ),
            "date_range": f"{start_date} to {end_date}",
            "collection_name": self.collection_name,
            "output_dir": str(self.output_dir),
        }
