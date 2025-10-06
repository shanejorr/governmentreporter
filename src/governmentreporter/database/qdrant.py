"""
Unified Qdrant client for document storage and retrieval.

This module provides a clean, simple interface to Qdrant for storing and
retrieving documents with their embeddings. It handles all aspects of
document management including storage, retrieval, and semantic search.

Python Learning Notes:
    - Qdrant is a vector database optimized for similarity search
    - Embeddings are numerical representations of text
    - Collections group related documents like database tables
    - Semantic search finds similar documents by vector distance
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from qdrant_client import QdrantClient as QdrantBaseClient
from qdrant_client.models import (Distance, FieldCondition, Filter, MatchAny,
                                  MatchValue, PointStruct, Range, VectorParams)

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """
    Represents a document to be stored in Qdrant.

    This dataclass provides a clear structure for documents, making it
    explicit what data is required and optional. Using a dataclass
    ensures type safety and provides automatic initialization.

    Attributes:
        id: Unique identifier for the document
        text: The full text content of the document
        embedding: Vector representation (1536 dimensions for OpenAI)
        metadata: Additional fields like title, date, author, etc.

    Python Learning Notes:
        - @dataclass decorator automatically creates __init__ and other methods
        - Type annotations ensure correct data types
        - Optional fields can be None
    """

    id: str
    text: str
    embedding: List[float]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchResult:
    """
    Represents a search result from Qdrant.

    Provides a clean structure for search results with both the document
    and its relevance score. This makes it easy to work with results
    in a type-safe way.

    Attributes:
        document: The retrieved document
        score: Similarity score (higher is more similar)

    Python Learning Notes:
        - Dataclasses can contain other dataclasses
        - Float scores typically range from 0 to 1
    """

    document: Document
    score: float


class QdrantDBClient:
    """
    Unified client for all Qdrant operations.

    This class provides a clean, simple interface for working with Qdrant.
    It handles document storage, retrieval, and search operations with
    clear, self-documenting methods.

    The client uses consistent patterns:
        - Documents are always stored with their ID as the Qdrant point ID
        - All methods return clear, predictable types
        - Errors are logged and re-raised with context
        - Collections are created automatically when needed

    Attributes:
        db_path: Path to the Qdrant database directory
        client: The underlying Qdrant client instance

    Example:
        # Initialize client
        client = QdrantClient(db_path="./data/qdrant/qdrant_db")

        # Store a document
        doc = Document(
            id="opinion_123",
            text="Supreme Court opinion text...",
            embedding=[0.1, 0.2, ...],  # 1536 dimensions
            metadata={"case": "Roe v. Wade", "year": 1973}
        )
        client.store_document(doc, "scotus_opinions")

        # Retrieve by ID
        retrieved = client.get_document("opinion_123", "scotus_opinions")

        # Search semantically
        results = client.search(query_embedding, "scotus_opinions", limit=5)
        for result in results:
            print(f"Score: {result.score:.3f} - {result.document.metadata['case']}")

    Python Learning Notes:
        - Single class handles all operations (no inheritance needed)
        - Methods are named clearly (store_document, not upsert)
        - Consistent patterns make the API predictable
    """

    # OpenAI text-embedding-3-small configuration
    EMBEDDING_DIMENSION = 1536
    DEFAULT_DISTANCE = Distance.COSINE

    def __init__(
        self,
        db_path: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
    ):
        """
        Initialize the Qdrant client with local storage or remote connection.

        Supports both local file-based Qdrant (for development) and remote
        Qdrant instances (for production). Provide either db_path for local
        or host/port/url for remote connection.

        Args:
            db_path: Path to the local Qdrant database directory (for local mode)
            host: Host address for remote Qdrant server (e.g., "localhost")
            port: Port number for remote Qdrant server (e.g., 6333)
            api_key: API key for remote Qdrant authentication
            url: Full URL for Qdrant cloud instances

        Raises:
            ValueError: If neither local nor remote connection params provided
            ConnectionError: If cannot connect to remote Qdrant

        Python Learning Notes:
            - __init__ is called when creating a new instance
            - Optional parameters allow flexible initialization
            - Multiple connection modes provide flexibility
        """
        # Remote connection mode (prioritize URL, then host/port)
        if url:
            self.client = QdrantBaseClient(url=url, api_key=api_key)
            self.connection_mode = "cloud"
            logger.info(f"Initialized Qdrant client with cloud URL: {url}")
        elif host:
            self.client = QdrantBaseClient(
                host=host, port=port or 6333, api_key=api_key
            )
            self.connection_mode = "remote"
            logger.info(f"Initialized Qdrant client at {host}:{port or 6333}")
        # Local file-based mode
        elif db_path:
            self.db_path = db_path
            self.client = QdrantBaseClient(path=db_path)
            self.connection_mode = "local"
            logger.info(f"Initialized local Qdrant client at {db_path}")
        else:
            raise ValueError(
                "Must provide either db_path for local storage or "
                "host/port/url for remote connection"
            )

    def create_collection(self, collection_name: str) -> bool:
        """
        Create a new collection or ensure it exists.

        Collections in Qdrant are like tables in a database. This method
        creates a collection configured for OpenAI embeddings if it doesn't
        already exist.

        Args:
            collection_name: Name of the collection to create

        Returns:
            True if collection was created or already exists

        Raises:
            Exception: If collection creation fails

        Python Learning Notes:
            - Idempotent operations can be called multiple times safely
            - try/except blocks handle errors gracefully
        """
        try:
            collections = self.client.get_collections().collections
            if any(col.name == collection_name for col in collections):
                logger.debug(f"Collection {collection_name} already exists")
                return True

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.EMBEDDING_DIMENSION,
                    distance=self.DEFAULT_DISTANCE,
                ),
            )
            logger.info(f"Created collection {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise

    def store_document(
        self, document: Document, collection_name: str, create_collection: bool = True
    ) -> bool:
        """
        Store a single document in Qdrant.

        Stores the document with its embedding and metadata. The document ID
        is used directly as the Qdrant point ID for simplicity.

        Args:
            document: Document to store
            collection_name: Collection to store in
            create_collection: Whether to create collection if it doesn't exist

        Returns:
            True if document was stored successfully

        Raises:
            ValueError: If document data is invalid
            Exception: If storage fails

        Example:
            doc = Document(
                id="doc_123",
                text="Document content...",
                embedding=embedding_vector,
                metadata={"author": "John Doe"}
            )
            success = client.store_document(doc, "my_collection")

        Python Learning Notes:
            - Default parameters provide sensible defaults
            - Validation ensures data integrity
            - Boolean returns indicate success/failure
        """
        # Validate document
        if not document.id:
            raise ValueError("Document must have an ID")
        if not document.embedding:
            raise ValueError("Document must have an embedding")
        if len(document.embedding) != self.EMBEDDING_DIMENSION:
            raise ValueError(
                f"Embedding must be {self.EMBEDDING_DIMENSION} dimensions, "
                f"got {len(document.embedding)}"
            )

        # Ensure collection exists
        if create_collection:
            self.create_collection(collection_name)

        # Prepare payload
        payload = {
            "text": document.text,
            **(document.metadata or {}),
        }

        # Create point with UUID - store original ID in payload
        # Generate deterministic UUID from document ID for consistency
        point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, document.id))
        payload["original_id"] = document.id  # Store original ID in payload

        point = PointStruct(
            id=point_uuid,  # Use UUID for Qdrant
            vector=document.embedding,
            payload=payload,
        )

        try:
            self.client.upsert(
                collection_name=collection_name,
                points=[point],
                wait=True,
            )
            logger.debug(f"Stored document {document.id} in {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to store document {document.id}: {e}")
            raise

    def store_documents_batch(
        self,
        documents: List[Document],
        collection_name: str,
        batch_size: int = 100,
        create_collection: bool = True,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[int, List[str]]:
        """
        Store multiple documents in batches.

        Efficiently stores large numbers of documents by processing them
        in batches. Returns counts of successful and failed documents.

        Args:
            documents: List of documents to store
            collection_name: Collection to store in
            batch_size: Number of documents per batch
            create_collection: Whether to create collection if it doesn't exist
            on_progress: Optional callback(processed, total) for progress updates

        Returns:
            Tuple of (success_count, list_of_failed_document_ids)

        Example:
            documents = [doc1, doc2, doc3, ...]
            success, failed_ids = client.store_documents_batch(
                documents,
                "my_collection",
                on_progress=lambda done, total: print(f"{done}/{total}")
            )
            print(f"Stored {success} documents, {len(failed_ids)} failed")

        Python Learning Notes:
            - Batch processing improves performance
            - Callbacks enable progress monitoring
            - Returning failed IDs helps with retry logic
        """
        if not documents:
            return 0, []

        # Validate all documents first
        for doc in documents:
            if not doc.id:
                raise ValueError(f"All documents must have IDs")
            if not doc.embedding or len(doc.embedding) != self.EMBEDDING_DIMENSION:
                raise ValueError(f"Document {doc.id} has invalid embedding")

        # Ensure collection exists
        if create_collection:
            self.create_collection(collection_name)

        success_count = 0
        failed_ids: List[str] = []
        total = len(documents)

        # Process in batches
        for i in range(0, total, batch_size):
            batch = documents[i : i + batch_size]

            # Prepare points
            points = []
            for doc in batch:
                payload = {
                    "text": doc.text,
                    **(doc.metadata or {}),
                }
                # Generate deterministic UUID from document ID
                point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc.id))
                payload["original_id"] = doc.id  # Store original ID in payload

                points.append(
                    PointStruct(
                        id=point_uuid,  # Use UUID for Qdrant
                        vector=doc.embedding,
                        payload=payload,
                    )
                )

            try:
                self.client.upsert(
                    collection_name=collection_name,
                    points=points,
                    wait=True,
                )
                success_count += len(batch)

            except Exception as e:
                logger.error(f"Batch failed: {e}")
                failed_ids.extend(doc.id for doc in batch)

            # Progress callback
            if on_progress:
                processed = min(i + batch_size, total)
                on_progress(processed, total)

        logger.info(
            f"Stored {success_count}/{total} documents in {collection_name}, "
            f"{len(failed_ids)} failed"
        )
        return success_count, failed_ids

    def get_document(
        self, document_id: str, collection_name: str
    ) -> Optional[Document]:
        """
        Retrieve a document by its ID.

        Retrieves a document using its original ID (converts to UUID for lookup).
        Returns None if the document doesn't exist.

        Args:
            document_id: Original ID of the document to retrieve
            collection_name: Collection to search in

        Returns:
            Document if found, None otherwise

        Example:
            doc = client.get_document("doc_123", "my_collection")
            if doc:
                print(f"Found: {doc.text[:100]}...")
            else:
                print("Document not found")

        Python Learning Notes:
            - Optional return type can be None
            - Direct ID lookup is O(1) complexity
            - Graceful handling of missing documents
        """
        try:
            # Convert original ID to UUID for lookup
            point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, document_id))

            results = self.client.retrieve(
                collection_name=collection_name,
                ids=[point_uuid],  # Use UUID for retrieval
                with_payload=True,
                with_vectors=True,
            )

            if not results:
                return None

            point = results[0]
            payload = point.payload or {}

            # Extract vector safely
            vector: List[float] = []
            if point.vector is not None:
                if isinstance(point.vector, list):
                    # Check if it's a nested list (multi-vector)
                    if point.vector and isinstance(point.vector[0], list):
                        vector = point.vector[0]  # Take first vector
                    else:
                        vector = point.vector  # type: ignore

            # Use original ID from payload if available, otherwise use point ID
            doc_id = payload.pop("original_id", str(point.id))

            return Document(
                id=doc_id,  # Return original document ID
                text=payload.pop("text", ""),
                embedding=vector,
                metadata=payload,  # Remaining fields are metadata
            )

        except Exception as e:
            logger.debug(f"Document {document_id} not found: {e}")
            return None

    def document_exists(self, document_id: str, collection_name: str) -> bool:
        """
        Check if a document exists in a collection.

        Efficient existence check without retrieving the full document.

        Args:
            document_id: Original ID to check
            collection_name: Collection to check in

        Returns:
            True if document exists, False otherwise

        Python Learning Notes:
            - Existence checks are more efficient than full retrieval
            - Boolean returns are clear and simple
        """
        try:
            # Convert original ID to UUID for lookup
            point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, document_id))

            results = self.client.retrieve(
                collection_name=collection_name,
                ids=[point_uuid],  # Use UUID for retrieval
                with_payload=False,
                with_vectors=False,
            )
            return len(results) > 0

        except Exception:
            return False

    def search(
        self,
        query_embedding: List[float],
        collection_name: str,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        query_filter: Optional[Dict] = None,
    ) -> List[SearchResult]:
        """
        Search for similar documents using semantic search.

        Finds documents similar to the query embedding using vector similarity.
        Results are sorted by similarity score (highest first).

        Args:
            query_embedding: Query vector (same dimensions as stored embeddings)
            collection_name: Collection to search in
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            metadata_filter: Filter by metadata fields (e.g., {"year": 2024})

        Returns:
            List of SearchResult objects sorted by score

        Example:
            # Search for similar documents
            results = client.search(
                query_embedding=query_vector,
                collection_name="scotus_opinions",
                limit=5,
                score_threshold=0.7,
                metadata_filter={"year": 2024}
            )

            for result in results:
                print(f"Score: {result.score:.3f}")
                print(f"Text: {result.document.text[:200]}...")

        Python Learning Notes:
            - Semantic search finds conceptually similar documents
            - Filters narrow results to specific criteria
            - List comprehensions transform data efficiently
        """
        # Validate embedding
        if len(query_embedding) != self.EMBEDDING_DIMENSION:
            raise ValueError(
                f"Query embedding must be {self.EMBEDDING_DIMENSION} dimensions"
            )

        # Build filter if provided
        filter_obj = None

        # Use query_filter if provided (complex filter from handlers)
        if query_filter:
            filter_obj = query_filter
        # Otherwise use simple metadata_filter
        elif metadata_filter:
            conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in metadata_filter.items()
            ]
            filter_obj = Filter(must=conditions)  # type: ignore[arg-type]

        try:
            # Perform search
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=filter_obj,
                score_threshold=score_threshold,
            )

            # Convert to SearchResult objects
            search_results = []
            for point in results:
                payload = point.payload or {}
                # Extract vector safely
                vector: List[float] = []
                if point.vector is not None:
                    if isinstance(point.vector, list):
                        # Check if it's a nested list (multi-vector)
                        if point.vector and isinstance(point.vector[0], list):
                            vector = point.vector[0]  # Take first vector
                        else:
                            vector = point.vector  # type: ignore

                # Use original ID from payload if available
                doc_id = payload.pop("original_id", str(point.id))

                doc = Document(
                    id=doc_id,  # Return original document ID
                    text=payload.pop("text", ""),
                    embedding=vector,
                    metadata=payload,
                )
                search_results.append(SearchResult(document=doc, score=point.score))

            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def semantic_search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        query_filter: Optional[Dict] = None,
    ) -> List[SearchResult]:
        """
        Semantic search method for MCP server compatibility.

        This is a wrapper around the search method that matches the interface
        expected by the MCP server handlers.

        Args:
            collection_name: Collection to search in
            query_vector: Query embedding vector
            limit: Maximum number of results
            query_filter: Optional filter conditions (can be complex Qdrant filter)

        Returns:
            List of SearchResult objects
        """
        return self.search(
            query_embedding=query_vector,
            collection_name=collection_name,
            limit=limit,
            query_filter=query_filter,  # Pass directly as query_filter for complex filters
        )

    def delete_document(self, document_id: str, collection_name: str) -> bool:
        """
        Delete a document from a collection.

        Args:
            document_id: Original ID of document to delete
            collection_name: Collection to delete from

        Returns:
            True if deletion was successful

        Python Learning Notes:
            - Deletion is idempotent (safe to call multiple times)
            - Boolean return indicates success
        """
        try:
            # Convert original ID to UUID for deletion
            point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, document_id))

            self.client.delete(
                collection_name=collection_name,
                points_selector=[point_uuid],  # Use UUID for deletion
            )
            logger.debug(f"Deleted document {document_id} from {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete an entire collection and all its documents.

        Args:
            collection_name: Collection to delete

        Returns:
            True if deletion was successful

        Warning:
            This permanently deletes all documents in the collection!

        Python Learning Notes:
            - Destructive operations should be used carefully
            - Clear documentation prevents accidents
        """
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a collection.

        Args:
            collection_name: Collection to inspect

        Returns:
            Dictionary with collection statistics or None if not found

        Python Learning Notes:
            - Metadata helps monitor system state
            - Dictionary returns are flexible
        """
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status,
            }

        except Exception as e:
            logger.debug(f"Collection {collection_name} not found: {e}")
            return None

    def list_collections(self) -> List[str]:
        """
        List all collections in the database.

        Returns:
            List of collection names

        Python Learning Notes:
            - List comprehensions create new lists efficiently
            - Simple return types are easy to use
        """
        try:
            collections = self.client.get_collections().collections
            return [col.name for col in collections]

        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
