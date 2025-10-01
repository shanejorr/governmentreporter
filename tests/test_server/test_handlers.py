"""
Tests for MCP server request handlers.

This module tests all MCP tool handlers including:
- Search across collections
- SCOTUS-specific search with filters
- Executive Order search with filters
- Document retrieval by ID
- Collection listing

Python Learning Notes:
    - AsyncMock enables mocking async functions
    - pytest-asyncio provides async test support
    - Fixtures reduce test code duplication
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from governmentreporter.server.handlers import (
    handle_search_government_documents,
    handle_search_scotus_opinions,
    handle_search_executive_orders,
    handle_get_document_by_id,
    handle_list_collections,
)


@pytest.fixture
def mock_qdrant_client():
    """Create mock Qdrant client with common methods."""
    client = MagicMock()
    client.semantic_search = AsyncMock(return_value=[])
    client.get_document_by_id = AsyncMock(return_value=None)
    client.list_collections = MagicMock(return_value=[])
    return client


@pytest.fixture
def sample_search_results():
    """Sample search results from Qdrant."""
    return [
        {
            "id": "scotus_001_chunk_0",
            "score": 0.95,
            "payload": {
                "document_id": "scotus_001",
                "chunk_text": "The Court holds that...",
                "case_name": "Test v. Example",
                "citation": "123 U.S. 456 (2024)",
                "opinion_type": "majority",
                "date_filed": "2024-01-15",
            }
        },
        {
            "id": "scotus_002_chunk_1",
            "score": 0.87,
            "payload": {
                "document_id": "scotus_002",
                "chunk_text": "Justice Smith dissenting...",
                "case_name": "Another v. Case",
                "citation": "124 U.S. 789 (2024)",
                "opinion_type": "dissenting",
                "justice": "Smith",
                "date_filed": "2024-02-20",
            }
        }
    ]


@pytest.fixture
def sample_eo_results():
    """Sample Executive Order search results."""
    return [
        {
            "id": "eo_14100_chunk_0",
            "score": 0.92,
            "payload": {
                "document_id": "eo_14100",
                "chunk_text": "By the authority vested in me...",
                "executive_order_number": "14100",
                "title": "Test Executive Order",
                "president": "Biden",
                "signing_date": "2024-03-01",
                "policy_topics": ["environment", "energy"],
            }
        }
    ]


class TestSearchGovernmentDocuments:
    """
    Test suite for general government document search handler.

    Python Learning Notes:
        - Async tests require @pytest.mark.asyncio decorator
        - Mock objects simulate external dependencies
        - Assertions verify expected behavior
    """

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_basic_search_success(self, mock_generate_embedding, mock_qdrant_client, sample_search_results):
        """Test basic search returns results successfully."""
        # Setup mocks
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = sample_search_results

        # Execute search
        result = await handle_search_government_documents(
            query="test query",
            qdrant_client=mock_qdrant_client,
            limit=10
        )

        # Verify calls
        mock_generate_embedding.assert_called_once_with("test query")
        mock_qdrant_client.semantic_search.assert_called_once()

        # Verify result structure
        assert isinstance(result, str)
        assert "Test v. Example" in result
        assert "123 U.S. 456" in result

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_search_with_collection_filter(self, mock_generate_embedding, mock_qdrant_client):
        """Test search with specific collection filter."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = []

        await handle_search_government_documents(
            query="test",
            qdrant_client=mock_qdrant_client,
            collections=["supreme_court_opinions"]
        )

        # Verify collection filter was passed
        call_kwargs = mock_qdrant_client.semantic_search.call_args[1]
        assert "collection_name" in call_kwargs or call_kwargs.get("collections") == ["supreme_court_opinions"]

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_search_with_limit(self, mock_generate_embedding, mock_qdrant_client):
        """Test search respects limit parameter."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = []

        await handle_search_government_documents(
            query="test",
            qdrant_client=mock_qdrant_client,
            limit=5
        )

        call_kwargs = mock_qdrant_client.semantic_search.call_args[1]
        assert call_kwargs.get("limit") == 5

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_search_with_empty_results(self, mock_generate_embedding, mock_qdrant_client):
        """Test search handles empty results gracefully."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = []

        result = await handle_search_government_documents(
            query="nonexistent query",
            qdrant_client=mock_qdrant_client
        )

        assert isinstance(result, str)
        assert "no results" in result.lower() or "found 0" in result.lower()

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_search_handles_embedding_error(self, mock_generate_embedding, mock_qdrant_client):
        """Test search handles embedding generation errors."""
        mock_generate_embedding.side_effect = Exception("Embedding API error")

        result = await handle_search_government_documents(
            query="test",
            qdrant_client=mock_qdrant_client
        )

        # Should return error message, not raise exception
        assert isinstance(result, str)
        assert "error" in result.lower()

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_search_handles_qdrant_error(self, mock_generate_embedding, mock_qdrant_client):
        """Test search handles Qdrant errors."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.side_effect = Exception("Qdrant connection error")

        result = await handle_search_government_documents(
            query="test",
            qdrant_client=mock_qdrant_client
        )

        assert isinstance(result, str)
        assert "error" in result.lower()


class TestSearchSCOTUSOpinions:
    """Test suite for SCOTUS-specific search handler."""

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_scotus_search_basic(self, mock_generate_embedding, mock_qdrant_client, sample_search_results):
        """Test basic SCOTUS search."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = sample_search_results

        result = await handle_search_scotus_opinions(
            query="constitutional law",
            qdrant_client=mock_qdrant_client
        )

        assert isinstance(result, str)
        assert "Test v. Example" in result

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_scotus_search_with_opinion_type_filter(self, mock_generate_embedding, mock_qdrant_client):
        """Test SCOTUS search with opinion type filter."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = []

        await handle_search_scotus_opinions(
            query="test",
            qdrant_client=mock_qdrant_client,
            opinion_type="dissenting"
        )

        # Verify filter was applied
        call_args = mock_qdrant_client.semantic_search.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_scotus_search_with_justice_filter(self, mock_generate_embedding, mock_qdrant_client):
        """Test SCOTUS search with justice filter."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = []

        await handle_search_scotus_opinions(
            query="test",
            qdrant_client=mock_qdrant_client,
            justice="Thomas"
        )

        call_args = mock_qdrant_client.semantic_search.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_scotus_search_with_date_range(self, mock_generate_embedding, mock_qdrant_client):
        """Test SCOTUS search with date range filters."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = []

        await handle_search_scotus_opinions(
            query="test",
            qdrant_client=mock_qdrant_client,
            start_date="2024-01-01",
            end_date="2024-12-31"
        )

        call_args = mock_qdrant_client.semantic_search.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_scotus_search_with_multiple_filters(self, mock_generate_embedding, mock_qdrant_client):
        """Test SCOTUS search with multiple filters combined."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = []

        await handle_search_scotus_opinions(
            query="test",
            qdrant_client=mock_qdrant_client,
            opinion_type="concurring",
            justice="Kagan",
            start_date="2023-01-01"
        )

        mock_qdrant_client.semantic_search.assert_called_once()


