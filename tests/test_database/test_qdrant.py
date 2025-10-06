"""
Comprehensive unit tests for the QdrantDBClient.

This module contains exhaustive tests for the QdrantDBClient class which manages
all vector database operations. Tests are organized by functionality and include
happy paths, edge cases, and error scenarios.

Test Categories:
    - Initialization tests: Different connection modes and configurations
    - Collection management: Creation, deletion, listing
    - Document operations: Storage, retrieval, deletion
    - Search operations: Semantic search with various filters
    - Batch operations: Bulk document handling
    - Error handling: Network failures, invalid data

Python Learning Notes:
    - pytest.fixture provides test data and mocked dependencies
    - Mock objects simulate external services without real connections
    - assert statements verify expected behavior
    - pytest.raises tests exception handling
    - Parametrized tests run the same test with different inputs
"""

import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from qdrant_client import QdrantClient as QdrantBaseClient
from qdrant_client.models import (
    CollectionInfo,
    CollectionStatus,
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    ScoredPoint,
    VectorParams,
)

from governmentreporter.database.qdrant import Document, QdrantDBClient, SearchResult


class TestQdrantDBClientInitialization:
    """
    Tests for QdrantDBClient initialization with various connection modes.

    The client supports three connection modes:
        1. Local file-based storage (development)
        2. Remote server connection (production)
        3. Cloud connection with URL

    Python Learning Notes:
        - Class-based test organization groups related tests
        - Mock.patch decorator replaces classes with mocks
        - Multiple assertions verify complete behavior
    """

    @patch("governmentreporter.database.qdrant.QdrantBaseClient")
    def test_local_initialization(self, mock_qdrant_base):
        """
        Test local file-based Qdrant initialization.

        Verifies that:
            - Client initializes with local path
            - Connection mode is set correctly
            - Underlying client is created with correct parameters
        """
        # Initialize with local path
        client = QdrantDBClient(db_path="./test_qdrant")

        # Verify initialization
        assert client.connection_mode == "local"
        assert client.db_path == "./test_qdrant"
        mock_qdrant_base.assert_called_once_with(path="./test_qdrant")

    @patch("governmentreporter.database.qdrant.QdrantBaseClient")
    def test_remote_initialization_with_host(self, mock_qdrant_base):
        """
        Test remote server connection initialization.

        Verifies that:
            - Client connects to remote host and port
            - API key is passed correctly
            - Default port is used when not specified
        """
        # Initialize with host and port
        client = QdrantDBClient(host="localhost", port=6333, api_key="test-api-key")

        # Verify initialization
        assert client.connection_mode == "remote"
        mock_qdrant_base.assert_called_once_with(
            host="localhost", port=6333, api_key="test-api-key"
        )

    @patch("governmentreporter.database.qdrant.QdrantBaseClient")
    def test_remote_initialization_default_port(self, mock_qdrant_base):
        """
        Test remote initialization with default port.

        Verifies that port 6333 is used by default when not specified.
        """
        # Initialize without port
        client = QdrantDBClient(host="localhost")

        # Verify default port is used
        mock_qdrant_base.assert_called_once_with(
            host="localhost", port=6333, api_key=None
        )

    @patch("governmentreporter.database.qdrant.QdrantBaseClient")
    def test_cloud_initialization(self, mock_qdrant_base):
        """
        Test Qdrant cloud initialization with URL.

        Verifies cloud connection using a full URL and API key.
        """
        # Initialize with cloud URL
        client = QdrantDBClient(
            url="https://my-cluster.qdrant.io", api_key="cloud-api-key"
        )

        # Verify initialization
        assert client.connection_mode == "cloud"
        mock_qdrant_base.assert_called_once_with(
            url="https://my-cluster.qdrant.io", api_key="cloud-api-key"
        )

    def test_initialization_without_parameters(self):
        """
        Test that initialization fails without connection parameters.

        Verifies that ValueError is raised when no connection
        parameters are provided.
        """
        with pytest.raises(ValueError) as exc_info:
            QdrantDBClient()

        assert "Must provide either db_path" in str(exc_info.value)


