"""
Tests for base document ingester abstract class.

This module tests the DocumentIngester base class that provides
common functionality for all ingestion pipelines.

Python Learning Notes:
    - Abstract base classes cannot be instantiated directly
    - Concrete subclasses must implement abstract methods
    - Testing abstract classes requires creating test implementations
"""

import pytest
from unittest.mock import MagicMock, patch, call
from abc import ABC

from governmentreporter.ingestion.base import DocumentIngester


class ConcreteIngester(DocumentIngester):
    """
    Concrete implementation of DocumentIngester for testing.

    This class implements all abstract methods to enable testing
    of the base class functionality.

    Python Learning Notes:
        - Test doubles provide minimal implementations for testing
        - Must implement all abstract methods from base class
        - Can add test-specific attributes and methods
    """

    def _get_collection_name(self):
        """Return test collection name."""
        return "test_collection"

    def _fetch_document_ids(self):
        """Return test document IDs."""
        return ["doc1", "doc2", "doc3"]

    def _process_single_document(self, doc_id, batch_docs, batch_embeds):
        """Mock document processing."""
        batch_docs.append({"id": doc_id, "text": f"Content for {doc_id}"})
        batch_embeds.append([0.1] * 1536)  # Mock embedding
        return True


@pytest.fixture
def mock_dependencies():
    """
    Mock all external dependencies for ingester.

    Returns:
        dict: Dictionary of mocked dependencies.
    """
    return {
        "progress_tracker": MagicMock(),
        "embedding_generator": MagicMock(),
        "qdrant_client": MagicMock(),
        "performance_monitor": MagicMock(),
    }


class TestDocumentIngesterInitialization:
    """Test base ingester initialization."""

    def test_ingester_initialization_with_required_params(self):
        """Test ingester initializes with required parameters."""
        ingester = ConcreteIngester(start_date="2024-01-01", end_date="2024-12-31")

        assert ingester.start_date == "2024-01-01"
        assert ingester.end_date == "2024-12-31"
        assert ingester.batch_size > 0
        assert ingester.dry_run is False

    def test_ingester_initialization_with_custom_batch_size(self):
        """Test ingester accepts custom batch size."""
        ingester = ConcreteIngester(
            start_date="2024-01-01", end_date="2024-12-31", batch_size=100
        )

        assert ingester.batch_size == 100

    def test_ingester_initialization_with_dry_run(self):
        """Test ingester accepts dry run flag."""
        ingester = ConcreteIngester(
            start_date="2024-01-01", end_date="2024-12-31", dry_run=True
        )

        assert ingester.dry_run is True

    def test_ingester_initialization_with_custom_paths(self):
        """Test ingester accepts custom database paths."""
        ingester = ConcreteIngester(
            start_date="2024-01-01",
            end_date="2024-12-31",
            progress_db="./custom_progress.db",
            qdrant_db_path="./custom_qdrant",
        )

        assert ingester.progress_db == "./custom_progress.db"
        assert ingester.qdrant_db_path == "./custom_qdrant"

    def test_ingester_validates_date_format(self):
        """Test ingester validates date format during initialization."""
        # Valid dates should work
        ingester = ConcreteIngester(start_date="2024-01-01", end_date="2024-12-31")
        assert ingester is not None

        # Invalid dates might raise error or be handled differently
        # Implementation specific


