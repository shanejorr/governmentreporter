"""
Unit tests for payload building orchestration.

This module provides comprehensive tests for the main orchestration functionality
that transforms Document objects into Qdrant-ready payloads. Tests cover the
complete pipeline including metadata extraction, chunking, and payload assembly.

Test Categories:
    - Happy path: Valid documents producing complete payloads
    - Edge cases: Empty documents, missing metadata, unknown document types
    - Error handling: API failures, invalid data, processing errors
    - Integration: End-to-end payload generation for different document types

Python Learning Notes:
    - Integration of multiple mocked components
    - Testing orchestration logic that coordinates subsystems
    - Validation of complex data transformations
"""

from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock, call
import pytest

from governmentreporter.apis.base import Document
from governmentreporter.processors.build_payloads import (
    build_payloads_from_document,
    extract_year_from_date,
    normalize_scotus_metadata,
    normalize_eo_metadata,
    validate_payload,
)


class TestExtractYearFromDate:
    """
    Test suite for year extraction utility function.

    Tests the extract_year_from_date function that safely extracts
    years from date strings with fallback handling.

    Python Learning Notes:
        - Simple utility functions need thorough testing
        - Edge cases in date parsing are common
        - Fallback behavior ensures robustness
    """

    def test_extract_year_standard_format(self):
        """
        Test year extraction from standard YYYY-MM-DD format.

        Verifies correct extraction from properly formatted dates.
        """
        # Test various standard dates
        assert extract_year_from_date("2024-01-15") == 2024
        assert extract_year_from_date("1954-05-17") == 1954  # Brown v. Board
        assert extract_year_from_date("2000-12-31") == 2000
        assert extract_year_from_date("1789-09-24") == 1789  # Judiciary Act

    def test_extract_year_slash_format(self):
        """
        Test year extraction from YYYY/MM/DD format.

        Ensures slash separators are handled correctly.
        """
        assert extract_year_from_date("2024/01/15") == 2024
        assert extract_year_from_date("1973/01/22") == 1973  # Roe v. Wade

    def test_extract_year_invalid_format(self):
        """
        Test fallback to current year for invalid formats.

        Verifies graceful handling of malformed date strings.
        """
        current_year = datetime.now().year

        # Various invalid formats should return current year
        assert extract_year_from_date("invalid") == current_year
        assert extract_year_from_date("01-15-2024") == current_year  # Wrong order
        assert extract_year_from_date("") == current_year
        assert extract_year_from_date("2024") == current_year  # Year only

    def test_extract_year_none_input(self):
        """
        Test handling of None input.

        Ensures function doesn't crash on None values.
        """
        current_year = datetime.now().year

        # Should handle None gracefully
        with patch('governmentreporter.processors.build_payloads.logger') as mock_logger:
            result = extract_year_from_date(None)
            assert result == current_year
            mock_logger.warning.assert_called()


class TestNormalizeSCOTUSMetadata:
    """
    Test suite for Supreme Court metadata normalization.

    Tests the normalize_scotus_metadata function that extracts
    and standardizes metadata from CourtListener documents.

    Python Learning Notes:
        - Normalization ensures consistent data structure
        - Defensive programming handles missing fields
        - Type preservation maintains data integrity
    """

    def test_normalize_scotus_complete_metadata(self):
        """
        Test normalization with complete SCOTUS metadata.

        Verifies all fields are properly extracted and mapped.
        """
        # Arrange
        doc = Document(
            id="cl-opinion-123",
            title="Brown v. Board of Education",
            date="1954-05-17",
            type="scotus_opinion",
            source="courtlistener",
            content="Opinion text here...",
            metadata={
                "case_name": "Brown v. Board of Education of Topeka",
                "docket_number": "1",
                "argued_date": "1952-12-09",
                "decided_date": "1954-05-17",
                "majority_author": "Warren",
                "vote_majority": 9,
                "vote_minority": 0
            },
            url="https://www.courtlistener.com/opinion/123/"
        )

        # Act
        normalized = normalize_scotus_metadata(doc)

        # Assert
        assert normalized["document_id"] == "cl-opinion-123"
        assert normalized["title"] == "Brown v. Board of Education of Topeka"
        assert normalized["publication_date"] == "1954-05-17"
        assert normalized["year"] == 1954
        assert normalized["source"] == "CourtListener"
        assert normalized["type"] == "Supreme Court Opinion"
        assert normalized["docket_number"] == "1"
        assert normalized["majority_author"] == "Warren"
        assert normalized["vote_majority"] == 9

    def test_normalize_scotus_minimal_metadata(self):
        """
        Test normalization with minimal metadata.

        Ensures function works with only required fields.
        """
        # Arrange
        doc = Document(
            id="cl-opinion-456",
            title="Test Case",
            date="2024-01-15",
            type="scotus_opinion",
            source="courtlistener",
            content="Opinion text...",
            metadata={},  # Empty metadata
            url="https://example.com"
        )

        # Act
        normalized = normalize_scotus_metadata(doc)

        # Assert
        assert normalized["document_id"] == "cl-opinion-456"
        assert normalized["title"] == "Test Case"
        assert normalized["year"] == 2024
        assert normalized["source"] == "CourtListener"
        assert normalized["type"] == "Supreme Court Opinion"

        # Optional fields should not be present or be None
        assert normalized.get("docket_number") is None
        assert normalized.get("majority_author") is None

    def test_normalize_scotus_missing_date(self):
        """
        Test normalization with missing date field.

        Verifies fallback to current year when date is missing.
        """
        # Arrange
        doc = Document(
            id="cl-opinion-789",
            title="Undated Case",
            date=None,  # Missing date
            type="scotus_opinion",
            source="courtlistener",
            content="Opinion text...",
            metadata={},
            url="https://example.com"
        )

        # Act
        normalized = normalize_scotus_metadata(doc)

        # Assert
        assert normalized["year"] == datetime.now().year
        assert normalized["publication_date"] is None


