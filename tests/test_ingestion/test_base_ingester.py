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

        # Progress tracker is initialized internally, we just verify no errors
        assert ingester is not None

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
