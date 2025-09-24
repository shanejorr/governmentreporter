"""
Shared test fixtures and configuration for GovernmentReporter tests.

This module provides reusable fixtures and mocks for testing the GovernmentReporter
application. It centralizes common test dependencies to avoid duplication across
test files and ensures consistent test setup.

Key Fixtures:
    - Mock clients for external services (OpenAI, Qdrant)
    - Sample data objects for testing
    - Configuration overrides for testing
    - Temporary file/directory helpers

Python Learning Notes:
    - conftest.py is automatically discovered by pytest
    - Fixtures defined here are available to all tests without import
    - @pytest.fixture decorator marks functions as fixtures
    - Fixtures can be injected into tests by name as parameters
    - yield in fixtures allows teardown code after the test
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, ScoredPoint

from governmentreporter.apis.base import Document
from governmentreporter.database.qdrant import Document as QdrantDocument
from governmentreporter.database.qdrant import SearchResult


@pytest.fixture
def mock_openai_client():
    """
    Mock OpenAI client for testing embedding and metadata generation.

    This fixture provides a mock OpenAI client that simulates the behavior
    of the real OpenAI API without making actual API calls. It includes
    mocked responses for embeddings and chat completions.

    Returns:
        Mock: Configured mock OpenAI client with preset responses

    Usage:
        def test_generate_embeddings(mock_openai_client):
            # mock_openai_client is automatically injected
            result = generate_embeddings("test text", mock_openai_client)
            assert len(result) == 1536  # OpenAI embedding dimension

    Python Learning Notes:
        - Mock objects simulate real objects for testing
        - MagicMock automatically creates attributes as accessed
        - return_value sets what a mocked method returns
    """
    mock_client = MagicMock(spec=OpenAI)

    # Mock embeddings.create response
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [
        MagicMock(embedding=[0.1] * 1536)  # OpenAI text-embedding-3-small dimension
    ]
    mock_client.embeddings.create.return_value = mock_embedding_response

    # Mock chat.completions.create response for metadata generation
    mock_chat_response = MagicMock()
    mock_chat_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"summary": "Test summary", "topics": ["law", "policy"], "entities": ["Supreme Court"]}'
            )
        )
    ]
    mock_client.chat.completions.create.return_value = mock_chat_response

    return mock_client


@pytest.fixture
def mock_qdrant_client():
    """
    Mock Qdrant client for testing vector database operations.

    This fixture provides a mock Qdrant client that simulates vector database
    operations without requiring an actual Qdrant instance. It includes mocked
    responses for search, upsert, and retrieval operations.

    Returns:
        Mock: Configured mock Qdrant client with preset responses

    Usage:
        def test_store_document(mock_qdrant_client):
            doc = create_document()
            store_document(doc, mock_qdrant_client)
            mock_qdrant_client.upsert.assert_called_once()

    Python Learning Notes:
        - spec parameter ensures mock has same interface as real class
        - assert_called_once() verifies a method was called exactly once
        - Mock.call_args gives access to arguments passed to mock
    """
    mock_client = MagicMock(spec=QdrantClient)

    # Mock search response
    mock_search_results = [
        ScoredPoint(
            id="test-id-1",
            score=0.95,
            payload={
                "text": "Test document content",
                "title": "Test Document",
                "date": "2024-01-01",
                "metadata": {"type": "scotus_opinion"}
            },
            version=1  # Required field for ScoredPoint
        )
    ]
    mock_client.search.return_value = mock_search_results

    # Mock collection operations
    mock_client.create_collection.return_value = True
    mock_client.collection_exists.return_value = True
    mock_client.upsert.return_value = True
    mock_client.retrieve.return_value = [
        MagicMock(
            id="test-id-1",
            payload={"text": "Retrieved document", "metadata": {}}
        )
    ]

    return mock_client


@pytest.fixture
def sample_document():
    """
    Create a sample Document object for testing.

    This fixture provides a fully populated Document instance that can be used
    across tests. It represents a typical Supreme Court opinion with all
    required and optional fields populated.

    Returns:
        Document: Sample document with test data

    Usage:
        def test_process_document(sample_document):
            result = process_document(sample_document)
            assert result.id == sample_document.id

    Python Learning Notes:
        - Fixtures can return any Python object
        - Document is imported from the actual codebase
        - Consistent test data helps catch regressions
    """
    return Document(
        id="test-doc-123",
        title="Test Case v. United States",
        date="2024-01-15",
        type="scotus_opinion",
        source="courtlistener",
        content="""This is a test Supreme Court opinion.

        The Court holds that testing is important for software quality.

        In reaching this decision, we consider the following factors:
        1. Comprehensive testing prevents bugs
        2. Unit tests provide fast feedback
        3. Mock objects isolate components

        Therefore, the judgment is affirmed.""",
        metadata={
            "docket_number": "23-456",
            "court": "SCOTUS",
            "judges": ["Roberts", "Thomas", "Alito"],
            "decision_type": "unanimous",
            "citations": ["123 U.S. 456", "789 F.3d 012"],
        },
        url="https://www.courtlistener.com/opinion/test-doc-123/"
    )


@pytest.fixture
def sample_executive_order():
    """
    Create a sample Executive Order document for testing.

    This fixture provides an Executive Order document instance for testing
    Federal Register API functionality and executive order processing.

    Returns:
        Document: Sample executive order with test data

    Python Learning Notes:
        - Multiple fixtures can provide different test scenarios
        - Fixtures help maintain DRY (Don't Repeat Yourself) principle
    """
    return Document(
        id="2024-12345",
        title="Executive Order on Testing Software Quality",
        date="2024-01-20",
        type="executive_order",
        source="federal_register",
        content="""EXECUTIVE ORDER

        By the authority vested in me as President by the Constitution and the
        laws of the United States of America, it is hereby ordered as follows:

        Section 1. Purpose. This order establishes requirements for software testing
        in federal systems to ensure quality and reliability.

        Sec. 2. Policy. It is the policy of the United States to promote comprehensive
        testing practices including unit tests, integration tests, and end-to-end tests.

        Sec. 3. Implementation. All federal agencies shall implement testing frameworks
        within 180 days of this order.""",
        metadata={
            "executive_order_number": "14123",
            "president": "Test President",
            "signing_date": "2024-01-20",
            "federal_register_number": "2024-12345",
            "agencies": ["All Federal Agencies"],
        },
        url="https://www.federalregister.gov/documents/2024/01/20/2024-12345/"
    )


@pytest.fixture
def sample_qdrant_document():
    """
    Create a sample Qdrant Document for database testing.

    This fixture provides a Document instance as used by the Qdrant database
    module, including embedding vectors.

    Returns:
        QdrantDocument: Document with embedding for Qdrant storage

    Python Learning Notes:
        - Different modules may have their own Document classes
        - Name aliasing (as QdrantDocument) prevents naming conflicts
    """
    return QdrantDocument(
        id="qdrant-test-123",
        text="This is test content for Qdrant storage and retrieval.",
        embedding=[0.1] * 1536,  # Mock embedding vector
        metadata={
            "title": "Test Qdrant Document",
            "date": "2024-01-15",
            "type": "test_document",
            "source": "test_fixture"
        }
    )


@pytest.fixture
def temp_config_file():
    """
    Create a temporary configuration file for testing.

    This fixture creates a temporary YAML configuration file that is
    automatically cleaned up after the test completes.

    Yields:
        Path: Path to temporary configuration file

    Usage:
        def test_load_config(temp_config_file):
            config = load_config(temp_config_file)
            assert config['database']['path'] == '/tmp/test_db'

    Python Learning Notes:
        - yield allows cleanup code after test completion
        - tempfile module provides secure temporary file creation
        - Context managers (with statement) ensure cleanup
    """
    config_content = """
database:
  path: /tmp/test_db
  collection: test_collection

openai:
  model: gpt-4
  embedding_model: text-embedding-3-small

apis:
  court_listener:
    base_url: https://api.courtlistener.com
  federal_register:
    base_url: https://api.federalregister.gov

processing:
  chunk_size: 500
  overlap: 50
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup after test
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def mock_environment_variables():
    """
    Set mock environment variables for testing.

    This fixture temporarily sets environment variables needed for testing
    and automatically cleans them up after the test completes.

    Yields:
        dict: Dictionary of set environment variables

    Python Learning Notes:
        - os.environ is a dict-like object for environment variables
        - Cleanup in fixtures ensures tests don't affect each other
        - monkeypatch is pytest's way to temporarily modify objects
    """
    env_vars = {
        'OPENAI_API_KEY': 'test-api-key-123',
        'COURT_LISTENER_API_TOKEN': 'test-court-listener-token',
        'QDRANT_HOST': 'localhost',
        'QDRANT_PORT': '6333',
        'LOG_LEVEL': 'DEBUG'
    }

    # Store original values
    original_values = {}
    for key, value in env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value

    yield env_vars

    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def mock_httpx_client():
    """
    Mock HTTPX client for testing HTTP requests.

    This fixture provides a mock HTTP client for testing API calls without
    making actual network requests.

    Returns:
        Mock: Configured mock HTTPX client

    Python Learning Notes:
        - AsyncMock is used for async methods
        - Side effects can simulate different responses
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"id": "1", "title": "Test Result 1"},
            {"id": "2", "title": "Test Result 2"}
        ]
    }
    mock_response.text = '{"status": "success"}'
    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response

    return mock_client


@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Reset singleton instances between tests.

    This fixture automatically runs before each test to ensure singleton
    instances don't carry state between tests. The autouse=True parameter
    means it runs without being explicitly requested.

    Python Learning Notes:
        - autouse=True makes fixture run for all tests automatically
        - Singletons can cause test interference if not reset
        - This ensures test isolation
    """
    # Reset any singleton instances or global state
    # This will be expanded as needed when singletons are identified
    pass


# Markers for test categorization
pytest.mark.unit = pytest.mark.mark(name="unit")
pytest.mark.integration = pytest.mark.mark(name="integration")
pytest.mark.slow = pytest.mark.mark(name="slow")
pytest.mark.external = pytest.mark.mark(name="external")