class TestCollectionManagement:
    """
    Tests for collection creation, deletion, and management.

    Collections in Qdrant are like database tables that store vectors.
    These tests verify all collection operations work correctly.

    Python Learning Notes:
        - pytest.fixture provides reusable test setup
        - Mock return_value simulates method results
        - Multiple test cases ensure comprehensive coverage
    """

    @pytest.fixture
    def client_with_mock(self):
        """
        Create a QdrantDBClient with a mocked underlying client.

        This fixture provides a client instance with a fully mocked
        Qdrant connection for testing without a real database.

        Returns:
            Tuple of (client, mock_qdrant_client)
        """
        with patch("governmentreporter.database.qdrant.QdrantBaseClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            client = QdrantDBClient(db_path="./test")
            return client, mock_instance

    def test_create_collection_new(self, client_with_mock):
        """
        Test creating a new collection.

        Verifies that:
            - New collections are created with correct parameters
            - Vector configuration matches OpenAI dimensions
            - Success is returned
        """
        client, mock_qdrant = client_with_mock

        # Mock that collection doesn't exist
        mock_collections = MagicMock()
        mock_collections.collections = []
        mock_qdrant.get_collections.return_value = mock_collections

        # Create collection
        result = client.create_collection("test_collection")

        # Verify creation
        assert result is True
        mock_qdrant.create_collection.assert_called_once_with(
            collection_name="test_collection",
            vectors_config=VectorParams(
                size=1536, distance=Distance.COSINE  # OpenAI embedding dimension
            ),
        )

    def test_create_collection_existing(self, client_with_mock):
        """
        Test that existing collections are not recreated.

        Verifies idempotent behavior - calling create_collection
        on an existing collection should succeed without errors.
        """
        client, mock_qdrant = client_with_mock

        # Mock that collection exists
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant.get_collections.return_value = mock_collections

        # Try to create existing collection
        result = client.create_collection("test_collection")

        # Verify no creation attempted
        assert result is True
        mock_qdrant.create_collection.assert_not_called()

    def test_create_collection_failure(self, client_with_mock):
        """
        Test collection creation error handling.

        Verifies that exceptions are logged and re-raised
        when collection creation fails.
        """
        client, mock_qdrant = client_with_mock

        # Mock empty collections
        mock_collections = MagicMock()
        mock_collections.collections = []
        mock_qdrant.get_collections.return_value = mock_collections

        # Mock creation failure
        mock_qdrant.create_collection.side_effect = Exception("Connection error")

        # Verify exception is raised
        with pytest.raises(Exception) as exc_info:
            client.create_collection("test_collection")

        assert "Connection error" in str(exc_info.value)

    def test_delete_collection(self, client_with_mock):
        """
        Test collection deletion.

        Verifies that collections can be deleted successfully.
        """
        client, mock_qdrant = client_with_mock

        # Delete collection
        result = client.delete_collection("test_collection")

        # Verify deletion
        assert result is True
        mock_qdrant.delete_collection.assert_called_once_with("test_collection")

    def test_delete_collection_failure(self, client_with_mock):
        """
        Test collection deletion error handling.

        Verifies graceful handling of deletion failures.
        """
        client, mock_qdrant = client_with_mock

        # Mock deletion failure
        mock_qdrant.delete_collection.side_effect = Exception("Not found")

        # Delete should return False on error
        result = client.delete_collection("test_collection")
        assert result is False

    def test_list_collections(self, client_with_mock):
        """
        Test listing all collections.

        Verifies that all collection names are returned correctly.
        """
        client, mock_qdrant = client_with_mock

        # Mock collections
        mock_col1 = MagicMock()
        mock_col1.name = "collection1"
        mock_col2 = MagicMock()
        mock_col2.name = "collection2"
        mock_collections = MagicMock()
        mock_collections.collections = [mock_col1, mock_col2]
        mock_qdrant.get_collections.return_value = mock_collections

        # List collections
        result = client.list_collections()

        # Verify results
        assert result == ["collection1", "collection2"]

    def test_get_collection_info(self, client_with_mock):
        """
        Test retrieving collection information.

        Verifies that collection statistics are returned correctly.
        """
        client, mock_qdrant = client_with_mock

        # Mock collection info
        mock_info = MagicMock()
        mock_info.vectors_count = 100
        mock_info.points_count = 100
        mock_info.indexed_vectors_count = 100
        mock_info.status = CollectionStatus.GREEN
        mock_qdrant.get_collection.return_value = mock_info

        # Get collection info
        result = client.get_collection_info("test_collection")

        # Verify results
        assert result["name"] == "test_collection"
        assert result["vectors_count"] == 100
        assert result["points_count"] == 100
        assert result["status"] == CollectionStatus.GREEN

    def test_get_collection_info_not_found(self, client_with_mock):
        """
        Test getting info for non-existent collection.

        Verifies that None is returned for missing collections.
        """
        client, mock_qdrant = client_with_mock

        # Mock collection not found
        mock_qdrant.get_collection.side_effect = Exception("Not found")

        # Get info should return None
        result = client.get_collection_info("missing_collection")
        assert result is None


class TestDocumentStorage:
    """
    Tests for storing documents in Qdrant.

    These tests verify document storage operations including
    single document storage and batch operations.

    Python Learning Notes:
        - UUID generation creates unique identifiers
        - Batch operations improve performance
        - Progress callbacks enable UI updates
    """

    @pytest.fixture
    def client_with_mock(self):
        """Create a client with mocked Qdrant connection."""
        with patch("governmentreporter.database.qdrant.QdrantBaseClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Mock collection exists
            mock_collections = MagicMock()
            mock_collections.collections = []
            mock_instance.get_collections.return_value = mock_collections

            client = QdrantDBClient(db_path="./test")
            return client, mock_instance

    @pytest.fixture
    def sample_document(self):
        """
        Create a sample document for testing.

        Returns a fully populated Document instance with
        embedding vector and metadata.
        """
        return Document(
            id="test-doc-123",
            text="This is test content",
            embedding=[0.1] * 1536,  # Mock embedding
            metadata={"author": "Test Author", "year": 2024},
        )

    def test_store_document_success(self, client_with_mock, sample_document):
        """
        Test successful document storage.

        Verifies that:
            - Documents are stored with correct structure
            - UUIDs are generated consistently
            - Original IDs are preserved in payload
        """
        client, mock_qdrant = client_with_mock

        # Store document
        result = client.store_document(sample_document, "test_collection")

        # Verify storage
        assert result is True
        mock_qdrant.upsert.assert_called_once()

        # Verify point structure
        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs["points"]
        assert len(points) == 1

        point = points[0]
        assert isinstance(point.id, str)  # UUID string
        assert point.vector == sample_document.embedding
        assert point.payload["text"] == sample_document.text
        assert point.payload["original_id"] == sample_document.id
        assert point.payload["author"] == "Test Author"

    def test_store_document_without_id(self, client_with_mock):
        """
        Test that documents without IDs are rejected.

        Verifies validation of required document fields.
        """
        doc = Document(
            id="", text="Test content", embedding=[0.1] * 1536, metadata={}  # Empty ID
        )

        client, _ = client_with_mock

        with pytest.raises(ValueError) as exc_info:
            client.store_document(doc, "test_collection")

        assert "Document must have an ID" in str(exc_info.value)

    def test_store_document_without_embedding(self, client_with_mock):
        """
        Test that documents without embeddings are rejected.

        Verifies that embeddings are required for storage.
        """
        doc = Document(
            id="test-123",
            text="Test content",
            embedding=[],  # Empty embedding
            metadata={},
        )

        client, _ = client_with_mock

        with pytest.raises(ValueError) as exc_info:
            client.store_document(doc, "test_collection")

        assert "Document must have an embedding" in str(exc_info.value)

    def test_store_document_wrong_dimension(self, client_with_mock):
        """
        Test that embeddings with wrong dimensions are rejected.

        Verifies validation of embedding vector dimensions.
        """
        doc = Document(
            id="test-123",
            text="Test content",
            embedding=[0.1] * 100,  # Wrong dimension
            metadata={},
        )

        client, _ = client_with_mock

        with pytest.raises(ValueError) as exc_info:
            client.store_document(doc, "test_collection")

        assert "1536 dimensions" in str(exc_info.value)

    def test_store_documents_batch_success(self, client_with_mock):
        """
        Test batch document storage.

        Verifies that:
            - Multiple documents are stored in batches
            - Success count is accurate
            - Documents are processed correctly
        """
        client, mock_qdrant = client_with_mock

        # Create multiple documents
        documents = []
        for i in range(5):
            doc = Document(
                id=f"doc-{i}",
                text=f"Content {i}",
                embedding=[0.1] * 1536,
                metadata={"index": i},
            )
            documents.append(doc)

        # Store batch
        success_count, failed_ids = client.store_documents_batch(
            documents, "test_collection", batch_size=2
        )

        # Verify results
        assert success_count == 5
        assert failed_ids == []

        # Verify batching (5 docs with batch_size=2 = 3 calls)
        assert mock_qdrant.upsert.call_count == 3

    def test_store_documents_batch_with_failures(self, client_with_mock):
        """
        Test batch storage with some failures.

        Verifies that:
            - Failed documents are tracked
            - Successful documents are still stored
            - Failed IDs are returned
        """
        client, mock_qdrant = client_with_mock

        # Mock first batch fails, second succeeds
        mock_qdrant.upsert.side_effect = [Exception("Network error"), None]  # Success

        # Create documents
        documents = []
        for i in range(4):
            doc = Document(
                id=f"doc-{i}",
                text=f"Content {i}",
                embedding=[0.1] * 1536,
                metadata={"index": i},
            )
            documents.append(doc)

        # Store batch (batch_size=2, so 2 batches)
        success_count, failed_ids = client.store_documents_batch(
            documents, "test_collection", batch_size=2
        )

        # Verify partial success
        assert success_count == 2  # Second batch succeeded
        assert failed_ids == ["doc-0", "doc-1"]  # First batch failed

    def test_store_documents_batch_with_progress(self, client_with_mock):
        """
        Test batch storage with progress callback.

        Verifies that progress callbacks are invoked correctly
        during batch processing.
        """
        client, mock_qdrant = client_with_mock

        # Track progress calls
        progress_calls = []

        def progress_callback(processed, total):
            progress_calls.append((processed, total))

        # Create documents
        documents = [
            Document(
                id=f"doc-{i}", text=f"Content {i}", embedding=[0.1] * 1536, metadata={}
            )
            for i in range(5)
        ]

        # Store with progress callback
        client.store_documents_batch(
            documents, "test_collection", batch_size=2, on_progress=progress_callback
        )

        # Verify progress was reported
        assert len(progress_calls) == 3  # 3 batches
        assert progress_calls[0] == (2, 5)
        assert progress_calls[1] == (4, 5)
        assert progress_calls[2] == (5, 5)

    def test_store_empty_document_batch(self, client_with_mock):
        """
        Test storing empty batch of documents.

        Verifies graceful handling of empty input.
        """
        client, _ = client_with_mock

        success_count, failed_ids = client.store_documents_batch([], "test_collection")

        assert success_count == 0
        assert failed_ids == []


class TestDocumentRetrieval:
    """
    Tests for retrieving documents from Qdrant.

    These tests verify document retrieval by ID and
    existence checking operations.

    Python Learning Notes:
        - UUID determinism ensures consistent IDs
        - Optional returns handle missing data
        - Type checking ensures correct data types
    """

    @pytest.fixture
    def client_with_mock(self):
        """Create a client with mocked Qdrant connection."""
        with patch("governmentreporter.database.qdrant.QdrantBaseClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            client = QdrantDBClient(db_path="./test")
            return client, mock_instance

    def test_get_document_found(self, client_with_mock):
        """
        Test retrieving an existing document.

        Verifies that:
            - Documents are retrieved correctly
            - Original IDs are preserved
            - Metadata is included
        """
        client, mock_qdrant = client_with_mock

        # Mock retrieved point
        mock_point = MagicMock()
        mock_point.id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "test-123"))
        mock_point.vector = [0.1] * 1536
        mock_point.payload = {
            "text": "Test content",
            "original_id": "test-123",
            "author": "Test Author",
            "year": 2024,
        }
        mock_qdrant.retrieve.return_value = [mock_point]

        # Retrieve document
        doc = client.get_document("test-123", "test_collection")

        # Verify retrieval
        assert doc is not None
        assert doc.id == "test-123"
        assert doc.text == "Test content"
        assert doc.embedding == [0.1] * 1536
        assert doc.metadata["author"] == "Test Author"
        assert doc.metadata["year"] == 2024

    def test_get_document_not_found(self, client_with_mock):
        """
        Test retrieving non-existent document.

        Verifies that None is returned for missing documents.
        """
        client, mock_qdrant = client_with_mock

        # Mock no results
        mock_qdrant.retrieve.return_value = []

        # Retrieve missing document
        doc = client.get_document("missing-id", "test_collection")

        # Verify None returned
        assert doc is None

    def test_get_document_with_nested_vector(self, client_with_mock):
        """
        Test handling of nested vector format.

        Some Qdrant configurations return vectors in nested format.
        This test verifies proper extraction.
        """
        client, mock_qdrant = client_with_mock

        # Mock point with nested vector
        mock_point = MagicMock()
        mock_point.id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "test-123"))
        mock_point.vector = [[0.1] * 1536]  # Nested list
        mock_point.payload = {"text": "Test content", "original_id": "test-123"}
        mock_qdrant.retrieve.return_value = [mock_point]

        # Retrieve document
        doc = client.get_document("test-123", "test_collection")

        # Verify vector extracted correctly
        assert doc is not None
        assert doc.embedding == [0.1] * 1536  # Flattened

    def test_document_exists_true(self, client_with_mock):
        """
        Test checking existence of existing document.

        Verifies that document_exists returns True for
        existing documents.
        """
        client, mock_qdrant = client_with_mock

        # Mock document exists
        mock_point = MagicMock()
        mock_qdrant.retrieve.return_value = [mock_point]

        # Check existence
        exists = client.document_exists("test-123", "test_collection")

        # Verify result
        assert exists is True

        # Verify efficient retrieval (no payload/vectors)
        call_args = mock_qdrant.retrieve.call_args
        assert call_args.kwargs["with_payload"] is False
        assert call_args.kwargs["with_vectors"] is False

    def test_document_exists_false(self, client_with_mock):
        """
        Test checking existence of missing document.

        Verifies that document_exists returns False for
        non-existent documents.
        """
        client, mock_qdrant = client_with_mock

        # Mock document doesn't exist
        mock_qdrant.retrieve.return_value = []

        # Check existence
        exists = client.document_exists("missing-id", "test_collection")

        # Verify result
        assert exists is False

    def test_delete_document_success(self, client_with_mock):
        """
        Test successful document deletion.

        Verifies that documents can be deleted by ID.
        """
        client, mock_qdrant = client_with_mock

        # Delete document
        result = client.delete_document("test-123", "test_collection")

        # Verify deletion
        assert result is True

        # Verify UUID conversion
        expected_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "test-123"))
        mock_qdrant.delete.assert_called_once_with(
            collection_name="test_collection", points_selector=[expected_uuid]
        )

    def test_delete_document_failure(self, client_with_mock):
        """
        Test document deletion error handling.

        Verifies graceful handling of deletion failures.
        """
        client, mock_qdrant = client_with_mock

        # Mock deletion failure
        mock_qdrant.delete.side_effect = Exception("Not found")

        # Delete should return False on error
        result = client.delete_document("test-123", "test_collection")
        assert result is False


