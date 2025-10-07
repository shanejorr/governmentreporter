"""
Comprehensive unit tests for the QdrantIngestionClient.

This module tests the ingestion pipeline that converts document payloads
into stored Qdrant documents. The ingestion client bridges the gap between
the processing pipeline and the database storage layer.

Test Categories:
    - Initialization and setup
    - Document batch processing
    - Payload conversion and validation
    - Collection statistics
    - Error handling and edge cases

Python Learning Notes:
    - Mock.patch replaces imports with test doubles
    - Fixtures provide reusable test data
    - Parametrize runs tests with multiple inputs
    - Side effects simulate different scenarios
"""

import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from governmentreporter.database.ingestion import QdrantIngestionClient
from governmentreporter.database.qdrant import Document


class TestIngestionClientInitialization:
    """
    Tests for QdrantIngestionClient initialization.

    The ingestion client wraps the base QdrantDBClient and provides
    specialized methods for document chunk storage.

    Python Learning Notes:
        - Constructor testing ensures proper initialization
        - Dependency injection allows for mocking
        - Error cases test validation logic
    """

    @patch("governmentreporter.database.ingestion.QdrantDBClient")
    def test_initialization_success(self, mock_qdrant_client_class):
        """
        Test successful initialization of ingestion client.

        Verifies that:
            - Collection name is stored
            - QdrantDBClient is initialized with correct path
            - Collection is created automatically
        """
        # Create mock instance
        mock_client_instance = MagicMock()
        mock_qdrant_client_class.return_value = mock_client_instance

        # Initialize ingestion client
        client = QdrantIngestionClient(
            collection_name="test_collection", db_path="./test_db"
        )

        # Verify initialization
        assert client.collection_name == "test_collection"
        assert client.client == mock_client_instance

        # Verify QdrantDBClient initialization
        mock_qdrant_client_class.assert_called_once_with("./test_db")

        # Verify collection creation
        mock_client_instance.create_collection.assert_called_once_with(
            "test_collection"
        )

    @patch("governmentreporter.database.ingestion.QdrantDBClient")
    def test_initialization_with_default_path(self, mock_qdrant_client_class):
        """
        Test initialization with default database path.

        Verifies that the default path "./data/qdrant/qdrant_db" is used
        when no path is specified.
        """
        mock_client_instance = MagicMock()
        mock_qdrant_client_class.return_value = mock_client_instance

        # Initialize without specifying path
        client = QdrantIngestionClient("test_collection")

        # Verify default path used
        mock_qdrant_client_class.assert_called_once_with("./data/qdrant/qdrant_db")

    def test_initialization_without_collection_name(self):
        """
        Test that initialization fails without collection name.

        Verifies that ValueError is raised when collection_name
        is empty or not provided.
        """
        with pytest.raises(ValueError) as exc_info:
            QdrantIngestionClient("")

        assert "collection_name is required" in str(exc_info.value)

    @patch("governmentreporter.database.ingestion.QdrantDBClient")
    def test_initialization_collection_creation_failure(self, mock_qdrant_client_class):
        """
        Test handling of collection creation failure during initialization.

        Verifies that exceptions during collection creation are
        properly propagated.
        """
        mock_client_instance = MagicMock()
        mock_qdrant_client_class.return_value = mock_client_instance

        # Mock collection creation failure
        mock_client_instance.create_collection.side_effect = Exception(
            "Connection failed"
        )

        # Initialization should raise the exception
        with pytest.raises(Exception) as exc_info:
            QdrantIngestionClient("test_collection")

        assert "Connection failed" in str(exc_info.value)


