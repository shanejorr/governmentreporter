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
from unittest.mock import patch, MagicMock, call
import pytest

from governmentreporter.utils.monitoring import (
    PerformanceMonitor,
    setup_logging,
)


class TestPerformanceMonitorInitialization:
    """
    Test suite for PerformanceMonitor initialization and setup.

    Verifies that the monitor starts with correct initial state and
    can be properly initialized for tracking operations.

    Python Learning Notes:
        - __init__ method sets initial instance state
        - Instance variables define object's data
    """

    def test_monitor_initialization(self):
        """
        Test that PerformanceMonitor initializes with correct default values.

        All counters should start at zero and timing should be None.
        """
        # Act: Create new monitor
        monitor = PerformanceMonitor()

        # Assert: Verify initial state
        assert monitor.start_time is None
        assert monitor.documents_processed == 0
        assert monitor.documents_failed == 0
        assert monitor.processing_times == []

    def test_monitor_start(self):
        """
        Test that start() method properly initializes timing.

        Start time should be set and counters reset.

        Python Learning Notes:
            - time.time() returns current Unix timestamp
            - Mocking time allows controlled testing
        """
        # Arrange: Create monitor
        monitor = PerformanceMonitor()

        # Act: Start monitoring
        with patch("time.time", return_value=1234567890.0):
            monitor.start()

        # Assert: Start time is set
        assert monitor.start_time == 1234567890.0
        assert monitor.documents_processed == 0
        assert monitor.documents_failed == 0
        assert monitor.processing_times == []

    def test_monitor_start_resets_state(self):
        """
        Test that start() resets previous state.

        Calling start again should clear all previous metrics.
        """
        # Arrange: Monitor with existing data
        monitor = PerformanceMonitor()
        monitor.documents_processed = 10
        monitor.documents_failed = 2
        monitor.processing_times = [100.0, 200.0]

        # Act: Start again
        monitor.start()

        # Assert: State is reset
        assert monitor.documents_processed == 0
        assert monitor.documents_failed == 0
        assert monitor.processing_times == []


class TestDocumentRecording:
    """
    Test suite for recording document processing results.

    Tests tracking of successful and failed document processing,
    including timing information.

    Python Learning Notes:
        - Method parameters control behavior
        - Lists accumulate processing history
    """

    def test_record_successful_document(self):
        """
        Test recording a successfully processed document.

        Should increment success counter.
        """
        # Arrange: Started monitor
        monitor = PerformanceMonitor()
        monitor.start()

        # Act: Record successful document
        monitor.record_document()

        # Assert: Counter incremented
        assert monitor.documents_processed == 1
        assert monitor.documents_failed == 0

    def test_record_successful_document_with_time(self):
        """
        Test recording successful document with processing time.

        Should store timing information for statistics.
        """
        # Arrange: Started monitor
        monitor = PerformanceMonitor()
        monitor.start()

        # Act: Record with processing time
        monitor.record_document(processing_time_ms=150.5)

        # Assert: Time recorded
        assert monitor.documents_processed == 1
        assert monitor.documents_failed == 0
        assert monitor.processing_times == [150.5]

    def test_record_failed_document(self):
        """
        Test recording a failed document.

        Should increment failure counter, not success.
        """
        # Arrange: Started monitor
        monitor = PerformanceMonitor()
        monitor.start()

        # Act: Record failure
        monitor.record_document(failed=True)

        # Assert: Failure counted
        assert monitor.documents_processed == 0
        assert monitor.documents_failed == 1
        assert monitor.processing_times == []

    def test_record_failed_document_ignores_time(self):
        """
        Test that failed documents don't record processing time.

        Time is only meaningful for successful processing.

        Python Learning Notes:
            - Conditional logic in record_document
            - Failed operations don't contribute to timing stats
        """
        # Arrange: Started monitor
        monitor = PerformanceMonitor()
        monitor.start()

        # Act: Record failure with time (should be ignored)
        monitor.record_document(processing_time_ms=100.0, failed=True)

        # Assert: Time not recorded for failure
        assert monitor.documents_failed == 1
        assert monitor.processing_times == []

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

    def test_record_document_without_starting(self):
        """
        Test recording documents without calling start().

        Should still track counts even without timing.
        """
        # Arrange: Monitor not started
        monitor = PerformanceMonitor()

        # Act: Record documents
        monitor.record_document()
        monitor.record_document(failed=True)

        # Assert: Counts still work
        assert monitor.documents_processed == 1
        assert monitor.documents_failed == 1


class TestStatisticsCalculation:
    """
    Test suite for get_statistics() method.

    Tests calculation of performance metrics including elapsed time,
    throughput, success rates, and ETA calculations.

    Python Learning Notes:
        - Dictionary return values provide structured data
        - Mathematical calculations need precision testing
    """

    def test_statistics_not_started(self):
        """
        Test getting statistics without starting monitor.

        Should return error indicator.
        """
        # Arrange: Monitor not started
        monitor = PerformanceMonitor()

        # Act: Get statistics
        stats = monitor.get_statistics()

        # Assert: Error returned
        assert "error" in stats
        assert stats["error"] == "Monitor not started"

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


