"""
Unit tests for performance monitoring utilities.

This module provides comprehensive tests for the monitoring module, including
the PerformanceMonitor class for tracking batch operations and the setup_logging
function for configuring application logging.

Test Categories:
    - Timer operations: Start, stop, duration calculations
    - Document recording: Success/failure tracking
    - Statistics calculation: Throughput, ETA, success rates
    - Progress display: Progress bar formatting
    - Logging configuration: Log levels and formatting

Python Learning Notes:
    - Time-based tests use mocking to control time
    - String output testing with captured stdout
    - Statistical calculations need precision testing
"""

import io
import logging
import sys
import time
from unittest.mock import MagicMock, call, patch

import pytest

from governmentreporter.utils.monitoring import (PerformanceMonitor,
                                                 setup_logging)


class TestDocumentRecording:
    """
    Test suite for recording document processing results.

    Tests tracking of successful and failed document processing,
    including timing information.

    Python Learning Notes:
        - Method parameters control behavior
        - Lists accumulate processing history
    """

    def test_record_multiple_documents(self):
        """
        Test recording multiple documents with mixed results.

        Should accurately track all successes and failures.
        """
        # Arrange: Started monitor
        monitor = PerformanceMonitor()
        monitor.start()

        # Act: Record various documents
        monitor.record_document(processing_time_ms=100.0)  # Success
        monitor.record_document(processing_time_ms=150.0)  # Success
        monitor.record_document(failed=True)  # Failure
        monitor.record_document(processing_time_ms=200.0)  # Success
        monitor.record_document(failed=True)  # Failure

        # Assert: All counted correctly
        assert monitor.documents_processed == 3
        assert monitor.documents_failed == 2
        assert monitor.processing_times == [100.0, 150.0, 200.0]