class TestBatchDocumentUpsert:
    """
    Tests for batch document upsert operations.

    The batch_upsert_documents method is the core functionality that
    converts payloads to Documents and stores them in Qdrant.

    Python Learning Notes:
        - zip() pairs corresponding elements from lists
        - enumerate() provides index with iteration
        - Exception handling ensures partial failures don't stop processing
    """

    @pytest.fixture
    def client_with_mock(self):
        """
        Create an ingestion client with mocked QdrantDBClient.

        Returns a tuple of (ingestion_client, mock_qdrant_client).
        """
        with patch(
            "governmentreporter.database.ingestion.QdrantDBClient"
        ) as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Mock successful batch storage
            mock_instance.store_documents_batch.return_value = (
                0,
                [],
            )  # Default: all succeed

            client = QdrantIngestionClient("test_collection")
            return client, mock_instance

    @pytest.fixture
    def sample_payloads(self):
        """
        Create sample payloads for testing.

        These payloads simulate the output from build_payloads_from_document().
        The format is: {"id": chunk_id, "text": chunk_text, "metadata": {...}}
        """
        payloads = []
        for i in range(3):
            payload = {
                "id": f"doc-123_chunk_{i}",  # Full chunk ID from build_payloads
                "text": f"Chunk {i} text content",  # Text at top level
                "embedding": [],  # Placeholder (filled by caller)
                "metadata": {
                    # Combined metadata from all sources
                    "chunk_id": f"doc-123_chunk_{i}",
                    "chunk_index": i,
                    "total_chunks": 3,
                    "start_char": i * 100,
                    "end_char": (i + 1) * 100,
                    "section_label": "Unknown",
                    "title": "Test Document",
                    "date": "2024-01-15",
                    "type": "opinion",
                    "source": "courtlistener",
                    "document_summary": "Test summary",
                    "topics_or_policy_areas": ["law", "testing"],
                    "entities": ["Supreme Court", "United States"],
                },
                "document_id": "doc-123",  # Added by ingester
            }
            payloads.append(payload)
        return payloads

    @pytest.fixture
    def sample_embeddings(self):
        """
        Create sample embeddings matching the payloads.

        Each embedding is a 1536-dimensional vector for OpenAI compatibility.
        """
        return [[0.1 + (i * 0.01)] * 1536 for i in range(3)]

    def test_batch_upsert_success(
        self, client_with_mock, sample_payloads, sample_embeddings
    ):
        """
        Test successful batch upsert of documents.

        Verifies that:
            - Payloads are converted to Documents correctly
            - Embeddings are paired with payloads
            - Success count is accurate
        """
        client, mock_qdrant = client_with_mock

        # Mock successful storage
        mock_qdrant.store_documents_batch.return_value = (3, [])

        # Perform batch upsert
        success, failed = client.batch_upsert_documents(
            sample_payloads, sample_embeddings, batch_size=100
        )

        # Verify results
        assert success == 3
        assert failed == 0

        # Verify documents were created correctly
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]  # First positional argument

        assert len(documents) == 3

        # Verify first document
        doc = documents[0]
        assert doc.id == "doc-123_chunk_0"
        assert doc.text == "Chunk 0 text content"
        assert doc.embedding == sample_embeddings[0]
        # Both top-level fields and metadata fields are flattened into metadata
        assert doc.metadata["document_id"] == "doc-123"
        assert doc.metadata["chunk_index"] == 0

    def test_batch_upsert_with_missing_chunk_text(
        self, client_with_mock, sample_embeddings
    ):
        """
        Test handling of payloads without text field.

        Verifies graceful handling when the text field is missing from payload.
        """
        client, mock_qdrant = client_with_mock

        # Payload without text field (new format from build_payloads)
        payloads = [
            {
                "id": "doc-123_chunk_0",
                # No "text" field
                "metadata": {"chunk_index": 0},
                "document_id": "doc-123",
            }
        ]

        mock_qdrant.store_documents_batch.return_value = (1, [])

        # Should handle missing text gracefully
        success, failed = client.batch_upsert_documents(
            payloads, [sample_embeddings[0]], batch_size=100
        )

        assert success == 1
        assert failed == 0

        # Verify document created with empty text
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        assert documents[0].text == ""

    def test_batch_upsert_mismatched_lengths(self, client_with_mock, sample_payloads):
        """
        Test that mismatched payload and embedding counts are rejected.

        Verifies validation that payloads and embeddings must match.
        """
        client, _ = client_with_mock

        # Different number of embeddings
        mismatched_embeddings = [[0.1] * 1536]  # Only 1 embedding for 3 payloads

        with pytest.raises(ValueError) as exc_info:
            client.batch_upsert_documents(
                sample_payloads, mismatched_embeddings, batch_size=100
            )

        assert "must have the same length" in str(exc_info.value)

    def test_batch_upsert_empty_inputs(self, client_with_mock):
        """
        Test handling of empty input lists.

        Verifies that empty inputs return zero counts without errors.
        """
        client, mock_qdrant = client_with_mock

        # Empty inputs
        success, failed = client.batch_upsert_documents([], [], batch_size=100)

        # Should return zeros without calling storage
        assert success == 0
        assert failed == 0
        mock_qdrant.store_documents_batch.assert_not_called()

    def test_batch_upsert_with_failures(
        self, client_with_mock, sample_payloads, sample_embeddings
    ):
        """
        Test handling of partial storage failures.

        Verifies that failures are properly counted and reported.
        """
        client, mock_qdrant = client_with_mock

        # Mock partial failure (2 succeed, 1 fails)
        mock_qdrant.store_documents_batch.return_value = (2, ["doc-123_chunk_2"])

        # Perform batch upsert
        success, failed = client.batch_upsert_documents(
            sample_payloads, sample_embeddings, batch_size=100
        )

        # Verify partial success
        assert success == 2
        assert failed == 1

    def test_batch_upsert_document_conversion_failure(
        self, client_with_mock, sample_embeddings
    ):
        """
        Test handling of document conversion failures.

        Verifies that individual conversion failures don't stop
        processing of other documents.
        """
        client, mock_qdrant = client_with_mock

        # Mix of valid and invalid payloads (new format)
        payloads = [
            {
                "id": "doc-1_chunk_0",
                "text": "Valid text",
                "metadata": {"chunk_index": 0},
                "document_id": "doc-1",
            },
            None,  # Invalid payload
            {
                "id": "doc-3_chunk_2",
                "text": "Another valid",
                "metadata": {"chunk_index": 2},
                "document_id": "doc-3",
            },
        ]

        # Mock storage of successfully converted documents
        mock_qdrant.store_documents_batch.return_value = (2, [])

        # Perform batch upsert
        success, failed = client.batch_upsert_documents(
            payloads, sample_embeddings, batch_size=100
        )

        # One should fail during conversion
        assert success == 2
        assert failed == 1

        # Verify only valid documents were passed to storage
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        assert len(documents) == 2

    def test_batch_upsert_with_custom_batch_size(
        self, client_with_mock, sample_payloads, sample_embeddings
    ):
        """
        Test that custom batch size is passed to storage layer.

        Verifies that the batch_size parameter is correctly propagated.
        """
        client, mock_qdrant = client_with_mock
        mock_qdrant.store_documents_batch.return_value = (3, [])

        # Use custom batch size
        client.batch_upsert_documents(sample_payloads, sample_embeddings, batch_size=50)

        # Verify batch size was passed
        call_args = mock_qdrant.store_documents_batch.call_args
        assert call_args.kwargs["batch_size"] == 50

    def test_batch_upsert_without_document_id(
        self, client_with_mock, sample_embeddings
    ):
        """
        Test handling of payloads without document_id.

        Verifies that unique IDs are generated when document_id is missing.
        """
        client, mock_qdrant = client_with_mock

        # Payload without document_id (new format)
        payloads = [
            {
                "id": "some_chunk_0",  # Has id but no document_id
                "text": "Text without doc ID",
                "metadata": {"chunk_index": 0},
                # No document_id
            }
        ]

        mock_qdrant.store_documents_batch.return_value = (1, [])

        # Should use the id from payload
        success, failed = client.batch_upsert_documents(
            payloads, [sample_embeddings[0]], batch_size=100
        )

        assert success == 1

        # Verify ID was used from payload
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        assert documents[0].id == "some_chunk_0"

    def test_batch_upsert_complete_failure(
        self, client_with_mock, sample_payloads, sample_embeddings
    ):
        """
        Test handling of complete storage failure.

        Verifies that storage exceptions are handled gracefully.
        """
        client, mock_qdrant = client_with_mock

        # Mock complete storage failure
        mock_qdrant.store_documents_batch.side_effect = Exception(
            "Database unavailable"
        )

        # Perform batch upsert
        success, failed = client.batch_upsert_documents(
            sample_payloads, sample_embeddings, batch_size=100
        )

        # All should fail
        assert success == 0
        assert failed == 3