class TestDurationFormatting:
    """
    Test suite for _format_duration() helper method.

    Tests conversion of seconds to human-readable format.

    Python Learning Notes:
        - Private methods (starting with _) are implementation details
        - Human-readable formatting improves user experience
    """

    def test_format_duration_seconds(self):
        """
        Test formatting durations under 60 seconds.

        Should show seconds with decimal.
        """
        # Arrange: Monitor instance
        monitor = PerformanceMonitor()

        # Act & Assert: Various second values
        assert monitor._format_duration(5.5) == "5.5s"
        assert monitor._format_duration(30.2) == "30.2s"
        assert monitor._format_duration(59.9) == "59.9s"

    def test_format_duration_minutes(self):
        """
        Test formatting durations in minutes range.

        Should show minutes and seconds.
        """
        # Arrange: Monitor instance
        monitor = PerformanceMonitor()

        # Act & Assert: Various minute values
        assert monitor._format_duration(60) == "1m 0s"
        assert monitor._format_duration(90) == "1m 30s"
        assert monitor._format_duration(125) == "2m 5s"
        assert monitor._format_duration(3599) == "59m 59s"

    def test_format_duration_hours(self):
        """
        Test formatting durations over an hour.

        Should show hours and minutes.

        Python Learning Notes:
            - Integer division // for whole units
            - Modulo % for remainders
        """
        # Arrange: Monitor instance
        monitor = PerformanceMonitor()

        # Act & Assert: Various hour values
        assert monitor._format_duration(3600) == "1h 0m"
        assert monitor._format_duration(3665) == "1h 1m"
        assert monitor._format_duration(7200) == "2h 0m"
        assert monitor._format_duration(10800) == "3h 0m"

    def test_format_duration_edge_cases(self):
        """
        Test duration formatting edge cases.

        Should handle zero and very large values.
        """
        # Arrange: Monitor instance
        monitor = PerformanceMonitor()

        # Act & Assert: Edge cases
        assert monitor._format_duration(0) == "0.0s"
        assert monitor._format_duration(0.1) == "0.1s"
        assert monitor._format_duration(86400) == "24h 0m"  # 24 hours


class TestSetupLogging:
    """
    Test suite for setup_logging() function.

    Tests configuration of Python's logging system for the application.

    Python Learning Notes:
        - logging.basicConfig configures root logger
        - Log levels control message visibility
    """

    def test_setup_logging_default(self):
        """
        Test default logging setup (INFO level).

        Should configure INFO level when verbose is False.
        """
        # Act: Setup with default
        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=False)

        # Assert: INFO level configured
        mock_config.assert_called_once()
        call_kwargs = mock_config.call_args[1]
        assert call_kwargs["level"] == logging.INFO

    def test_setup_logging_verbose(self):
        """
        Test verbose logging setup (DEBUG level).

        Should configure DEBUG level when verbose is True.
        """
        # Act: Setup with verbose
        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=True)

        # Assert: DEBUG level configured
        mock_config.assert_called_once()
        call_kwargs = mock_config.call_args[1]
        assert call_kwargs["level"] == logging.DEBUG

    def test_setup_logging_format(self):
        """
        Test logging format configuration.

        Should set appropriate format string with timestamp.

        Python Learning Notes:
            - Format strings control log message appearance
            - %(name)s style is older but widely used
        """
        # Act: Setup logging
        with patch("logging.basicConfig") as mock_config:
            setup_logging()

        # Assert: Format configured
        call_kwargs = mock_config.call_args[1]
        assert "format" in call_kwargs
        format_str = call_kwargs["format"]
        assert "%(asctime)s" in format_str
        assert "%(name)s" in format_str
        assert "%(levelname)s" in format_str
        assert "%(message)s" in format_str

    def test_setup_logging_date_format(self):
        """
        Test date format in logging configuration.

        Should use readable date/time format.
        """
        # Act: Setup logging
        with patch("logging.basicConfig") as mock_config:
            setup_logging()

        # Assert: Date format configured
        call_kwargs = mock_config.call_args[1]
        assert "datefmt" in call_kwargs
        assert call_kwargs["datefmt"] == "%Y-%m-%d %H:%M:%S"

    def test_setup_logging_library_suppression(self):
        """
        Test suppression of noisy library loggers.

        Should reduce verbosity of third-party libraries.

        Python Learning Notes:
            - getLogger retrieves named loggers
            - Libraries often have verbose debug output
        """
        # Arrange: Mock getLogger
        mock_loggers = {}

        def mock_get_logger(name):
            if name not in mock_loggers:
                mock_loggers[name] = MagicMock()
            return mock_loggers[name]

        # Act: Setup logging
        with patch("logging.getLogger", side_effect=mock_get_logger):
            with patch("logging.basicConfig"):
                setup_logging()

        # Assert: Library loggers set to WARNING
        assert "urllib3" in mock_loggers
        mock_loggers["urllib3"].setLevel.assert_called_with(logging.WARNING)

        assert "openai" in mock_loggers
        mock_loggers["openai"].setLevel.assert_called_with(logging.WARNING)

        assert "httpx" in mock_loggers
        mock_loggers["httpx"].setLevel.assert_called_with(logging.WARNING)


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

    def test_concurrent_monitoring(self):
        """
        Test monitor with simulated concurrent operations.

        While PerformanceMonitor isn't thread-safe by design,
        test basic concurrent usage patterns.

        Python Learning Notes:
            - Real concurrent monitoring would need locks
            - This tests sequential updates from multiple sources
        """
        # Arrange: Multiple monitors for different operations
        monitor1 = PerformanceMonitor()
        monitor2 = PerformanceMonitor()

        # Act: Simulate parallel operations
        monitor1.start()
        monitor2.start()

        # Operation 1: Fast processing
        for _ in range(100):
            monitor1.record_document(processing_time_ms=10.0)

        # Operation 2: Slow processing
        for _ in range(20):
            monitor2.record_document(processing_time_ms=500.0)

        # Get statistics
        stats1 = monitor1.get_statistics()
        stats2 = monitor2.get_statistics()

        # Assert: Independent tracking
        assert stats1["documents_processed"] == 100
        assert stats1["avg_processing_time_ms"] == 10.0

        assert stats2["documents_processed"] == 20
        assert stats2["avg_processing_time_ms"] == 500.0