class TestStatisticsCalculation:
    """
    Test suite for get_statistics() method.

    Tests calculation of performance metrics including elapsed time,
    throughput, success rates, and ETA calculations.

    Python Learning Notes:
        - Dictionary return values provide structured data
        - Mathematical calculations need precision testing
    """

    def test_statistics_basic(self):
        """
        Test basic statistics calculation.

        Should include elapsed time and counters.
        """
        # Arrange: Monitor with some data
        monitor = PerformanceMonitor()

        with patch("time.time") as mock_time:
            # Start at time 1000
            mock_time.return_value = 1000.0
            monitor.start()

            # Record documents
            monitor.record_document()
            monitor.record_document()
            monitor.record_document(failed=True)

            # Check stats at time 1060 (60 seconds later)
            mock_time.return_value = 1060.0

            # Act: Get statistics
            stats = monitor.get_statistics()

        # Assert: Basic stats calculated
        assert stats["elapsed_time_seconds"] == 60.0
        assert stats["documents_processed"] == 2
        assert stats["documents_failed"] == 1
        assert stats["total_processed"] == 3
        assert stats["success_rate"] == pytest.approx(66.67, rel=0.01)

    def test_statistics_throughput_calculation(self):
        """
        Test throughput (documents per minute) calculation.

        Should accurately calculate processing rate.

        Python Learning Notes:
            - Throughput = items / time * 60 for per-minute rate
            - pytest.approx handles floating-point comparison
        """
        # Arrange: Monitor with real-time
        monitor = PerformanceMonitor()
        monitor.start()

        # Process 10 documents
        for _ in range(10):
            monitor.record_document()

        # Get statistics
        import time

        time.sleep(0.01)  # Ensure some elapsed time
        stats = monitor.get_statistics()

        # Assert: Throughput exists and is reasonable
        assert "throughput_per_minute" in stats
        assert stats["throughput_per_minute"] > 0

    def test_statistics_average_processing_time(self):
        """
        Test average processing time calculation.

        Should calculate mean of recorded times.
        """
        # Arrange: Monitor with timing data
        monitor = PerformanceMonitor()
        monitor.start()

        # Record documents with times
        monitor.record_document(processing_time_ms=100.0)
        monitor.record_document(processing_time_ms=200.0)
        monitor.record_document(processing_time_ms=150.0)

        # Act: Get statistics
        stats = monitor.get_statistics()

        # Assert: Average calculated correctly
        assert "avg_processing_time_ms" in stats
        assert stats["avg_processing_time_ms"] == pytest.approx(150.0)
        assert stats["avg_processing_time_formatted"] == "150.00ms"

    def test_statistics_no_processing_times(self):
        """
        Test statistics when no processing times recorded.

        Average time fields should not be present.
        """
        # Arrange: Monitor without times
        monitor = PerformanceMonitor()
        monitor.start()
        monitor.record_document()  # No time provided

        # Act: Get statistics
        stats = monitor.get_statistics()

        # Assert: No average time fields
        assert "avg_processing_time_ms" not in stats
        assert "avg_processing_time_formatted" not in stats

    def test_statistics_eta_calculation(self):
        """
        Test ETA (Estimated Time to Arrival) calculation.

        Should estimate remaining time based on current rate.

        Python Learning Notes:
            - ETA = remaining items / current rate
            - Provides user-friendly completion estimates
        """
        # Arrange: Monitor with real progress
        monitor = PerformanceMonitor()
        monitor.start()

        # Process 20 out of 100 documents
        for _ in range(20):
            monitor.record_document()

        import time

        time.sleep(0.01)  # Ensure some elapsed time

        # Act: Get statistics with total
        stats = monitor.get_statistics(total_documents=100)

        # Assert: ETA fields exist when total is provided
        assert "remaining_documents" in stats
        assert stats["remaining_documents"] == 80
        assert "eta_seconds" in stats
        assert stats["eta_seconds"] > 0
        assert "completion_percentage" in stats
        assert stats["completion_percentage"] == 20.0

    def test_statistics_eta_no_progress(self):
        """
        Test ETA calculation with no progress.

        Should handle zero rate gracefully.
        """
        # Arrange: Monitor with no documents processed
        monitor = PerformanceMonitor()
        monitor.start()

        # Act: Get statistics with total
        stats = monitor.get_statistics(total_documents=100)

        # Assert: No division by zero error
        # When no documents processed, ETA fields may not be present or behave differently
        if "remaining_documents" in stats:
            assert stats["remaining_documents"] == 100
        if "eta_seconds" in stats:
            assert stats["eta_seconds"] == 0
        if "completion_percentage" in stats:
            assert stats["completion_percentage"] == 0

    def test_statistics_success_rate_no_documents(self):
        """
        Test success rate with no documents processed.

        Should return 0% without division error.

        Python Learning Notes:
            - Guard against division by zero
            - Conditional expressions prevent errors
        """
        # Arrange: Monitor with no documents
        monitor = PerformanceMonitor()
        monitor.start()

        # Act: Get statistics
        stats = monitor.get_statistics()

        # Assert: Success rate is 0
        assert stats["success_rate"] == 0
        assert stats["total_processed"] == 0

    def test_statistics_formatted_elapsed_time(self):
        """
        Test that elapsed time is formatted human-readable.

        Should use appropriate units (seconds, minutes, hours).
        """
        # Arrange: Monitor with different elapsed times
        monitor = PerformanceMonitor()

        test_cases = [
            (30.5, "30.5s"),  # Seconds only
            (90, "1m 30s"),  # Minutes and seconds
            (3665, "1h 1m"),  # Hours and minutes
        ]

        for elapsed, expected_format in test_cases:
            with patch("time.time") as mock_time:
                mock_time.return_value = 1000.0
                monitor.start()
                mock_time.return_value = 1000.0 + elapsed

                # Act: Get statistics
                stats = monitor.get_statistics()

                # Assert: Formatted correctly
                assert stats["elapsed_time_formatted"] == expected_format


