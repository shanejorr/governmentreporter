"""
Comprehensive test suite for the CourtListenerClient API client.

This module provides network-isolated unit tests for the Court Listener API client,
covering happy paths, error cases, pagination, and data transformations. All network
calls are mocked using respx to ensure tests are fast, deterministic, and reliable.

Testing Principles:
    - AAA Pattern: Arrange, Act, Assert
    - Pure unit tests with mocked HTTP calls
    - Small, focused test cases
    - Explicit assertions with clear naming
    - No real network calls

Coverage Areas:
    - Opinion retrieval by ID
    - Cluster data fetching and fallback
    - Document object construction
    - Citation formatting
    - Pagination handling
    - Error scenarios (404s, timeouts, server errors)
"""

import httpx
import pytest
import respx
from httpx import Response

from governmentreporter.apis.base import Document
from governmentreporter.apis.court_listener import CourtListenerClient

# Constants for test configuration
BASE_URL = "https://www.courtlistener.com/api/rest/v4"


class TestCourtListenerClientConfiguration:
    """Tests for client initialization and configuration."""

    def test_client_initialization_with_token(self):
        """Test client initializes correctly with provided token."""
        # Arrange
        token = "test-api-token-123"

        # Act
        client = CourtListenerClient(token=token)

        # Assert
        assert client.api_key == token
        assert client.base_url == BASE_URL
        assert client.headers["Authorization"] == f"Token {token}"
        assert "GovernmentReporter" in client.headers["User-Agent"]

    def test_base_url_configuration(self, court_listener_client):
        """Test that base URL is correctly configured."""
        # Assert
        assert court_listener_client._get_base_url() == BASE_URL


class TestGetOpinion:
    """Tests for the get_opinion method."""

    @respx.mock
    def test_get_opinion_happy_path(self, court_listener_client, opinions_payload):
        """Test successful retrieval of an opinion by ID."""
        # Arrange
        opinion_id = 9973155
        url = f"{BASE_URL}/opinions/{opinion_id}/"

        # Mock the API response
        respx.get(url).mock(return_value=Response(200, json=opinions_payload))

        # Act
        result = court_listener_client.get_opinion(opinion_id)

        # Assert
        assert result["id"] == opinion_id
        assert result["cluster"] == opinions_payload["cluster"]
        assert "plain_text" in result
        assert result["author_id"] == 3200
        assert result["download_url"] == opinions_payload["download_url"]

    @respx.mock
    def test_get_opinion_not_found(self, court_listener_client):
        """Test handling of 404 error when opinion not found."""
        # Arrange
        opinion_id = 999999999
        url = f"{BASE_URL}/opinions/{opinion_id}/"

        # Mock 404 response
        respx.get(url).mock(return_value=Response(404))

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            court_listener_client.get_opinion(opinion_id)

        assert exc_info.value.response.status_code == 404

    @respx.mock
    def test_get_opinion_unauthorized(self, court_listener_client):
        """Test handling of 401 error for invalid authentication."""
        # Arrange
        opinion_id = 123456
        url = f"{BASE_URL}/opinions/{opinion_id}/"

        # Mock 401 response
        respx.get(url).mock(return_value=Response(401))

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            court_listener_client.get_opinion(opinion_id)

        assert exc_info.value.response.status_code == 401

    @respx.mock
    def test_get_opinion_server_error(self, court_listener_client):
        """Test handling of 500 server error."""
        # Arrange
        opinion_id = 123456
        url = f"{BASE_URL}/opinions/{opinion_id}/"

        # Mock 500 response
        respx.get(url).mock(return_value=Response(500))

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            court_listener_client.get_opinion(opinion_id)

        assert exc_info.value.response.status_code == 500