class TestCollectionStatistics:
    """
    Tests for retrieving collection statistics.

    The get_collection_stats method provides information about
    the stored documents and collection configuration.

    Python Learning Notes:
        - Dictionary returns provide flexible data structures
        - Error handling ensures graceful degradation
        - Mock chains simulate nested object attributes
    """

    @pytest.fixture
    def client_with_mock(self):
        """
        Create an ingestion client with mocked collection info.
        """
        with patch(
            "governmentreporter.database.ingestion.QdrantDBClient"
        ) as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Create nested mock structure for Qdrant client
            mock_qdrant_base = MagicMock()
            mock_instance.client = mock_qdrant_base

            client = QdrantIngestionClient("test_collection")
            return client, mock_instance, mock_qdrant_base

    def test_get_stats_success(self, client_with_mock):
        """
        Test successful retrieval of collection statistics.

        Verifies that collection information is correctly extracted
        and formatted.
        """
        client, mock_qdrant, mock_base = client_with_mock

        # Mock collection list
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_collections_response = MagicMock()
        mock_collections_response.collections = [mock_collection]
        mock_base.get_collections.return_value = mock_collections_response

        # Mock collection info
        mock_info = MagicMock()
        mock_info.points_count = 150
        mock_info.config.params.vectors.size = 1536
        mock_info.config.params.vectors.distance = "Cosine"
        mock_base.get_collection.return_value = mock_info

        # Get stats
        stats = client.get_collection_stats()

        # Verify stats
        assert stats["collection_name"] == "test_collection"
        assert stats["total_documents"] == 150
        assert stats["vector_size"] == 1536
        assert stats["distance_metric"] == "Cosine"

    def test_get_stats_collection_not_found(self, client_with_mock):
        """
        Test stats retrieval when collection doesn't exist.

        Verifies graceful handling when collection is not found.
        """
        client, mock_qdrant, mock_base = client_with_mock

        # Mock empty collections
        mock_collections_response = MagicMock()
        mock_collections_response.collections = []
        mock_base.get_collections.return_value = mock_collections_response

        # Get stats
        stats = client.get_collection_stats()

        # Verify error response
        assert stats["collection_name"] == "test_collection"
        assert stats["total_documents"] == 0
        assert "error" in stats
        assert stats["error"] == "Collection not found"

    def test_get_stats_api_error(self, client_with_mock):
        """
        Test stats retrieval with API error.

        Verifies graceful handling of Qdrant API failures.
        """
        client, mock_qdrant, mock_base = client_with_mock

        # Mock API failure
        mock_base.get_collections.side_effect = Exception("Connection timeout")

        # Get stats
        stats = client.get_collection_stats()

        # Verify error response
        assert stats["collection_name"] == "test_collection"
        assert stats["total_documents"] == 0
        assert "error" in stats
        assert "Connection timeout" in stats["error"]


