"""
Unit tests for server/resources.py module.

Tests the polymorphic resource handling system that fetches full documents
from government APIs using the abstract base class interface.
"""

from unittest.mock import Mock, patch

import pytest

from governmentreporter.apis.base import Document
from governmentreporter.apis.court_listener import CourtListenerClient
from governmentreporter.apis.federal_register import FederalRegisterClient
from governmentreporter.server.resources import (
    format_document_resource,
    get_api_client,
    list_available_resources,
    parse_resource_uri,
    read_resource,
)


class TestParseResourceUri:
    """Test URI parsing for different resource types."""

    def test_parse_scotus_uri(self):
        """Test parsing Supreme Court opinion URI."""
        uri = "scotus://opinion/12345678"
        doc_type, doc_id = parse_resource_uri(uri)

        assert doc_type == "scotus"
        assert doc_id == "12345678"

    def test_parse_executive_order_uri(self):
        """Test parsing Executive Order URI."""
        uri = "eo://document/2024-12345"
        doc_type, doc_id = parse_resource_uri(uri)

        assert doc_type == "executive_order"
        assert doc_id == "2024-12345"

    def test_parse_invalid_uri_raises_error(self):
        """Test that invalid URI format raises ValueError."""
        invalid_uri = "invalid://unknown/123"

        with pytest.raises(ValueError, match="Unknown resource URI format"):
            parse_resource_uri(invalid_uri)


class TestGetApiClient:
    """Test API client factory function."""

    def test_get_scotus_client(self):
        """Test getting CourtListener client for SCOTUS documents."""
        client = get_api_client("scotus")

        assert isinstance(client, CourtListenerClient)

    def test_get_executive_order_client(self):
        """Test getting FederalRegister client for Executive Orders."""
        client = get_api_client("executive_order")

        assert isinstance(client, FederalRegisterClient)

    def test_get_client_invalid_type_raises_error(self):
        """Test that invalid document type raises ValueError."""
        with pytest.raises(ValueError, match="No client available"):
            get_api_client("invalid_type")


class TestFormatDocumentResource:
    """Test document formatting for MCP responses."""

    def test_format_scotus_document(self):
        """Test formatting a Supreme Court document."""
        document = Document(
            id="scotus_12345678",
            title="Test v. Example",
            date="2024-05-16",
            type="Supreme Court Opinion",
            source="CourtListener API",
            content="This is the full opinion text...",
            metadata={
                "case_name": "Test v. Example",
                "citation": "601 U.S. 123 (2024)",
                "vote_breakdown": "7-2",
                "legal_topics": ["Constitutional Law", "Commerce Clause"],
            },
            url="https://www.courtlistener.com/opinion/12345678/",
        )

        formatted = format_document_resource(document)

        # Check that all key components are present
        assert "# Test v. Example" in formatted
        assert "**Document ID:** scotus_12345678" in formatted
        assert "**Type:** Supreme Court Opinion" in formatted
        assert "**Date:** 2024-05-16" in formatted
        assert "## Document Content" in formatted
        assert "This is the full opinion text..." in formatted
        assert "## Metadata" in formatted
        assert "**citation:** 601 U.S. 123 (2024)" in formatted
        assert "**legal_topics:** Constitutional Law, Commerce Clause" in formatted

    def test_format_executive_order_document(self):
        """Test formatting an Executive Order document."""
        document = Document(
            id="eo_2024_12345",
            title="Executive Order 14067",
            date="2024-03-15",
            type="Executive Order",
            source="Federal Register API",
            content="By the authority vested in me...",
            metadata={
                "president": "Biden",
                "executive_order_number": "14067",
                "policy_topics": ["cryptocurrency", "financial regulation"],
                "impacted_agencies": ["Treasury", "SEC", "CFTC"],
            },
            url="https://www.federalregister.gov/documents/2024/03/15/2024-12345",
        )

        formatted = format_document_resource(document)

        # Check formatting
        assert "# Executive Order 14067" in formatted
        assert "**Document ID:** eo_2024_12345" in formatted
        assert "**Type:** Executive Order" in formatted
        assert "By the authority vested in me..." in formatted
        assert "**president:** Biden" in formatted
        assert "**policy_topics:** cryptocurrency, financial regulation" in formatted
        assert "**impacted_agencies:** Treasury, SEC, CFTC" in formatted