class TestGetOpinionCluster:
    """Tests for the get_opinion_cluster method."""

    @respx.mock
    def test_get_cluster_happy_path(self, court_listener_client, cluster_payload):
        """Test successful retrieval of cluster data."""
        # Arrange
        cluster_url = f"{BASE_URL}/clusters/9506542/"

        # Mock the API response
        respx.get(cluster_url).mock(return_value=Response(200, json=cluster_payload))

        # Act
        result = court_listener_client.get_opinion_cluster(cluster_url)

        # Assert
        assert result["id"] == 9506542
        assert result["case_name"] == cluster_payload["case_name"]
        assert len(result["citations"]) == 1
        assert result["citations"][0]["volume"] == 601
        assert result["citations"][0]["reporter"] == "U.S."
        assert result["citations"][0]["page"] == "416"
        assert result["date_filed"] == "2024-05-16"

    @respx.mock
    def test_get_cluster_not_found(self, court_listener_client):
        """Test handling of 404 when cluster not found."""
        # Arrange
        cluster_url = f"{BASE_URL}/clusters/999999/"

        # Mock 404 response
        respx.get(cluster_url).mock(return_value=Response(404))

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            court_listener_client.get_opinion_cluster(cluster_url)

        assert exc_info.value.response.status_code == 404

    @respx.mock
    def test_get_cluster_timeout(self, court_listener_client):
        """Test handling of network timeout."""
        # Arrange
        cluster_url = f"{BASE_URL}/clusters/123/"

        # Mock timeout
        respx.get(cluster_url).mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        # Act & Assert
        with pytest.raises(httpx.TimeoutException):
            court_listener_client.get_opinion_cluster(cluster_url)


class TestGetDocument:
    """Tests for the get_document method which combines opinion and cluster data."""

    @respx.mock
    def test_get_document_with_cluster(
        self, court_listener_client, opinions_payload, cluster_payload
    ):
        """Test building a complete Document with opinion and cluster data."""
        # Arrange
        opinion_id = "9973155"
        opinion_url = f"{BASE_URL}/opinions/{opinion_id}/"
        cluster_url = f"{BASE_URL}/clusters/9506542/"

        # Mock both API responses
        respx.get(opinion_url).mock(return_value=Response(200, json=opinions_payload))
        respx.get(cluster_url).mock(return_value=Response(200, json=cluster_payload))

        # Act
        document = court_listener_client.get_document(opinion_id)

        # Assert - Document structure
        assert isinstance(document, Document)
        assert document.id == opinion_id
        assert document.title == cluster_payload["case_name"]
        assert document.type == "Supreme Court Opinion"
        assert document.source == "CourtListener"
        assert document.date == "2024-05-23"  # Parsed from date_created

        # Assert - Content
        assert document.content == opinions_payload["plain_text"]
        assert len(document.content) > 0

        # Assert - Metadata
        assert document.metadata["case_name"] == cluster_payload["case_name"]
        assert (
            document.metadata["citation"] == "601 U.S. 416 (2024)"
        )  # Built from cluster
        assert document.metadata["author_id"] == 3200
        assert document.metadata["download_url"] == opinions_payload["download_url"]

        # Assert - URL
        assert document.url == opinions_payload["download_url"]

    @respx.mock
    def test_get_document_cluster_fallback(
        self, court_listener_client, opinions_payload
    ):
        """Test Document creation when cluster fetch fails (fallback to opinion data only)."""
        # Arrange
        opinion_id = "9973155"
        opinion_url = f"{BASE_URL}/opinions/{opinion_id}/"
        cluster_url = f"{BASE_URL}/clusters/9506542/"

        # Mock opinion success, cluster failure
        respx.get(opinion_url).mock(return_value=Response(200, json=opinions_payload))
        respx.get(cluster_url).mock(return_value=Response(404))

        # Act
        document = court_listener_client.get_document(opinion_id)

        # Assert - Document still created with degraded data
        assert isinstance(document, Document)
        assert document.id == opinion_id
        assert document.title == "Unknown Case"  # Fallback title
        assert document.type == "Supreme Court Opinion"
        assert document.source == "CourtListener"
        assert document.content == opinions_payload["plain_text"]

        # Metadata should not have cluster-specific fields
        assert (
            "citation" not in document.metadata or document.metadata["citation"] is None
        )
        # case_name is added to metadata when cluster fails
        assert (
            document.metadata.get("case_name") == "Unknown Case"
            or "case_name" not in document.metadata
        )

    @respx.mock
    def test_get_document_not_found(self, court_listener_client):
        """Test handling when opinion doesn't exist."""
        # Arrange
        opinion_id = "999999999"
        opinion_url = f"{BASE_URL}/opinions/{opinion_id}/"

        # Mock 404 for opinion
        respx.get(opinion_url).mock(return_value=Response(404))

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            court_listener_client.get_document(opinion_id)

        assert exc_info.value.response.status_code == 404