class TestIngestionWorkflows:
    """
    Tests for complete ingestion workflows.

    These tests verify end-to-end scenarios for document ingestion.

    Python Learning Notes:
        - Workflow tests ensure components work together
        - Multiple operations test consistency
        - Real-world scenarios validate design
    """

    @pytest.fixture
    def full_mock_setup(self):
        """
        Create a complete mock setup for workflow testing.

        Provides ingestion client with fully mocked dependencies.
        """
        with patch(
            "governmentreporter.database.ingestion.QdrantDBClient"
        ) as mock_class:
            mock_qdrant = MagicMock()
            mock_class.return_value = mock_qdrant

            # Setup mock responses
            mock_qdrant.create_collection.return_value = True
            mock_qdrant.store_documents_batch.return_value = (0, [])

            # Mock base client for stats
            mock_base = MagicMock()
            mock_qdrant.client = mock_base

            # Mock collection info
            mock_collection = MagicMock()
            mock_collection.name = "workflow_collection"
            mock_collections = MagicMock()
            mock_collections.collections = [mock_collection]
            mock_base.get_collections.return_value = mock_collections

            mock_info = MagicMock()
            mock_info.points_count = 0  # Initially empty
            mock_info.config.params.vectors.size = 1536
            mock_info.config.params.vectors.distance = "Cosine"
            mock_base.get_collection.return_value = mock_info

            client = QdrantIngestionClient("workflow_collection")
            return client, mock_qdrant, mock_base, mock_info

    def test_complete_ingestion_workflow(self, full_mock_setup):
        """
        Test complete document ingestion workflow.

        Simulates the full process from initialization through
        document storage and stats retrieval.
        """
        client, mock_qdrant, mock_base, mock_info = full_mock_setup

        # Step 1: Verify initialization created collection
        mock_qdrant.create_collection.assert_called_once_with("workflow_collection")

        # Step 2: Prepare document chunks (new format from build_payloads)
        payloads = []
        embeddings = []
        for i in range(10):
            payload = {
                "id": f"scotus-2024-001_chunk_{i}",
                "text": f"Chunk {i} of Supreme Court opinion",
                "embedding": [],
                "metadata": {
                    "chunk_index": i,
                    "total_chunks": 10,
                    "title": "Test v. United States",
                    "date": "2024-01-15",
                    "court": "SCOTUS",
                    "document_summary": "Important legal ruling",
                    "topics_or_policy_areas": ["constitutional law", "civil rights"],
                },
                "document_id": "scotus-2024-001",
            }
            payloads.append(payload)
            embeddings.append([0.1 + (i * 0.01)] * 1536)

        # Step 3: Ingest documents
        mock_qdrant.store_documents_batch.return_value = (10, [])
        success, failed = client.batch_upsert_documents(
            payloads, embeddings, batch_size=5
        )

        assert success == 10
        assert failed == 0

        # Verify documents were converted correctly
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        assert len(documents) == 10

        # Verify chunk IDs are unique
        chunk_ids = [doc.id for doc in documents]
        assert len(set(chunk_ids)) == 10  # All unique

        # Step 4: Update mock to reflect stored documents
        mock_info.points_count = 10

        # Step 5: Get collection statistics
        stats = client.get_collection_stats()

        assert stats["collection_name"] == "workflow_collection"
        assert stats["total_documents"] == 10
        assert stats["vector_size"] == 1536

    def test_multi_document_ingestion_workflow(self, full_mock_setup):
        """
        Test ingesting chunks from multiple documents.

        Verifies that chunks from different documents maintain
        proper separation and identification.
        """
        client, mock_qdrant, mock_base, mock_info = full_mock_setup

        all_payloads = []
        all_embeddings = []

        # Create chunks for 3 different documents (new format)
        for doc_idx in range(3):
            for chunk_idx in range(5):
                payload = {
                    "id": f"doc-{doc_idx}_chunk_{chunk_idx}",
                    "text": f"Document {doc_idx}, Chunk {chunk_idx}",
                    "embedding": [],
                    "metadata": {
                        "chunk_index": chunk_idx,
                        "total_chunks": 5,
                        "title": f"Document {doc_idx}",
                    },
                    "document_id": f"doc-{doc_idx}",
                }
                all_payloads.append(payload)
                all_embeddings.append(
                    [0.1 + (doc_idx * 0.1) + (chunk_idx * 0.01)] * 1536
                )

        # Ingest all chunks
        mock_qdrant.store_documents_batch.return_value = (15, [])
        success, failed = client.batch_upsert_documents(all_payloads, all_embeddings)

        assert success == 15
        assert failed == 0

        # Verify document structure
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]

        # Verify chunk IDs maintain document association
        doc_0_chunks = [d for d in documents if d.id.startswith("doc-0_")]
        doc_1_chunks = [d for d in documents if d.id.startswith("doc-1_")]
        doc_2_chunks = [d for d in documents if d.id.startswith("doc-2_")]

        assert len(doc_0_chunks) == 5
        assert len(doc_1_chunks) == 5
        assert len(doc_2_chunks) == 5

    def test_error_recovery_workflow(self, full_mock_setup):
        """
        Test workflow with errors and recovery.

        Verifies that the system can handle and recover from
        partial failures during ingestion.
        """
        client, mock_qdrant, mock_base, mock_info = full_mock_setup

        # Prepare test data (new format)
        payloads = [
            {
                "id": f"doc-1_chunk_{i}",
                "text": f"Chunk {i}",
                "metadata": {"chunk_index": i},
                "document_id": "doc-1",
            }
            for i in range(5)
        ]
        embeddings = [[0.1] * 1536 for _ in range(5)]

        # First attempt: partial failure
        mock_qdrant.store_documents_batch.return_value = (
            3,
            ["doc-1_chunk_3", "doc-1_chunk_4"],
        )
        success1, failed1 = client.batch_upsert_documents(payloads, embeddings)

        assert success1 == 3
        assert failed1 == 2

        # Retry failed documents
        failed_payloads = payloads[3:5]  # Last 2 that failed
        failed_embeddings = embeddings[3:5]

        # Second attempt: success
        mock_qdrant.store_documents_batch.return_value = (2, [])
        success2, failed2 = client.batch_upsert_documents(
            failed_payloads, failed_embeddings
        )

        assert success2 == 2
        assert failed2 == 0

        # Total success after retry
        total_success = success1 + success2
        assert total_success == 5


