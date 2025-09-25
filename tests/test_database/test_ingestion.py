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
from unittest.mock import MagicMock, Mock, patch, call

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

    @patch('governmentreporter.database.ingestion.QdrantDBClient')
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
            collection_name="test_collection",
            db_path="./test_db"
        )

        # Verify initialization
        assert client.collection_name == "test_collection"
        assert client.client == mock_client_instance

        # Verify QdrantDBClient initialization
        mock_qdrant_client_class.assert_called_once_with("./test_db")

        # Verify collection creation
        mock_client_instance.create_collection.assert_called_once_with("test_collection")

    @patch('governmentreporter.database.ingestion.QdrantDBClient')
    def test_initialization_with_default_path(self, mock_qdrant_client_class):
        """
        Test initialization with default database path.

        Verifies that the default path "./qdrant_db" is used
        when no path is specified.
        """
        mock_client_instance = MagicMock()
        mock_qdrant_client_class.return_value = mock_client_instance

        # Initialize without specifying path
        client = QdrantIngestionClient("test_collection")

        # Verify default path used
        mock_qdrant_client_class.assert_called_once_with("./qdrant_db")

    def test_initialization_without_collection_name(self):
        """
        Test that initialization fails without collection name.

        Verifies that ValueError is raised when collection_name
        is empty or not provided.
        """
        with pytest.raises(ValueError) as exc_info:
            QdrantIngestionClient("")

        assert "collection_name is required" in str(exc_info.value)

    @patch('governmentreporter.database.ingestion.QdrantDBClient')
    def test_initialization_collection_creation_failure(self, mock_qdrant_client_class):
        """
        Test handling of collection creation failure during initialization.

        Verifies that exceptions during collection creation are
        properly propagated.
        """
        mock_client_instance = MagicMock()
        mock_qdrant_client_class.return_value = mock_client_instance

        # Mock collection creation failure
        mock_client_instance.create_collection.side_effect = Exception("Connection failed")

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
        with patch('governmentreporter.database.ingestion.QdrantDBClient') as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # Mock successful batch storage
            mock_instance.store_documents_batch.return_value = (0, [])  # Default: all succeed

            client = QdrantIngestionClient("test_collection")
            return client, mock_instance

    @pytest.fixture
    def sample_payloads(self):
        """
        Create sample payloads for testing.

        These payloads simulate the output from the processing pipeline.
        """
        payloads = []
        for i in range(3):
            payload = {
                "chunk_metadata": {
                    "text": f"Chunk {i} text content",
                    "chunk_index": i,
                    "total_chunks": 3,
                    "start_char": i * 100,
                    "end_char": (i + 1) * 100
                },
                "document_metadata": {
                    "title": "Test Document",
                    "date": "2024-01-15",
                    "type": "opinion",
                    "source": "courtlistener"
                },
                "llm_extracted_metadata": {
                    "summary": "Test summary",
                    "topics": ["law", "testing"],
                    "entities": ["Supreme Court", "United States"]
                },
                "document_id": "doc-123"
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

    def test_batch_upsert_success(self, client_with_mock, sample_payloads, sample_embeddings):
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
            sample_payloads,
            sample_embeddings,
            batch_size=100
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
        assert doc.metadata["document_id"] == "doc-123"
        assert doc.metadata["chunk_metadata"]["chunk_index"] == 0

    def test_batch_upsert_with_missing_chunk_text(self, client_with_mock, sample_embeddings):
        """
        Test handling of payloads without chunk text.

        Verifies graceful handling when chunk_metadata doesn't contain text.
        """
        client, mock_qdrant = client_with_mock

        # Payload without text in chunk_metadata
        payloads = [
            {
                "chunk_metadata": {
                    "chunk_index": 0
                    # No "text" field
                },
                "document_id": "doc-123"
            }
        ]

        mock_qdrant.store_documents_batch.return_value = (1, [])

        # Should handle missing text gracefully
        success, failed = client.batch_upsert_documents(
            payloads,
            [sample_embeddings[0]],
            batch_size=100
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
                sample_payloads,
                mismatched_embeddings,
                batch_size=100
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

    def test_batch_upsert_with_failures(self, client_with_mock, sample_payloads, sample_embeddings):
        """
        Test handling of partial storage failures.

        Verifies that failures are properly counted and reported.
        """
        client, mock_qdrant = client_with_mock

        # Mock partial failure (2 succeed, 1 fails)
        mock_qdrant.store_documents_batch.return_value = (2, ["doc-123_chunk_2"])

        # Perform batch upsert
        success, failed = client.batch_upsert_documents(
            sample_payloads,
            sample_embeddings,
            batch_size=100
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

        # Mix of valid and invalid payloads
        payloads = [
            {
                "chunk_metadata": {"text": "Valid text", "chunk_index": 0},
                "document_id": "doc-1"
            },
            None,  # Invalid payload
            {
                "chunk_metadata": {"text": "Another valid", "chunk_index": 2},
                "document_id": "doc-3"
            }
        ]

        # Mock storage of successfully converted documents
        mock_qdrant.store_documents_batch.return_value = (2, [])

        # Perform batch upsert
        success, failed = client.batch_upsert_documents(
            payloads,
            sample_embeddings,
            batch_size=100
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
        client.batch_upsert_documents(
            sample_payloads,
            sample_embeddings,
            batch_size=50
        )

        # Verify batch size was passed
        call_args = mock_qdrant.store_documents_batch.call_args
        assert call_args.kwargs["batch_size"] == 50

    def test_batch_upsert_without_document_id(self, client_with_mock, sample_embeddings):
        """
        Test handling of payloads without document_id.

        Verifies that unique IDs are generated when document_id is missing.
        """
        client, mock_qdrant = client_with_mock

        # Payload without document_id
        payloads = [
            {
                "chunk_metadata": {
                    "text": "Text without doc ID",
                    "chunk_index": 0
                }
                # No document_id
            }
        ]

        mock_qdrant.store_documents_batch.return_value = (1, [])

        # Should generate unique ID
        success, failed = client.batch_upsert_documents(
            payloads,
            [sample_embeddings[0]],
            batch_size=100
        )

        assert success == 1

        # Verify UUID was generated
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        assert documents[0].id is not None
        assert "_chunk_0" in documents[0].id

    def test_batch_upsert_complete_failure(self, client_with_mock, sample_payloads, sample_embeddings):
        """
        Test handling of complete storage failure.

        Verifies that storage exceptions are handled gracefully.
        """
        client, mock_qdrant = client_with_mock

        # Mock complete storage failure
        mock_qdrant.store_documents_batch.side_effect = Exception("Database unavailable")

        # Perform batch upsert
        success, failed = client.batch_upsert_documents(
            sample_payloads,
            sample_embeddings,
            batch_size=100
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
        with patch('governmentreporter.database.ingestion.QdrantDBClient') as mock_class:
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
        with patch('governmentreporter.database.ingestion.QdrantDBClient') as mock_class:
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

        # Step 2: Prepare document chunks
        payloads = []
        embeddings = []
        for i in range(10):
            payload = {
                "chunk_metadata": {
                    "text": f"Chunk {i} of Supreme Court opinion",
                    "chunk_index": i,
                    "total_chunks": 10
                },
                "document_metadata": {
                    "title": "Test v. United States",
                    "date": "2024-01-15",
                    "court": "SCOTUS"
                },
                "llm_extracted_metadata": {
                    "summary": "Important legal ruling",
                    "topics": ["constitutional law", "civil rights"]
                },
                "document_id": "scotus-2024-001"
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

        # Create chunks for 3 different documents
        for doc_idx in range(3):
            for chunk_idx in range(5):
                payload = {
                    "chunk_metadata": {
                        "text": f"Document {doc_idx}, Chunk {chunk_idx}",
                        "chunk_index": chunk_idx,
                        "total_chunks": 5
                    },
                    "document_metadata": {
                        "title": f"Document {doc_idx}"
                    },
                    "document_id": f"doc-{doc_idx}"
                }
                all_payloads.append(payload)
                all_embeddings.append([0.1 + (doc_idx * 0.1) + (chunk_idx * 0.01)] * 1536)

        # Ingest all chunks
        mock_qdrant.store_documents_batch.return_value = (15, [])
        success, failed = client.batch_upsert_documents(
            all_payloads, all_embeddings
        )

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

        # Prepare test data
        payloads = [
            {
                "chunk_metadata": {"text": f"Chunk {i}", "chunk_index": i},
                "document_id": "doc-1"
            }
            for i in range(5)
        ]
        embeddings = [[0.1] * 1536 for _ in range(5)]

        # First attempt: partial failure
        mock_qdrant.store_documents_batch.return_value = (3, ["doc-1_chunk_3", "doc-1_chunk_4"])
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
        with patch('governmentreporter.database.ingestion.QdrantDBClient') as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance
            client = QdrantIngestionClient("test_collection")
            return client, mock_instance

    def test_payload_without_chunk_metadata(self, client_with_mock):
        """
        Test handling of payload without chunk_metadata.

        Verifies graceful handling when chunk_metadata is missing.
        """
        client, mock_qdrant = client_with_mock

        payloads = [
            {
                "document_id": "doc-1"
                # No chunk_metadata
            }
        ]
        embeddings = [[0.1] * 1536]

        mock_qdrant.store_documents_batch.return_value = (1, [])

        # Should handle missing chunk_metadata
        success, failed = client.batch_upsert_documents(payloads, embeddings)

        assert success == 1
        assert failed == 0

        # Verify document created with empty text
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        assert documents[0].text == ""

    def test_payload_with_non_dict_chunk_metadata(self, client_with_mock):
        """
        Test handling of non-dict chunk_metadata.

        Verifies that non-dict chunk_metadata is handled safely.
        """
        client, mock_qdrant = client_with_mock

        payloads = [
            {
                "chunk_metadata": "not a dict",  # Wrong type
                "document_id": "doc-1"
            }
        ]
        embeddings = [[0.1] * 1536]

        mock_qdrant.store_documents_batch.return_value = (1, [])

        # Should handle invalid chunk_metadata
        success, failed = client.batch_upsert_documents(payloads, embeddings)

        assert success == 1
        assert failed == 0

        # Verify document created with empty text
        call_args = mock_qdrant.store_documents_batch.call_args
        documents = call_args[0][0]
        assert documents[0].text == ""

    def test_very_large_batch(self, client_with_mock):
        """
        Test handling of very large batches.

        Verifies that large batches are processed correctly.
        """
        client, mock_qdrant = client_with_mock

        # Create large batch
        large_size = 1000
        payloads = []
        embeddings = []
        for i in range(large_size):
            payloads.append({
                "chunk_metadata": {"text": f"Chunk {i}", "chunk_index": i},
                "document_id": f"doc-{i // 100}"  # 10 docs, 100 chunks each
            })
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

        # Payloads with same document_id but different chunks
        payloads = [
            {
                "chunk_metadata": {"text": f"Chunk {i}", "chunk_index": i},
                "document_id": "same-doc"
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