class TestGetDocumentText:
    """Tests for the get_document_text method."""

    @respx.mock
    def test_get_document_text_happy_path(
        self, court_listener_client, opinions_payload
    ):
        """Test retrieving just the text content of an opinion."""
        # Arrange
        opinion_id = "9973155"
        opinion_url = f"{BASE_URL}/opinions/{opinion_id}/"

        # Mock the API response
        respx.get(opinion_url).mock(return_value=Response(200, json=opinions_payload))

        # Act
        text = court_listener_client.get_document_text(opinion_id)

        # Assert
        assert text == opinions_payload["plain_text"]
        assert "CONSUMER FINANCIAL PROTECTION BUREAU" in text
        assert "Supreme Court" in text

    @respx.mock
    def test_get_document_text_empty(self, court_listener_client):
        """Test handling of opinion with no plain text."""
        # Arrange
        opinion_id = "123456"
        opinion_url = f"{BASE_URL}/opinions/{opinion_id}/"

        # Mock response without plain_text
        empty_opinion = {"id": 123456, "cluster": "url", "author_id": 1}
        respx.get(opinion_url).mock(return_value=Response(200, json=empty_opinion))

        # Act
        text = court_listener_client.get_document_text(opinion_id)

        # Assert
        assert text == ""


class TestSearchDocuments:
    """Tests for the search_documents method with pagination."""

    @respx.mock
    def test_search_documents_basic(self, court_listener_client):
        """Test basic search without full content retrieval."""
        # Arrange
        search_url = f"{BASE_URL}/opinions/"
        search_results = {
            "count": 2,
            "next": None,
            "results": [
                {
                    "id": 111,
                    "snippet": "First opinion snippet",
                    "date_created": "2024-01-15T10:30:00Z",
                    "resource_uri": "/api/rest/v4/opinions/111/",
                    "absolute_url": "/opinion/111/test-case-1/",
                },
                {
                    "id": 222,
                    "snippet": "Second opinion snippet",
                    "date_created": "2024-02-20T14:45:00Z",
                    "resource_uri": "/api/rest/v4/opinions/222/",
                    "absolute_url": "/opinion/222/test-case-2/",
                },
            ],
        }

        # Mock the search response
        respx.get(search_url).mock(return_value=Response(200, json=search_results))

        # Act
        documents = court_listener_client.search_documents(
            query="test query", limit=5, full_content=False
        )

        # Assert
        assert len(documents) == 2

        # Check first document
        doc1 = documents[0]
        assert doc1.id == "111"
        assert doc1.title == "First opinion snippet"
        assert doc1.date == "2024-01-15"
        assert doc1.type == "Supreme Court Opinion"
        assert doc1.source == "CourtListener"
        assert doc1.content == ""  # No content in summary mode
        assert doc1.metadata["summary_mode"] is True

        # Check second document
        doc2 = documents[1]
        assert doc2.id == "222"
        assert doc2.date == "2024-02-20"

    @respx.mock
    def test_search_documents_with_pagination(self, court_listener_client):
        """Test search with multiple pages of results."""
        # Arrange
        base_url = f"{BASE_URL}/opinions/"

        # First page
        page1_results = {
            "count": 150,
            "next": f"{base_url}?page=2",
            "results": [
                {
                    "id": i,
                    "snippet": f"Opinion {i}",
                    "date_created": "2024-01-01T00:00:00Z",
                }
                for i in range(1, 101)  # 100 results
            ],
        }

        # Second page
        page2_results = {
            "count": 150,
            "next": f"{base_url}?page=3",
            "results": [
                {
                    "id": i,
                    "snippet": f"Opinion {i}",
                    "date_created": "2024-01-01T00:00:00Z",
                }
                for i in range(101, 151)  # 50 results
            ],
        }

        # Mock the paginated responses
        # The implementation calls client.get(url, params=params)
        # On the second call, url is the full next URL and params is empty {}
        # So we need a more sophisticated mock that returns different results based on call count

        call_count = [0]  # Use list to make it mutable in closure

        def mock_response(request):  # noqa: ARG001
            call_count[0] += 1
            if call_count[0] == 1:
                # First call - return page 1
                return Response(200, json=page1_results)
            # Second call - return page 2
            return Response(200, json=page2_results)

        # Mock any GET to the opinions URL
        respx.get(url__regex=r".*opinions.*").mock(side_effect=mock_response)

        # Act - Request 120 documents (should fetch 2 pages)
        documents = court_listener_client.search_documents(
            query="test", limit=120, full_content=False
        )

        # Assert
        assert len(documents) == 120
        assert documents[0].id == "1"
        assert documents[99].id == "100"  # Last from first page
        assert documents[100].id == "101"  # First from second page
        assert documents[119].id == "120"  # Last document

    @respx.mock
    def test_search_documents_with_date_filters(self, court_listener_client):
        """Test search with date range filters."""
        # Arrange
        search_url = f"{BASE_URL}/opinions/"
        empty_results = {"count": 0, "next": None, "results": []}

        # Mock the search with date parameters
        route = respx.get(search_url).mock(
            return_value=Response(200, json=empty_results)
        )

        # Act
        documents = court_listener_client.search_documents(
            query="constitutional",
            start_date="2024-01-01",
            end_date="2024-12-31",
            limit=10,
        )

        # Assert - Check that date parameters were included
        assert route.called
        request = route.calls.last.request
        assert "date_created__gte=2024-01-01" in str(request.url)
        assert "date_created__lte=2024-12-31" in str(request.url)
        assert len(documents) == 0  # Empty results

    @respx.mock
    def test_search_documents_with_full_content(
        self, court_listener_client, opinions_payload, cluster_payload
    ):
        """Test search with full content retrieval for each result."""
        # Arrange
        search_url = f"{BASE_URL}/opinions/"
        search_results = {
            "count": 1,
            "next": None,
            "results": [
                {
                    "id": 9973155,
                    "snippet": "Test opinion",
                    "date_created": "2024-05-23T08:03:26.705254-07:00",
                }
            ],
        }

        opinion_url = f"{BASE_URL}/opinions/9973155/"
        cluster_url = f"{BASE_URL}/clusters/9506542/"

        # Mock all the required API calls
        respx.get(search_url).mock(return_value=Response(200, json=search_results))
        respx.get(opinion_url).mock(return_value=Response(200, json=opinions_payload))
        respx.get(cluster_url).mock(return_value=Response(200, json=cluster_payload))

        # Act
        documents = court_listener_client.search_documents(
            query="test", limit=10, full_content=True  # Request full content
        )

        # Assert
        assert len(documents) == 1
        doc = documents[0]
        assert doc.id == "9973155"
        assert doc.content == opinions_payload["plain_text"]  # Full content retrieved
        assert doc.title == cluster_payload["case_name"]  # From cluster
        assert doc.metadata["citation"] == "601 U.S. 416 (2024)"

    @respx.mock
    def test_search_documents_error_handling(self, court_listener_client):
        """Test search handles individual document errors gracefully."""
        # Arrange
        search_url = f"{BASE_URL}/opinions/"
        search_results = {
            "count": 3,
            "next": None,
            "results": [
                {
                    "id": 111,
                    "snippet": "Good 1",
                    "date_created": "2024-01-01T00:00:00Z",
                },
                {"id": None, "snippet": "Bad - no ID"},  # Invalid - no ID
                {
                    "id": 333,
                    "snippet": "Good 2",
                    "date_created": "2024-01-03T00:00:00Z",
                },
            ],
        }

        # Mock the search response
        respx.get(search_url).mock(return_value=Response(200, json=search_results))

        # Act
        documents = court_listener_client.search_documents("test", limit=10)

        # Assert - Should skip the invalid document
        assert len(documents) == 2
        assert documents[0].id == "111"
        assert documents[1].id == "333"


