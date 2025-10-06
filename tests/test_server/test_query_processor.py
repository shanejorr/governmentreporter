"""
Tests for MCP server query result processor.

This module tests the QueryProcessor class that formats search results
from Qdrant into LLM-friendly text representations.

Python Learning Notes:
    - Query processor transforms raw database results into readable text
    - Different document types require different formatting strategies
    - Truncation and summarization prevent context overflow
"""

import pytest
from governmentreporter.server.query_processor import QueryProcessor


@pytest.fixture
def query_processor():
    """Create QueryProcessor instance for testing."""
    return QueryProcessor(max_chunk_length=500)


@pytest.fixture
def scotus_search_results():
    """Sample SCOTUS search results from Qdrant."""
    return [
        {
            "id": "scotus_001_chunk_0",
            "score": 0.95,
            "payload": {
                "document_id": "scotus_001",
                "chunk_text": "The Court holds that Congress' statutory authorization satisfies the Appropriations Clause.",
                "case_name": "Consumer Financial Protection Bureau v. Community Financial Services Assn.",
                "citation": "601 U.S. 416 (2024)",
                "opinion_type": "majority",
                "date_filed": "2024-05-16",
                "legal_topics": ["Constitutional Law", "Administrative Law"],
                "constitutional_provisions": ["Art. I, § 9, cl. 7"],
            },
        },
        {
            "id": "scotus_001_chunk_1",
            "score": 0.88,
            "payload": {
                "document_id": "scotus_001",
                "chunk_text": "The dissent argues that the funding mechanism violates separation of powers.",
                "case_name": "Consumer Financial Protection Bureau v. Community Financial Services Assn.",
                "citation": "601 U.S. 416 (2024)",
                "opinion_type": "dissenting",
                "justice": "Alito",
                "date_filed": "2024-05-16",
            },
        },
    ]


@pytest.fixture
def eo_search_results():
    """Sample Executive Order search results."""
    return [
        {
            "id": "eo_14100_chunk_0",
            "score": 0.92,
            "payload": {
                "document_id": "eo_14100",
                "chunk_text": "By the authority vested in me as President, it is hereby ordered...",
                "executive_order_number": "14100",
                "title": "Promoting Access to Voting",
                "president": "Biden",
                "signing_date": "2024-03-07",
                "policy_topics": ["voting rights", "civil rights"],
                "impacted_agencies": ["DOJ", "DHS"],
            },
        }
    ]


class TestQueryProcessorInitialization:
    """Test QueryProcessor initialization and configuration."""

    def test_processor_initialization_default(self):
        """Test processor initializes with default settings."""
        processor = QueryProcessor()
        assert processor is not None
        assert processor.max_chunk_length > 0

    def test_processor_initialization_custom_length(self):
        """Test processor respects custom max chunk length."""
        processor = QueryProcessor(max_chunk_length=300)
        assert processor.max_chunk_length == 300

    def test_processor_initialization_zero_length_rejected(self):
        """Test processor rejects invalid max_chunk_length."""
        # Should either raise error or use sensible default
        try:
            processor = QueryProcessor(max_chunk_length=0)
            assert processor.max_chunk_length > 0  # Should use default
        except ValueError:
            pass  # Expected behavior


class TestFormatSearchResults:
    """Test general search result formatting."""

    def test_format_empty_results(self, query_processor):
        """Test formatting empty search results."""
        result = query_processor.format_search_results("test query", [])

        assert isinstance(result, str)
        assert len(result) > 0
        assert "no results" in result.lower() or "0" in result

    def test_format_single_result(self, query_processor, scotus_search_results):
        """Test formatting single search result."""
        result = query_processor.format_search_results("test query", [scotus_search_results[0]])

        assert isinstance(result, str)
        assert "Consumer Financial Protection Bureau" in result
        assert "601 U.S. 416" in result
        assert "0.95" in result or "95" in result  # Score

    def test_format_multiple_results(self, query_processor, scotus_search_results):
        """Test formatting multiple search results."""
        result = query_processor.format_search_results("test query", scotus_search_results)

        assert isinstance(result, str)
        assert "Consumer Financial Protection Bureau" in result
        assert "majority" in result.lower()
        assert "dissenting" in result.lower()
        assert "Alito" in result

    def test_format_truncates_long_chunks(self, query_processor):
        """Test that long chunks are truncated."""
        long_text = "A" * 1000  # Much longer than max_chunk_length
        results = [
            {
                "id": "test_id",
                "score": 0.9,
                "payload": {"chunk_text": long_text, "case_name": "Test Case"},
            }
        ]

        result = query_processor.format_search_results("test query", results)

        # Result should not contain the entire long text
        assert len(result) < len(long_text) + 200  # Allow for metadata
        assert "..." in result or "truncated" in result.lower()

    def test_format_includes_relevance_scores(
        self, query_processor, scotus_search_results
    ):
        """Test that relevance scores are included in output."""
        result = query_processor.format_search_results("test query", scotus_search_results)

        # Should show scores in some format
        assert "0.95" in result or "95%" in result or "score" in result.lower()