class TestNormalizeEOMetadata:
    """
    Test suite for Executive Order metadata normalization.

    Tests the normalize_eo_metadata function that standardizes
    metadata from Federal Register documents.

    Python Learning Notes:
        - Different document types require different normalization
        - Consistent field mapping ensures compatibility
    """

    def test_normalize_eo_complete_metadata(self):
        """
        Test normalization with complete EO metadata.

        Verifies all EO-specific fields are properly extracted.
        """
        # Arrange
        doc = Document(
            id="2024-12345",
            title="Executive Order on Climate Action",
            date="2024-01-20",
            type="executive_order",
            source="federal_register",
            content="EO text here...",
            metadata={
                "executive_order_number": "14123",
                "president": "Test President",
                "signing_date": "2024-01-20",
                "effective_date": "2024-02-01",
                "federal_register_number": "2024-12345",
                "agencies": ["EPA", "DOE", "DOD"],
                "revokes": ["13990", "13834"]
            },
            url="https://www.federalregister.gov/documents/2024/01/20/"
        )

        # Act
        normalized = normalize_eo_metadata(doc)

        # Assert
        assert normalized["document_id"] == "2024-12345"
        assert normalized["title"] == "Executive Order on Climate Action"
        assert normalized["publication_date"] == "2024-01-20"
        assert normalized["year"] == 2024
        assert normalized["source"] == "Federal Register"
        assert normalized["type"] == "Executive Order"
        assert normalized["executive_order_number"] == "14123"
        assert normalized["president"] == "Test President"
        assert "EPA" in normalized.get("agencies", [])

    def test_normalize_eo_minimal_metadata(self):
        """
        Test normalization with minimal EO metadata.

        Ensures function works with only required fields.
        """
        # Arrange
        doc = Document(
            id="eo-minimal",
            title="Minimal Order",
            date="2024-01-15",
            type="executive_order",
            source="federal_register",
            content="Order text...",
            metadata={},
            url="https://example.com"
        )

        # Act
        normalized = normalize_eo_metadata(doc)

        # Assert
        assert normalized["document_id"] == "eo-minimal"
        assert normalized["title"] == "Minimal Order"
        assert normalized["year"] == 2024
        assert normalized["source"] == "Federal Register"
        assert normalized["type"] == "Executive Order"


class TestValidatePayload:
    """
    Test suite for payload validation.

    Tests the validate_payload function that ensures
    payloads have the required structure.

    Python Learning Notes:
        - Validation ensures data integrity
        - Type checking prevents runtime errors
    """

    def test_validate_valid_payload(self):
        """
        Test validation of a properly structured payload.

        Verifies that valid payloads pass validation.
        """
        # Arrange
        payload = {
            "id": "test-123",
            "text": "This is the chunk text",
            "metadata": {
                "document_id": "doc-123",
                "title": "Test Document",
                "type": "Test Type"
            }
        }

        # Act & Assert
        assert validate_payload(payload) == True

    def test_validate_missing_id(self):
        """
        Test validation fails for payload missing id.

        Ensures required fields are checked.
        """
        # Arrange
        payload = {
            # "id": missing
            "text": "This is the chunk text",
            "metadata": {}
        }

        # Act & Assert
        assert validate_payload(payload) == False

    def test_validate_missing_text(self):
        """
        Test validation fails for payload missing text.

        Ensures text field is required.
        """
        # Arrange
        payload = {
            "id": "test-123",
            # "text": missing
            "metadata": {}
        }

        # Act & Assert
        assert validate_payload(payload) == False

    def test_validate_missing_metadata(self):
        """
        Test validation fails for payload missing metadata.

        Ensures metadata field is required.
        """
        # Arrange
        payload = {
            "id": "test-123",
            "text": "Text"
            # "metadata": missing
        }

        # Act & Assert
        assert validate_payload(payload) == False