class TestExtractBasicMetadata:
    """Tests for the extract_basic_metadata method."""

    def test_extract_metadata_complete(self, court_listener_client, opinions_payload):
        """Test metadata extraction with all fields present."""
        # Act
        metadata = court_listener_client.extract_basic_metadata(opinions_payload)

        # Assert
        assert metadata["id"] == 9973155
        assert metadata["date"] == "2024-05-23"
        assert metadata["plain_text"] == opinions_payload["plain_text"]
        assert metadata["author_id"] == 3200
        assert metadata["download_url"] == opinions_payload["download_url"]
        assert metadata["type"] == "010combined"
        assert metadata["page_count"] == 58

    def test_extract_metadata_missing_fields(self, court_listener_client):
        """Test metadata extraction with missing optional fields."""
        # Arrange
        minimal_opinion = {"id": 123, "date_created": "2024-01-15T10:30:00Z"}

        # Act
        metadata = court_listener_client.extract_basic_metadata(minimal_opinion)

        # Assert
        assert metadata["id"] == 123
        assert metadata["date"] == "2024-01-15"
        assert metadata["plain_text"] == ""
        assert metadata["author_id"] is None
        assert metadata["download_url"] is None

    def test_extract_metadata_invalid_date(self, court_listener_client):
        """Test metadata extraction with invalid date format."""
        # Arrange
        opinion_with_bad_date = {
            "id": 456,
            "date_created": "not-a-date",
            "plain_text": "Some text",
        }

        # Act
        metadata = court_listener_client.extract_basic_metadata(opinion_with_bad_date)

        # Assert
        assert metadata["id"] == 456
        assert metadata["date"] is None  # Failed to parse
        assert metadata["plain_text"] == "Some text"


class TestDateValidation:
    """Tests for date format validation."""

    def test_validate_date_format_valid(self, court_listener_client):
        """Test validation of correctly formatted dates."""
        assert court_listener_client.validate_date_format("2024-01-15") is True
        assert court_listener_client.validate_date_format("2024-12-31") is True
        assert court_listener_client.validate_date_format("2000-01-01") is True

    def test_validate_date_format_invalid(self, court_listener_client):
        """Test validation rejects incorrectly formatted dates."""
        assert court_listener_client.validate_date_format("01/15/2024") is False
        assert (
            court_listener_client.validate_date_format("2024-1-15") is False
        )  # Missing zeros
        assert court_listener_client.validate_date_format("2024/01/15") is False
        assert court_listener_client.validate_date_format("15-01-2024") is False
        assert court_listener_client.validate_date_format("not-a-date") is False

    def test_validate_date_format_edge_cases(self, court_listener_client):
        """Test validation with edge cases (format only, not validity)."""
        # These pass format check even if invalid dates
        assert (
            court_listener_client.validate_date_format("2024-13-45") is True
        )  # Invalid but correct format
        assert (
            court_listener_client.validate_date_format("2024-00-00") is True
        )  # Invalid but correct format
