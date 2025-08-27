"""
Performance monitoring utilities for ingestion and processing.

This module provides tools for monitoring and reporting on the performance of
batch operations, particularly document ingestion. It tracks processing times,
throughput, success rates, and provides estimated completion times for long-running
operations.

The module focuses on:
    - Real-time progress tracking with visual progress bars
    - Performance metrics calculation (throughput, success rate)
    - Estimated time to completion (ETA) calculations
    - Human-readable duration formatting
    - Statistical analysis of processing times

Python Learning Notes:
    - Performance monitoring helps identify bottlenecks
    - Progress bars improve user experience for long operations
    - Statistical metrics help optimize batch sizes
    - Time tracking enables capacity planning
"""

import time
from typing import Any, Dict, List, Optional


class PerformanceMonitor:
    """
    Monitors and reports on batch operation performance metrics.

    This class tracks processing times, throughput, and provides
    estimated completion times for batch operations. It's particularly
    useful for monitoring document ingestion, API calls, and other
    long-running processes where progress feedback is valuable.

    The monitor tracks:
        - Elapsed time and processing rates
        - Success/failure counts and rates
        - Individual operation timing statistics
        - Progress visualization with ETA

    Attributes:
        start_time (float): Unix timestamp when monitoring started
        documents_processed (int): Count of successfully processed items
        documents_failed (int): Count of failed items
        processing_times (List[float]): Individual processing times in milliseconds

    Example:
        # Initialize and start monitoring
        monitor = PerformanceMonitor()
        monitor.start()

        # Process documents with progress tracking
        total_docs = 1000
        for i, doc in enumerate(documents):
            start = time.time()
            try:
                process_document(doc)
                monitor.record_document((time.time() - start) * 1000)
                monitor.print_progress(i + 1, total_docs)
            except Exception as e:
                monitor.record_document(failed=True)

        # Get final statistics
        stats = monitor.get_statistics(total_docs)
        print(f"Completed in {stats['elapsed_time_formatted']}")
        print(f"Success rate: {stats['success_rate']:.1f}%")
        print(f"Throughput: {stats['throughput_per_minute']:.1f} docs/min")

    Python Learning Notes:
        - Classes encapsulate related state and behavior
        - time.time() returns Unix timestamp in seconds
        - Instance variables track state across method calls
        - Type hints clarify expected types
    """

    def __init__(self):
        """
        Initialize the performance monitor.

        Sets up the monitor with initial state. The monitor must be
        explicitly started with start() before recording metrics.

        Python Learning Notes:
            - __init__ is called when creating new instances
            - None is Python's null value
            - Lists store ordered collections of items
        """
        self.start_time: Optional[float] = None
        self.documents_processed: int = 0
        self.documents_failed: int = 0
        self.processing_times: List[float] = []

    def start(self) -> None:
        """
        Start timing a batch operation.

        Resets all metrics and begins timing. This should be called at the
        beginning of each batch operation you want to monitor.

        Example:
            monitor = PerformanceMonitor()
            monitor.start()  # Begin timing
            # ... perform operations ...
            stats = monitor.get_statistics()

        Python Learning Notes:
            - -> None indicates the method returns nothing
            - time.time() gives current time as float seconds
            - Resetting state ensures clean metrics
        """
        self.start_time = time.time()
        self.documents_processed = 0
        self.documents_failed = 0
        self.processing_times = []

    def record_document(
        self, processing_time_ms: Optional[float] = None, failed: bool = False
    ) -> None:
        """
        Record that a document has been processed.

        Updates the appropriate counters and optionally records the processing
        time for statistical analysis. This should be called after each item
        is processed, whether successfully or not.

        Args:
            processing_time_ms (Optional[float]): Time taken to process this
                document in milliseconds. Used for calculating average times
                and identifying performance patterns.
            failed (bool): Whether processing failed. Failed items are counted
                separately and affect the success rate calculation.

        Example:
            # Record successful processing with timing
            start = time.time()
            process_document(doc)
            elapsed_ms = (time.time() - start) * 1000
            monitor.record_document(processing_time_ms=elapsed_ms)

            # Record failure
            try:
                process_document(bad_doc)
            except:
                monitor.record_document(failed=True)

        Python Learning Notes:
            - Optional parameters can be None
            - Boolean flags control conditional logic
            - append() adds items to end of list
            - += increments counter variables
        """
        if failed:
            self.documents_failed += 1
        else:
            self.documents_processed += 1
            if processing_time_ms:
                self.processing_times.append(processing_time_ms)

    def get_statistics(self, total_documents: Optional[int] = None) -> Dict[str, Any]:
        """
        Get current performance statistics.

        Calculates and returns comprehensive performance metrics including
        elapsed time, throughput, success rates, and ETA if total is provided.

        Args:
            total_documents (Optional[int]): Total number of documents to process.
                When provided, enables ETA calculation and completion percentage.

        Returns:
            Dict[str, Any]: Dictionary containing performance metrics:
                - elapsed_time_seconds: Total elapsed time in seconds
                - elapsed_time_formatted: Human-readable elapsed time
                - documents_processed: Count of successful items
                - documents_failed: Count of failed items
                - total_processed: Sum of processed and failed
                - success_rate: Percentage of successful items
                - throughput_per_minute: Items processed per minute
                - avg_processing_time_ms: Average time per item (if available)
                - remaining_documents: Items left to process (if total provided)
                - eta_seconds: Estimated seconds to completion (if total provided)
                - eta_formatted: Human-readable ETA (if total provided)
                - completion_percentage: Progress percentage (if total provided)

        Example:
            # Get statistics during processing
            stats = monitor.get_statistics(total_documents=5000)

            print(f"Progress: {stats['completion_percentage']:.1f}%")
            print(f"ETA: {stats['eta_formatted']}")
            print(f"Success rate: {stats['success_rate']:.1f}%")
            print(f"Throughput: {stats['throughput_per_minute']:.0f} docs/min")

            if 'avg_processing_time_ms' in stats:
                print(f"Avg time: {stats['avg_processing_time_ms']:.2f}ms")

        Python Learning Notes:
            - Dictionary comprehension creates dictionaries efficiently
            - Conditional expressions (x if condition else y)
            - Division by zero checks prevent crashes
            - f-strings format numbers with precision
        """
        if not self.start_time:
            return {"error": "Monitor not started"}

        elapsed_time = time.time() - self.start_time
        total_processed = self.documents_processed + self.documents_failed

        stats = {
            "elapsed_time_seconds": elapsed_time,
            "elapsed_time_formatted": self._format_duration(elapsed_time),
            "documents_processed": self.documents_processed,
            "documents_failed": self.documents_failed,
            "total_processed": total_processed,
            "success_rate": (
                (self.documents_processed / total_processed * 100)
                if total_processed > 0
                else 0
            ),
            "throughput_per_minute": (
                (total_processed / elapsed_time * 60) if elapsed_time > 0 else 0
            ),
        }

        # Add average processing time if available
        if self.processing_times:
            avg_time = sum(self.processing_times) / len(self.processing_times)
            stats["avg_processing_time_ms"] = avg_time
            stats["avg_processing_time_formatted"] = f"{avg_time:.2f}ms"

        # Calculate ETA if total is provided
        if total_documents and total_processed > 0:
            remaining = total_documents - total_processed
            rate = total_processed / elapsed_time
            eta_seconds = remaining / rate if rate > 0 else 0

            stats["remaining_documents"] = remaining
            stats["eta_seconds"] = eta_seconds
            stats["eta_formatted"] = self._format_duration(eta_seconds)
            stats["completion_percentage"] = total_processed / total_documents * 100

        return stats

    def print_progress(
        self, current: int, total: int, prefix: str = "Progress"
    ) -> None:
        """
        Print a progress bar to console.

        Displays a visual progress bar with percentage, counts, and ETA.
        The bar updates in place using carriage return, providing a clean
        progress display without scrolling.

        Args:
            current (int): Current number of items processed
            total (int): Total number of items to process
            prefix (str): Prefix text for the progress bar. Default is "Progress".
                Custom prefixes help distinguish multiple operations.

        Example:
            # Simple progress tracking
            monitor = PerformanceMonitor()
            monitor.start()

            for i in range(100):
                process_item(items[i])
                monitor.record_document()
                monitor.print_progress(i + 1, 100, "Processing")

            # Output: Processing: |████████████████████░░░░░| 80.0% (80/100) ETA: 30s

        Python Learning Notes:
            - \\r returns cursor to line start for overwriting
            - end='' prevents newline, flush=True forces immediate output
            - Unicode characters (█, ░) create visual progress bars
            - String multiplication ('x' * n) repeats characters
        """
        if total == 0:
            return

        percent = current / total * 100
        bar_length = 50
        filled = int(bar_length * current / total)
        bar = "█" * filled + "░" * (bar_length - filled)

        stats = self.get_statistics(total)
        eta = stats.get("eta_formatted", "calculating...")

        # Use carriage return to overwrite the same line
        print(
            f"\r{prefix}: |{bar}| {percent:.1f}% ({current}/{total}) ETA: {eta}",
            end="",
            flush=True,
        )

        if current >= total:
            print()  # New line when complete

    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in seconds to human-readable string.

        Converts raw seconds into a readable format like "2h 15m 30s" or
        "45.3s" depending on the duration length. This makes times more
        understandable for users.

        Args:
            seconds (float): Duration in seconds to format

        Returns:
            str: Formatted string like "2h 15m 30s", "15m 45s", or "30.5s"
                depending on the duration magnitude.

        Example:
            print(_format_duration(7890))  # "2h 11m"
            print(_format_duration(185))   # "3m 5s"
            print(_format_duration(42.7))  # "42.7s"

        Python Learning Notes:
            - Integer division // discards remainder
            - Modulo % gives remainder after division
            - Conditional chains (if/elif/else) handle cases
            - f-strings embed expressions with formatting
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for ingestion scripts.

    Sets up Python's logging system with appropriate format and level.
    This function configures logging for the entire application, making
    debug output and error messages consistent and informative.

    Args:
        verbose (bool): If True, sets logging level to DEBUG for detailed
            output. If False (default), uses INFO level for normal output.

    Example:
        # Normal logging
        setup_logging()

        # Verbose logging for debugging
        setup_logging(verbose=True)

        # After setup, use logging throughout code
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Starting ingestion")
        logger.debug("Detailed debug info")  # Only shown if verbose=True

    Python Learning Notes:
        - logging module provides flexible event logging
        - basicConfig sets up the root logger
        - getLogger creates/retrieves named loggers
        - Log levels control message visibility (DEBUG < INFO < WARNING < ERROR)
    """
    import logging

    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Reduce noise from some libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