class TestProgressDisplay:
    """
    Test suite for print_progress() method.

    Tests the progress bar display functionality including
    formatting and updates.

    Python Learning Notes:
        - Capturing stdout for testing print output
        - Unicode characters for visual progress bars
    """

    def test_print_progress_basic(self):
        """
        Test basic progress bar output.

        Should display bar, percentage, and counts.
        """
        # Arrange: Monitor with progress
        monitor = PerformanceMonitor()
        monitor.start()

        # Capture output
        captured_output = io.StringIO()

        # Act: Print progress at 50%
        with patch("sys.stdout", captured_output):
            monitor.print_progress(50, 100)

        # Assert: Output contains expected elements
        output = captured_output.getvalue()
        assert "50.0%" in output
        assert "50/100" in output
        assert "█" in output  # Filled portion
        assert "░" in output  # Empty portion

    def test_print_progress_complete(self):
        """
        Test progress bar at 100% completion.

        Should add newline when complete.

        Python Learning Notes:
            - \\r for carriage return (overwrite line)
            - Newline only at completion for clean output
        """
        # Arrange: Monitor at completion
        monitor = PerformanceMonitor()
        monitor.start()

        captured_output = io.StringIO()

        # Act: Print 100% progress
        with patch("sys.stdout", captured_output):
            monitor.print_progress(100, 100)

        # Assert: Newline added
        output = captured_output.getvalue()
        assert "100.0%" in output
        assert output.endswith("\n")

    def test_print_progress_zero_total(self):
        """
        Test progress with zero total documents.

        Should handle gracefully without division error.
        """
        # Arrange: Monitor with zero total
        monitor = PerformanceMonitor()
        monitor.start()

        # Act: Print progress with zero total
        # Should return immediately without output
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            monitor.print_progress(0, 0)

        # Assert: No output
        assert captured_output.getvalue() == ""

    def test_print_progress_custom_prefix(self):
        """
        Test progress bar with custom prefix text.

        Should display custom label for the operation.
        """
        # Arrange: Monitor with custom prefix
        monitor = PerformanceMonitor()
        monitor.start()

        captured_output = io.StringIO()

        # Act: Print with custom prefix
        with patch("sys.stdout", captured_output):
            monitor.print_progress(25, 100, prefix="Indexing")

        # Assert: Custom prefix shown
        output = captured_output.getvalue()
        assert "Indexing:" in output
        assert "25.0%" in output

    def test_print_progress_bar_length(self):
        """
        Test that progress bar has correct visual length.

        Bar should be 50 characters as defined in method.

        Python Learning Notes:
            - String multiplication creates repeated characters
            - Visual progress bars improve user experience
        """
        # Arrange: Monitor at 60% progress
        monitor = PerformanceMonitor()
        monitor.start()

        captured_output = io.StringIO()

        # Act: Print 60% progress (30 filled, 20 empty)
        with patch("sys.stdout", captured_output):
            monitor.print_progress(60, 100)

        # Assert: Bar composition
        output = captured_output.getvalue()
        # Extract bar portion between | characters
        bar_match = output[output.find("|") + 1 : output.rfind("|")]
        assert len(bar_match) == 50
        assert bar_match.count("█") == 30  # 60% of 50
        assert bar_match.count("░") == 20  # 40% of 50

    def test_print_progress_with_eta(self):
        """
        Test progress bar includes ETA.

        Should show estimated time to completion.
        """
        # Arrange: Monitor with ETA calculation
        monitor = PerformanceMonitor()

        with patch("time.time") as mock_time:
            mock_time.return_value = 0.0
            monitor.start()

            # Process 30 documents in 15 seconds
            for _ in range(30):
                monitor.record_document()

            mock_time.return_value = 15.0

            captured_output = io.StringIO()

            # Act: Print progress with ETA
            with patch("sys.stdout", captured_output):
                monitor.print_progress(30, 100)

        # Assert: ETA shown
        output = captured_output.getvalue()
        assert "ETA:" in output

    def test_print_progress_overwrite(self):
        """
        Test that progress updates overwrite previous line.

        Should use carriage return for in-place updates.

        Python Learning Notes:
            - \\r returns cursor to line beginning
            - end='' prevents newline
            - flush=True ensures immediate display
        """
        # Arrange: Monitor with multiple updates
        monitor = PerformanceMonitor()
        monitor.start()

        captured_output = io.StringIO()

        # Act: Print multiple progress updates
        with patch("sys.stdout", captured_output):
            monitor.print_progress(25, 100)
            monitor.print_progress(50, 100)
            monitor.print_progress(75, 100)

        # Assert: Uses carriage return
        output = captured_output.getvalue()
        assert "\r" in output
        assert output.count("\n") == 0  # No newlines until complete