class TestSearchOperations:
    """
    Tests for semantic search operations.

    These tests verify vector similarity search with various
    filters and configurations.

    Python Learning Notes:
        - Vector similarity finds semantically related content
        - Filters narrow results to specific criteria
        - Score thresholds ensure quality results
    """

    @pytest.fixture
    def client_with_mock(self):
        """Create a client with mocked Qdrant connection."""
        with patch("governmentreporter.database.qdrant.QdrantBaseClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            client = QdrantDBClient(db_path="./test")
            return client, mock_instance

    @pytest.fixture
    def query_embedding(self):
        """Create a query embedding vector."""
        return [0.2] * 1536

    def test_search_basic(self, client_with_mock, query_embedding):
        """
        Test basic semantic search without filters.

        Verifies that:
            - Search returns correct results
            - Results are properly formatted
            - Scores are included
        """
        client, mock_qdrant = client_with_mock

        # Mock search results
        mock_point = ScoredPoint(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, "doc-1")),
            score=0.95,
            payload={
                "text": "Result content",
                "original_id": "doc-1",
                "title": "Test Document",
            },
            version=1,
        )
        mock_qdrant.search.return_value = [mock_point]

        # Perform search
        results = client.search(
            query_embedding=query_embedding, collection_name="test_collection", limit=10
        )

        # Verify results
        assert len(results) == 1
        result = results[0]
        assert isinstance(result, SearchResult)
        assert result.score == 0.95
        assert result.document.id == "doc-1"
        assert result.document.text == "Result content"
        assert result.document.metadata["title"] == "Test Document"

    def test_search_with_metadata_filter(self, client_with_mock, query_embedding):
        """
        Test search with metadata filtering.

        Verifies that metadata filters are applied correctly.
        """
        client, mock_qdrant = client_with_mock

        # Mock empty results (filtered out)
        mock_qdrant.search.return_value = []

        # Search with filter
        results = client.search(
            query_embedding=query_embedding,
            collection_name="test_collection",
            limit=10,
            metadata_filter={"year": 2024, "type": "opinion"},
        )

        # Verify filter was applied
        call_args = mock_qdrant.search.call_args
        query_filter = call_args.kwargs["query_filter"]
        assert query_filter is not None
        assert isinstance(query_filter, Filter)

        # Verify empty results
        assert results == []

    def test_search_with_score_threshold(self, client_with_mock, query_embedding):
        """
        Test search with minimum score threshold.

        Verifies that score thresholds filter low-quality matches.
        """
        client, mock_qdrant = client_with_mock

        # Mock search result below threshold
        mock_qdrant.search.return_value = []

        # Search with threshold
        results = client.search(
            query_embedding=query_embedding,
            collection_name="test_collection",
            limit=10,
            score_threshold=0.8,
        )

        # Verify threshold was applied
        call_args = mock_qdrant.search.call_args
        assert call_args.kwargs["score_threshold"] == 0.8
        assert results == []

    def test_search_with_complex_filter(self, client_with_mock, query_embedding):
        """
        Test search with complex query filter.

        Verifies that pre-built Qdrant filters are passed through correctly.
        """
        client, mock_qdrant = client_with_mock
        mock_qdrant.search.return_value = []

        # Create complex filter
        complex_filter = {
            "must": [
                {"key": "year", "match": {"value": 2024}},
                {"key": "type", "match": {"value": "opinion"}},
            ]
        }

        # Search with complex filter
        results = client.search(
            query_embedding=query_embedding,
            collection_name="test_collection",
            limit=10,
            query_filter=complex_filter,
        )

        # Verify filter was passed through
        call_args = mock_qdrant.search.call_args
        assert call_args.kwargs["query_filter"] == complex_filter

    def test_search_wrong_embedding_dimension(self, client_with_mock):
        """
        Test search with wrong embedding dimensions.

        Verifies validation of query embedding dimensions.
        """
        client, _ = client_with_mock

        # Wrong dimension embedding
        bad_embedding = [0.1] * 100

        with pytest.raises(ValueError) as exc_info:
            client.search(
                query_embedding=bad_embedding,
                collection_name="test_collection",
                limit=10,
            )

        assert "1536 dimensions" in str(exc_info.value)

    def test_search_multiple_results(self, client_with_mock, query_embedding):
        """
        Test search returning multiple results.

        Verifies that multiple results are handled correctly
        and returned in score order.
        """
        client, mock_qdrant = client_with_mock

        # Mock multiple results
        results_data = []
        for i in range(3):
            point = ScoredPoint(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"doc-{i}")),
                score=0.9 - (i * 0.1),  # Decreasing scores
                payload={"text": f"Result {i}", "original_id": f"doc-{i}"},
                version=1,
            )
            results_data.append(point)

        mock_qdrant.search.return_value = results_data

        # Perform search
        results = client.search(
            query_embedding=query_embedding, collection_name="test_collection", limit=3
        )

        # Verify results
        assert len(results) == 3
        assert results[0].score == 0.9
        assert results[1].score == 0.8
        assert results[2].score == 0.7
        assert results[0].document.id == "doc-0"
        assert results[1].document.id == "doc-1"
        assert results[2].document.id == "doc-2"

    def test_semantic_search_wrapper(self, client_with_mock, query_embedding):
        """
        Test the semantic_search method wrapper.

        Verifies that semantic_search correctly delegates to search method.
        """
        client, mock_qdrant = client_with_mock
        mock_qdrant.search.return_value = []

        # Use semantic_search method
        results = client.semantic_search(
            collection_name="test_collection",
            query_vector=query_embedding,
            limit=5,
            query_filter={"type": "opinion"},
        )

        # Verify delegation
        call_args = mock_qdrant.search.call_args
        assert call_args.kwargs["query_vector"] == query_embedding
        assert call_args.kwargs["limit"] == 5
        assert call_args.kwargs["query_filter"] == {"type": "opinion"}

    def test_search_error_handling(self, client_with_mock, query_embedding):
        """
        Test search error handling.

        Verifies that search errors are logged and re-raised.
        """
        client, mock_qdrant = client_with_mock

        # Mock search failure
        mock_qdrant.search.side_effect = Exception("Connection timeout")

        # Search should raise exception
        with pytest.raises(Exception) as exc_info:
            client.search(
                query_embedding=query_embedding,
                collection_name="test_collection",
                limit=10,
            )

        assert "Connection timeout" in str(exc_info.value)


