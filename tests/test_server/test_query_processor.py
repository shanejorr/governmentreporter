"""
Tests for query_processor module - result formatting for LLM consumption.

Tests cover:
- Full document hint generation
- Search result formatting with hints
- SCOTUS-specific formatting
- Executive Order formatting
- Edge cases and threshold behavior
"""

import pytest

from governmentreporter.server.query_processor import QueryProcessor


# Module-level fixtures available to all test classes
@pytest.fixture
def processor():
    """Create a QueryProcessor instance for testing."""
    return QueryProcessor()


@pytest.fixture
def scotus_results():
    """Sample SCOTUS search results for testing."""
    return [
        {
            "type": "scotus",
            "score": 0.85,
            "payload": {
                "document_id": "12345678",
                "chunk_id": "12345678_chunk_5",
                "case_name": "Brown v. Board of Education",
                "citation": "347 U.S. 483 (1954)",
                "opinion_type": "majority",
                "justice": "Warren",
                "section": "II",
                "text": "We conclude that in the field of public education...",
            },
        },
        {
            "type": "scotus",
            "score": 0.78,
            "payload": {
                "document_id": "12345678",
                "chunk_id": "12345678_chunk_10",
                "case_name": "Brown v. Board of Education",
                "opinion_type": "majority",
                "text": "Separate educational facilities are inherently unequal.",
            },
        },
    ]


@pytest.fixture
def eo_results():
    """Sample Executive Order search results for testing."""
    return [
        {
            "type": "executive_order",
            "score": 0.72,
            "payload": {
                "document_id": "2024-12345",
                "chunk_id": "2024-12345_chunk_0",
                "title": "Protecting Consumer Data",
                "executive_order_number": "14123",
                "president": "Biden",
                "signing_date": "2024-01-15",
                "text": "By the authority vested in me as President...",
            },
        }
    ]


@pytest.fixture
def mixed_results():
    """Sample mixed SCOTUS and EO results."""
    return [
        {
            "type": "scotus",
            "score": 0.65,
            "payload": {
                "document_id": "11111111",
                "chunk_id": "11111111_chunk_0",
                "case_name": "Test Case A",
                "text": "Sample text...",
            },
        },
        {
            "type": "executive_order",
            "score": 0.60,
            "payload": {
                "document_id": "2024-99999",
                "chunk_id": "2024-99999_chunk_0",
                "title": "Test Order",
                "executive_order_number": "14999",
                "text": "Sample EO text...",
            },
        },
    ]


class TestFullDocumentHintGeneration:
    """Tests for _generate_full_document_hint method."""

    def test_hint_generation_with_focused_scotus_results(
        self, processor, scotus_results
    ):
        """Test hint appears for focused SCOTUS search (≤3 results, score ≥0.4)."""
        hint = processor._generate_full_document_hint(scotus_results)

        assert hint != ""
        assert "📄 Full Document Access" in hint
        assert "Brown v. Board of Education" in hint
        assert "get_document_by_id" in hint
        assert "12345678_chunk_5" in hint
        assert "supreme_court_opinions" in hint
        assert "full_document=true" in hint

    def test_hint_generation_with_executive_orders(self, processor, eo_results):
        """Test hint appears for Executive Order results."""
        hint = processor._generate_full_document_hint(eo_results)

        assert hint != ""
        assert "📄 Full Document Access" in hint
        assert "Protecting Consumer Data" in hint
        assert "2024-12345_chunk_0" in hint
        assert "executive_orders" in hint

    def test_hint_deduplication_same_document(self, processor, scotus_results):
        """Test that multiple chunks from same document only generate one hint."""
        # Both results are from same document_id (12345678)
        hint = processor._generate_full_document_hint(scotus_results)

        # Should only mention the case once
        case_mentions = hint.count("Brown v. Board of Education:")
        assert case_mentions == 1

    def test_hint_with_mixed_document_types(self, processor, mixed_results):
        """Test hint generation with both SCOTUS and EO results."""
        hint = processor._generate_full_document_hint(mixed_results)

        assert "Test Case A" in hint
        assert "Test Order" in hint
        assert hint.count("get_document_by_id") == 2  # One for each document

    def test_no_hint_when_too_many_results(self, processor, scotus_results):
        """Test hint is suppressed when results exceed threshold."""
        # Create 5 results (exceeds default max_results=3)
        many_results = scotus_results + [
            {
                "type": "scotus",
                "score": 0.70,
                "payload": {
                    "document_id": "99999999",
                    "chunk_id": "99999999_chunk_0",
                    "case_name": "Another Case",
                    "text": "More text...",
                },
            },
            {
                "type": "scotus",
                "score": 0.65,
                "payload": {
                    "document_id": "88888888",
                    "chunk_id": "88888888_chunk_0",
                    "case_name": "Yet Another Case",
                    "text": "Even more text...",
                },
            },
        ]

        hint = processor._generate_full_document_hint(many_results)
        assert hint == ""

    def test_no_hint_when_scores_too_low(self, processor):
        """Test hint is suppressed when relevance scores are too low."""
        low_score_results = [
            {
                "type": "scotus",
                "score": 0.25,  # Below default threshold of 0.4
                "payload": {
                    "document_id": "12345678",
                    "chunk_id": "12345678_chunk_0",
                    "case_name": "Low Relevance Case",
                    "text": "Sample text...",
                },
            }
        ]

        hint = processor._generate_full_document_hint(low_score_results)
        assert hint == ""

    def test_no_hint_for_empty_results(self, processor):
        """Test hint is not generated for empty results."""
        hint = processor._generate_full_document_hint([])
        assert hint == ""

    def test_no_hint_when_missing_document_id(self, processor):
        """Test hint is suppressed when document_id is missing."""
        results_no_id = [
            {
                "type": "scotus",
                "score": 0.85,
                "payload": {
                    "case_name": "Missing ID Case",
                    "text": "Sample text...",
                    # No document_id
                },
            }
        ]

        hint = processor._generate_full_document_hint(results_no_id)
        assert hint == ""

    def test_custom_thresholds(self, processor, scotus_results):
        """Test hint generation with custom max_results and min_score."""
        # Lower max_results threshold
        hint = processor._generate_full_document_hint(
            scotus_results, max_results=1, min_score=0.4
        )
        assert hint == ""  # 2 results exceeds max_results=1

        # Higher min_score threshold
        low_score_results = [
            {
                "type": "scotus",
                "score": 0.50,
                "payload": {
                    "document_id": "12345678",
                    "chunk_id": "12345678_chunk_0",
                    "case_name": "Test Case",
                    "text": "Text...",
                },
            }
        ]
        hint = processor._generate_full_document_hint(
            low_score_results, max_results=3, min_score=0.80
        )
        assert hint == ""  # 0.50 below min_score=0.80

    def test_hint_text_formatting(self, processor, scotus_results):
        """Test that hint has proper markdown formatting."""
        hint = processor._generate_full_document_hint(scotus_results)

        # Check for markdown elements
        assert "##" in hint  # Header
        assert "```" in hint  # Code block
        assert "---" in hint  # Separator
        assert "**" in hint  # Bold text


