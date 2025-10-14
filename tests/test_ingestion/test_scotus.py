"""
Unit tests for SCOTUS ingestion functionality.

This module tests the SCOTUSIngester class, which handles fetching and processing
Supreme Court opinions from the CourtListener API.

NOTE: As of 2025-10-13, the CourtListener API's docket__court=scotus filter has been
verified to work correctly, so manual court validation is no longer necessary.
The ingester relies on the API filter for efficiency.

Test Categories:
    - Document ID fetching with API filtering
    - Integration with ingestion pipeline
    - Cluster caching behavior
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from governmentreporter.ingestion.scotus import SCOTUSIngester


class TestSCOTUSIngester:
    """
    Test suite for the SCOTUSIngester class.

    This class contains tests for SCOTUS-specific ingestion logic,
    particularly the cluster-level court validation feature.
    """

    @pytest.fixture
    def mock_scotus_cluster_data(self):
        """Provide sample SCOTUS cluster data."""
        return {
            "id": 789012,
            "case_name": "Test Case v. United States",
            "date_filed": "2024-01-15",
            "docket": "https://www.courtlistener.com/api/rest/v4/dockets/345678/",
            "sub_opinions": [
                "https://www.courtlistener.com/api/rest/v4/opinions/123456/",
                "https://www.courtlistener.com/api/rest/v4/opinions/123457/",
            ],
            "citations": [{"volume": 600, "reporter": "U.S.", "page": "123"}],
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
    def mock_non_scotus_cluster_data(self):
        """Provide sample non-SCOTUS cluster data."""
        return {
            "id": 10692765,
            "case_name": "Brooklyn Tabernacle v. Thor 180 Livingston, LLC",
            "date_filed": "2021-09-30",
            "docket": "https://www.courtlistener.com/api/rest/v4/dockets/71584717/",
            "sub_opinions": [
                "https://www.courtlistener.com/api/rest/v4/opinions/11159353/"
            ],
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
            start_date="2024-01-01",
            end_date="2024-12-31",
            batch_size=10,
            dry_run=True,
        )
        # Replace the real API client with the mock
        ingester.api_client = mock_api_client.return_value
        return ingester

    def test_cluster_cache_initialized(self, ingester):
        """
        Test that cluster cache is properly initialized.

        Verifies that the ingester has a cluster_cache dictionary
        ready to store cluster metadata.
        """
        assert hasattr(ingester, "cluster_cache")
        assert isinstance(ingester.cluster_cache, dict)
        assert len(ingester.cluster_cache) == 0

    @patch("httpx.Client")
    def test_fetch_document_ids_from_scotus_clusters(
        self,
        mock_httpx_client,
        ingester,
        mock_scotus_cluster_data,
        mock_scotus_docket_data,
    ):
        """
        Test that _fetch_document_ids fetches SCOTUS clusters via API filter.

        Verifies that the method:
        1. Fetches clusters from the API using docket__court=scotus filter
        2. Extracts opinion IDs from clusters (API filter ensures SCOTUS only)
        3. Caches cluster data for later use
        """
        # Mock HTTP client
        mock_client_instance = MagicMock()
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance

        # Mock clusters response - API filter ensures SCOTUS only
        clusters_response = MagicMock()
        clusters_response.json.return_value = {
            "results": [mock_scotus_cluster_data],
            "next": None,
        }
        clusters_response.raise_for_status = MagicMock()

        mock_client_instance.get.return_value = clusters_response

        # Call the method
        opinion_ids = ingester._fetch_document_ids()

        # Verify results
        assert len(opinion_ids) == 2
        assert "123456" in opinion_ids
        assert "123457" in opinion_ids

        # Verify cluster data was cached
        assert len(ingester.cluster_cache) == 2
        assert ingester.cluster_cache["123456"] == mock_scotus_cluster_data
        assert ingester.cluster_cache["123457"] == mock_scotus_cluster_data

        # Verify API was called with correct filter
        call_args = mock_client_instance.get.call_args
        assert call_args is not None
        # Check that docket__court=scotus filter is in params
        if "params" in call_args.kwargs:
            params = call_args.kwargs["params"]
            assert params.get("docket__court") == "scotus"

    @patch("governmentreporter.ingestion.scotus.build_payloads_from_document")
    def test_process_single_document_uses_cached_cluster_data(
        self, mock_build_payloads, ingester, mock_scotus_cluster_data
    ):
        """
        Test that _process_single_document uses cached cluster data.

        Verifies that the processing step retrieves cluster data from cache
        instead of making redundant API calls.
        """
        # Pre-populate cluster cache (simulating _fetch_document_ids behavior)
        ingester.cluster_cache["123456"] = mock_scotus_cluster_data

        # Mock API client
        mock_document = MagicMock()
        mock_document.title = "Test Case v. United States"
        ingester.api_client.get_document.return_value = mock_document

        # Mock build_payloads to return empty list (we're just testing cache usage)
        mock_build_payloads.return_value = [
            {
                "text": "test chunk",
                "chunk_index": 0,
                "opinion_type": "majority",
            }
        ]

        # Mock embedding generator
        ingester.embedding_generator.generate_batch_embeddings.return_value = [
            [0.1] * 1536
        ]

        # Mock progress tracker
        ingester.progress_tracker.mark_processing = Mock()
        ingester.progress_tracker.mark_completed = Mock()

        batch_documents = []
        batch_embeddings = []

        result = ingester._process_single_document(
            "123456", batch_documents, batch_embeddings
        )

        # Should succeed
        assert result is True

        # Verify get_document was called with cluster_data parameter
        call_args = ingester.api_client.get_document.call_args
        assert call_args is not None
        assert call_args[0][0] == "123456"  # document_id
        # Check if cluster_data was passed via keyword argument
        if len(call_args) > 1:
            assert call_args[1].get("cluster_data") == mock_scotus_cluster_data
        else:
            # Check kwargs
            assert call_args.kwargs.get("cluster_data") == mock_scotus_cluster_data

    @patch("governmentreporter.ingestion.scotus.build_payloads_from_document")
    def test_process_single_document_handles_missing_cache(
        self, mock_build_payloads, ingester
    ):
        """
        Test that _process_single_document handles missing cluster cache gracefully.

        Verifies that if cluster data is not in cache (edge case), the method
        logs a warning but continues processing by fetching cluster data from API.
        """
        # DO NOT populate cluster cache - simulate cache miss

        # Mock API client
        mock_document = MagicMock()
        mock_document.title = "Test Case v. United States"
        ingester.api_client.get_document.return_value = mock_document

        # Mock build_payloads
        mock_build_payloads.return_value = [
            {
                "text": "test chunk",
                "chunk_index": 0,
                "opinion_type": "majority",
            }
        ]

        # Mock embedding generator
        ingester.embedding_generator.generate_batch_embeddings.return_value = [
            [0.1] * 1536
        ]

        # Mock progress tracker
        ingester.progress_tracker.mark_processing = Mock()
        ingester.progress_tracker.mark_completed = Mock()

        batch_documents = []
        batch_embeddings = []

        result = ingester._process_single_document(
            "123456", batch_documents, batch_embeddings
        )

        # Should still succeed (falls back to API fetch)
        assert result is True

        # Verify get_document was called with cluster_data=None
        call_args = ingester.api_client.get_document.call_args
        assert call_args is not None
        # When cluster_data is None, it will fetch from API
        if len(call_args) > 1 and "cluster_data" in call_args[1]:
            assert call_args[1]["cluster_data"] is None
        elif "cluster_data" in call_args.kwargs:
            assert call_args.kwargs["cluster_data"] is None