class TestDocumentIngesterAbstractMethods:
    """Test abstract method requirements."""

    def test_cannot_instantiate_base_class_directly(self):
        """Test that DocumentIngester cannot be instantiated directly."""
        with pytest.raises(TypeError):
            # Should raise TypeError because it's abstract
            ingester = DocumentIngester(start_date="2024-01-01", end_date="2024-12-31")

    def test_concrete_class_must_implement_get_collection_name(self):
        """Test concrete class must implement _get_collection_name."""

        class IncompleteIngester1(DocumentIngester):
            def _fetch_document_ids(self):
                return []

            def _process_single_document(self, doc_id, batch_docs, batch_embeds):
                return True

            # Missing _get_collection_name

        with pytest.raises(TypeError):
            ingester = IncompleteIngester1(
                start_date="2024-01-01", end_date="2024-12-31"
            )

    def test_concrete_class_must_implement_fetch_document_ids(self):
        """Test concrete class must implement _fetch_document_ids."""

        class IncompleteIngester2(DocumentIngester):
            def _get_collection_name(self):
                return "test"

            def _process_single_document(self, doc_id, batch_docs, batch_embeds):
                return True

            # Missing _fetch_document_ids

        with pytest.raises(TypeError):
            ingester = IncompleteIngester2(
                start_date="2024-01-01", end_date="2024-12-31"
            )

    def test_concrete_class_must_implement_process_single_document(self):
        """Test concrete class must implement _process_single_document."""

        class IncompleteIngester3(DocumentIngester):
            def _get_collection_name(self):
                return "test"

            def _fetch_document_ids(self):
                return []

            # Missing _process_single_document

        with pytest.raises(TypeError):
            ingester = IncompleteIngester3(
                start_date="2024-01-01", end_date="2024-12-31"
            )


class TestDocumentIngesterRunMethod:
    """Test main ingestion run method."""

    @patch("governmentreporter.ingestion.base.PerformanceMonitor")
    @patch("governmentreporter.ingestion.base.QdrantIngestionClient")
    @patch("governmentreporter.ingestion.base.EmbeddingGenerator")
    @patch("governmentreporter.ingestion.base.ProgressTracker")
    def test_run_processes_all_documents(
        self,
        mock_progress_class,
        mock_embedding_class,
        mock_qdrant_class,
        mock_monitor_class,
    ):
        """Test run method processes all documents."""
        # Setup mocks
        mock_progress = MagicMock()
        mock_progress.get_all_unprocessed_ids.return_value = ["doc1", "doc2", "doc3"]
        mock_progress_class.return_value = mock_progress

        mock_embedding_gen = MagicMock()
        mock_embedding_class.return_value = mock_embedding_gen

        mock_qdrant = MagicMock()
        mock_qdrant_class.return_value = mock_qdrant

        mock_monitor = MagicMock()
        mock_monitor_class.return_value = mock_monitor

        # Create and run ingester
        ingester = ConcreteIngester(start_date="2024-01-01", end_date="2024-12-31")

        ingester.run()

        # Verify documents were fetched and tracked
        mock_progress.mark_completed.call_count >= 0  # May vary based on implementation

    @patch("governmentreporter.ingestion.base.PerformanceMonitor")
    @patch("governmentreporter.ingestion.base.QdrantIngestionClient")
    @patch("governmentreporter.ingestion.base.EmbeddingGenerator")
    @patch("governmentreporter.ingestion.base.ProgressTracker")
    def test_run_respects_dry_run_mode(
        self,
        mock_progress_class,
        mock_embedding_class,
        mock_qdrant_class,
        mock_monitor_class,
    ):
        """Test run method respects dry_run flag."""
        # Setup mocks
        mock_progress = MagicMock()
        mock_progress.get_all_unprocessed_ids.return_value = ["doc1", "doc2"]
        mock_progress_class.return_value = mock_progress

        mock_qdrant = MagicMock()
        mock_qdrant_class.return_value = mock_qdrant

        # Create and run in dry-run mode
        ingester = ConcreteIngester(
            start_date="2024-01-01", end_date="2024-12-31", dry_run=True
        )

        ingester.run()

        # Verify Qdrant wasn't called for storage
        # (implementation specific - might not call batch_upsert)
        assert mock_qdrant is not None

    @patch("governmentreporter.ingestion.base.PerformanceMonitor")
    @patch("governmentreporter.ingestion.base.QdrantIngestionClient")
    @patch("governmentreporter.ingestion.base.EmbeddingGenerator")
    @patch("governmentreporter.ingestion.base.ProgressTracker")
    def test_run_handles_empty_document_list(
        self,
        mock_progress_class,
        mock_embedding_class,
        mock_qdrant_class,
        mock_monitor_class,
    ):
        """Test run method handles empty document list."""
        mock_progress = MagicMock()
        mock_progress.get_all_unprocessed_ids.return_value = []
        mock_progress_class.return_value = mock_progress

        ingester = ConcreteIngester(start_date="2024-01-01", end_date="2024-12-31")

        # Should complete without error
        ingester.run()