class TestEdgeCasesAndValidation:
    """
    Tests for edge cases and input validation.

    These tests ensure robust handling of unusual or invalid inputs.

    Python Learning Notes:
        - Edge case testing improves reliability
        - Input validation prevents downstream errors
        - Graceful degradation maintains system stability
    """

    @pytest.fixture
    def client_with_mock(self):
        """Create ingestion client with mocked dependencies."""
        with patch(
            "governmentreporter.database.ingestion.QdrantDBClient"
        ) as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            client = QdrantIngestionClient("test_collection")
            return client, mock_instance

    def test_payload_without_metadata(self, client_with_mock):
        """
        Test handling of payload without metadata field.

        Verifies graceful handling when metadata is missing.
        """
        client, mock_qdrant = client_with_mock

        payloads = [
            {
                "id": "doc-1_chunk_0",
                "text": "Some text",
                "document_id": "doc-1",
                # No metadata
            }
        ]
        embeddings = [[0.1] * 1536]

        mock_qdrant.store_documents_batch.return_value = (1, [])

        # Should handle missing metadata
        success, failed = client.batch_upsert_documents(payloads, embeddings)

        assert success == 1
        assert failed == 0

        # Verify document created successfully
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        assert documents[0].text == "Some text"

    def test_payload_with_non_dict_metadata(self, client_with_mock):
        """
        Test handling of non-dict metadata.

        Verifies that non-dict metadata is handled safely.
        """
        client, mock_qdrant = client_with_mock

        payloads = [
            {
                "id": "doc-1_chunk_0",
                "text": "Some text",
                "metadata": "not a dict",  # Wrong type
                "document_id": "doc-1",
            }
        ]
        embeddings = [[0.1] * 1536]

        mock_qdrant.store_documents_batch.return_value = (1, [])

        # Should handle invalid metadata
        success, failed = client.batch_upsert_documents(payloads, embeddings)

        assert success == 1
        assert failed == 0

        # Verify document created
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        assert documents[0].text == "Some text"

    def test_very_large_batch(self, client_with_mock):
        """
        Test handling of very large batches.

        Verifies that large batches are processed correctly.
        """
        client, mock_qdrant = client_with_mock

        # Create large batch (new format)
        large_size = 1000
        payloads = []
        embeddings = []
        for i in range(large_size):
            payloads.append(
                {
                    "id": f"doc-{i // 100}_chunk_{i % 100}",
                    "text": f"Chunk {i}",
                    "metadata": {"chunk_index": i},
                    "document_id": f"doc-{i // 100}",  # 10 docs, 100 chunks each
                }
            )
            embeddings.append([0.1] * 1536)

        mock_qdrant.store_documents_batch.return_value = (large_size, [])

        # Process large batch
        success, failed = client.batch_upsert_documents(
            payloads, embeddings, batch_size=100
        )

        assert success == large_size
        assert failed == 0

        # Verify batch was processed
        assert mock_qdrant.store_documents_batch.called

    def test_unique_chunk_id_generation(self, client_with_mock):
        """
        Test that chunk IDs are generated uniquely.

        Verifies that each chunk gets a unique identifier.
        """
        client, mock_qdrant = client_with_mock

        # Payloads with same document_id but different chunks (new format)
        payloads = [
            {
                "id": f"same-doc_chunk_{i}",
                "text": f"Chunk {i}",
                "metadata": {"chunk_index": i},
                "document_id": "same-doc",
            }
            for i in range(5)
        ]
        embeddings = [[0.1] * 1536 for _ in range(5)]

        mock_qdrant.store_documents_batch.return_value = (5, [])

        client.batch_upsert_documents(payloads, embeddings)

        # Verify unique IDs
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]

        ids = [doc.id for doc in documents]
        assert len(set(ids)) == 5  # All unique

        # Verify ID format
        for i, doc_id in enumerate(ids):
            assert f"same-doc_chunk_{i}" == doc_id


