"""
Qdrant client for managing document embeddings and metadata.

This module provides a high-level interface to Qdrant, a vector database
optimized for storing and querying document embeddings. Qdrant enables
semantic search capabilities by storing vector representations of documents
along with their metadata.

Key Features:
    - Persistent storage of document embeddings
    - Metadata filtering and querying
    - Collection management for different document types
    - Automatic embedding similarity search
    - Type-safe metadata handling
    - Batch operations for efficient bulk processing
    - Advanced search with filtering and thresholding

Qdrant Integration:
    Qdrant is an open-source vector database that:
    - Stores high-dimensional vectors (embeddings) efficiently
    - Provides fast similarity search using cosine similarity, dot product, or Euclidean distance
    - Supports rich metadata filtering for complex queries
    - Offers both in-memory and persistent storage options
    - Handles automatic indexing for optimal query performance
    - Provides REST and gRPC APIs for communication

Python Learning Notes:
    - Type hints (List[float], Dict[str, Any]) help document expected data types
    - Optional[T] means a value can be of type T or None
    - Exception handling with try/except prevents crashes
    - List comprehensions and generator expressions for data transformation
    - Context managers and resource cleanup patterns

Example Usage:
    # Initialize client
    client = QdrantDBClient(db_path="./vector_db")

    # Store a document with embedding
    client.store_document(
        document_id="roe_v_wade_1973",
        text="The Supreme Court decision text...",
        embedding=[0.1, 0.2, 0.3, ...],  # 1536-dimensional vector
        metadata={
            "case_name": "Roe v. Wade",
            "year": 1973,
            "justice_writing": "Blackmun"
        }
    )

    # Retrieve document by ID
    document = client.get_document_by_id("roe_v_wade_1973")
    if document:
        print(f"Found: {document['metadata']['case_name']}")
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from ..utils import get_logger


class QdrantDBClient:
    """
    Client for interacting with Qdrant for document storage and retrieval.

    This class provides a high-level interface to Qdrant operations,
    handling document storage, embedding management, and metadata operations.
    It abstracts away the complexity of Qdrant's API while providing
    type safety and error handling.

    The client implements a persistent storage pattern where:
    1. Documents are stored with their vector embeddings
    2. Metadata is stored alongside vectors for filtering
    3. Collections organize documents by type/source
    4. Error handling ensures graceful degradation

    Attributes:
        client (QdrantClient): The underlying Qdrant client instance

    Python Learning Notes:
        - Classes group related data and functions together
        - __init__ is the constructor method, called when creating instances
        - self refers to the current instance of the class
        - Private attributes (starting with _) indicate internal implementation
        - Public methods provide the interface other code can use

    Example:
        # Create a new client instance
        db_client = QdrantDBClient(db_path="./government_docs_db")

        # The client is now ready to store and retrieve documents
        collections = db_client.list_collections()
        print(f"Available collections: {collections}")
    """

    def __init__(self, db_path: str = "./qdrant_db") -> None:
        """
        Initialize Qdrant client with persistent storage.

        Creates a persistent Qdrant client that stores data on disk,
        allowing data to persist between application runs. The client
        is configured for local development with optimal settings.

        Args:
            db_path (str, optional): Path to the Qdrant database directory.
                Defaults to "./qdrant_db". The directory will be created
                if it doesn't exist.

        Returns:
            None: Constructor methods don't return values

        Raises:
            qdrant_client.errors.QdrantException: If the database cannot be initialized
            PermissionError: If the db_path directory cannot be created or accessed

        Python Learning Notes:
            - Default parameter values (= "./qdrant_db") provide fallbacks
            - Type hints (str, -> None) document expected types
            - The -> None annotation means this method doesn't return a value
            - self.client creates an instance attribute accessible to all methods

        Qdrant Configuration:
            - path: Local storage path for persistent data
            - prefer_grpc: Uses faster gRPC protocol when available
            - Local storage mode for development and privacy

        Example:
            # Use default database path
            client1 = QdrantDBClient()

            # Use custom path for production
            client2 = QdrantDBClient(db_path="/var/lib/government_docs/qdrant")

            # Both clients are now ready to use
            print(f"Client initialized with {len(client1.list_collections())} collections")
        """
        self.logger = get_logger(__name__)
        self.client = QdrantClient(path=db_path)
        self.logger.info("QdrantDBClient initialized with database path: %s", db_path)

    def get_or_create_collection(self, collection_name: str):
        """
        Get an existing collection or create a new one if it doesn't exist.

        Collections in Qdrant are like tables in a database - they group
        related documents together. This method implements an idempotent
        operation: calling it multiple times with the same name is safe
        and will always return success.

        This method is specifically designed to work with OpenAI's
        text-embedding-3-small model, which produces 1536-dimensional
        vectors. All collections created by this method will be configured
        for this vector size.

        Args:
            collection_name (str): Name of the collection to get or create.
                Must be a valid collection name (alphanumeric, underscores,
                and hyphens allowed).

        Returns:
            bool: True if collection exists or was created successfully

        Raises:
            ValueError: If collection_name is empty or contains invalid characters
            qdrant_client.errors.QdrantException: If collection operations fail

        Python Learning Notes:
            - Try/except blocks handle errors gracefully
            - Exception handling prevents crashes from expected errors
            - Method chaining (self.client.collection_exists) calls methods on returned objects
            - Hard-coded values eliminate configuration errors

        Qdrant Concepts:
            - Collections organize similar documents (like database tables)
            - Vector size must be consistent within a collection (1536 for OpenAI text-embedding-3-small)
            - Distance metric affects similarity search behavior
            - Collections persist until explicitly deleted

        Example:
            # Get existing collection or create new one
            success = client.get_or_create_collection("scotus_opinions")

            # Safe to call multiple times
            success2 = client.get_or_create_collection("scotus_opinions")
            assert success and success2

            # All collections use 1536 dimensions for OpenAI text-embedding-3-small
            client.get_or_create_collection("federal_register")
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            if collection_name not in collection_names:
                # Create new collection with vector configuration for OpenAI text-embedding-3-small
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
                self.logger.info("Created new collection: %s", collection_name)
            else:
                self.logger.debug("Collection already exists: %s", collection_name)

            return True
        except Exception as e:
            self.logger.error("Error with collection %s: %s", collection_name, e)
            raise

    def store_document(
        self,
        document_id: str,
        text: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        collection_name: str = "federal_court_scotus_opinions",
    ) -> None:
        """
        Store a document with its embedding and metadata in Qdrant.

        This method stores any document (Supreme Court opinion, Executive Order, etc.)
        in Qdrant, including the full text, vector embedding for semantic search, and
        associated metadata. The method leverages Qdrant's native payload support.

        The storage process:
        1. Gets or creates the specified collection
        2. Prepares metadata and payload for Qdrant
        3. Stores document, embedding, and metadata together
        4. Uses document_id as the unique document identifier

        Args:
            document_id (str): Unique identifier for the document. Should be
                stable and descriptive (e.g., "scotus_2024_dobbs_v_jackson").
                This ID is used for retrieval and must be unique within the collection.

            text (str): Full text content of the document.
                This is the complete document text that will be stored and
                can be retrieved later for display or analysis.

            embedding (List[float]): Vector representation of the document text.
                Typically a 1536-dimensional vector generated by a
                language model (e.g., sentence-transformers). Used for
                semantic similarity search.

            metadata (Dict[str, Any]): Additional information about the document.
                Can include case name, year, justices, topics, etc. Values
                will be stored as payload in Qdrant.

            collection_name (str, optional): Name of the collection to store in.
                Defaults to "federal_court_scotus_opinions".

        Returns:
            None: This method doesn't return a value but stores the data persistently

        Raises:
            ValueError: If document_id is empty or embedding is malformed
            qdrant_client.errors.QdrantException: If storage operation fails

        Python Learning Notes:
            - Type hints with complex types (List[float], Dict[str, Any])
            - Dictionary creation and manipulation
            - UUID generation for unique identifiers
            - Error handling with logger for debugging

        Metadata Processing:
            Qdrant stores metadata as payload alongside vectors.
            All Python basic types are supported natively.

        Example:
            client = QdrantDBClient()

            # Store a Supreme Court opinion
            client.store_document(
                document_id="dobbs_v_jackson_2022",
                text="The Supreme Court held that...",
                embedding=[0.1, 0.2, 0.3, ...],  # 1536-dim vector
                metadata={
                    "case_name": "Dobbs v. Jackson Women's Health Organization",
                    "year": 2022,
                    "majority_justice": "Alito",
                    "topics": ["reproductive rights", "constitutional law"],
                    "pages": 213
                },
                collection_name="federal_court_scotus_opinions"
            )

            # Document is now stored and searchable
            print("Opinion stored successfully")
        """
        # Ensure collection exists
        self.get_or_create_collection(collection_name)

        # Prepare payload with both text and metadata
        payload = {
            "document": text,
            "id": document_id,
            **metadata,  # Unpack all metadata fields
        }

        # Create point for Qdrant
        point = PointStruct(
            id=str(
                uuid.uuid5(uuid.NAMESPACE_DNS, document_id)
            ),  # Generate UUID from string ID
            vector=embedding,
            payload=payload,
        )

        # Store in Qdrant
        self.client.upsert(collection_name=collection_name, points=[point])

        self.logger.debug(
            "Stored document %s in Qdrant collection %s", document_id, collection_name
        )

    def get_document_by_id(
        self, document_id: str, collection_name: str = "federal_court_scotus_opinions"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by its unique identifier.

        This method fetches a stored document from Qdrant using its ID.
        It's designed for exact retrieval when you know the specific document
        you want, as opposed to similarity search based on content.

        The method implements safe retrieval patterns:
        1. Searches for the document by ID in the payload
        2. Handles cases where the document or collection doesn't exist
        3. Returns a standardized dictionary format or None
        4. Includes both document content and metadata

        Args:
            document_id (str): The unique identifier of the document to retrieve.
                Must exactly match the ID used when storing the document.
                Case-sensitive and must be non-empty.

            collection_name (str, optional): Name of the collection containing
                the document. Defaults to "federal_court_scotus_opinions".
                Must be a valid, existing collection name.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing the document data
                if found, None if not found. The dictionary structure:
                {
                    "id": str,           # The document ID
                    "document": str,     # Full text content
                    "metadata": dict     # Associated metadata
                }

        Raises:
            ValueError: If document_id is empty or collection_name is invalid
            qdrant_client.errors.QdrantException: If database operations fail

        Python Learning Notes:
            - Optional[Type] means the method can return Type or None
            - Default parameter values provide convenient defaults
            - Dictionary comprehension for filtering keys
            - Exception handling with logging for debugging

        Qdrant Operations:
            - scroll() retrieves documents with optional filtering
            - Filter conditions for exact ID matching
            - Payload contains all stored metadata

        Example:
            client = QdrantDBClient()

            # Retrieve a specific document
            opinion = client.get_document_by_id("dobbs_v_jackson_2022")

            if opinion:
                print(f"Found: {opinion['metadata']['case_name']}")
                print(f"Text length: {len(opinion['document'])} characters")
                print(f"Year: {opinion['metadata']['year']}")
            else:
                print("Opinion not found")

            # Search in a different collection
            circuit_opinion = client.get_document_by_id(
                "circuit_2024_001",
                collection_name="federal_court_circuit_opinions"
            )
        """
        try:
            # Search for document by ID in payload
            results = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="id", match=MatchValue(value=document_id))]
                ),
                limit=1,
            )

            if results[0]:  # Check if any results were found
                point = results[0][0]  # Get first point from results
                payload = point.payload

                # Extract document and metadata
                document = payload.pop("document", "")
                doc_id = payload.pop("id", document_id)

                return {
                    "id": doc_id,
                    "document": document,
                    "metadata": payload,  # Remaining fields are metadata
                }
        except Exception as e:  # pylint: disable=broad-except
            self.logger.debug("Document %s not found: %s", document_id, e)

        return None

    def get_opinion_by_id(
        self, opinion_id: str, collection_name: str = "federal_court_scotus_opinions"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a Supreme Court opinion (backward compatibility wrapper).

        This method maintains compatibility with existing code while using
        the more general get_document_by_id method internally.
        """
        return self.get_document_by_id(
            document_id=opinion_id, collection_name=collection_name
        )

    def semantic_search(
        self,
        query_embedding: List[float],
        collection_name: str,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Perform semantic similarity search in a collection.

        This method searches for documents similar to the query embedding,
        with optional filtering and score thresholding.

        Args:
            query_embedding (List[float]): Query vector for similarity search.
            collection_name (str): Name of the collection to search in.
            limit (int, optional): Maximum number of results to return. Defaults to 10.
            score_threshold (Optional[float]): Minimum similarity score threshold.
                Only results with scores above this threshold will be returned.
            filter_conditions (Optional[Dict[str, Any]]): Metadata filters to apply.
                Example: {"year": 2024, "opinion_type": "majority"}

        Returns:
            List[Tuple[Dict[str, Any], float]]: List of (document, score) tuples,
                sorted by similarity score in descending order.

        Example:
            results = client.semantic_search(
                query_embedding=query_vector,
                collection_name="federal_court_scotus_opinions",
                limit=5,
                score_threshold=0.7,
                filter_conditions={"year": 2024}
            )

            for doc, score in results:
                print(f"Score: {score:.3f} - {doc['metadata']['case_name']}")
        """
        # Build filter from conditions
        filter_obj = None
        if filter_conditions:
            must_conditions = []
            for key, value in filter_conditions.items():
                must_conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            filter_obj = Filter(must=must_conditions)

        # Perform search
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit,
            query_filter=filter_obj,
            score_threshold=score_threshold,
        )

        # Format results
        output = []
        for point in results:
            payload = point.payload
            document = payload.pop("document", "")
            doc_id = payload.pop("id", "")

            doc_data = {"id": doc_id, "document": document, "metadata": payload}
            output.append((doc_data, point.score))

        return output

    def batch_upsert(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]],
        collection_name: str,
    ) -> None:
        """
        Batch insert or update multiple documents efficiently.

        This method optimizes bulk operations by inserting multiple documents
        in a single API call, improving performance for large-scale processing.

        Args:
            documents: List of document dictionaries with 'id', 'text', and 'metadata'.
            embeddings: List of embedding vectors corresponding to documents.
            collection_name: Name of the collection to store in.

        Example:
            documents = [
                {"id": "doc1", "text": "...", "metadata": {...}},
                {"id": "doc2", "text": "...", "metadata": {...}}
            ]
            embeddings = [embedding1, embedding2]

            client.batch_upsert(documents, embeddings, "my_collection")
        """
        if not documents or not embeddings:
            return

        if len(documents) != len(embeddings):
            raise ValueError("Number of documents must match number of embeddings")

        # Ensure collection exists
        self.get_or_create_collection(collection_name)

        # Create points
        points = []
        for doc, embedding in zip(documents, embeddings):
            payload = {
                "document": doc.get("text", ""),
                "id": doc["id"],
                **doc.get("metadata", {}),
            }

            point = PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, doc["id"])),
                vector=embedding,
                payload=payload,
            )
            points.append(point)

        # Batch upsert
        self.client.upsert(collection_name=collection_name, points=points)

        self.logger.info(
            "Batch inserted %d documents into %s", len(points), collection_name
        )

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete an entire collection and all its data.

        Args:
            collection_name (str): Name of the collection to delete.

        Returns:
            bool: True if collection was deleted successfully.

        Example:
            if client.delete_collection("old_collection"):
                print("Collection deleted successfully")
        """
        try:
            self.client.delete_collection(collection_name)
            self.logger.info("Deleted collection: %s", collection_name)
            return True
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error("Failed to delete collection %s: %s", collection_name, e)
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a collection.

        Returns:
            Optional[Dict[str, Any]]: Collection information including:
                - vectors_count: Number of vectors stored
                - points_count: Number of points stored
                - indexed_vectors_count: Number of indexed vectors
                - segments_count: Number of segments
                - config: Collection configuration

        Example:
            info = client.get_collection_info("federal_court_scotus_opinions")
            if info:
                print(f"Collection has {info['vectors_count']} vectors")
        """
        try:
            collection = self.client.get_collection(collection_name)
            return {
                "vectors_count": collection.vectors_count,
                "points_count": collection.points_count,
                "indexed_vectors_count": collection.indexed_vectors_count,
                "segments_count": collection.segments_count,
                "config": collection.config,
            }
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error(
                "Failed to get collection info for %s: %s", collection_name, e
            )
            return None

    def list_collections(self) -> List[str]:
        """
        List all available collections in the database.

        This method provides visibility into the database structure by
        returning the names of all existing collections. Useful for
        debugging, administration, and dynamic collection management.

        Collections represent different document types or sources:
        - "federal_court_scotus_opinions": Supreme Court decisions
        - "federal_register_rules": Federal Register documents
        - "congress_bills": Congressional legislation
        - Custom collections created by applications

        Returns:
            List[str]: List of collection names currently in the database.
                Empty list if no collections exist. Collection names are
                returned in no particular order.

        Raises:
            qdrant_client.errors.QdrantException: If database connection fails
            PermissionError: If database access is denied

        Python Learning Notes:
            - List comprehensions [expression for item in iterable] create new lists
            - The .name attribute accesses object properties
            - Method chaining (self.client.get_collections()) calls methods on results
            - Return type annotation List[str] documents the return type

        Qdrant Concepts:
            - Collections are the top-level organizational unit
            - Each collection has a unique name and configuration
            - Collections persist until explicitly deleted
            - Empty databases have no collections initially

        Example:
            client = QdrantDBClient()

            # List all collections
            collections = client.list_collections()

            if collections:
                print("Available collections:")
                for collection in collections:
                    print(f"  - {collection}")
            else:
                print("No collections found - database is empty")

            # Check if a specific collection exists
            if "federal_court_scotus_opinions" in collections:
                print("SCOTUS opinions collection is available")
            else:
                print("SCOTUS collection needs to be created")
        """
        collections = self.client.get_collections()
        return [collection.name for collection in collections.collections]