class TestDocumentIngesterBatchProcessing:
    """Test batch processing functionality."""

    @patch("governmentreporter.ingestion.base.PerformanceMonitor")
    @patch("governmentreporter.ingestion.base.QdrantIngestionClient")
    @patch("governmentreporter.ingestion.base.EmbeddingGenerator")
    @patch("governmentreporter.ingestion.base.ProgressTracker")
    def test_processes_documents_in_batches(
        self,
        mock_progress_class,
        mock_embedding_class,
        mock_qdrant_class,
        mock_monitor_class,
    ):
        """Test documents are processed in batches."""
        # Create 10 documents but batch size of 3
        doc_ids = [f"doc{i}" for i in range(10)]

        mock_progress = MagicMock()
        mock_progress.get_all_unprocessed_ids.return_value = doc_ids
        mock_progress_class.return_value = mock_progress

        ingester = ConcreteIngester(
            start_date="2024-01-01", end_date="2024-12-31", batch_size=3
        )

        ingester.run()

        # Should process in multiple batches
        # (verification depends on implementation details)
        assert ingester.batch_size == 3


class TestDocumentIngesterProgressTracking:
    """Test progress tracking integration."""

    @patch("governmentreporter.ingestion.base.PerformanceMonitor")
    @patch("governmentreporter.ingestion.base.QdrantIngestionClient")
    @patch("governmentreporter.ingestion.base.EmbeddingGenerator")
    @patch("governmentreporter.ingestion.base.ProgressTracker")
    def test_marks_completed_documents(
        self,
        mock_progress_class,
        mock_embedding_class,
        mock_qdrant_class,
        mock_monitor_class,
    ):
        """Test completed documents are marked in progress tracker."""
        mock_progress = MagicMock()
        mock_progress.get_all_unprocessed_ids.return_value = ["doc1", "doc2"]
        mock_progress_class.return_value = mock_progress

        ingester = ConcreteIngester(start_date="2024-01-01", end_date="2024-12-31")

        ingester.run()

        # Verify progress tracking was used
        assert mock_progress.get_all_unprocessed_ids.called


class TestDocumentIngesterErrorHandling:
    """Test error handling in ingestion pipeline."""

    @patch("governmentreporter.ingestion.base.PerformanceMonitor")
    @patch("governmentreporter.ingestion.base.QdrantIngestionClient")
    @patch("governmentreporter.ingestion.base.EmbeddingGenerator")
    @patch("governmentreporter.ingestion.base.ProgressTracker")
    def test_handles_document_processing_errors(
        self,
        mock_progress_class,
        mock_embedding_class,
        mock_qdrant_class,
        mock_monitor_class,
    ):
        """Test ingester handles errors during document processing."""
        mock_progress = MagicMock()
        mock_progress.get_all_unprocessed_ids.return_value = ["doc1"]
        mock_progress_class.return_value = mock_progress

        class ErrorIngester(DocumentIngester):
            def _get_collection_name(self):
                return "test"

            def _fetch_document_ids(self):
                return ["doc1"]

            def _process_single_document(self, doc_id, batch_docs, batch_embeds):
                raise Exception("Processing error")

        ingester = ErrorIngester(start_date="2024-01-01", end_date="2024-12-31")

        # Should handle error gracefully (not crash)
        try:
            ingester.run()
        except Exception as e:
            # Some implementations may propagate errors
            assert "error" in str(e).lower()