class TestIngestionClientAdvancedScenarios:
    """
    Tests for advanced ingestion scenarios and edge cases.

    These tests cover complex real-world scenarios that might occur
    during document ingestion.

    Python Learning Notes:
        - Complex scenarios test system robustness
        - Edge cases reveal hidden bugs
        - Real-world testing improves reliability
    """

    @pytest.fixture
    def client_with_mock(self):
        """Create ingestion client with advanced mocking."""
        with patch(
            "governmentreporter.database.ingestion.QdrantDBClient"
        ) as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            client = QdrantIngestionClient("test_collection")
            return client, mock_instance

    def test_mixed_embedding_dimensions(self, client_with_mock):
        """
        Test handling of embeddings with inconsistent dimensions.

        Verifies that dimension mismatches are caught and handled.
        """
        client, mock_qdrant = client_with_mock

        payloads = [
            {
                "chunk_metadata": {"text": "Text 1", "chunk_index": 0},
                "document_id": "doc-1",
            },
            {
                "chunk_metadata": {"text": "Text 2", "chunk_index": 1},
                "document_id": "doc-1",
            },
        ]

        # Embeddings with different dimensions (should be caught by QdrantDBClient)
        embeddings = [[0.1] * 1536, [0.2] * 768]  # Wrong dimension

        # Mock that storage will reject the second document
        mock_qdrant.store_documents_batch.return_value = (1, ["doc-1_chunk_1"])

        success, failed = client.batch_upsert_documents(payloads, embeddings)

        # First should succeed, second should fail
        assert success == 1
        assert failed == 1

    def test_duplicate_document_ids_handling(self, client_with_mock):
        """
        Test handling of duplicate document IDs in batch.

        Verifies that documents with same IDs are handled properly.
        """
        client, mock_qdrant = client_with_mock

        # Same document_id and chunk_index creates duplicate IDs
        payloads = [
            {
                "id": "doc-1_chunk_0",
                "text": "Version 1",
                "metadata": {"chunk_index": 0},
            },
            {
                "id": "doc-1_chunk_0",
                "text": "Version 2",
                "metadata": {"chunk_index": 0},
            },
        ]
        embeddings = [[0.1] * 1536, [0.2] * 1536]

        mock_qdrant.store_documents_batch.return_value = (2, [])

        success, failed = client.batch_upsert_documents(payloads, embeddings)

        # Both should be processed (upsert will update the first)
        assert success == 2
        assert failed == 0

        # Verify both documents were created with same ID (will be upserted)
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        assert documents[0].id == "doc-1_chunk_0"
        assert documents[1].id == "doc-1_chunk_0"

    def test_extremely_large_text_content(self, client_with_mock):
        """
        Test handling of documents with very large text content.

        Verifies that large text fields are handled without issues.
        """
        client, mock_qdrant = client_with_mock

        # Create payload with very large text
        large_text = "A" * 1_000_000  # 1MB of text
        payloads = [
            {
                "id": "large-doc_chunk_0",
                "text": large_text,
                "metadata": {"chunk_index": 0, "document_id": "large-doc"},
            }
        ]
        embeddings = [[0.1] * 1536]

        mock_qdrant.store_documents_batch.return_value = (1, [])

        success, failed = client.batch_upsert_documents(payloads, embeddings)

        assert success == 1
        assert failed == 0

        # Verify large text was included
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        assert len(documents[0].text) == 1_000_000

    def test_nested_metadata_structures(self, client_with_mock):
        """
        Test handling of deeply nested metadata structures.

        Verifies that complex nested metadata is preserved.
        """
        client, mock_qdrant = client_with_mock

        payloads = [
            {
                "chunk_metadata": {
                    "text": "Nested test",
                    "chunk_index": 0,
                    "annotations": {
                        "entities": {
                            "people": ["John Doe", "Jane Smith"],
                            "organizations": {
                                "government": ["Supreme Court", "Congress"],
                                "private": ["ACLU", "EFF"],
                            },
                        },
                        "citations": [
                            {"case": "Roe v Wade", "year": 1973, "relevance": 0.9},
                            {"case": "Brown v Board", "year": 1954, "relevance": 0.8},
                        ],
                    },
                },
                "document_metadata": {
                    "hierarchy": {"level1": {"level2": {"level3": "deep value"}}}
                },
                "document_id": "nested-doc",
            }
        ]
        embeddings = [[0.1] * 1536]

        mock_qdrant.store_documents_batch.return_value = (1, [])

        success, failed = client.batch_upsert_documents(payloads, embeddings)

        assert success == 1

        # Verify nested structure is preserved
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        metadata = documents[0].metadata

        # Check nested structures
        assert (
            metadata["chunk_metadata"]["annotations"]["entities"]["people"][0]
            == "John Doe"
        )
        assert (
            metadata["chunk_metadata"]["annotations"]["citations"][0]["case"]
            == "Roe v Wade"
        )
        assert (
            metadata["document_metadata"]["hierarchy"]["level1"]["level2"]["level3"]
            == "deep value"
        )

    def test_unicode_and_special_characters(self, client_with_mock):
        """
        Test handling of Unicode and special characters in all fields.

        Verifies international text and special characters are preserved.
        """
        client, mock_qdrant = client_with_mock

        payloads = [
            {
                "id": "unicode-doc-2024_chunk_0",
                "text": "Legal text with émojis 🎯⚖️ and symbols €£¥",
                "metadata": {
                    "chunk_index": 0,
                    "document_id": "unicode-doc-2024",
                    "languages": ["English", "Español", "中文", "العربية"],
                    "title": "Case № 2024-001: Müller vs. O'Connor",
                    "special_chars": "∀x∈ℝ: x²≥0",
                    "rtl_text": "مرحبا بك",
                    "emoji_tags": ["📚", "🔍", "⚖️"],
                },
            }
        ]
        embeddings = [[0.1] * 1536]

        mock_qdrant.store_documents_batch.return_value = (1, [])

        success, failed = client.batch_upsert_documents(payloads, embeddings)

        assert success == 1

        # Verify Unicode is preserved
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]

        assert "émojis 🎯⚖️" in documents[0].text
        metadata = documents[0].metadata
        assert "中文" in metadata["languages"]
        assert metadata["title"] == "Case № 2024-001: Müller vs. O'Connor"
        assert metadata["emoji_tags"][0] == "📚"

    def test_concurrent_batch_processing(self, client_with_mock):
        """
        Test handling of concurrent batch processing scenarios.

        Simulates multiple batches being processed simultaneously.
        """
        client, mock_qdrant = client_with_mock

        # Create multiple batches
        batch1_payloads = [
            {
                "chunk_metadata": {"text": f"Batch 1, Chunk {i}", "chunk_index": i},
                "document_id": "doc-batch1",
            }
            for i in range(50)
        ]
        batch1_embeddings = [[0.1] * 1536 for _ in range(50)]

        batch2_payloads = [
            {
                "chunk_metadata": {"text": f"Batch 2, Chunk {i}", "chunk_index": i},
                "document_id": "doc-batch2",
            }
            for i in range(50)
        ]
        batch2_embeddings = [[0.2] * 1536 for _ in range(50)]

        # Mock successful storage
        mock_qdrant.store_documents_batch.return_value = (50, [])

        # Process both batches
        success1, failed1 = client.batch_upsert_documents(
            batch1_payloads, batch1_embeddings, batch_size=25
        )
        success2, failed2 = client.batch_upsert_documents(
            batch2_payloads, batch2_embeddings, batch_size=25
        )

        assert success1 == 50
        assert failed1 == 0
        assert success2 == 50
        assert failed2 == 0

        # Verify both batches were processed
        assert mock_qdrant.store_documents_batch.call_count == 2