class TestFormatMethodsWithHints:
    """Tests for format_* methods to ensure hints are appended."""

    def test_format_search_results_includes_hint(self, processor, scotus_results):
        """Test format_search_results appends hint for focused results."""
        output = processor.format_search_results("test query", scotus_results)

        assert "Search Results for:" in output
        assert "📄 Full Document Access" in output
        assert "Brown v. Board of Education" in output

    def test_format_scotus_results_includes_hint(self, processor, scotus_results):
        """Test format_scotus_results appends hint."""
        output = processor.format_scotus_results("test query", scotus_results)

        assert "Supreme Court Opinion Search Results" in output
        assert "📄 Full Document Access" in output

    def test_format_eo_results_includes_hint(self, processor, eo_results):
        """Test format_eo_results appends hint."""
        output = processor.format_eo_results("test query", eo_results)

        assert "Executive Order Search Results" in output
        assert "📄 Full Document Access" in output

    def test_format_methods_without_hint_for_many_results(self, processor):
        """Test that format methods don't include hints when conditions aren't met."""
        many_results = [
            {
                "type": "scotus",
                "score": 0.60,
                "payload": {
                    "document_id": f"doc_{i}",
                    "chunk_id": f"doc_{i}_chunk_0",
                    "case_name": f"Case {i}",
                    "text": "Text...",
                },
            }
            for i in range(5)  # 5 results exceeds threshold
        ]

        output = processor.format_search_results("test query", many_results)
        assert "📄 Full Document Access" not in output

    def test_format_handles_empty_results(self, processor):
        """Test format methods handle empty results gracefully."""
        output = processor.format_search_results("test query", [])
        assert "No results found" in output
        assert "📄 Full Document Access" not in output


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_hint_with_missing_optional_fields(self, processor):
        """Test hint generation when optional payload fields are missing."""
        minimal_result = [
            {
                "type": "scotus",
                "score": 0.75,
                "payload": {
                    "document_id": "12345678",
                    # Missing chunk_id - should use fallback
                    "title": "Minimal Case",
                    "text": "Text...",
                },
            }
        ]

        hint = processor._generate_full_document_hint(minimal_result)
        assert "12345678_chunk_0" in hint  # Fallback chunk_id

    def test_hint_with_unknown_document_type(self, processor):
        """Test hint skips results with unknown document types."""
        unknown_type_results = [
            {
                "type": "unknown",
                "score": 0.85,
                "payload": {
                    "document_id": "12345678",
                    "text": "Some text...",
                },
            }
        ]

        hint = processor._generate_full_document_hint(unknown_type_results)
        assert hint == ""  # Should skip unknown types