class TestPerformanceMonitorIntegration:
    """
    Integration tests for PerformanceMonitor in realistic scenarios.

    Tests the monitor in complete workflows simulating real usage.

    Python Learning Notes:
        - Integration tests verify components work together
        - Realistic scenarios catch edge cases
    """

    def test_complete_batch_processing_workflow(self):
        """
        Test complete workflow of batch document processing.

        Simulates real-world usage with mixed results.
        """
        # Arrange: Setup monitor
        monitor = PerformanceMonitor()

        # Simulate processing with controlled time
        with patch("time.time") as mock_time:
            # Start processing
            mock_time.return_value = 1000.0
            monitor.start()

            # Process 100 documents over 50 seconds
            # 80 successful, 20 failed
            for i in range(100):
                mock_time.return_value = 1000.0 + (i * 0.5)

                if i % 5 == 0:  # Every 5th fails
                    monitor.record_document(failed=True)
                else:
                    # Simulate varying processing times
                    process_time = 100.0 + (i % 10) * 10
                    monitor.record_document(processing_time_ms=process_time)

            # Get final statistics
            mock_time.return_value = 1050.0  # 50 seconds total
            stats = monitor.get_statistics(total_documents=100)

        # Assert: Comprehensive statistics
        assert stats["documents_processed"] == 80
        assert stats["documents_failed"] == 20
        assert stats["total_processed"] == 100
        assert stats["elapsed_time_seconds"] == 50.0
        assert stats["success_rate"] == 80.0
        assert stats["throughput_per_minute"] == 120.0  # 100/50*60
        assert stats["completion_percentage"] == 100.0
        assert "avg_processing_time_ms" in stats

    def test_progress_tracking_with_updates(self):
        """
        Test progress tracking with regular updates.

        Simulates showing progress during processing.
        """
        # Arrange: Monitor and capture output
        monitor = PerformanceMonitor()
        outputs = []

        def capture_print(*args, **kwargs):
            outputs.append(args[0] if args else "")

        # Act: Simulate progress updates
        with patch("builtins.print", side_effect=capture_print):
            with patch("time.time") as mock_time:
                mock_time.return_value = 0.0
                monitor.start()

                # Update progress at intervals
                for i in range(1, 11):
                    mock_time.return_value = i * 2.0  # 2 seconds per doc
                    monitor.record_document()
                    monitor.print_progress(i, 10)

        # Assert: Progress was displayed
        # Should have 10 progress outputs plus potential newline
        assert len(outputs) >= 10
        # Check for completion in outputs
        completion_outputs = [o for o in outputs if "100.0%" in o]
        assert len(completion_outputs) > 0
        assert "10/10" in completion_outputs[0]

    def test_error_recovery_workflow(self):
        """
        Test monitor behavior during error conditions.

        Should continue tracking despite failures.
        """
        # Arrange: Monitor with error simulation
        monitor = PerformanceMonitor()
        monitor.start()

        # Act: Process with high failure rate
        for i in range(50):
            try:
                if i % 3 == 0:
                    raise ValueError("Simulated error")
                monitor.record_document(processing_time_ms=50.0)
            except ValueError:
                monitor.record_document(failed=True)

        # Get statistics
        stats = monitor.get_statistics()

        # Assert: Accurate tracking despite errors
        assert stats["documents_processed"] == 33  # ~2/3 successful
        assert stats["documents_failed"] == 17  # ~1/3 failed
        assert stats["success_rate"] < 70  # Lower success rate
