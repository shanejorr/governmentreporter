"""
Unit tests for SCOTUS ingestion with court validation.

This module tests the SCOTUSIngester class, focusing on the court validation
functionality that defends against API index inconsistencies.

Test Categories:
    - Court validation (SCOTUS vs non-SCOTUS)
    - Validation error handling
    - Integration with ingestion pipeline
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from governmentreporter.ingestion.scotus import SCOTUSIngester


class TestSCOTUSIngester:
    """
    Test suite for the SCOTUSIngester class.

    This class contains tests for SCOTUS-specific ingestion logic,
    particularly the court validation feature.
    """

    @pytest.fixture
    def mock_scotus_opinion_data(self):
        """Provide sample SCOTUS opinion data."""
        return {
            "id": 123456,
            "cluster": "https://www.courtlistener.com/api/rest/v4/clusters/789012/",
            "plain_text": "Test opinion text",
        }

    @pytest.fixture
    def mock_scotus_cluster_data(self):
        """Provide sample SCOTUS cluster data."""
        return {
            "id": 789012,
            "case_name": "Test Case v. United States",
            "docket": "https://www.courtlistener.com/api/rest/v4/dockets/345678/",
        }

    @pytest.fixture
    def mock_scotus_docket_data(self):
        """Provide sample SCOTUS docket data."""
        return {
            "id": 345678,
            "court_id": "scotus",
            "case_name": "Test Case v. United States",
            "docket_number": "22-123",
        }

    @pytest.fixture
    def mock_non_scotus_opinion_data(self):
        """Provide sample non-SCOTUS opinion data."""
        return {
            "id": 11159353,
            "cluster": "https://www.courtlistener.com/api/rest/v4/clusters/10692765/",
            "plain_text": "",
        }

    @pytest.fixture
    def mock_non_scotus_cluster_data(self):
        """Provide sample non-SCOTUS cluster data."""
        return {
            "id": 10692765,
            "case_name": "Brooklyn Tabernacle v. Thor 180 Livingston, LLC",
            "docket": "https://www.courtlistener.com/api/rest/v4/dockets/71584717/",
        }

    @pytest.fixture
    def mock_non_scotus_docket_data(self):
        """Provide sample non-SCOTUS (NY Appellate Division) docket data."""
        return {
            "id": 71584717,
            "court_id": "nyappdiv",
            "case_name": "Brooklyn Tabernacle v. Thor 180 Livingston, LLC",
            "docket_number": "2021-07005",
        }

    @pytest.fixture
    @patch("governmentreporter.ingestion.base.QdrantIngestionClient")
    @patch("governmentreporter.ingestion.base.EmbeddingGenerator")
    @patch("governmentreporter.ingestion.base.ProgressTracker")
    @patch("governmentreporter.ingestion.scotus.CourtListenerClient")
    def ingester(
        self,
        mock_api_client,
        mock_progress_tracker,
        mock_embedding_gen,
        mock_qdrant,
    ):
        """Create a SCOTUSIngester instance with mocked dependencies."""
        ingester = SCOTUSIngester(
            start_date="2025-01-01",
            end_date="2025-12-31",
            batch_size=10,
            dry_run=True,
        )
        # Replace the real API client with the mock
        ingester.api_client = mock_api_client.return_value
        return ingester

    def test_validate_court_scotus_success(
        self,
        ingester,
        mock_scotus_opinion_data,
        mock_scotus_cluster_data,
        mock_scotus_docket_data,
    ):
        """
        Test successful validation for SCOTUS opinion.

        Verifies that validation passes when opinion belongs to SCOTUS.
        """
        # Mock the API client methods
        ingester.api_client.get_opinion.return_value = mock_scotus_opinion_data
        ingester.api_client.get_opinion_cluster.return_value = mock_scotus_cluster_data
        ingester.api_client.get_docket.return_value = mock_scotus_docket_data

        is_valid, error_message = ingester._validate_court("123456")

        assert is_valid is True
        assert error_message == ""

        # Verify API calls were made
        ingester.api_client.get_opinion.assert_called_once_with(123456)
        ingester.api_client.get_opinion_cluster.assert_called_once()
        ingester.api_client.get_docket.assert_called_once()

    def test_validate_court_non_scotus_failure(
        self,
        ingester,
        mock_non_scotus_opinion_data,
        mock_non_scotus_cluster_data,
        mock_non_scotus_docket_data,
    ):
        """
        Test validation failure for non-SCOTUS opinion.

        Verifies that validation fails when opinion belongs to a different court
        (e.g., NY Appellate Division) and provides descriptive error message.
        """
        # Mock the API client methods
        ingester.api_client.get_opinion.return_value = mock_non_scotus_opinion_data
        ingester.api_client.get_opinion_cluster.return_value = (
            mock_non_scotus_cluster_data
        )
        ingester.api_client.get_docket.return_value = mock_non_scotus_docket_data

        is_valid, error_message = ingester._validate_court("11159353")

        assert is_valid is False
        assert "nyappdiv" in error_message
        assert "not scotus" in error_message.lower()
        assert "Brooklyn Tabernacle" in error_message
        assert "API index inconsistency" in error_message

    def test_validate_court_missing_cluster_url(self, ingester):
        """
        Test validation failure when opinion has no cluster URL.

        Verifies proper error handling for malformed opinion data.
        """
        # Mock opinion with no cluster URL
        ingester.api_client.get_opinion.return_value = {"id": 123456, "cluster": None}

        is_valid, error_message = ingester._validate_court("123456")

        assert is_valid is False
        assert "no cluster URL" in error_message

    def test_validate_court_missing_docket_url(
        self, ingester, mock_scotus_opinion_data
    ):
        """
        Test validation failure when cluster has no docket URL.

        Verifies proper error handling for malformed cluster data.
        """
        # Mock opinion with cluster but cluster has no docket
        ingester.api_client.get_opinion.return_value = mock_scotus_opinion_data
        ingester.api_client.get_opinion_cluster.return_value = {
            "id": 789012,
            "docket": None,
        }

        is_valid, error_message = ingester._validate_court("123456")

        assert is_valid is False
        assert "no docket URL" in error_message

    def test_validate_court_missing_court_id(
        self, ingester, mock_scotus_opinion_data, mock_scotus_cluster_data
    ):
        """
        Test validation failure when docket has no court_id.

        Verifies proper error handling for malformed docket data.
        """
        # Mock opinion and cluster, but docket has no court_id
        ingester.api_client.get_opinion.return_value = mock_scotus_opinion_data
        ingester.api_client.get_opinion_cluster.return_value = mock_scotus_cluster_data
        ingester.api_client.get_docket.return_value = {"id": 345678, "court_id": None}

        is_valid, error_message = ingester._validate_court("123456")

        assert is_valid is False
        assert "no court_id" in error_message

    def test_validate_court_api_error_propagation(self, ingester):
        """
        Test that API errors are propagated during validation.

        Verifies that exceptions from API calls are not caught by validation
        but are propagated to the caller for proper error handling.
        """
        # Mock API error
        ingester.api_client.get_opinion.side_effect = Exception("API connection failed")

        with pytest.raises(Exception) as exc_info:
            ingester._validate_court("123456")

        assert "API connection failed" in str(exc_info.value)

    @patch("governmentreporter.ingestion.scotus.build_payloads_from_document")
    def test_process_single_document_skips_non_scotus(
        self,
        mock_build_payloads,
        ingester,
        mock_non_scotus_opinion_data,
        mock_non_scotus_cluster_data,
        mock_non_scotus_docket_data,
    ):
        """
        Test that non-SCOTUS opinions are skipped during processing.

        Verifies that validation prevents non-SCOTUS opinions from being
        processed, embedded, or stored.
        """
        # Mock validation to return non-SCOTUS
        ingester.api_client.get_opinion.return_value = mock_non_scotus_opinion_data
        ingester.api_client.get_opinion_cluster.return_value = (
            mock_non_scotus_cluster_data
        )
        ingester.api_client.get_docket.return_value = mock_non_scotus_docket_data

        # Mock progress tracker
        ingester.progress_tracker.mark_processing = Mock()
        ingester.progress_tracker.mark_failed = Mock()

        batch_documents = []
        batch_embeddings = []

        result = ingester._process_single_document(
            "11159353", batch_documents, batch_embeddings
        )

        # Should return False (failed)
        assert result is False

        # Should mark as failed with descriptive error
        ingester.progress_tracker.mark_failed.assert_called_once()
        error_message = ingester.progress_tracker.mark_failed.call_args[0][1]
        assert "nyappdiv" in error_message
        assert "not scotus" in error_message.lower()

        # Should NOT process the document further
        mock_build_payloads.assert_not_called()
        assert len(batch_documents) == 0
        assert len(batch_embeddings) == 0