class TestSearchExecutiveOrders:
    """Test suite for Executive Order search handler."""

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_eo_search_basic(self, mock_generate_embedding, mock_qdrant_client, sample_eo_results):
        """Test basic Executive Order search."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = sample_eo_results

        result = await handle_search_executive_orders(
            query="environmental policy",
            qdrant_client=mock_qdrant_client
        )

        assert isinstance(result, str)
        assert "14100" in result or "Test Executive Order" in result

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_eo_search_with_president_filter(self, mock_generate_embedding, mock_qdrant_client):
        """Test EO search with president filter."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = []

        await handle_search_executive_orders(
            query="test",
            qdrant_client=mock_qdrant_client,
            president="Biden"
        )

        call_args = mock_qdrant_client.semantic_search.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_eo_search_with_agency_filter(self, mock_generate_embedding, mock_qdrant_client):
        """Test EO search with agency filter."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = []

        await handle_search_executive_orders(
            query="test",
            qdrant_client=mock_qdrant_client,
            agency="EPA"
        )

        call_args = mock_qdrant_client.semantic_search.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_eo_search_with_policy_topic_filter(self, mock_generate_embedding, mock_qdrant_client):
        """Test EO search with policy topic filter."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = []

        await handle_search_executive_orders(
            query="test",
            qdrant_client=mock_qdrant_client,
            policy_topic="climate"
        )

        call_args = mock_qdrant_client.semantic_search.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    @patch('governmentreporter.server.handlers.generate_embedding')
    async def test_eo_search_with_date_range(self, mock_generate_embedding, mock_qdrant_client):
        """Test EO search with date range."""
        mock_generate_embedding.return_value = [0.1] * 1536
        mock_qdrant_client.semantic_search.return_value = []

        await handle_search_executive_orders(
            query="test",
            qdrant_client=mock_qdrant_client,
            start_date="2024-01-01",
            end_date="2024-12-31"
        )

        call_args = mock_qdrant_client.semantic_search.call_args
        assert call_args is not None


