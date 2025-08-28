"""
Qdrant database ingestion utilities.

This module provides specialized functionality for ingesting documents into Qdrant,
a vector database used for semantic search. It extends the basic Qdrant client with
ingestion-specific features like duplicate detection, batch operations, and
collection management.

The module focuses on:
    - Efficient batch document insertion with progress tracking
    - Duplicate detection to avoid redundant storage
    - Collection initialization with proper vector configuration
    - Atomic operations ensuring data consistency
    - Performance monitoring and error recovery

Python Learning Notes:
    - Qdrant stores vectors with associated metadata (payloads)
    - Collections in Qdrant are like tables in traditional databases
    - Vector similarity uses cosine distance for semantic matching
    - Batch operations improve performance for large datasets
"""

import hashlib
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from qdrant_client.models import Distance, PointStruct, VectorParams

from .qdrant_client import QdrantDBClient

logger = logging.getLogger(__name__)


class QdrantIngestionClient:
    """
    Specialized Qdrant client for document ingestion operations.

    This class extends the basic Qdrant functionality with ingestion-specific
    features like duplicate detection, batch upsert with progress tracking,
    and collection initialization. It provides a high-level interface for
    efficiently loading large document sets into Qdrant for semantic search.

    The client handles:
        - Collection creation and configuration
        - Duplicate document detection
        - Batch insertion with progress callbacks
        - Consistent ID generation for document chunks
        - Collection statistics and monitoring

    Attributes:
        collection_name (str): Name of the Qdrant collection to use
        embedding_dimension (int): Dimension of embedding vectors (default: 1536)
        db_client (QdrantDBClient): Underlying Qdrant database client

    Example:
        # Initialize client for Supreme Court opinions
        client = QdrantIngestionClient("scotus_opinions", "./qdrant_db")

        # Initialize with custom database path and embedding dimension
        client = QdrantIngestionClient(
            "scotus_opinions",
            "/path/to/custom/qdrant_db",
            embedding_dimension=768
        )

        # Prepare documents and embeddings
        documents = [{"document_id": "123", "text": "...", "metadata": {...}}]
        embeddings = [[0.1, 0.2, ...], ...]  # 1536-dimensional vectors

        # Ingest with progress tracking
        def progress(success, failed):
            print(f"Processed: {success} successful, {failed} failed")

        successful, failed = client.batch_upsert_documents(
            documents, embeddings, progress_callback=progress
        )

        # Check collection statistics
        stats = client.get_collection_stats()
        print(f"Total documents: {stats['total_documents']}")

    Python Learning Notes:
        - Classes encapsulate related data and behavior
        - __init__ is the constructor called when creating instances
        - Type hints improve code clarity and IDE support
        - Callbacks allow customizable progress reporting
    """

    def __init__(
        self, collection_name: str, db_path: str, embedding_dimension: int = 1536
    ):
        """
        Initialize the Qdrant ingestion client.

        Creates or connects to a Qdrant collection configured for the specified
        embedding dimension. The collection uses cosine distance for similarity
        matching, which works well for normalized embeddings from models like
        text-embedding-3-small.

        Args:
            collection_name (str): Name of the Qdrant collection to use.
                Collections are created if they don't exist. Names should be
                descriptive (e.g., "scotus_opinions", "executive_orders").
            db_path (str): Path to the Qdrant database directory.
                Can be absolute or relative path. The directory will be created
                if it doesn't exist. This parameter is required.
            embedding_dimension (int): Dimension of embedding vectors.
                Default is 1536 for text-embedding-3-small. Must match the
                dimension of embeddings you'll be storing.

        Raises:
            Exception: If collection creation or connection fails

        Python Learning Notes:
            - self stores instance state across method calls
            - Methods can be called during initialization
            - Default parameters provide sensible defaults
        """
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension
        self.db_client = QdrantDBClient(db_path=db_path)
        self.ensure_collection_exists()

    def ensure_collection_exists(self) -> None:
        """
        Create the collection if it doesn't exist with proper configuration.

        Sets up the collection with:
            - Cosine distance metric for similarity (best for normalized vectors)
            - Proper vector dimension matching the embedding model
            - Optimized indexing parameters for search performance

        This method is idempotent - it's safe to call multiple times as it
        only creates the collection if it doesn't already exist.

        Raises:
            Exception: If collection creation fails or Qdrant is unavailable

        Python Learning Notes:
            - try/except blocks handle potential errors
            - List comprehension [x for x in items] creates new lists
            - Logging provides visibility into operations
        """
        try:
            # Check if collection exists
            collections = self.db_client.client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating new collection: {self.collection_name}")
                self.db_client.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE,  # Best for semantic similarity
                    ),
                )
                logger.info(f"Collection {self.collection_name} created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")

        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise

    def document_exists(self, document_id: str) -> bool:
        """
        Check if a document already exists in the collection.

        This method helps avoid duplicate ingestion by checking if a document
        with the given ID already exists. It's useful for incremental updates
        where you only want to add new documents.

        Args:
            document_id (str): ID of the document to check. This should be
                the same ID format used when inserting documents.

        Returns:
            bool: True if document exists in the collection, False otherwise.
                Returns False on errors to allow ingestion to proceed.

        Example:
            # Skip documents that already exist
            if not client.document_exists("scotus_opinion_123"):
                client.batch_upsert_documents([doc], [embedding])
            else:
                print("Document already ingested, skipping")

        Python Learning Notes:
            - retrieve() fetches documents by ID without searching
            - len() returns the number of items in a collection
            - try/except with return ensures function always returns
        """
        try:
            # Try to retrieve the document
            result = self.db_client.client.retrieve(
                collection_name=self.collection_name,
                ids=[document_id],
                with_payload=False,  # Don't need the data, just existence
                with_vectors=False,  # Don't need the vectors either
            )
            return len(result) > 0

        except Exception as e:
            logger.warning(f"Error checking document existence: {e}")
            return False  # Assume doesn't exist on error

    def batch_upsert_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
        batch_size: int = 100,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[int, int]:
        """
        Insert or update multiple documents in batches.

        This method efficiently inserts large numbers of documents by processing
        them in batches. It generates unique IDs for each document chunk and
        handles errors gracefully. Progress can be tracked via an optional callback.

        The method is atomic at the batch level - either all documents in a batch
        succeed or all fail. This ensures data consistency while allowing partial
        progress on large ingestion jobs.

        Args:
            documents (List[Dict[str, Any]]): List of document payloads to store.
                Each document should contain at minimum a "document_id" field
                and typically includes text, metadata, and chunk information.
            embeddings (List[List[float]]): Corresponding embedding vectors.
                Must have the same length as documents. Each embedding should
                match the collection's configured dimension.
            batch_size (int): Number of documents to upsert in each batch.
                Default is 100. Larger batches are more efficient but use more
                memory. Maximum depends on Qdrant configuration.
            progress_callback (Optional[Callable[[int, int], None]]): Optional
                callback function called after each batch. Receives two arguments:
                (successful_count, failed_count) for the batch.

        Returns:
            Tuple[int, int]: Total counts as (successful_count, failed_count).
                Successful count includes all documents successfully inserted.
                Failed count includes documents that couldn't be inserted.

        Raises:
            ValueError: If the number of documents doesn't match embeddings

        Example:
            # Prepare data
            documents = [
                {"document_id": "1", "text": "First document", "chunk_index": 0},
                {"document_id": "2", "text": "Second document", "chunk_index": 0}
            ]
            embeddings = [[0.1, 0.2, ...], [0.3, 0.4, ...]]

            # Ingest with progress tracking
            def show_progress(success, failed):
                print(f"Batch complete: {success} succeeded, {failed} failed")

            total_success, total_failed = client.batch_upsert_documents(
                documents, embeddings, progress_callback=show_progress
            )

            print(f"Ingestion complete: {total_success} documents added")

        Python Learning Notes:
            - Optional[Callable] allows None or a function as parameter
            - Tuple[int, int] returns exactly two integers
            - zip() pairs elements from multiple sequences
            - Slicing [i:i+n] extracts portions of lists
        """
        if len(documents) != len(embeddings):
            raise ValueError("Number of documents must match number of embeddings")

        successful = 0
        failed = 0

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_embeddings = embeddings[i : i + batch_size]

            # Create points for this batch
            points = []
            for doc, embedding in zip(batch_docs, batch_embeddings):
                # Generate a unique ID for this chunk
                chunk_id = self._generate_chunk_id(doc)

                point = PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload=doc,  # Store document as payload
                )
                points.append(point)

            try:
                # Upsert the batch (insert or update)
                self.db_client.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                    wait=True,  # Wait for operation to complete
                )
                successful += len(points)

                if progress_callback:
                    progress_callback(len(points), 0)

            except Exception as e:
                logger.error(f"Batch upsert failed: {e}")
                failed += len(points)

                if progress_callback:
                    progress_callback(0, len(points))

        return successful, failed

    def _generate_chunk_id(self, document: Dict[str, Any]) -> str:
        """
        Generate a unique ID for a document chunk.

        Uses a hash of the document ID and chunk index to ensure uniqueness
        and consistent length. This approach ensures that the same document
        chunk always gets the same ID, enabling idempotent updates.

        Args:
            document (Dict[str, Any]): Document payload containing at minimum
                a "document_id" field and optionally a "chunk_index" field.

        Returns:
            str: Unique hexadecimal string ID for this chunk. The ID is
                deterministic - the same input always produces the same ID.

        Example:
            doc = {"document_id": "scotus_123", "chunk_index": 2}
            chunk_id = client._generate_chunk_id(doc)
            # Returns something like "a3f5d8b2c9e1..."

        Python Learning Notes:
            - get() returns a default value if key doesn't exist
            - f-strings embed expressions in strings
            - hashlib provides cryptographic hash functions
            - encode() converts strings to bytes for hashing
        """
        # Create a unique ID based on document ID and chunk index
        doc_id = document.get("document_id", "unknown")
        chunk_index = document.get("chunk_index", 0)

        # Create a deterministic ID
        id_string = f"{doc_id}_chunk_{chunk_index}"

        # Hash it to ensure consistent length and format
        id_hash = hashlib.md5(id_string.encode()).hexdigest()

        return id_hash

    def _extract_vector_config(self, vectors_config) -> Dict[str, Any]:
        """
        Extract vector configuration from Qdrant collection info.

        Handles both VectorParams object and dictionary configurations.

        Args:
            vectors_config: Vector configuration from Qdrant collection info

        Returns:
            Dict[str, Any]: Dictionary with vector_size and distance
        """
        try:
            if hasattr(vectors_config, "size") and hasattr(vectors_config, "distance"):
                # VectorParams object
                return {
                    "vector_size": vectors_config.size,
                    "distance": vectors_config.distance,
                }
            elif isinstance(vectors_config, dict):
                # Dictionary configuration
                default_config = (
                    next(iter(vectors_config.values())) if vectors_config else None
                )
                if (
                    default_config
                    and hasattr(default_config, "size")
                    and hasattr(default_config, "distance")
                ):
                    return {
                        "vector_size": default_config.size,
                        "distance": default_config.distance,
                    }

            # Fallback for unknown configuration types
            return {"vector_size": "unknown", "distance": "unknown"}

        except Exception:
            return {"vector_size": "unknown", "distance": "unknown"}

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.

        Retrieves comprehensive information about the collection's current state,
        including document counts, indexing status, and configuration. Useful
        for monitoring ingestion progress and debugging issues.

        Returns:
            Dict[str, Any]: Dictionary with collection statistics including:
                - collection_name: Name of the collection
                - total_documents: Number of points/documents in collection
                - vectors_count: Number of vectors (may differ during indexing)
                - indexed_vectors: Number of indexed vectors ready for search
                - status: Collection status (green/yellow/red)
                - config: Collection configuration (vector size, distance metric)

                Returns error dictionary if retrieval fails.

        Example:
            stats = client.get_collection_stats()
            print(f"Collection: {stats['collection_name']}")
            print(f"Documents: {stats['total_documents']}")
            print(f"Status: {stats['status']}")

            if stats['total_documents'] == 0:
                print("Collection is empty, ready for ingestion")

        Python Learning Notes:
            - Dictionary literals {} create key-value mappings
            - or operator returns 0 if value is None
            - Nested dictionaries organize related data
            - try/except returns error info instead of crashing
        """
        try:
            info = self.db_client.client.get_collection(self.collection_name)

            return {
                "collection_name": self.collection_name,
                "total_documents": info.points_count or 0,
                "vectors_count": info.vectors_count or 0,
                "indexed_vectors": info.indexed_vectors_count or 0,
                "status": info.status,
                "config": self._extract_vector_config(info.config.params.vectors),
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