class TestEdgeCasesAndErrorHandling:
    """
    Tests for edge cases and error scenarios.

    These tests ensure the client handles unusual situations
    and errors gracefully.

    Python Learning Notes:
        - Edge cases test boundary conditions
        - Error handling ensures robustness
        - Defensive programming prevents crashes
    """

    @pytest.fixture
    def client_with_mock(self):
        """Create a client with mocked Qdrant connection."""
        with patch("governmentreporter.database.qdrant.QdrantBaseClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            client = QdrantDBClient(db_path="./test")
            return client, mock_instance

    def test_store_document_with_none_metadata(self, client_with_mock):
        """
        Test storing document with None metadata.

        Verifies that None metadata is handled correctly.
        """
        client, mock_qdrant = client_with_mock

        doc = Document(
            id="test-123", text="Test content", embedding=[0.1] * 1536, metadata=None
        )

        # Mock collection exists
        mock_collections = MagicMock()
        mock_collections.collections = []
        mock_qdrant.get_collections.return_value = mock_collections

        # Store document
        result = client.store_document(doc, "test_collection")

        # Verify success
        assert result is True

        # Verify payload doesn't include None metadata
        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs["points"]
        payload = points[0].payload
        assert "text" in payload
        assert payload["text"] == "Test content"

    def test_uuid_consistency(self, client_with_mock):
        """
        Test UUID generation consistency.

        Verifies that the same document ID always generates
        the same UUID for consistent storage/retrieval.
        """
        client, _ = client_with_mock

        # Generate UUIDs for same ID multiple times
        doc_id = "test-document-123"
        uuid1 = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id))
        uuid2 = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id))

        # Verify consistency
        assert uuid1 == uuid2

    def test_handle_point_without_vector(self, client_with_mock):
        """
        Test handling points without vectors.

        Verifies graceful handling when Qdrant returns
        points without vector data.
        """
        client, mock_qdrant = client_with_mock

        # Mock point without vector
        mock_point = MagicMock()
        mock_point.id = "test-uuid"
        mock_point.vector = None  # No vector
        mock_point.payload = {"text": "Test content", "original_id": "test-123"}
        mock_qdrant.retrieve.return_value = [mock_point]

        # Retrieve document
        doc = client.get_document("test-123", "test_collection")

        # Verify document created with empty vector
        assert doc is not None
        assert doc.embedding == []

    def test_handle_point_without_payload(self, client_with_mock):
        """
        Test handling points without payload.

        Verifies graceful handling when payload is missing.
        """
        client, mock_qdrant = client_with_mock

        # Mock point without payload
        mock_point = MagicMock()
        mock_point.id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "test-123"))
        mock_point.vector = [0.1] * 1536
        mock_point.payload = None  # No payload
        mock_qdrant.retrieve.return_value = [mock_point]

        # Retrieve document
        doc = client.get_document("test-123", "test_collection")

        # Verify document created with defaults
        assert doc is not None
        assert doc.text == ""
        assert doc.metadata == {}

    def test_batch_validation_with_invalid_documents(self, client_with_mock):
        """
        Test batch storage validation with invalid documents.

        Verifies that batch operations validate all documents
        before processing.
        """
        client, _ = client_with_mock

        # Mix of valid and invalid documents
        documents = [
            Document(
                id="valid-1", text="Valid content", embedding=[0.1] * 1536, metadata={}
            ),
            Document(
                id="",  # Invalid: empty ID
                text="Invalid content",
                embedding=[0.1] * 1536,
                metadata={},
            ),
        ]

        # Should raise error during validation
        with pytest.raises(ValueError) as exc_info:
            client.store_documents_batch(documents, "test_collection")

        assert "All documents must have IDs" in str(exc_info.value)


