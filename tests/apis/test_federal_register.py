"""
Comprehensive test suite for the FederalRegisterClient API client.

This module provides network-isolated unit tests for the Federal Register API client,
covering happy paths, error cases, retry logic, and text cleaning. All network calls
are mocked using respx to ensure tests are fast, deterministic, and reliable.

Testing Principles:
    - AAA Pattern: Arrange, Act, Assert
    - Pure unit tests with mocked HTTP calls
    - Small, focused test cases
    - Explicit assertions with clear naming
    - No real network calls

Coverage Areas:
    - Executive order retrieval by document number
    - Raw text extraction and HTML cleaning
    - Document object construction
    - Pagination and listing operations
    - Retry logic with exponential backoff
    - Error scenarios (404s, timeouts, rate limiting, server errors)
"""

import time
from datetime import datetime
from typing import Any, Dict

import httpx
import pytest
import respx
from httpx import Response

from governmentreporter.apis.base import Document
from governmentreporter.apis.federal_register import FederalRegisterClient


class TestFederalRegisterClientConfiguration:
    """Tests for client initialization and configuration."""

    def test_client_initialization(self):
        """Test client initializes correctly without authentication."""
        # Act
        client = FederalRegisterClient()

        # Assert
        assert client.api_key is None  # No authentication needed
        assert client.base_url == "https://www.federalregister.gov/api/v1"
        assert client.rate_limit_delay == 1.1
        assert client.max_retries == 5
        assert client.retry_delay == 1.0
        assert "GovernmentReporter" in client.headers["User-Agent"]
        assert client.headers["Accept"] == "application/json"

    def test_base_url_configuration(self, federal_register_client):
        """Test that base URL is correctly configured."""
        # Assert
        assert (
            federal_register_client._get_base_url()
            == "https://www.federalregister.gov/api/v1"
        )

    def test_rate_limit_delay_configuration(self, federal_register_client):
        """Test that rate limit delay is correctly configured."""
        # Assert
        assert federal_register_client._get_rate_limit_delay() == 1.1


class TestMakeRequestWithRetry:
    """Tests for the retry logic implementation."""

    @respx.mock
    def test_request_success_first_attempt(self, federal_register_client):
        """Test successful request on first attempt."""
        # Arrange
        url = "https://www.federalregister.gov/api/v1/test"
        mock_response = {"status": "success"}

        # Mock successful response
        respx.get(url).mock(return_value=Response(200, json=mock_response))

        # Act
        response = federal_register_client._make_request_with_retry(url)

        # Assert
        assert response.status_code == 200
        assert response.json() == mock_response

    @respx.mock
    def test_request_retry_on_429(self, federal_register_client):
        """Test retry logic for rate limiting (429) responses."""
        # Arrange
        url = "https://www.federalregister.gov/api/v1/test"
        mock_response = {"status": "success"}

        # Mock 429 then success
        route = respx.get(url)
        route.side_effect = [
            Response(429),  # First attempt - rate limited
            Response(200, json=mock_response),  # Second attempt - success
        ]

        # Act
        start_time = time.time()
        response = federal_register_client._make_request_with_retry(url)
        elapsed = time.time() - start_time

        # Assert
        assert response.status_code == 200
        assert response.json() == mock_response
        assert elapsed >= 1.0  # Should have delayed at least 1 second

    @respx.mock
    def test_request_no_retry_on_500(self, federal_register_client):
        """Test that server errors (500+) are not retried (only 429 is retried)."""
        # Arrange
        url = "https://www.federalregister.gov/api/v1/test"

        # Mock 500 response
        respx.get(url).mock(return_value=Response(500))

        # Act & Assert - Should raise immediately without retry
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            federal_register_client._make_request_with_retry(url)

        assert exc_info.value.response.status_code == 500

    @respx.mock
    def test_request_max_retries_exceeded(self, federal_register_client):
        """Test that max retries are respected and exception raised."""
        # Arrange
        url = "https://www.federalregister.gov/api/v1/test"

        # Mock all attempts as failures
        respx.get(url).mock(return_value=Response(429))

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError):
            federal_register_client._make_request_with_retry(url)

    @respx.mock
    def test_request_no_retry_on_404(self, federal_register_client):
        """Test that 404 errors are not retried."""
        # Arrange
        url = "https://www.federalregister.gov/api/v1/test"

        # Mock 404 response
        respx.get(url).mock(return_value=Response(404))

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            federal_register_client._make_request_with_retry(url)

        assert exc_info.value.response.status_code == 404

    @respx.mock
    def test_request_retry_on_network_error(self, federal_register_client):
        """Test retry logic for network errors."""
        # Arrange
        url = "https://www.federalregister.gov/api/v1/test"

        # Mock network error then success
        route = respx.get(url)
        route.side_effect = [
            httpx.ConnectTimeout("Connection timed out"),
            Response(200, json={"status": "success"}),
        ]

        # Act
        response = federal_register_client._make_request_with_retry(url)

        # Assert
        assert response.status_code == 200