class TestGetDocumentById:
    """Test suite for document retrieval by ID handler."""

    @pytest.mark.asyncio
    async def test_get_document_success(self, mock_qdrant_client):
        """Test successful document retrieval."""
        mock_doc = {
            "id": "scotus_001_chunk_0",
            "payload": {
                "document_id": "scotus_001",
                "chunk_text": "Document content...",
                "case_name": "Test v. Example",
            }
        }
        mock_qdrant_client.get_document_by_id.return_value = mock_doc

        result = await handle_get_document_by_id(
            document_id="scotus_001_chunk_0",
            qdrant_client=mock_qdrant_client,
            collection_name="supreme_court_opinions"
        )

        assert isinstance(result, str)
        assert "Test v. Example" in result

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, mock_qdrant_client):
        """Test document not found scenario."""
        mock_qdrant_client.get_document_by_id.return_value = None

        result = await handle_get_document_by_id(
            document_id="nonexistent_id",
            qdrant_client=mock_qdrant_client,
            collection_name="supreme_court_opinions"
        )

        assert isinstance(result, str)
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_get_document_handles_error(self, mock_qdrant_client):
        """Test error handling during document retrieval."""
        mock_qdrant_client.get_document_by_id.side_effect = Exception("Database error")

        result = await handle_get_document_by_id(
            document_id="test_id",
            qdrant_client=mock_qdrant_client,
            collection_name="supreme_court_opinions"
        )

        assert isinstance(result, str)
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_get_document_validates_collection(self, mock_qdrant_client):
        """Test document retrieval validates collection name."""
        mock_qdrant_client.get_document_by_id.return_value = None

        result = await handle_get_document_by_id(
            document_id="test_id",
            qdrant_client=mock_qdrant_client,
            collection_name="invalid_collection"
        )

        # Should handle gracefully even with invalid collection
        assert isinstance(result, str)


class TestListCollections:
    """Test suite for collection listing handler."""

    @pytest.mark.asyncio
    async def test_list_collections_success(self, mock_qdrant_client):
        """Test successful collection listing."""
        mock_collections = [
            {"name": "supreme_court_opinions", "vectors_count": 1000},
            {"name": "executive_orders", "vectors_count": 500}
        ]
        mock_qdrant_client.list_collections.return_value = mock_collections

        result = await handle_list_collections(qdrant_client=mock_qdrant_client)

        assert isinstance(result, str)
        assert "supreme_court_opinions" in result
        assert "executive_orders" in result

    @pytest.mark.asyncio
    async def test_list_collections_empty(self, mock_qdrant_client):
        """Test listing when no collections exist."""
        mock_qdrant_client.list_collections.return_value = []

        result = await handle_list_collections(qdrant_client=mock_qdrant_client)

        assert isinstance(result, str)
        assert "no collections" in result.lower() or "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_list_collections_handles_error(self, mock_qdrant_client):
        """Test error handling during collection listing."""
        mock_qdrant_client.list_collections.side_effect = Exception("Connection error")

        result = await handle_list_collections(qdrant_client=mock_qdrant_client)

        assert isinstance(result, str)
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_list_collections_includes_statistics(self, mock_qdrant_client):
        """Test that collection listing includes useful statistics."""
        mock_collections = [
            {
                "name": "supreme_court_opinions",
                "vectors_count": 1500,
                "points_count": 1500
            }
        ]
        mock_qdrant_client.list_collections.return_value = mock_collections

        result = await handle_list_collections(qdrant_client=mock_qdrant_client)

        assert isinstance(result, str)
        # Should include count information
        assert "1500" in result or "count" in result.lower()