class TestBuildPayloadsFromDocument:
    """
    Test suite for main payload building interface.

    Tests the build_payloads_from_document function that serves
    as the primary entry point for document processing.

    Python Learning Notes:
        - Public interfaces need thorough testing
        - Integration testing verifies component interaction
    """

    @patch('governmentreporter.processors.build_payloads.generate_scotus_llm_fields')
    @patch('governmentreporter.processors.build_payloads.chunk_supreme_court_opinion')
    def test_build_payloads_scotus_document(self, mock_chunk, mock_llm):
        """
        Test payload building for SCOTUS document.

        Verifies complete pipeline for Supreme Court opinions.

        Args:
            mock_chunk: Mock chunking function
            mock_llm: Mock LLM extraction
        """
        # Arrange
        doc = Document(
            id="scotus-test",
            title="Test Case",
            date="2024-01-15",
            type="scotus_opinion",
            source="courtlistener",
            content="Opinion text",
            url="https://example.com"
        )

        mock_chunk.return_value = [
            ("Chunk 1 text", {"chunk_index": 0, "chunk_total": 1})
        ]

        mock_llm.return_value = {
            "plain_language_summary": "Summary",
            "constitution_cited": [],
            "federal_statutes_cited": [],
            "federal_regulations_cited": [],
            "cases_cited": [],
            "topics_or_policy_areas": ["t1", "t2", "t3", "t4", "t5"],
            "holding_plain": "Holding",
            "outcome_simple": "Outcome",
            "issue_plain": "Issue",
            "reasoning": "Reasoning"
        }

        # Act
        payloads = build_payloads_from_document(doc)

        # Assert
        assert len(payloads) >= 1
        assert payloads[0]["text"] == "Chunk 1 text"

    @patch('governmentreporter.processors.build_payloads.generate_eo_llm_fields')
    @patch('governmentreporter.processors.build_payloads.chunk_executive_order')
    def test_build_payloads_eo_document(self, mock_chunk, mock_llm):
        """
        Test payload building for EO document.

        Verifies complete pipeline for Executive Orders.

        Args:
            mock_chunk: Mock chunking function
            mock_llm: Mock LLM extraction
        """
        # Arrange
        doc = Document(
            id="eo-test",
            title="Test Order",
            date="2024-01-15",
            type="executive_order",
            source="federal_register",
            content="Order text",
            url="https://example.com"
        )

        mock_chunk.return_value = [
            ("Chunk 1 text", {"chunk_index": 0, "chunk_total": 1})
        ]

        mock_llm.return_value = {
            "plain_summary": "Summary",
            "federal_statutes_referenced": [],
            "federal_regulations_referenced": [],
            "agencies_or_entities": [],
            "topics_or_policy_areas": ["t1", "t2", "t3", "t4", "t5"],
            "action_plain": "Action",
            "impact_simple": "Impact",
            "implementation_requirements": "Requirements"
        }

        # Act
        payloads = build_payloads_from_document(doc)

        # Assert
        assert len(payloads) >= 1

    def test_build_payloads_unknown_document(self):
        """
        Test handling of unknown document types.

        Verifies appropriate error for unsupported documents.
        """
        # Arrange
        doc = Document(
            id="unknown",
            title="Unknown Doc",
            date="2024-01-15",
            type="unknown_type",
            source="unknown_source",
            content="Unknown content",
            url="https://example.com"
        )

        # Act
        with patch('governmentreporter.processors.build_payloads.logger') as mock_logger:
            payloads = build_payloads_from_document(doc)

            # Should return empty list for unknown types
            assert payloads == []
            # Should log a warning
            mock_logger.warning.assert_called()


# Test fixtures for build_payloads tests
@pytest.fixture
def sample_scotus_document():
    """
    Provide sample Supreme Court Document for testing.

    Returns:
        Document: SCOTUS document with metadata

    Python Learning Notes:
        - Fixtures provide consistent test data
        - Document objects simulate API responses
    """
    return Document(
        id="fixture-scotus-123",
        title="Fixture v. Test Case",
        date="2024-01-15",
        type="scotus_opinion",
        source="courtlistener",
        content="""
        Syllabus

        The Court held that fixtures are useful for testing.

        CHIEF JUSTICE FIXTURE delivered the opinion of the Court.

        This case presents the question whether fixtures improve test quality.
        We hold that they do.
        """,
        metadata={
            "docket_number": "23-FIX",
            "majority_author": "Fixture",
            "vote_majority": 9,
            "vote_minority": 0
        },
        url="https://fixture.test/scotus"
    )


@pytest.fixture
def sample_eo_document():
    """
    Provide sample Executive Order Document for testing.

    Returns:
        Document: EO document with metadata
    """
    return Document(
        id="fixture-eo-14999",
        title="Executive Order on Testing",
        date="2024-01-20",
        type="executive_order",
        source="federal_register",
        content="""
        EXECUTIVE ORDER

        By the authority vested in me as President...

        Section 1. Purpose. This order promotes testing.

        Sec. 2. Policy. All code shall be tested.

        Sec. 3. Implementation. Tests shall be comprehensive.
        """,
        metadata={
            "executive_order_number": "14999",
            "president": "Test President",
            "agencies": ["Test Agency"]
        },
        url="https://fixture.test/eo"
    )