class TestFormatSCOTUSResults:
    """Test SCOTUS-specific result formatting."""

    def test_format_scotus_includes_case_metadata(
        self, query_processor, scotus_search_results
    ):
        """Test SCOTUS formatting includes legal metadata."""
        result = query_processor.format_scotus_results("test query", scotus_search_results)

        assert "Consumer Financial Protection Bureau" in result
        assert "601 U.S. 416 (2024)" in result
        assert "2024-05-16" in result or "May 16, 2024" in result

    def test_format_scotus_shows_opinion_type(
        self, query_processor, scotus_search_results
    ):
        """Test SCOTUS formatting distinguishes opinion types."""
        result = query_processor.format_scotus_results("test query", scotus_search_results)

        assert "majority" in result.lower()
        assert "dissenting" in result.lower()

    def test_format_scotus_attributes_justices(
        self, query_processor, scotus_search_results
    ):
        """Test SCOTUS formatting attributes opinions to justices."""
        result = query_processor.format_scotus_results("test query", scotus_search_results)

        # Dissenting opinion should be attributed to Alito
        assert "Alito" in result

    def test_format_scotus_includes_legal_topics(
        self, query_processor, scotus_search_results
    ):
        """Test SCOTUS formatting includes legal topics."""
        result = query_processor.format_scotus_results("test query", scotus_search_results)

        assert "Constitutional Law" in result
        assert "Administrative Law" in result

    def test_format_scotus_includes_constitutional_provisions(
        self, query_processor, scotus_search_results
    ):
        """Test SCOTUS formatting includes constitutional citations."""
        result = query_processor.format_scotus_results("test query", scotus_search_results)

        assert (
            "Art. I, § 9, cl. 7" in result or "Appropriations Clause" in result.lower()
        )

    def test_format_scotus_empty_results(self, query_processor):
        """Test SCOTUS formatting handles empty results."""
        result = query_processor.format_scotus_results("test query", [])

        assert isinstance(result, str)
        assert len(result) > 0


class TestFormatEOResults:
    """Test Executive Order-specific result formatting."""

    def test_format_eo_includes_order_metadata(
        self, query_processor, eo_search_results
    ):
        """Test EO formatting includes order metadata."""
        result = query_processor.format_eo_results("test query", eo_search_results)

        assert "14100" in result
        assert "Promoting Access to Voting" in result
        assert "Biden" in result
        assert "2024-03-07" in result or "March 7, 2024" in result

    def test_format_eo_includes_policy_topics(self, query_processor, eo_search_results):
        """Test EO formatting includes policy topics."""
        result = query_processor.format_eo_results("test query", eo_search_results)

        assert "voting rights" in result
        assert "civil rights" in result

    def test_format_eo_includes_agencies(self, query_processor, eo_search_results):
        """Test EO formatting includes impacted agencies."""
        result = query_processor.format_eo_results("test query", eo_search_results)

        assert "DOJ" in result
        assert "DHS" in result

    def test_format_eo_empty_results(self, query_processor):
        """Test EO formatting handles empty results."""
        result = query_processor.format_eo_results("test query", [])

        assert isinstance(result, str)
        assert len(result) > 0


