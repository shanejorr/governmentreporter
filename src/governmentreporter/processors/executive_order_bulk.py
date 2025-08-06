"""Bulk processor for Executive Orders from Federal Register API."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

from ..apis.federal_register import FederalRegisterClient
from ..utils import get_logger
from .executive_order_chunker import ExecutiveOrderProcessor


class ExecutiveOrderBulkProcessor:
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
    ):
        """Initialize the bulk processor.
        
        Args:
            output_dir: Directory to store progress and error logs
            collection_name: ChromaDB collection name for storage
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.collection_name = collection_name
        self.logger = get_logger(__name__)
        
        # Initialize clients
        self.federal_client = FederalRegisterClient()
        self.order_processor = ExecutiveOrderProcessor(logger=self.logger)
        
        # Progress tracking
        self.progress_file = self.output_dir / "processing_progress.json"
        self.error_log_file = self.output_dir / "error_log.jsonl"
        self.processed_document_numbers: Set[str] = set()
        
        # Load existing progress
        self._load_progress()
    
    def _load_progress(self) -> None:
        """Load previously processed document numbers from progress file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r") as f:
                    progress_data = json.load(f)
                    self.processed_document_numbers = set(
                        progress_data.get("processed_document_numbers", [])
                    )
                    self.logger.info(
                        f"Loaded progress: {len(self.processed_document_numbers)} "
                        "executive orders already processed"
                    )
            except Exception as e:
                self.logger.warning(f"Could not load progress file: {e}")
                self.processed_document_numbers = set()
    
    def _save_progress(self) -> None:
        """Save current progress to file."""
        progress_data = {
            "processed_document_numbers": list(self.processed_document_numbers),
            "last_updated": datetime.now().isoformat(),
            "total_processed": len(self.processed_document_numbers),
            "collection_name": self.collection_name,
        }
        
        with open(self.progress_file, "w") as f:
            json.dump(progress_data, f, indent=2)
    
    def _log_error(
        self, document_number: str, error: str, order_data: Optional[Dict] = None
    ) -> None:
        """Log errors to error log file."""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "document_number": document_number,
            "error": error,
            "order_data": order_data,
        }
        
        with open(self.error_log_file, "a") as f:
            f.write(json.dumps(error_entry) + "\n")
    
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
    
    def _process_single_order(self, order_summary: Dict[str, Any]) -> bool:
        """Process a single executive order through the hierarchical chunking pipeline.
        
        Args:
            order_summary: Executive order metadata from the listing API
            
        Returns:
            True if successful, False otherwise
        """
        document_number = order_summary.get("document_number")
        
        if not document_number:
            self.logger.warning("No document_number in order summary")
            return False
        
        # Check if already processed
        if document_number in self.processed_document_numbers:
            self.logger.debug(f"Skipping {document_number} - already in progress file")
            return True
        
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
            self.logger.info("  Processing executive order with hierarchical chunking...")
            result = self.order_processor.process_and_store(
                document_id=document_number,
                collection_name=self.collection_name
            )
            
            if result["success"]:
                self.logger.info(f"  Generated {result['chunks_processed']} chunks")
                self.logger.info(f"  ✅ Stored {result['chunks_stored']} chunks in database")
                self.processed_document_numbers.add(document_number)
                return True
            else:
                raise Exception(result.get("error", "Unknown error during processing"))
        
        except Exception as e:
            error_msg = f"Failed to process executive order {document_number}: {str(e)}"
            self.logger.error(f"  ❌ {error_msg}")
            self._log_error(document_number, error_msg, order_summary)
            return False
    
    def process_executive_orders(
        self,
        start_date: str,
        end_date: str,
        max_orders: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process all executive orders between the specified dates.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_orders: Maximum number of orders to process (None for all)
            
        Returns:
            Dictionary with processing statistics
        """
        self.logger.info(f"Starting Executive Order processing from {start_date} to {end_date}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Collection: {self.collection_name}")
        
        start_time = time.time()
        processed_count = 0
        failed_count = 0
        skipped_count = 0
        
        try:
            # Iterate through all executive orders
            for order_summary in self.federal_client.list_executive_orders(
                start_date=start_date,
                end_date=end_date,
                max_results=max_orders,
            ):
                document_number = order_summary.get("document_number")
                
                # Check if already processed (quick check before processing)
                if document_number in self.processed_document_numbers:
                    skipped_count += 1
                    continue
                
                # Check if exists in database
                if self._check_if_exists_in_db(document_number):
                    self.logger.info(f"Skipping {document_number} - already in database")
                    self.processed_document_numbers.add(document_number)
                    skipped_count += 1
                    continue
                
                # Process the order
                success = self._process_single_order(order_summary)
                
                if success:
                    processed_count += 1
                else:
                    failed_count += 1
                
                # Save progress every 5 orders
                if (processed_count + failed_count) % 5 == 0:
                    self._save_progress()
                
                # Show progress
                elapsed = time.time() - start_time
                if elapsed > 0:
                    rate = processed_count / elapsed if processed_count > 0 else 0
                    self.logger.info(
                        f"Progress: {processed_count} processed, {failed_count} failed, "
                        f"{skipped_count} skipped, {rate:.2f} orders/sec"
                    )
        
        except KeyboardInterrupt:
            self.logger.warning("⚠️  Processing interrupted by user")
        except Exception as e:
            self.logger.error(f"❌ Processing failed with error: {e}")
        finally:
            # Save final progress
            self._save_progress()
            
            # Print summary
            elapsed = time.time() - start_time
            total_attempted = processed_count + failed_count + skipped_count
            
            self.logger.info("=" * 60)
            self.logger.info("Processing Summary:")
            self.logger.info(f"  Total attempted: {total_attempted}")
            self.logger.info(f"  Successfully processed: {processed_count}")
            self.logger.info(f"  Failed: {failed_count}")
            self.logger.info(f"  Skipped (already in DB): {skipped_count}")
            self.logger.info(f"  Time elapsed: {elapsed/60:.1f} minutes")
            if processed_count > 0:
                self.logger.info(f"  Average rate: {processed_count/elapsed:.2f} orders/sec")
            self.logger.info(f"  Progress saved to: {self.progress_file}")
            if failed_count > 0:
                self.logger.info(f"  Error log: {self.error_log_file}")
        
        return {
            "processed_count": processed_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "elapsed_time": elapsed,
            "success_rate": (
                processed_count / (processed_count + failed_count)
                if (processed_count + failed_count) > 0
                else 0
            ),
        }
    
    def get_processing_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get current processing statistics.
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range
            
        Returns:
            Dictionary with current progress statistics
        """
        # Count total orders available in date range
        total_available = 0
        try:
            for _ in self.federal_client.list_executive_orders(
                start_date=start_date,
                end_date=end_date,
                max_results=None
            ):
                total_available += 1
        except Exception as e:
            self.logger.warning(f"Could not count total orders: {e}")
        
        return {
            "total_available": total_available,
            "processed_count": len(self.processed_document_numbers),
            "remaining_count": max(0, total_available - len(self.processed_document_numbers)),
            "progress_percentage": (
                (len(self.processed_document_numbers) / total_available * 100)
                if total_available > 0
                else 0
            ),
            "date_range": f"{start_date} to {end_date}",
            "collection_name": self.collection_name,
            "output_dir": str(self.output_dir),
        }