class TestReadResource:
    """Test full resource reading with mocked API clients."""

    @pytest.mark.asyncio
    async def test_read_scotus_resource(self):
        """Test reading a Supreme Court opinion resource."""
        # Mock the CourtListenerClient
        mock_document = Document(
            id="scotus_12345678",
            title="Mock v. Test",
            date="2024-01-01",
            type="Supreme Court Opinion",
            source="CourtListener API",
            content="Mock opinion content",
            metadata={"citation": "601 U.S. 999 (2024)"},
            url="https://example.com",
        )

        mock_client = Mock(spec=CourtListenerClient)
        mock_client.get_document.return_value = mock_document

        # Patch the get_api_client to return our mock
        with patch(
            "governmentreporter.server.resources.get_api_client",
            return_value=mock_client,
        ):
            # Read the resource
            result = await read_resource("scotus://opinion/12345678")

            # Verify the client was called correctly
            mock_client.get_document.assert_called_once_with("12345678")

            # Verify the result contains expected content
            assert "# Mock v. Test" in result
            assert "Mock opinion content" in result

    @pytest.mark.asyncio
    async def test_read_executive_order_resource(self):
        """Test reading an Executive Order resource."""
        # Mock the FederalRegisterClient
        mock_document = Document(
            id="eo_2024_12345",
            title="Executive Order 14999",
            date="2024-01-01",
            type="Executive Order",
            source="Federal Register API",
            content="Mock executive order content",
            metadata={"president": "Biden"},
            url="https://example.com",
        )

        mock_client = Mock(spec=FederalRegisterClient)
        mock_client.get_document.return_value = mock_document

        # Patch the get_api_client
        with patch(
            "governmentreporter.server.resources.get_api_client",
            return_value=mock_client,
        ):
            # Read the resource
            result = await read_resource("eo://document/2024-12345")

            # Verify
            mock_client.get_document.assert_called_once_with("2024-12345")
            assert "# Executive Order 14999" in result
            assert "Mock executive order content" in result

    @pytest.mark.asyncio
    async def test_read_resource_invalid_uri(self):
        """Test that invalid URI raises ValueError."""
        with pytest.raises(ValueError):
            await read_resource("invalid://bad/uri")

    @pytest.mark.asyncio
    async def test_read_resource_api_error(self):
        """Test that API errors are properly propagated."""
        # Mock client that raises an error
        mock_client = Mock(spec=CourtListenerClient)
        mock_client.get_document.side_effect = Exception("API connection failed")

        # Should raise exception with helpful message
        with patch(
            "governmentreporter.server.resources.get_api_client",
            return_value=mock_client,
        ):
            with pytest.raises(Exception, match="Failed to retrieve resource"):
                await read_resource("scotus://opinion/12345678")


class TestListAvailableResources:
    """Test resource listing for LLM discovery."""

    def test_list_returns_resources(self):
        """Test that list_available_resources returns Resource objects."""
        resources = list_available_resources()

        assert len(resources) == 2
        assert all(hasattr(r, "uri") for r in resources)
        assert all(hasattr(r, "name") for r in resources)
        assert all(hasattr(r, "description") for r in resources)

    def test_scotus_resource_in_list(self):
        """Test that SCOTUS resource template is included."""
        resources = list_available_resources()

        scotus_resource = next(
            (r for r in resources if "scotus://" in str(r.uri)), None
        )
        assert scotus_resource is not None
        assert "Supreme Court" in scotus_resource.name
        assert "opinion_id" in str(scotus_resource.uri)

    def test_executive_order_resource_in_list(self):
        """Test that Executive Order resource template is included."""
        resources = list_available_resources()

        eo_resource = next((r for r in resources if "eo://" in str(r.uri)), None)
        assert eo_resource is not None
        assert "Executive Order" in eo_resource.name
        assert "document_number" in str(eo_resource.uri)