class TestGetExecutiveOrderText:
    """Tests for raw text extraction and HTML cleaning."""

    @respx.mock
    def test_get_text_plain_format(self, federal_register_client):
        """Test extraction of plain text without HTML."""
        # Arrange
        raw_text_url = (
            "https://www.federalregister.gov/documents/full_text/txt/test.txt"
        )
        plain_text = "Executive Order 14000\n\nBy the authority vested in me..."

        # Mock plain text response
        respx.get(raw_text_url).mock(return_value=Response(200, text=plain_text))

        # Act
        result = federal_register_client.get_executive_order_text(raw_text_url)

        # Assert
        assert result == plain_text

    @respx.mock
    def test_get_text_html_format(self, federal_register_client, eo_raw_text):
        """Test extraction and cleaning of HTML-formatted text."""
        # Arrange
        raw_text_url = (
            "https://www.federalregister.gov/documents/full_text/txt/test.txt"
        )

        # Mock HTML response
        respx.get(raw_text_url).mock(return_value=Response(200, text=eo_raw_text))

        # Act
        result = federal_register_client.get_executive_order_text(raw_text_url)

        # Assert
        assert "Executive Order 14304" in result
        assert "Leading the World in Supersonic Flight" in result
        assert "<html>" not in result  # HTML tags removed
        assert "<pre>" not in result
        assert "Federal Register Volume 90" in result

    @respx.mock
    def test_get_text_with_html_entities(self, federal_register_client):
        """Test proper decoding of HTML entities."""
        # Arrange
        raw_text_url = (
            "https://www.federalregister.gov/documents/full_text/txt/test.txt"
        )
        html_with_entities = """<html><body><pre>
        Test &lt;document&gt;
        &quot;Quoted text&quot;
        AT&amp;T Corporation
        </pre></body></html>"""

        # Mock response with HTML entities
        respx.get(raw_text_url).mock(
            return_value=Response(200, text=html_with_entities)
        )

        # Act
        result = federal_register_client.get_executive_order_text(raw_text_url)

        # Assert
        assert "<document>" in result  # &lt; and &gt; decoded
        assert '"Quoted text"' in result  # &quot; decoded
        assert "AT&T Corporation" in result  # &amp; decoded

    @respx.mock
    def test_get_text_404_error(self, federal_register_client):
        """Test handling of missing raw text URL."""
        # Arrange
        raw_text_url = (
            "https://www.federalregister.gov/documents/full_text/txt/missing.txt"
        )

        # Mock 404 response
        respx.get(raw_text_url).mock(return_value=Response(404))

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            federal_register_client.get_executive_order_text(raw_text_url)

        assert exc_info.value.response.status_code == 404


class TestGetExecutiveOrder:
    """Tests for retrieving executive order metadata."""

    @respx.mock
    def test_get_executive_order_happy_path(
        self, federal_register_client, eo_metadata_payload
    ):
        """Test successful retrieval of executive order by document number."""
        # Arrange
        document_number = "2025-10800"
        url = f"https://www.federalregister.gov/api/v1/documents/{document_number}"

        # Mock the API response
        respx.get(url).mock(return_value=Response(200, json=eo_metadata_payload))

        # Act
        result = federal_register_client.get_executive_order(document_number)

        # Assert
        assert result["document_number"] == document_number
        assert result["executive_order_number"] == "14304"
        assert result["title"] == "Leading the World in Supersonic Flight"
        assert result["signing_date"] == "2025-06-06"
        assert result["raw_text_url"] == eo_metadata_payload["raw_text_url"]
        assert result["agencies"] == [
            "Executive Office of the President"
        ]  # Extracted names

    @respx.mock
    def test_get_executive_order_not_found(self, federal_register_client):
        """Test handling of invalid document number."""
        # Arrange
        document_number = "9999-99999"
        url = f"https://www.federalregister.gov/api/v1/documents/{document_number}"

        # Mock 404 response
        respx.get(url).mock(return_value=Response(404))

        # Act & Assert
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            federal_register_client.get_executive_order(document_number)

        assert exc_info.value.response.status_code == 404