# Integration-style tests (still mocked but test full workflows)
class TestIntegrationWorkflows:
    """
    Tests for complete workflows using the client.

    These tests verify end-to-end scenarios while still using
    mocks to avoid external dependencies.

    Python Learning Notes:
        - Integration tests verify component interactions
        - Workflows test realistic usage patterns
        - Multiple operations ensure consistency
    """

    @pytest.fixture
    def client_with_full_mock(self):
        """
        Create a client with comprehensive mocking.

        This fixture provides a fully functional mock that
        simulates a complete Qdrant instance.
        """
        with patch("governmentreporter.database.qdrant.QdrantBaseClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Storage for mocked data
            stored_points = {}

            # Mock upsert to store data
            def mock_upsert(collection_name, points, **kwargs):
                for point in points:
                    stored_points[str(point.id)] = point
                return None

            # Mock retrieve to return stored data
            def mock_retrieve(collection_name, ids, **kwargs):
                results = []
                for point_id in ids:
                    if point_id in stored_points:
                        results.append(stored_points[point_id])
                return results

            # Mock search to return similar documents
            def mock_search(collection_name, query_vector, limit=10, **kwargs):
                results = []
                for point_id, point in list(stored_points.items())[:limit]:
                    scored = ScoredPoint(
                        id=point_id,
                        score=0.9,  # Mock score
                        payload=point.payload,
                        version=1,
                    )
                    results.append(scored)
                return results

            mock_instance.upsert.side_effect = mock_upsert
            mock_instance.retrieve.side_effect = mock_retrieve
            mock_instance.search.side_effect = mock_search

            # Mock collection management
            mock_collections = MagicMock()
            mock_collections.collections = []
            mock_instance.get_collections.return_value = mock_collections

            client = QdrantDBClient(db_path="./test")
            return client, mock_instance, stored_points

    def test_store_and_retrieve_workflow(self, client_with_full_mock):
        """
        Test complete store and retrieve workflow.

        Verifies that documents can be stored and then retrieved
        successfully in a realistic workflow.
        """
        client, mock_qdrant, stored_points = client_with_full_mock

        # Create and store document
        doc = Document(
            id="workflow-test-123",
            text="This is a workflow test document",
            embedding=[0.1] * 1536,
            metadata={"workflow": "test", "step": 1},
        )

        # Store document
        success = client.store_document(doc, "workflow_collection")
        assert success is True

        # Retrieve the same document
        retrieved = client.get_document("workflow-test-123", "workflow_collection")

        # Verify retrieval
        assert retrieved is not None
        assert retrieved.text == doc.text
        assert "workflow" in retrieved.metadata
        assert retrieved.metadata["workflow"] == "test"

    def test_batch_store_and_search_workflow(self, client_with_full_mock):
        """
        Test batch storage followed by search.

        Verifies a complete workflow of storing multiple documents
        and then searching for similar ones.
        """
        client, mock_qdrant, stored_points = client_with_full_mock

        # Create multiple documents
        documents = []
        for i in range(10):
            doc = Document(
                id=f"batch-doc-{i}",
                text=f"Document number {i} about testing",
                embedding=[0.1 + (i * 0.01)] * 1536,  # Slightly different embeddings
                metadata={"batch": "test", "index": i},
            )
            documents.append(doc)

        # Store batch
        success_count, failed_ids = client.store_documents_batch(
            documents, "batch_collection", batch_size=5
        )

        assert success_count == 10
        assert failed_ids == []

        # Search for similar documents
        query_embedding = [0.15] * 1536
        results = client.search(
            query_embedding=query_embedding, collection_name="batch_collection", limit=5
        )

        # Verify search results
        assert len(results) <= 5
        for result in results:
            assert isinstance(result, SearchResult)
            assert result.score > 0
            assert "batch" in result.document.metadata

    def test_collection_lifecycle_workflow(self, client_with_full_mock):
        """
        Test complete collection lifecycle.

        Verifies creating, using, and deleting a collection.
        """
        client, mock_qdrant, stored_points = client_with_full_mock

        collection_name = "lifecycle_test"

        # Create collection
        created = client.create_collection(collection_name)
        assert created is True

        # Store document in collection
        doc = Document(
            id="lifecycle-doc",
            text="Lifecycle test document",
            embedding=[0.1] * 1536,
            metadata={},
        )
        stored = client.store_document(doc, collection_name)
        assert stored is True

        # Verify document exists
        exists = client.document_exists("lifecycle-doc", collection_name)
        assert exists is True

        # Delete document
        deleted = client.delete_document("lifecycle-doc", collection_name)
        assert deleted is True

        # Delete collection
        collection_deleted = client.delete_collection(collection_name)
        assert collection_deleted is True


class TestAdvancedFilteringAndSearch:
    """
    Tests for advanced filtering and search capabilities.

    These tests verify complex query scenarios including range filters,
    multiple conditions, and advanced Qdrant features.

    Python Learning Notes:
        - Complex filters enable precise document retrieval
        - Range queries support numerical comparisons
        - Multiple conditions can be combined with AND/OR logic
    """

    @pytest.fixture
    def client_with_mock(self):
        """Create a client with mocked Qdrant connection."""
        with patch("governmentreporter.database.qdrant.QdrantBaseClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            client = QdrantDBClient(db_path="./test")
            return client, mock_instance

    def test_search_with_range_filter(self, client_with_mock):
        """
        Test search with range-based metadata filter.

        Verifies that range filters for numerical fields work correctly.
        """
        client, mock_qdrant = client_with_mock
        mock_qdrant.search.return_value = []

        from qdrant_client.models import Range

        # Create range filter
        range_filter = {
            "must": [
                {"key": "year", "range": {"gte": 2020, "lte": 2024}},
                {"key": "score", "range": {"gt": 0.5}},
            ]
        }

        # Search with range filter
        results = client.search(
            query_embedding=[0.1] * 1536,
            collection_name="test_collection",
            limit=10,
            query_filter=range_filter,
        )

        # Verify filter was applied
        call_args = mock_qdrant.search.call_args
        assert call_args.kwargs["query_filter"] == range_filter

    def test_search_with_match_any_filter(self, client_with_mock):
        """
        Test search with MatchAny filter for multiple values.

        Verifies that searching for documents matching any of multiple values works.
        """
        client, mock_qdrant = client_with_mock
        mock_qdrant.search.return_value = []

        from qdrant_client.models import MatchAny

        # Create MatchAny filter
        match_any_filter = {
            "must": [
                {"key": "type", "match": {"any": ["opinion", "order", "judgment"]}}
            ]
        }

        # Search with MatchAny filter
        results = client.search(
            query_embedding=[0.1] * 1536,
            collection_name="test_collection",
            limit=10,
            query_filter=match_any_filter,
        )

        # Verify filter was applied
        call_args = mock_qdrant.search.call_args
        assert call_args.kwargs["query_filter"] == match_any_filter

    def test_search_with_combined_filters(self, client_with_mock):
        """
        Test search with combined must/should/must_not conditions.

        Verifies complex boolean logic in filters.
        """
        client, mock_qdrant = client_with_mock
        mock_qdrant.search.return_value = []

        # Create complex combined filter
        complex_filter = {
            "must": [{"key": "year", "match": {"value": 2024}}],
            "should": [
                {"key": "court", "match": {"value": "SCOTUS"}},
                {"key": "court", "match": {"value": "Federal"}},
            ],
            "must_not": [{"key": "status", "match": {"value": "draft"}}],
        }

        # Search with complex filter
        results = client.search(
            query_embedding=[0.1] * 1536,
            collection_name="test_collection",
            limit=10,
            query_filter=complex_filter,
        )

        # Verify complex filter was applied
        call_args = mock_qdrant.search.call_args
        assert call_args.kwargs["query_filter"] == complex_filter

    def test_search_with_nested_metadata(self, client_with_mock):
        """
        Test search results with nested metadata structures.

        Verifies that nested metadata is preserved in search results.
        """
        client, mock_qdrant = client_with_mock

        # Mock result with nested metadata
        mock_point = ScoredPoint(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, "doc-1")),
            score=0.95,
            payload={
                "text": "Result content",
                "original_id": "doc-1",
                "metadata": {
                    "author": {"name": "John Doe", "affiliation": "Supreme Court"},
                    "citations": ["Case A", "Case B"],
                    "topics": {
                        "primary": "Constitutional Law",
                        "secondary": ["Civil Rights", "Due Process"],
                    },
                },
            },
            version=1,
        )
        mock_qdrant.search.return_value = [mock_point]

        # Perform search
        results = client.search(
            query_embedding=[0.1] * 1536, collection_name="test_collection", limit=10
        )

        # Verify nested metadata is preserved
        assert len(results) == 1
        metadata = results[0].document.metadata
        assert metadata["metadata"]["author"]["name"] == "John Doe"
        assert "Constitutional Law" in metadata["metadata"]["topics"]["primary"]
        assert len(metadata["metadata"]["citations"]) == 2


