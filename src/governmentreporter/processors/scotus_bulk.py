"""Bulk processor for Supreme Court opinions from CourtListener API."""

from typing import Any, Dict, Optional

from ..apis import CourtListenerClient
from ..utils import get_logger
from .base_bulk import BaseBulkProcessor
from .scotus_opinion_chunker import SCOTUSOpinionProcessor


class SCOTUSBulkProcessor(BaseBulkProcessor):
    """Processes all SCOTUS opinions through the complete hierarchical chunking pipeline.

    This class handles the systematic processing of Supreme Court opinions
    from the CourtListener API, including:
    - API pagination and rate limiting
    - Hierarchical chunking by opinion type and sections
    - Complete pipeline processing (metadata, embeddings, storage)
    - Progress tracking and error handling
    - Resumable operations
    """

    def __init__(
        self,
        output_dir: str = "raw-data/scotus_data",
        since_date: str = "1900-01-01",
        until_date: Optional[str] = None,
        rate_limit_delay: float = 0.75,
        max_retries: int = 3,
        collection_name: str = "federal_court_scotus_opinions",
    ):
        """Initialize the bulk processor.

        Args:
            output_dir: Directory to store progress and error logs
            since_date: Start date for opinion retrieval (YYYY-MM-DD)
            until_date: End date for opinion retrieval (YYYY-MM-DD, optional)
            rate_limit_delay: Delay between API requests in seconds
            max_retries: Maximum number of retries for failed requests
            collection_name: Qdrant collection name for storage
        """
        # Initialize base class
        super().__init__(output_dir, collection_name, rate_limit_delay)

        self.since_date = since_date
        self.until_date = until_date
        self.max_retries = max_retries
        self.logger = get_logger(__name__)

        # Initialize clients
        self.court_client = CourtListenerClient()
        self.opinion_processor = SCOTUSOpinionProcessor()
        
        self.logger.info(
            f"SCOTUSBulkProcessor initialized: dates={since_date} to {until_date}, "
            f"collection={collection_name}"
        )

    def _get_additional_progress_data(self) -> Dict[str, Any]:
        """Get additional data to save in progress file."""
        return {
            "since_date": self.since_date,
            "until_date": self.until_date,
        }

    def _extract_document_id(self, document_summary: Dict[str, Any]) -> str:
        """Extract the document ID from an opinion summary."""
        return str(document_summary.get("id"))

    def _process_single_document(self, opinion_summary: Dict[str, Any]) -> bool:
        """Process a single opinion through the hierarchical chunking pipeline.

        Args:
            opinion_summary: Opinion metadata from the listing API

        Returns:
            True if successful, False otherwise
        """
        opinion_id = self._extract_document_id(opinion_summary)
        self.logger.info(f"Processing opinion {opinion_id}")

        try:
            # Process and store opinion using the processor's integrated method
            self.logger.debug(f"Processing opinion {opinion_id} with hierarchical chunking")
            result = self.opinion_processor.process_and_store(
                document_id=opinion_id, collection_name=self.collection_name
            )

            if result["success"]:
                self.logger.info(
                    f"Opinion {opinion_id}: Generated {result['chunks_processed']} chunks, "
                    f"stored {result['chunks_stored']} chunks in database"
                )
                return True
            else:
                raise Exception(result.get("error", "Unknown error during processing"))

        except Exception as e:
            error_msg = f"Failed to process opinion {opinion_id}: {str(e)}"
            self.logger.error(error_msg)
            self._log_error(opinion_id, error_msg, opinion_summary)
            return False

    def get_total_count(self, **kwargs) -> int:
        """Get total count of SCOTUS opinions to process.

        Returns:
            Total number of opinions matching the criteria
        """
        # Since the API doesn't provide a separate count endpoint,
        # we return 0 to indicate unknown count
        # The progress will still work based on processed documents
        self.logger.info("Total count not available, progress will be tracked by documents processed")
        return 0

    def get_documents_iterator(self, max_results=None, **kwargs):
        """Return an iterator over SCOTUS opinions.

        Args:
            max_results: Maximum number of results
            **kwargs: Additional arguments

        Yields:
            Opinion summaries
        """
        # Fetch documents using search_documents with full_content=False
        # This avoids fetching full text and making extra API calls
        # since we only need the IDs for bulk processing
        limit = max_results if max_results is not None else 10000
        
        documents = self.court_client.search_documents(
            query="",  # Empty query to get all documents
            start_date=self.since_date,
            end_date=self.until_date,
            limit=limit,
            full_content=False  # Only get summaries, not full content
        )
        
        # Convert Document objects to opinion summaries for compatibility
        # The bulk processor only needs the ID from each document
        for doc in documents:
            # Create a minimal opinion summary with just the ID
            yield {"id": int(doc.id)}

    def process_all_opinions(
        self, max_opinions: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process all SCOTUS opinions within the specified date range.

        Args:
            max_opinions: Maximum number of opinions to process (None for all)

        Returns:
            Dictionary with processing statistics
        """
        date_range = f"since {self.since_date}"
        if self.until_date:
            date_range = f"from {self.since_date} to {self.until_date}"

        self.logger.info(f"Starting SCOTUS opinion processing {date_range}")

        # Use the base class method
        return self.process_documents(max_documents=max_opinions)

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics.

        Returns:
            Dictionary with current progress statistics
        """
        total_count = self.get_total_count()

        return {
            "total_available": total_count,
            "processed_count": len(self.processed_ids),
            "remaining_count": max(0, total_count - len(self.processed_ids)),
            "progress_percentage": (
                (len(self.processed_ids) / total_count * 100) if total_count > 0 else 0
            ),
            "since_date": self.since_date,
            "until_date": self.until_date,
            "collection_name": self.collection_name,
            "output_dir": str(self.output_dir),
        }
