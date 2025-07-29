"""Bulk processor for Supreme Court opinions from CourtListener API."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set

from ..apis import CourtListenerClient
from ..database import ChromaDBClient
from ..metadata import GeminiMetadataGenerator
from ..utils import GoogleEmbeddingsClient


class SCOTUSBulkProcessor:
    """Processes all SCOTUS opinions through the complete pipeline.

    This class handles the systematic processing of Supreme Court opinions
    from the CourtListener API, including:
    - API pagination and rate limiting
    - Complete pipeline processing (metadata, embeddings, storage)
    - Progress tracking and error handling
    - Resumable operations
    """

    def __init__(
        self,
        output_dir: str = "raw-data/scotus_data",
        since_date: str = "1900-01-01",
        rate_limit_delay: float = 0.75,
        max_retries: int = 3,
        collection_name: str = "federal_court_scotus_opinions",
    ):
        """Initialize the bulk processor.

        Args:
            output_dir: Directory to store progress and error logs
            since_date: Start date for opinion retrieval (YYYY-MM-DD)
            rate_limit_delay: Delay between API requests in seconds
            max_retries: Maximum number of retries for failed requests
            collection_name: ChromaDB collection name for storage
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.since_date = since_date
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.collection_name = collection_name

        # Initialize clients
        self.court_client = CourtListenerClient()
        self.db_client = ChromaDBClient()
        self.metadata_generator = GeminiMetadataGenerator()
        self.embeddings_client = GoogleEmbeddingsClient()

        # Progress tracking
        self.progress_file = self.output_dir / "processing_progress.json"
        self.error_log_file = self.output_dir / "error_log.jsonl"
        self.processed_ids: Set[str] = set()

        # Load existing progress
        self._load_progress()

    def _load_progress(self) -> None:
        """Load previously processed opinion IDs from progress file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r") as f:
                    progress_data = json.load(f)
                    self.processed_ids = set(progress_data.get("processed_ids", []))
                    print(
                        f"Loaded progress: {len(self.processed_ids)} opinions already processed"
                    )
            except Exception as e:
                print(f"Warning: Could not load progress file: {e}")
                self.processed_ids = set()

    def _save_progress(self) -> None:
        """Save current progress to file."""
        progress_data = {
            "processed_ids": list(self.processed_ids),
            "last_updated": datetime.now().isoformat(),
            "total_processed": len(self.processed_ids),
            "since_date": self.since_date,
            "collection_name": self.collection_name,
        }

        with open(self.progress_file, "w") as f:
            json.dump(progress_data, f, indent=2)

    def _log_error(
        self, opinion_id: str, error: str, opinion_data: Optional[Dict] = None
    ) -> None:
        """Log errors to error log file."""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "opinion_id": opinion_id,
            "error": error,
            "opinion_data": opinion_data,
        }

        with open(self.error_log_file, "a") as f:
            f.write(json.dumps(error_entry) + "\n")

    def _process_single_opinion(self, opinion_summary: Dict[str, Any]) -> bool:
        """Process a single opinion through the complete pipeline.

        Args:
            opinion_summary: Opinion metadata from the listing API

        Returns:
            True if successful, False otherwise
        """
        opinion_id = str(opinion_summary.get("id"))

        if opinion_id in self.processed_ids:
            return True  # Already processed

        print(f"Processing opinion {opinion_id}...")

        try:
            # Step 1: Get full opinion details with retry logic
            for attempt in range(self.max_retries):
                try:
                    raw_opinion_data = self.court_client.get_opinion(int(opinion_id))
                    break
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise e
                    print(f"  Retry {attempt + 1} for opinion {opinion_id}: {e}")
                    time.sleep(self.rate_limit_delay * 2)

            basic_metadata = self.court_client.extract_basic_metadata(raw_opinion_data)

            # Skip if no text content
            plain_text = basic_metadata.get("plain_text", "").strip()
            if not plain_text:
                print(f"  Skipping opinion {opinion_id}: No text content")
                self.processed_ids.add(opinion_id)
                return True

            print(f"  Text length: {len(plain_text)} characters")

            # Step 2: Generate AI metadata
            print("  Generating metadata with Gemini...")
            ai_metadata = self.metadata_generator.generate_scotus_metadata(plain_text)

            # Step 3: Generate embeddings
            print("  Generating embeddings...")
            embedding = self.embeddings_client.generate_embedding(plain_text)

            # Step 4: Combine metadata
            combined_metadata = {**basic_metadata, **ai_metadata}
            final_metadata = {
                k: v for k, v in combined_metadata.items() if k != "plain_text"
            }

            # Step 5: Store in ChromaDB
            print("  Storing in ChromaDB...")
            self.db_client.store_scotus_opinion(
                opinion_id=opinion_id,
                plain_text=plain_text,
                embedding=embedding,
                metadata=final_metadata,
            )

            # Mark as processed
            self.processed_ids.add(opinion_id)
            print(f"  ✅ Successfully processed opinion {opinion_id}")

            return True

        except Exception as e:
            error_msg = f"Failed to process opinion {opinion_id}: {str(e)}"
            print(f"  ❌ {error_msg}")
            self._log_error(opinion_id, error_msg, opinion_summary)
            return False

    def get_total_count(self) -> int:
        """Get total count of SCOTUS opinions to process.

        Returns:
            Total number of opinions matching the criteria
        """
        try:
            return self.court_client.get_scotus_opinion_count(
                since_date=self.since_date
            )
        except Exception as e:
            print(f"Warning: Could not get total count: {e}")
            return 0

    def process_all_opinions(
        self, max_opinions: Optional[int] = None
    ) -> Dict[str, Any]:
        """Process all SCOTUS opinions since the specified date.

        Args:
            max_opinions: Maximum number of opinions to process (None for all)

        Returns:
            Dictionary with processing statistics
        """
        print(f"Starting SCOTUS opinion processing since {self.since_date}")
        print(f"Output directory: {self.output_dir}")
        print(f"Rate limit delay: {self.rate_limit_delay}s")
        print(f"Collection: {self.collection_name}")

        # Get total count
        total_count = self.get_total_count()
        if total_count > 0:
            print(f"Total opinions available: {total_count:,}")
            remaining = total_count - len(self.processed_ids)
            print(f"Remaining to process: {remaining:,}")

        start_time = time.time()
        processed_count = 0
        failed_count = 0

        try:
            # Iterate through all opinions
            for opinion_summary in self.court_client.list_scotus_opinions(
                since_date=self.since_date,
                max_results=max_opinions,
                rate_limit_delay=self.rate_limit_delay,
            ):
                success = self._process_single_opinion(opinion_summary)

                if success:
                    processed_count += 1
                else:
                    failed_count += 1

                # Save progress every 10 opinions
                if (processed_count + failed_count) % 10 == 0:
                    self._save_progress()

                # Show progress
                elapsed = time.time() - start_time
                if elapsed > 0:
                    rate = processed_count / elapsed
                    print(
                        f"Progress: {processed_count} processed, {failed_count} failed, "
                        f"{rate:.2f} opinions/sec"
                    )

                # Respect rate limits
                time.sleep(self.rate_limit_delay)

        except KeyboardInterrupt:
            print("\n⚠️  Processing interrupted by user")
        except Exception as e:
            print(f"\n❌ Processing failed with error: {e}")
        finally:
            # Save final progress
            self._save_progress()

            # Print summary
            elapsed = time.time() - start_time
            print(f"\n{'='*60}")
            print(f"Processing Summary:")
            print(f"  Total processed: {processed_count}")
            print(f"  Total failed: {failed_count}")
            print(f"  Time elapsed: {elapsed/60:.1f} minutes")
            print(
                f"  Average rate: {processed_count/elapsed:.2f} opinions/sec"
                if elapsed > 0
                else ""
            )
            print(f"  Progress saved to: {self.progress_file}")
            if failed_count > 0:
                print(f"  Error log: {self.error_log_file}")

        return {
            "processed_count": processed_count,
            "failed_count": failed_count,
            "elapsed_time": elapsed,
            "total_available": total_count,
            "success_rate": (
                processed_count / (processed_count + failed_count)
                if (processed_count + failed_count) > 0
                else 0
            ),
        }

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
            "collection_name": self.collection_name,
            "output_dir": str(self.output_dir),
        }