class TestIngestionClientRecoveryAndResilience:
    """
    Tests for recovery and resilience features.

    These tests verify that the ingestion client can recover from
    failures and handle degraded conditions.

    Python Learning Notes:
        - Resilience patterns prevent cascading failures
        - Recovery mechanisms ensure data consistency
        - Graceful degradation maintains partial functionality
    """

    @pytest.fixture
    def client_with_mock(self):
        """Create client with failure simulation capabilities."""
        with patch(
            "governmentreporter.database.ingestion.QdrantDBClient"
        ) as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            client = QdrantIngestionClient("test_collection")
            return client, mock_instance

    def test_partial_batch_recovery(self, client_with_mock):
        """
        Test recovery from partial batch failures.

        Verifies that successful items are preserved even when some fail.
        """
        client, mock_qdrant = client_with_mock

        payloads = [
            {
                "chunk_metadata": {"text": f"Chunk {i}", "chunk_index": i},
                "document_id": f"doc-{i}",
            }
            for i in range(10)
        ]
        embeddings = [[0.1] * 1536 for _ in range(10)]

        # Simulate partial failure (7 succeed, 3 fail)
        mock_qdrant.store_documents_batch.return_value = (
            7,
            ["doc-7_chunk_7", "doc-8_chunk_8", "doc-9_chunk_9"],
        )

        success, failed = client.batch_upsert_documents(payloads, embeddings)

        assert success == 7
        assert failed == 3

    def test_collection_recreation_after_deletion(self, client_with_mock):
        """
        Test that collection is recreated if deleted externally.

        Verifies automatic recovery from collection deletion.
        """
        client, mock_qdrant = client_with_mock

        # First operation succeeds
        mock_qdrant.store_documents_batch.return_value = (1, [])

        payloads = [
            {
                "chunk_metadata": {"text": "Test", "chunk_index": 0},
                "document_id": "doc-1",
            }
        ]
        embeddings = [[0.1] * 1536]

        # Initial storage should work
        success, failed = client.batch_upsert_documents(payloads, embeddings)
        assert success == 1

        # Simulate collection was deleted
        mock_qdrant.store_documents_batch.side_effect = Exception(
            "Collection not found"
        )

        # Next operation should fail but gracefully
        success, failed = client.batch_upsert_documents(payloads, embeddings)
        assert success == 0
        assert failed == 1  # Converted to documents but storage failed

    def test_memory_pressure_handling(self, client_with_mock):
        """
        Test handling of memory pressure with very large batches.

        Verifies that large batches are processed without memory issues.
        """
        client, mock_qdrant = client_with_mock

        # Create a very large batch that might cause memory pressure
        large_batch_size = 10000

        # Use generator to avoid creating all data at once
        def generate_payloads():
            for i in range(large_batch_size):
                yield {
                    "chunk_metadata": {"text": f"Chunk {i}", "chunk_index": i % 100},
                    "document_id": f"doc-{i // 100}",
                }

        def generate_embeddings():
            for i in range(large_batch_size):
                yield [0.1 + (i * 0.0001)] * 1536

        payloads = list(generate_payloads())
        embeddings = list(generate_embeddings())

        # Mock successful storage
        mock_qdrant.store_documents_batch.return_value = (large_batch_size, [])

        # Process large batch
        success, failed = client.batch_upsert_documents(
            payloads, embeddings, batch_size=500
        )

        assert success == large_batch_size
        assert failed == 0

    def test_invalid_json_serialization(self, client_with_mock):
        """
        Test handling of objects that can't be JSON serialized.

        Verifies graceful handling of non-serializable metadata.
        """
        client, mock_qdrant = client_with_mock

        # Create payload with non-serializable object
        import datetime

        payloads = [
            {
                "chunk_metadata": {
                    "text": "Test text",
                    "chunk_index": 0,
                    "date": datetime.datetime.now(),  # Not directly JSON serializable
                    "set_data": {1, 2, 3},  # Sets aren't JSON serializable
                },
                "document_id": "doc-1",
            }
        ]
        embeddings = [[0.1] * 1536]

        # Should handle by converting to documents (datetime becomes string in dict)
        mock_qdrant.store_documents_batch.return_value = (1, [])

        # This should work as the payload becomes part of metadata
        success, failed = client.batch_upsert_documents(payloads, embeddings)

        # Should succeed as we're just passing the dict as metadata
        assert success == 1
        assert failed == 0