class TestListExecutiveOrders:
    """Tests for listing executive orders with pagination."""

    @respx.mock
    def test_list_orders_single_page(self, federal_register_client):
        """Test listing executive orders with single page of results."""
        # Arrange
        url = "https://www.federalregister.gov/api/v1/documents"
        results = {
            "results": [
                {
                    "document_number": "2024-00001",
                    "title": "Order 1",
                    "executive_order_number": 14001,
                    "signing_date": "2024-01-15",
                    "agencies": [{"name": "EPA"}],
                },
                {
                    "document_number": "2024-00002",
                    "title": "Order 2",
                    "executive_order_number": 14002,
                    "signing_date": "2024-02-20",
                    "agencies": [{"name": "DOD"}],
                },
            ],
            "total_pages": 1,
        }

        # Mock the API response
        respx.get(url).mock(return_value=Response(200, json=results))

        # Act
        orders = list(
            federal_register_client.list_executive_orders("2024-01-01", "2024-12-31")
        )

        # Assert
        assert len(orders) == 2
        assert orders[0]["document_number"] == "2024-00001"
        assert orders[0]["agencies"] == ["EPA"]  # Name extracted
        assert orders[1]["document_number"] == "2024-00002"
        assert orders[1]["agencies"] == ["DOD"]

    @respx.mock
    def test_list_orders_with_pagination(self, federal_register_client):
        """Test listing executive orders across multiple pages."""
        # Arrange
        url = "https://www.federalregister.gov/api/v1/documents"

        # Page 1
        page1_results = {
            "results": [
                {
                    "document_number": f"2024-{i:05d}",
                    "title": f"Order {i}",
                    "executive_order_number": 14000 + i,
                }
                for i in range(1, 101)  # 100 results
            ],
            "total_pages": 2,
        }

        # Page 2
        page2_results = {
            "results": [
                {
                    "document_number": f"2024-{i:05d}",
                    "title": f"Order {i}",
                    "executive_order_number": 14000 + i,
                }
                for i in range(101, 151)  # 50 results
            ],
            "total_pages": 2,
        }

        # Mock paginated responses
        routes = [
            respx.get(url, params__contains={"page": 1}).mock(
                return_value=Response(200, json=page1_results)
            ),
            respx.get(url, params__contains={"page": 2}).mock(
                return_value=Response(200, json=page2_results)
            ),
        ]

        # Act
        orders = list(
            federal_register_client.list_executive_orders("2024-01-01", "2024-12-31")
        )

        # Assert
        assert len(orders) == 150
        assert orders[0]["document_number"] == "2024-00001"
        assert orders[99]["document_number"] == "2024-00100"
        assert orders[100]["document_number"] == "2024-00101"
        assert orders[149]["document_number"] == "2024-00150"

    @respx.mock
    def test_list_orders_with_max_results(self, federal_register_client):
        """Test limiting the number of results returned."""
        # Arrange
        url = "https://www.federalregister.gov/api/v1/documents"
        results = {
            "results": [
                {
                    "document_number": f"2024-{i:05d}",
                    "title": f"Order {i}",
                    "executive_order_number": 14000 + i,
                }
                for i in range(1, 101)
            ],
            "total_pages": 3,
        }

        # Mock the API response
        respx.get(url).mock(return_value=Response(200, json=results))

        # Act
        orders = list(
            federal_register_client.list_executive_orders(
                "2024-01-01", "2024-12-31", max_results=25
            )
        )

        # Assert
        assert len(orders) == 25  # Limited to max_results
        assert orders[0]["document_number"] == "2024-00001"
        assert orders[24]["document_number"] == "2024-00025"

    def test_list_orders_invalid_date_format(self, federal_register_client):
        """Test that invalid date formats are rejected."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid start_date format"):
            list(
                federal_register_client.list_executive_orders(
                    "01/01/2024", "2024-12-31"
                )
            )

        with pytest.raises(ValueError, match="Invalid end_date format"):
            list(
                federal_register_client.list_executive_orders(
                    "2024-01-01", "12/31/2024"
                )
            )


class TestSearchDocuments:
    """Tests for the search_documents method."""

    @respx.mock
    def test_search_documents_basic(self, federal_register_client):
        """Test basic search without full content."""
        # Arrange
        url = "https://www.federalregister.gov/api/v1/documents"
        search_results = {
            "results": [
                {
                    "document_number": "2024-12345",
                    "title": "Climate Action Executive Order",
                    "signing_date": "2024-03-15",
                    "publication_date": "2024-03-20",
                    "executive_order_number": 14100,
                    "html_url": "https://www.federalregister.gov/documents/2024/03/20/2024-12345/climate-action",
                    "agencies": [{"name": "EPA"}, {"name": "DOE"}],
                }
            ]
        }

        # Mock the search response
        respx.get(url).mock(return_value=Response(200, json=search_results))

        # Act
        documents = federal_register_client.search_documents(
            query="climate change", limit=10, full_content=False
        )

        # Assert
        assert len(documents) == 1
        doc = documents[0]
        assert doc.id == "2024-12345"
        assert doc.title == "Climate Action Executive Order"
        assert doc.date == "2024-03-20"  # Uses publication_date
        assert doc.type == "Executive Order"
        assert doc.source == "Federal Register"
        assert doc.content == ""  # No content in summary mode
        assert doc.metadata["summary_mode"] is True
        assert doc.metadata["agencies"] == ["EPA", "DOE"]

    @respx.mock
    def test_search_documents_with_full_content(
        self, federal_register_client, eo_metadata_payload, eo_raw_text
    ):
        """Test search with full content retrieval."""
        # Arrange
        search_url = "https://www.federalregister.gov/api/v1/documents"
        search_results = {
            "results": [
                {
                    "document_number": "2025-10800",
                    "title": "Leading the World in Supersonic Flight",
                    "signing_date": "2025-06-06",
                    "raw_text_url": "https://www.federalregister.gov/documents/full_text/text/2025/06/11/2025-10800.txt",
                }
            ]
        }

        doc_url = "https://www.federalregister.gov/api/v1/documents/2025-10800"
        text_url = "https://www.federalregister.gov/documents/full_text/text/2025/06/11/2025-10800.txt"

        # Mock all required API calls
        respx.get(search_url).mock(return_value=Response(200, json=search_results))
        respx.get(doc_url).mock(return_value=Response(200, json=eo_metadata_payload))
        respx.get(text_url).mock(return_value=Response(200, text=eo_raw_text))

        # Act
        documents = federal_register_client.search_documents(
            query="supersonic", limit=10, full_content=True
        )

        # Assert
        assert len(documents) == 1
        doc = documents[0]
        assert doc.id == "2025-10800"
        assert doc.title == "Leading the World in Supersonic Flight"
        assert "Executive Order 14304" in doc.content  # Full text retrieved
        assert doc.metadata["executive_order_number"] == "14304"

    @respx.mock
    def test_search_documents_with_date_filters(self, federal_register_client):
        """Test search with date range filtering."""
        # Arrange
        url = "https://www.federalregister.gov/api/v1/documents"
        empty_results = {"results": []}

        # Mock the search response
        route = respx.get(url).mock(return_value=Response(200, json=empty_results))

        # Act
        documents = federal_register_client.search_documents(
            query="test query", start_date="2024-01-01", end_date="2024-12-31", limit=10
        )

        # Assert - Check date parameters were included
        assert route.called
        request = route.calls.last.request
        params = dict(request.url.params)
        assert params["conditions[signing_date][gte]"] == "2024-01-01"
        assert params["conditions[signing_date][lte]"] == "2024-12-31"
        assert params["term"] == "test query"
        assert len(documents) == 0

    @respx.mock
    def test_search_documents_error_handling(self, federal_register_client):
        """Test search handles document processing errors gracefully."""
        # Arrange
        search_url = "https://www.federalregister.gov/api/v1/documents"
        doc_url = "https://www.federalregister.gov/api/v1/documents/2024-99999"

        search_results = {
            "results": [{"document_number": "2024-99999", "title": "Test Order"}]
        }

        # Mock search success but document fetch failure
        respx.get(search_url).mock(return_value=Response(200, json=search_results))
        respx.get(doc_url).mock(return_value=Response(500))  # Server error

        # Act
        documents = federal_register_client.search_documents(
            query="test", limit=10, full_content=True  # Try to get full content
        )

        # Assert - Should create partial document on error
        assert len(documents) == 1
        doc = documents[0]
        assert doc.id == "2024-99999"
        assert doc.metadata["summary_mode"] is True
        assert "error" in doc.metadata  # Error captured in metadata


class TestGetDocument:
    """Tests for the get_document method."""

    @respx.mock
    def test_get_document_happy_path(
        self, federal_register_client, eo_metadata_payload, eo_raw_text
    ):
        """Test building a complete Document with metadata and text."""
        # Arrange
        document_id = "2025-10800"
        doc_url = f"https://www.federalregister.gov/api/v1/documents/{document_id}"
        text_url = eo_metadata_payload["raw_text_url"]

        # Mock both API responses
        respx.get(doc_url).mock(return_value=Response(200, json=eo_metadata_payload))
        respx.get(text_url).mock(return_value=Response(200, text=eo_raw_text))

        # Act
        document = federal_register_client.get_document(document_id)

        # Assert - Document structure
        assert isinstance(document, Document)
        assert document.id == document_id
        assert document.title == "Leading the World in Supersonic Flight"
        assert document.type == "Executive Order"
        assert document.source == "Federal Register"
        assert document.date == "2025-06-11"  # Publication date

        # Assert - Content
        assert "Executive Order 14304" in document.content
        assert "supersonic flight" in document.content.lower()
        assert len(document.content) > 0

        # Assert - Metadata
        assert document.metadata["executive_order_number"] == "14304"
        assert document.metadata["signing_date"] == "2025-06-06"
        assert document.metadata["agencies"] == ["Executive Office of the President"]
        assert document.url == eo_metadata_payload["html_url"]

    @respx.mock
    def test_get_document_no_raw_text(self, federal_register_client):
        """Test Document creation when raw_text_url is missing."""
        # Arrange
        document_id = "2024-00001"
        doc_url = f"https://www.federalregister.gov/api/v1/documents/{document_id}"

        metadata = {
            "document_number": "2024-00001",
            "title": "Test Order",
            "publication_date": "2024-01-15",
            "executive_order_number": 14001,
            "html_url": "https://example.com/order",
            # No raw_text_url field
        }

        # Mock metadata response without raw_text_url
        respx.get(doc_url).mock(return_value=Response(200, json=metadata))

        # Act
        document = federal_register_client.get_document(document_id)

        # Assert
        assert document.id == document_id
        assert document.title == "Test Order"
        assert document.content == ""  # Empty content when no raw text
        assert document.metadata["executive_order_number"] == 14001

    @respx.mock
    def test_get_document_text_fetch_failure(
        self, federal_register_client, eo_metadata_payload
    ):
        """Test Document creation when text fetch fails but metadata succeeds."""
        # Arrange
        document_id = "2025-10800"
        doc_url = f"https://www.federalregister.gov/api/v1/documents/{document_id}"
        text_url = eo_metadata_payload["raw_text_url"]

        # Mock metadata success, text failure
        respx.get(doc_url).mock(return_value=Response(200, json=eo_metadata_payload))
        respx.get(text_url).mock(return_value=Response(404))

        # Act - Should not raise, but content will be empty
        # The implementation catches the error internally
        with pytest.raises(httpx.HTTPStatusError):
            # Note: Based on the implementation, this will actually raise
            # since get_executive_order_text doesn't catch the error
            document = federal_register_client.get_document(document_id)


class TestGetDocumentText:
    """Tests for the get_document_text method."""

    @respx.mock
    def test_get_document_text_happy_path(
        self, federal_register_client, eo_metadata_payload, eo_raw_text
    ):
        """Test retrieving just the text content of an executive order."""
        # Arrange
        document_id = "2025-10800"
        doc_url = f"https://www.federalregister.gov/api/v1/documents/{document_id}"
        text_url = eo_metadata_payload["raw_text_url"]

        # Mock the API responses
        respx.get(doc_url).mock(return_value=Response(200, json=eo_metadata_payload))
        respx.get(text_url).mock(return_value=Response(200, text=eo_raw_text))

        # Act
        text = federal_register_client.get_document_text(document_id)

        # Assert
        assert "Executive Order 14304" in text
        assert "Leading the World in Supersonic Flight" in text
        assert "<html>" not in text  # HTML cleaned

    @respx.mock
    def test_get_document_text_no_url(self, federal_register_client):
        """Test handling when document has no raw_text_url."""
        # Arrange
        document_id = "2024-00001"
        doc_url = f"https://www.federalregister.gov/api/v1/documents/{document_id}"

        metadata = {
            "document_number": "2024-00001",
            "title": "Test Order",
            # No raw_text_url
        }

        # Mock metadata without raw_text_url
        respx.get(doc_url).mock(return_value=Response(200, json=metadata))

        # Act
        text = federal_register_client.get_document_text(document_id)

        # Assert
        assert text == ""  # Empty string when no text available


class TestExtractBasicMetadata:
    """Tests for the extract_basic_metadata method."""

    def test_extract_metadata_complete(
        self, federal_register_client, eo_metadata_payload
    ):
        """Test metadata extraction with all fields present."""
        # Act
        metadata = federal_register_client.extract_basic_metadata(eo_metadata_payload)

        # Assert
        assert metadata["document_number"] == "2025-10800"
        assert metadata["title"] == "Leading the World in Supersonic Flight"
        assert metadata["executive_order_number"] == "14304"
        assert metadata["signing_date"] == "2025-06-06"
        assert metadata["president"] == "Unknown"  # No president in our fixture
        assert metadata["citation"] == "90 FR 24717"
        assert metadata["agencies"] == ["Executive Office of the President"]

    def test_extract_metadata_with_president_dict(self, federal_register_client):
        """Test metadata extraction with president as dictionary."""
        # Arrange
        order_data = {
            "document_number": "2024-00001",
            "title": "Test Order",
            "signing_date": "2024-01-15",
            "president": {"name": "Joe Biden", "term": "2021-2025"},
        }

        # Act
        metadata = federal_register_client.extract_basic_metadata(order_data)

        # Assert
        assert metadata["president"] == "Joe Biden"

    def test_extract_metadata_with_president_string(self, federal_register_client):
        """Test metadata extraction with president as string."""
        # Arrange
        order_data = {
            "document_number": "2024-00001",
            "title": "Test Order",
            "signing_date": "2024-01-15",
            "president": "Donald Trump",
        }

        # Act
        metadata = federal_register_client.extract_basic_metadata(order_data)

        # Assert
        assert metadata["president"] == "Donald Trump"

    def test_extract_metadata_minimal(self, federal_register_client):
        """Test metadata extraction with minimal fields."""
        # Arrange
        minimal_data = {"document_number": "2024-00001"}

        # Act
        metadata = federal_register_client.extract_basic_metadata(minimal_data)

        # Assert
        assert metadata["document_number"] == "2024-00001"
        assert metadata["title"] == ""
        assert metadata["executive_order_number"] is None
        assert metadata["president"] == "Unknown"
        assert metadata["agencies"] == []

    def test_extract_metadata_invalid_date(self, federal_register_client):
        """Test metadata extraction with invalid date format."""
        # Arrange
        order_data = {"document_number": "2024-00001", "signing_date": "not-a-date"}

        # Act
        metadata = federal_register_client.extract_basic_metadata(order_data)

        # Assert
        assert (
            metadata["signing_date"] == "not-a-date"
        )  # Returns original if parsing fails


class TestDateValidation:
    """Tests for date format validation."""

    def test_validate_date_format_valid(self, federal_register_client):
        """Test validation of correctly formatted dates."""
        assert federal_register_client.validate_date_format("2024-01-15") is True
        assert federal_register_client.validate_date_format("2024-12-31") is True
        assert federal_register_client.validate_date_format("2000-01-01") is True

    def test_validate_date_format_invalid(self, federal_register_client):
        """Test validation rejects incorrectly formatted dates."""
        assert federal_register_client.validate_date_format("01/15/2024") is False
        assert federal_register_client.validate_date_format("2024-1-15") is False
        assert federal_register_client.validate_date_format("2024/01/15") is False
        assert federal_register_client.validate_date_format("15-01-2024") is False
        assert federal_register_client.validate_date_format("January 15, 2024") is False
