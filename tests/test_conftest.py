"""
Test file to verify that conftest fixtures are working correctly.

This test file validates that all fixtures defined in conftest.py are
properly configured and can be successfully injected into tests.

Python Learning Notes:
    - Tests can request fixtures by including them as parameters
    - pytest automatically injects fixture return values
    - assert statements verify expected conditions
"""

import pytest
from governmentreporter.apis.base import Document
from governmentreporter.database.qdrant import Document as QdrantDocument


def test_mock_openai_client_fixture(mock_openai_client):
    """
    Test that the mock OpenAI client fixture is properly configured.

    This test verifies that the mock OpenAI client has the expected
    methods and returns appropriate mock responses.

    Python Learning Notes:
        - Fixtures are injected by parameter name
        - hasattr() checks if object has an attribute
        - Mock objects track how they're used
    """
    # Test that embeddings.create method exists and returns expected structure
    response = mock_openai_client.embeddings.create(
        input="test text", model="text-embedding-3-small"
    )
    assert response.data[0].embedding is not None
    assert len(response.data[0].embedding) == 1536

    # Test chat completions for metadata generation
    chat_response = mock_openai_client.chat.completions.create(
        model="gpt-4", messages=[{"role": "user", "content": "test"}]
    )
    assert chat_response.choices[0].message.content is not None


def test_mock_qdrant_client_fixture(mock_qdrant_client):
    """
    Test that the mock Qdrant client fixture is properly configured.

    This test verifies that the mock Qdrant client has the expected
    methods and returns appropriate mock responses.
    """
    # Test search functionality
    results = mock_qdrant_client.search(
        collection_name="test", query_vector=[0.1] * 1536, limit=5
    )
    assert len(results) > 0
    assert results[0].score > 0

    # Test collection operations
    assert mock_qdrant_client.collection_exists("test") is True
    assert mock_qdrant_client.upsert("test", points=[]) is True


def test_sample_document_fixture(sample_document):
    """
    Test that the sample document fixture provides valid Document instance.

    This test ensures the sample document has all required fields
    properly populated for use in other tests.
    """
    assert isinstance(sample_document, Document)
    assert sample_document.id == "test-doc-123"
    assert sample_document.title == "Test Case v. United States"
    assert sample_document.type == "scotus_opinion"
    assert sample_document.content is not None
    assert sample_document.metadata is not None
    assert "docket_number" in sample_document.metadata


def test_sample_executive_order_fixture(sample_executive_order):
    """
    Test that the sample executive order fixture is properly configured.
    """
    assert isinstance(sample_executive_order, Document)
    assert sample_executive_order.type == "executive_order"
    assert sample_executive_order.source == "federal_register"
    assert "Section 1" in sample_executive_order.content


def test_sample_qdrant_document_fixture(sample_qdrant_document):
    """
    Test that the sample Qdrant document fixture is properly configured.
    """
    assert isinstance(sample_qdrant_document, QdrantDocument)
    assert sample_qdrant_document.id == "qdrant-test-123"
    assert len(sample_qdrant_document.embedding) == 1536
    assert sample_qdrant_document.metadata is not None


def test_temp_config_file_fixture(temp_config_file):
    """
    Test that the temporary config file fixture creates and cleans up properly.
    """
    import yaml

    assert temp_config_file.exists()

    with open(temp_config_file, "r") as f:
        config = yaml.safe_load(f)

    assert "database" in config
    assert config["database"]["path"] == "/tmp/test_db"
    assert "openai" in config
    assert "apis" in config


def test_mock_environment_variables_fixture(mock_environment_variables):
    """
    Test that environment variables are properly set by the fixture.
    """
    import os

    assert os.environ.get("OPENAI_API_KEY") == "test-api-key-123"
    assert os.environ.get("COURT_LISTENER_API_TOKEN") == "test-court-listener-token"
    assert "OPENAI_API_KEY" in mock_environment_variables


def test_mock_httpx_client_fixture(mock_httpx_client):
    """
    Test that the mock HTTPX client fixture is properly configured.
    """
    response = mock_httpx_client.get("https://test.com/api")
    assert response.status_code == 200
    assert "results" in response.json()
    assert len(response.json()["results"]) == 2


def test_multiple_fixtures_together(
    sample_document, mock_openai_client, mock_qdrant_client
):
    """
    Test that multiple fixtures can be used together in a single test.

    This verifies that fixtures don't interfere with each other and can
    be composed as needed for complex test scenarios.
    """
    # All fixtures should be properly injected
    assert sample_document is not None
    assert mock_openai_client is not None
    assert mock_qdrant_client is not None

    # Each should work independently
    assert sample_document.id == "test-doc-123"
    assert mock_openai_client.embeddings.create is not None
    assert mock_qdrant_client.search is not None