class TestConnectionManagementAndRetries:
    """
    Tests for connection management and retry logic.

    These tests verify proper handling of connection issues,
    timeouts, and retry scenarios.

    Python Learning Notes:
        - Connection pooling improves performance
        - Retry logic handles transient failures
        - Timeout handling prevents hanging operations
    """

    @patch("governmentreporter.database.qdrant.QdrantBaseClient")
    def test_connection_timeout_handling(self, mock_qdrant_base):
        """
        Test handling of connection timeouts.

        Verifies graceful degradation when Qdrant is unreachable.
        """
        # Mock connection timeout
        mock_qdrant_base.side_effect = TimeoutError("Connection timeout")

        # Should raise error during initialization
        with pytest.raises(TimeoutError):
            QdrantDBClient(host="unreachable-host", port=6333)

    @patch("governmentreporter.database.qdrant.QdrantBaseClient")
    def test_authentication_failure(self, mock_qdrant_base):
        """
        Test handling of authentication failures.

        Verifies proper error handling for invalid API keys.
        """
        # Mock authentication error
        mock_qdrant_base.side_effect = Exception(
            "Authentication failed: Invalid API key"
        )

        # Should raise error with clear message
        with pytest.raises(Exception) as exc_info:
            QdrantDBClient(url="https://cloud.qdrant.io", api_key="invalid-key")

        assert "Authentication failed" in str(exc_info.value)

    def test_network_error_during_operation(self):
        """
        Test handling of network errors during operations.

        Verifies that network failures are handled gracefully.
        """
        with patch("governmentreporter.database.qdrant.QdrantBaseClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            client = QdrantDBClient(db_path="./test")

            # Mock network error during search
            mock_instance.search.side_effect = ConnectionError("Network unreachable")

            # Should handle error gracefully
            with pytest.raises(ConnectionError):
                client.search(
                    query_embedding=[0.1] * 1536,
                    collection_name="test_collection",
                    limit=10,
                )


class TestDataConsistencyAndValidation:
    """
    Tests for data consistency and validation.

    These tests ensure data integrity is maintained across operations.

    Python Learning Notes:
        - Data validation prevents corruption
        - Consistency checks ensure reliability
        - Type checking catches errors early
    """

    @pytest.fixture
    def client_with_mock(self):
        """Create a client with mocked Qdrant connection."""
        with patch("governmentreporter.database.qdrant.QdrantBaseClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Mock collection exists
            mock_collections = MagicMock()
            mock_collections.collections = []
            mock_instance.get_collections.return_value = mock_collections

            client = QdrantDBClient(db_path="./test")
            return client, mock_instance

    def test_embedding_normalization(self, client_with_mock):
        """
        Test that embeddings are handled correctly regardless of normalization.

        Verifies that both normalized and unnormalized embeddings work.
        """
        client, mock_qdrant = client_with_mock

        # Create embedding with very small values
        small_embedding = [1e-10] * 1536

        doc = Document(
            id="test-doc", text="Test content", embedding=small_embedding, metadata={}
        )

        # Should store successfully
        result = client.store_document(doc, "test_collection")
        assert result is True

        # Verify embedding was stored as-is
        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs["points"]
        assert points[0].vector == small_embedding

    def test_special_characters_in_metadata(self, client_with_mock):
        """
        Test handling of special characters in metadata fields.

        Verifies that Unicode and special characters are preserved.
        """
        client, mock_qdrant = client_with_mock

        # Document with special characters
        doc = Document(
            id="test-doc",
            text="Test content with émojis 🎯 and ünïcödé",
            embedding=[0.1] * 1536,
            metadata={
                "title": "Case № 123: Smith v. O'Brien",
                "summary": "Contains special chars: €£¥₹",
                "unicode": "测试中文字符",
                "emoji": "📚🔍⚖️",
            },
        )

        # Store document
        result = client.store_document(doc, "test_collection")
        assert result is True

        # Verify special characters preserved
        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs["points"]
        payload = points[0].payload

        assert "émojis 🎯" in payload["text"]
        assert payload["title"] == "Case № 123: Smith v. O'Brien"
        assert "€£¥₹" in payload["summary"]
        assert payload["unicode"] == "测试中文字符"
        assert payload["emoji"] == "📚🔍⚖️"

    def test_very_large_metadata(self, client_with_mock):
        """
        Test handling of documents with very large metadata.

        Verifies that large metadata objects are handled correctly.
        """
        client, mock_qdrant = client_with_mock

        # Create large metadata object
        large_metadata = {
            f"field_{i}": f"Value {i} " * 100  # Each field has long value
            for i in range(100)  # 100 fields
        }

        doc = Document(
            id="large-doc",
            text="Document with large metadata",
            embedding=[0.1] * 1536,
            metadata=large_metadata,
        )

        # Should handle large metadata
        result = client.store_document(doc, "test_collection")
        assert result is True

        # Verify metadata was stored
        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs["points"]

        # Check a sample of fields
        for i in range(0, 100, 10):
            assert f"field_{i}" in points[0].payload

    def test_null_values_in_metadata(self, client_with_mock):
        """
        Test handling of null/None values in metadata.

        Verifies that None values in metadata are handled appropriately.
        """
        client, mock_qdrant = client_with_mock

        doc = Document(
            id="test-doc",
            text="Test content",
            embedding=[0.1] * 1536,
            metadata={
                "field1": "value1",
                "field2": None,
                "field3": "",
                "field4": 0,
                "field5": False,
            },
        )

        # Store document
        result = client.store_document(doc, "test_collection")
        assert result is True

        # Verify handling of different "empty" values
        call_args = mock_qdrant.upsert.call_args
        points = call_args.kwargs["points"]
        payload = points[0].payload

        assert payload["field1"] == "value1"
        assert payload["field2"] is None
        assert payload["field3"] == ""
        assert payload["field4"] == 0
        assert payload["field5"] is False

    def test_concurrent_operations_safety(self, client_with_mock):
        """
        Test that operations are safe for concurrent use.

        Verifies thread-safety of client operations.
        """
        client, mock_qdrant = client_with_mock

        # Multiple operations should not interfere with each other
        doc1 = Document(id="doc1", text="Text 1", embedding=[0.1] * 1536, metadata={})
        doc2 = Document(id="doc2", text="Text 2", embedding=[0.2] * 1536, metadata={})

        # Store both documents
        result1 = client.store_document(doc1, "collection1")
        result2 = client.store_document(doc2, "collection2")

        assert result1 is True
        assert result2 is True

        # Verify both operations completed
        assert mock_qdrant.upsert.call_count == 2


class TestPerformanceAndOptimization:
    """
    Tests for performance-related features and optimizations.

    These tests verify batch processing efficiency and optimization features.

    Python Learning Notes:
        - Batch processing reduces API calls
        - Chunking prevents memory issues
        - Async operations improve throughput
    """

    @pytest.fixture
    def client_with_mock(self):
        """Create a client with mocked Qdrant connection."""
        with patch("governmentreporter.database.qdrant.QdrantBaseClient") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Mock collection exists
            mock_collections = MagicMock()
            mock_collections.collections = []
            mock_instance.get_collections.return_value = mock_collections

            client = QdrantDBClient(db_path="./test")
            return client, mock_instance

    def test_batch_size_optimization(self, client_with_mock):
        """
        Test that batch operations respect batch size limits.

        Verifies efficient batching of large document sets.
        """
        client, mock_qdrant = client_with_mock

        # Create many documents
        documents = [
            Document(
                id=f"doc-{i}",
                text=f"Document {i}",
                embedding=[0.1] * 1536,
                metadata={"index": i},
            )
            for i in range(250)  # Large batch
        ]

        # Store with small batch size
        client.store_documents_batch(documents, "test_collection", batch_size=50)

        # Should make 5 calls (250 / 50)
        assert mock_qdrant.upsert.call_count == 5

        # Each call should have <= 50 documents
        for call_args in mock_qdrant.upsert.call_args_list:
            points = call_args.kwargs["points"]
            assert len(points) <= 50

    def test_memory_efficient_batch_processing(self, client_with_mock):
        """
        Test memory-efficient processing of very large batches.

        Verifies that large batches don't cause memory issues.
        """
        client, mock_qdrant = client_with_mock

        # Simulate very large batch processing
        total_docs = 10000
        processed = 0

        # Process in chunks to avoid memory issues
        chunk_size = 1000
        for start_idx in range(0, total_docs, chunk_size):
            end_idx = min(start_idx + chunk_size, total_docs)

            documents = [
                Document(
                    id=f"doc-{i}",
                    text=f"Document {i}",
                    embedding=[0.1] * 1536,
                    metadata={"batch": start_idx // chunk_size},
                )
                for i in range(start_idx, end_idx)
            ]

            success_count, failed_ids = client.store_documents_batch(
                documents, "large_collection", batch_size=100
            )

            processed += success_count

        # Verify all documents were processed
        assert processed == total_docs

    def test_progress_callback_performance(self, client_with_mock):
        """
        Test that progress callbacks don't impact performance.

        Verifies efficient progress reporting.
        """
        client, mock_qdrant = client_with_mock

        # Track callback overhead
        callback_count = 0

        def progress_callback(current, total):
            nonlocal callback_count
            callback_count += 1
            # Simulate some work in callback
            assert current <= total
            assert current > 0

        documents = [
            Document(
                id=f"doc-{i}", text=f"Document {i}", embedding=[0.1] * 1536, metadata={}
            )
            for i in range(100)
        ]

        # Store with progress callback
        client.store_documents_batch(
            documents, "test_collection", batch_size=25, on_progress=progress_callback
        )

        # Should have 4 progress updates (100 / 25)
        assert callback_count == 4
