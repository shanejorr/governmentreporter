"""
Unit tests for abstract base classes and data models in the APIs module.

Streamlined test suite covering essential functionality.
"""

import pytest
from abc import ABC
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock

from governmentreporter.apis.base import Document, GovernmentAPIClient


class TestDocumentDataclass:
    """Test suite for the Document dataclass."""

    def test_document_creation_with_required_fields(self):
        """Test creating a Document with only required fields."""
        doc = Document(
            id="test-123",
            title="Test Document",
            date="2024-01-15",
            type="test_type",
            source="test_source",
        )

        assert doc.id == "test-123"
        assert doc.title == "Test Document"
        assert doc.date == "2024-01-15"
        assert doc.type == "test_type"
        assert doc.source == "test_source"
        assert doc.content is None
        assert doc.metadata is None
        assert doc.url is None

    def test_document_creation_with_all_fields(self):
        """Test creating a Document with all fields populated."""
        metadata = {
            "court": "Supreme Court",
            "docket": "20-123",
            "judges": ["Roberts", "Thomas"],
        }

        doc = Document(
            id="full-456",
            title="Full Document",
            date="2024-02-20",
            type="opinion",
            source="courtlistener",
            content="Full text of the document here...",
            metadata=metadata,
            url="https://example.com/doc/456",
        )

        assert doc.id == "full-456"
        assert doc.content == "Full text of the document here..."
        assert doc.metadata == metadata
        assert doc.url == "https://example.com/doc/456"

    def test_document_equality(self):
        """Test Document equality comparison."""
        doc1 = Document(
            id="eq-123",
            title="Equal Test",
            date="2024-01-01",
            type="test",
            source="test",
        )

        doc2 = Document(
            id="eq-123",
            title="Equal Test",
            date="2024-01-01",
            type="test",
            source="test",
        )

        doc3 = Document(
            id="different-456",
            title="Different",
            date="2024-01-01",
            type="test",
            source="test",
        )

        assert doc1 == doc2
        assert doc1 != doc3


class MockGovernmentAPIClient(GovernmentAPIClient):
    """Mock implementation for testing."""

    def _get_base_url(self) -> str:
        """Return mock base URL."""
        return "https://mock-api.example.com/v1"

    def _get_rate_limit_delay(self) -> float:
        """Return mock rate limit delay."""
        return 0.1

    def search_documents(
        self, query: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> list:
        return [
            Document(
                id="mock-1",
                title="Mock Document",
                date="2024-01-01",
                type="mock",
                source="mock_api",
            )
        ]

    def get_document(self, document_id: str) -> Optional[Document]:
        if document_id == "exists":
            return Document(
                id="exists",
                title="Existing",
                date="2024-01-01",
                type="test",
                source="mock",
            )
        return None

    def get_document_text(self, document_id: str) -> Optional[str]:
        if document_id == "text-exists":
            return "Document text content"
        return None


class TestGovernmentAPIClient:
    """Test suite for GovernmentAPIClient abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that abstract class cannot be instantiated directly."""
        with pytest.raises(TypeError) as exc_info:
            GovernmentAPIClient()

        assert "abstract" in str(exc_info.value).lower()

    def test_mock_implementation_initialization(self):
        """Test that concrete implementation can be initialized."""
        client = MockGovernmentAPIClient(api_key="test-key")

        assert client.api_key == "test-key"
        assert hasattr(client, "search_documents")
        assert hasattr(client, "get_document")
        assert hasattr(client, "get_document_text")

    def test_initialization_without_api_key(self):
        """Test initialization without API key."""
        client = MockGovernmentAPIClient()
        assert client.api_key is None

    def test_validate_date_format_valid_dates(self):
        """Test date validation with valid dates."""
        client = MockGovernmentAPIClient()

        # Valid dates should not raise
        client.validate_date_format("2024-01-15")
        client.validate_date_format("2023-12-31")
        client.validate_date_format("2020-02-29")  # Leap year

    def test_validate_date_format_invalid_dates(self):
        """Test date validation with invalid dates."""
        client = MockGovernmentAPIClient()

        with pytest.raises(ValueError):
            client.validate_date_format("2024-13-01")  # Invalid month

        with pytest.raises(ValueError):
            client.validate_date_format("2024-01-32")  # Invalid day

        with pytest.raises(ValueError):
            client.validate_date_format("not-a-date")

        with pytest.raises(ValueError):
            client.validate_date_format("01/15/2024")  # Wrong format

    def test_mock_search_documents(self):
        """Test search_documents implementation."""
        client = MockGovernmentAPIClient()
        results = client.search_documents("test query")

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].title == "Mock Document"

    def test_mock_get_document(self):
        """Test get_document implementation."""
        client = MockGovernmentAPIClient()

        doc = client.get_document("exists")
        assert doc is not None
        assert doc.id == "exists"

        doc = client.get_document("not-exists")
        assert doc is None

    def test_mock_get_document_text(self):
        """Test get_document_text implementation."""
        client = MockGovernmentAPIClient()

        text = client.get_document_text("text-exists")
        assert text == "Document text content"

        text = client.get_document_text("no-text")
        assert text is None

    def test_incomplete_implementation_raises_error(self):
        """Test that incomplete implementations raise TypeError."""

        class IncompleteClient(GovernmentAPIClient):
            def search_documents(self, query, start_date=None, end_date=None):
                return []
            # Missing get_document and get_document_text

        with pytest.raises(TypeError) as exc_info:
            IncompleteClient()

        assert "abstract" in str(exc_info.value).lower()


class TestAPIClientIntegration:
    """Integration tests for API client usage patterns."""

    def test_api_client_with_mock_responses(self):
        """Test API client with mocked responses."""
        client = MockGovernmentAPIClient(api_key="test-key")

        # Search documents
        results = client.search_documents("supreme court")
        assert len(results) > 0
        assert all(isinstance(doc, Document) for doc in results)

        # Get document
        doc = client.get_document("exists")
        assert doc is not None
        assert isinstance(doc, Document)

        # Get document text
        text = client.get_document_text("text-exists")
        assert text is not None
        assert isinstance(text, str)

    def test_error_handling_pattern(self):
        """Test error handling in API operations."""
        client = MockGovernmentAPIClient()

        # Getting non-existent document should return None
        result = client.get_document("does-not-exist")
        assert result is None

        # Getting text for non-existent document should return None
        text = client.get_document_text("does-not-exist")
        assert text is None