class TestCollectionStatisticsAdvanced:
    """
    Advanced tests for collection statistics and monitoring.

    These tests verify detailed statistics gathering and edge cases.

    Python Learning Notes:
        - Statistics provide observability into system state
        - Monitoring helps identify issues early
        - Metrics guide optimization decisions
    """

    @pytest.fixture
    def client_with_advanced_mock(self):
        """Create client with advanced statistics mocking."""
        with patch(
            "governmentreporter.database.ingestion.QdrantDBClient"
        ) as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Create sophisticated mock for statistics
            mock_base = MagicMock()
            mock_instance.client = mock_base

            # Setup collection mock
            mock_collection = MagicMock()
            mock_collection.name = "test_collection"

            mock_collections_response = MagicMock()
            mock_collections_response.collections = [mock_collection]
            mock_base.get_collections.return_value = mock_collections_response

            # Setup detailed collection info
            mock_info = MagicMock()
            mock_info.points_count = 1500
            mock_info.vectors_count = 1500
            mock_info.indexed_vectors_count = 1450
            mock_info.segments_count = 3
            mock_info.config.params.vectors.size = 1536
            mock_info.config.params.vectors.distance = "Cosine"
            mock_info.config.params.vectors.on_disk = False
            mock_info.status = "green"
            mock_info.optimizer_status = "idle"

            mock_base.get_collection.return_value = mock_info

            client = QdrantIngestionClient("test_collection")
            return client, mock_instance, mock_base, mock_info

    def test_detailed_statistics_retrieval(self, client_with_advanced_mock):
        """
        Test retrieval of detailed collection statistics.

        Verifies that all available statistics are captured.
        """
        client, mock_qdrant, mock_base, mock_info = client_with_advanced_mock

        stats = client.get_collection_stats()

        # Verify basic stats
        assert stats["collection_name"] == "test_collection"
        assert stats["total_documents"] == 1500
        assert stats["vector_size"] == 1536
        assert stats["distance_metric"] == "Cosine"

    def test_statistics_with_multiple_collections(self, client_with_advanced_mock):
        """
        Test statistics when multiple collections exist.

        Verifies correct collection is queried.
        """
        client, mock_qdrant, mock_base, mock_info = client_with_advanced_mock

        # Add more collections to the mock
        other_collection = MagicMock()
        other_collection.name = "other_collection"
        test_collection = MagicMock()
        test_collection.name = "test_collection"

        mock_collections_response = MagicMock()
        mock_collections_response.collections = [other_collection, test_collection]
        mock_base.get_collections.return_value = mock_collections_response

        stats = client.get_collection_stats()

        # Should still get stats for the correct collection
        assert stats["collection_name"] == "test_collection"
        mock_base.get_collection.assert_called_with("test_collection")

    def test_statistics_during_indexing(self, client_with_advanced_mock):
        """
        Test statistics retrieval during active indexing.

        Verifies statistics accuracy during ongoing operations.
        """
        client, mock_qdrant, mock_base, mock_info = client_with_advanced_mock

        # Simulate indexing in progress
        mock_info.indexed_vectors_count = 1200  # Less than total
        mock_info.optimizer_status = "indexing"

        stats = client.get_collection_stats()

        # Should reflect indexing state
        assert stats["total_documents"] == 1500

    def test_statistics_error_recovery(self, client_with_advanced_mock):
        """
        Test statistics recovery from transient errors.

        Verifies graceful handling of temporary API failures.
        """
        client, mock_qdrant, mock_base, mock_info = client_with_advanced_mock

        # First call fails
        original_get_collections = mock_base.get_collections.return_value
        mock_base.get_collections.side_effect = Exception("Temporary network error")

        # First attempt should fail gracefully
        stats1 = client.get_collection_stats()
        assert "error" in stats1
        assert "network error" in stats1["error"].lower()

        # Reset for second call to succeed
        mock_base.get_collections.side_effect = None
        mock_base.get_collections.return_value = original_get_collections

        # Second attempt should succeed
        stats2 = client.get_collection_stats()
        assert stats2["total_documents"] == 1500