class TestFormatDocumentChunk:
    """Test single document chunk formatting."""

    def test_format_chunk_basic(self, query_processor):
        """Test basic chunk formatting."""
        chunk = {
            "id": "test_id",
            "payload": {"chunk_text": "Test content", "document_id": "doc_123"},
        }

        result = query_processor.format_document_chunk(chunk)

        assert isinstance(result, str)
        assert "Test content" in result
        assert "doc_123" in result

    def test_format_chunk_with_metadata(self, query_processor):
        """Test chunk formatting includes metadata."""
        chunk = {
            "id": "test_id",
            "payload": {
                "chunk_text": "Test content",
                "document_id": "doc_123",
                "case_name": "Test v. Example",
                "date_filed": "2024-01-01",
            },
        }

        result = query_processor.format_document_chunk(chunk)

        assert "Test v. Example" in result
        assert "2024-01-01" in result or "January 1, 2024" in result

    def test_format_chunk_handles_missing_text(self, query_processor):
        """Test chunk formatting handles missing chunk_text."""
        chunk = {"id": "test_id", "payload": {"document_id": "doc_123"}}

        result = query_processor.format_document_chunk(chunk)

        assert isinstance(result, str)
        # Should not crash, should indicate missing content
        assert "no content" in result.lower() or "not available" in result.lower()

    def test_format_chunk_truncates_long_text(self, query_processor):
        """Test chunk formatting truncates very long text."""
        long_text = "X" * 2000
        chunk = {
            "id": "test_id",
            "payload": {"chunk_text": long_text, "document_id": "doc_123"},
        }

        result = query_processor.format_document_chunk(chunk)

        # Should be truncated
        assert len(result) < len(long_text)


class TestFormatCollectionsList:
    """Test collection listing formatting."""

    def test_format_collections_basic(self, query_processor):
        """Test basic collection list formatting."""
        collections = [
            {"name": "supreme_court_opinions", "vectors_count": 1000},
            {"name": "executive_orders", "vectors_count": 500},
        ]

        result = query_processor.format_collections_list(collections)

        assert isinstance(result, str)
        assert "supreme_court_opinions" in result
        assert "executive_orders" in result
        assert "1000" in result
        assert "500" in result

    def test_format_collections_empty(self, query_processor):
        """Test formatting empty collection list."""
        result = query_processor.format_collections_list([])

        assert isinstance(result, str)
        assert "no collections" in result.lower() or "empty" in result.lower()

    def test_format_collections_shows_statistics(self, query_processor):
        """Test collection formatting shows useful statistics."""
        collections = [
            {
                "name": "test_collection",
                "vectors_count": 1500,
                "points_count": 1500,
                "status": "green",
            }
        ]

        result = query_processor.format_collections_list(collections)

        assert "1500" in result
        assert "test_collection" in result


class TestQueryProcessorEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_none_input(self, query_processor):
        """Test processor handles None input gracefully."""
        result = query_processor.format_search_results("test query", None)

        assert isinstance(result, str)
        # Should not crash

    def test_handles_malformed_results(self, query_processor):
        """Test processor handles malformed result data."""
        malformed = [{"invalid": "structure"}, {"id": "test", "payload": None}]

        # Should not crash
        result = query_processor.format_search_results("test query", malformed)
        assert isinstance(result, str)

    def test_handles_missing_payload(self, query_processor):
        """Test processor handles results with missing payload."""
        results = [{"id": "test_id", "score": 0.9}]

        result = query_processor.format_search_results("test query", results)
        assert isinstance(result, str)

    def test_handles_unicode_content(self, query_processor):
        """Test processor handles unicode content correctly."""
        results = [
            {
                "id": "test_id",
                "score": 0.9,
                "payload": {
                    "chunk_text": "Test with émojis 🎉 and ünïcödé",
                    "case_name": "Tëst v. Éxample",
                },
            }
        ]

        result = query_processor.format_search_results("test query", results)
        assert isinstance(result, str)
        assert "🎉" in result or "emoji" in result.lower()

    def test_handles_very_large_result_sets(self, query_processor):
        """Test processor handles large number of results efficiently."""
        large_results = [
            {
                "id": f"doc_{i}",
                "score": 0.9,
                "payload": {"chunk_text": f"Content {i}", "document_id": f"doc_{i}"},
            }
            for i in range(100)
        ]

        result = query_processor.format_search_results("test query", large_results)
        assert isinstance(result, str)
        # Should complete in reasonable time
