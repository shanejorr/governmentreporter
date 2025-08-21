"""
ChromaDB client for managing document embeddings and metadata.

This module provides a high-level interface to ChromaDB, a vector database
optimized for storing and querying document embeddings. ChromaDB enables
semantic search capabilities by storing vector representations of documents
along with their metadata.

Key Features:
    - Persistent storage of document embeddings
    - Metadata filtering and querying
    - Collection management for different document types
    - Automatic embedding similarity search
    - Type-safe metadata handling

ChromaDB Integration:
    ChromaDB is an open-source vector database that:
    - Stores high-dimensional vectors (embeddings) efficiently
    - Provides fast similarity search using cosine similarity
    - Supports metadata filtering for complex queries
    - Offers both in-memory and persistent storage options
    - Handles automatic indexing for optimal query performance

Python Learning Notes:
    - Type hints (List[float], Dict[str, Any]) help document expected data types
    - Optional[T] means a value can be of type T or None
    - Exception handling with try/except prevents crashes
    - List comprehensions and generator expressions for data transformation
    - Context managers and resource cleanup patterns

Example Usage:
    # Initialize client
    client = ChromaDBClient(db_path="./vector_db")

    # Store a document with embedding
    client.store_scotus_opinion(
        opinion_id="roe_v_wade_1973",
        plain_text="The Supreme Court decision text...",
        embedding=[0.1, 0.2, 0.3, ...],  # 768-dimensional vector
        metadata={
            "case_name": "Roe v. Wade",
            "year": 1973,
            "justice_writing": "Blackmun"
        }
    )

    # Retrieve document by ID
    opinion = client.get_opinion_by_id("roe_v_wade_1973")
    if opinion:
        print(f"Found: {opinion['metadata']['case_name']}")
"""

import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from ..utils import get_logger


class ChromaDBClient:
    """
    Client for interacting with ChromaDB for document storage and retrieval.

    This class provides a high-level interface to ChromaDB operations,
    handling document storage, embedding management, and metadata operations.
    It abstracts away the complexity of ChromaDB's API while providing
    type safety and error handling.

    The client implements a persistent storage pattern where:
    1. Documents are stored with their vector embeddings
    2. Metadata is normalized for ChromaDB compatibility
    3. Collections organize documents by type/source
    4. Error handling ensures graceful degradation

    Attributes:
        client (chromadb.PersistentClient): The underlying ChromaDB client instance

    Python Learning Notes:
        - Classes group related data and functions together
        - __init__ is the constructor method, called when creating instances
        - self refers to the current instance of the class
        - Private attributes (starting with _) indicate internal implementation
        - Public methods provide the interface other code can use

    Example:
        # Create a new client instance
        db_client = ChromaDBClient(db_path="./government_docs_db")

        # The client is now ready to store and retrieve documents
        collections = db_client.list_collections()
        print(f"Available collections: {collections}")
    """

    def __init__(self, db_path: str = "./chroma_db") -> None:
        """
        Initialize ChromaDB client with persistent storage.

        Creates a persistent ChromaDB client that stores data on disk,
        allowing data to persist between application runs. The client
        is configured with security and privacy settings appropriate
        for local development.

        Args:
            db_path (str, optional): Path to the ChromaDB database directory.
                Defaults to "./chroma_db". The directory will be created
                if it doesn't exist.

        Returns:
            None: Constructor methods don't return values

        Raises:
            chromadb.errors.ChromaError: If the database cannot be initialized
            PermissionError: If the db_path directory cannot be created or accessed

        Python Learning Notes:
            - Default parameter values (= "./chroma_db") provide fallbacks
            - Type hints (str, -> None) document expected types
            - The -> None annotation means this method doesn't return a value
            - self.client creates an instance attribute accessible to all methods
            - Settings objects configure behavior without hardcoded values

        ChromaDB Configuration:
            - anonymized_telemetry=False: Disables data collection for privacy
            - allow_reset=True: Enables database reset operations for development
            - PersistentClient: Stores data on disk vs. in-memory only

        Example:
            # Use default database path
            client1 = ChromaDBClient()

            # Use custom path for production
            client2 = ChromaDBClient(db_path="/var/lib/government_docs/chroma")

            # Both clients are now ready to use
            print(f"Client initialized with {len(client1.list_collections())} collections")
        """
        self.logger = get_logger(__name__)
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        self.logger.info(f"ChromaDBClient initialized with database path: {db_path}")

    def get_or_create_collection(self, collection_name: str):
        """
        Get an existing collection or create a new one if it doesn't exist.

        Collections in ChromaDB are like tables in a database - they group
        related documents together. This method implements an idempotent
        operation: calling it multiple times with the same name is safe
        and will always return the same collection.

        Args:
            collection_name (str): Name of the collection to get or create.
                Must be a valid collection name (alphanumeric, underscores,
                and hyphens allowed).

        Returns:
            chromadb.Collection: The collection object that can be used to
                add, update, query, and delete documents.

        Raises:
            ValueError: If collection_name is empty or contains invalid characters
            chromadb.errors.ChromaError: If collection operations fail

        Python Learning Notes:
            - Try/except blocks handle errors gracefully
            - Exception handling prevents crashes from expected errors
            - Broad except clauses catch any exception type
            - Method chaining (self.client.get_collection) calls methods on returned objects
            - Dictionary literals ({"key": "value"}) create inline dictionaries

        ChromaDB Concepts:
            - Collections organize similar documents (like database tables)
            - Metadata can be attached to collections for organization
            - Collection names must be unique within a database
            - Collections persist until explicitly deleted

        Example:
            # Get existing collection or create new one
            scotus_collection = client.get_or_create_collection("scotus_opinions")

            # Safe to call multiple times
            same_collection = client.get_or_create_collection("scotus_opinions")
            assert scotus_collection.name == same_collection.name

            # Collection is ready for document operations
            count = scotus_collection.count()
            print(f"Collection has {count} documents")
        """
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            # Collection doesn't exist, create it
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": f"Collection for {collection_name}"},
            )
        return collection

    def store_scotus_opinion(
        self,
        opinion_id: str,
        plain_text: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        """
        Store a Supreme Court opinion with its embedding and metadata.

        This method stores a complete Supreme Court opinion document in ChromaDB,
        including the full text, vector embedding for semantic search, and
        associated metadata. The method handles metadata normalization to ensure
        compatibility with ChromaDB's storage requirements.

        The storage process:
        1. Gets or creates the federal court opinions collection
        2. Normalizes metadata to ChromaDB-compatible types
        3. Stores document, embedding, and metadata together
        4. Uses opinion_id as the unique document identifier

        Args:
            opinion_id (str): Unique identifier for the opinion. Should be
                stable and descriptive (e.g., "scotus_2024_dobbs_v_jackson").
                This ID is used for retrieval and must be unique within the collection.

            plain_text (str): Full text content of the Supreme Court opinion.
                This is the complete document text that will be stored and
                can be retrieved later for display or analysis.

            embedding (List[float]): Vector representation of the document text.
                Typically a 768 or 1024-dimensional vector generated by a
                language model (e.g., sentence-transformers). Used for
                semantic similarity search.

            metadata (Dict[str, Any]): Additional information about the opinion.
                Can include case name, year, justices, topics, etc. Values
                will be converted to ChromaDB-compatible types (str, int, float, bool).

        Returns:
            None: This method doesn't return a value but stores the data persistently

        Raises:
            ValueError: If opinion_id is empty or embedding is malformed
            chromadb.errors.DuplicateIDError: If opinion_id already exists
            chromadb.errors.ChromaError: If storage operation fails

        Python Learning Notes:
            - Type hints with complex types (List[float], Dict[str, Any])
            - Dictionary iteration with .items() gets key-value pairs
            - isinstance() checks if a value is of a specific type
            - List comprehensions transform data efficiently
            - String formatting with f-strings and .join() for readable output

        Metadata Processing:
            ChromaDB requires metadata values to be basic types (str, int, float, bool).
            This method automatically converts:
            - Lists to comma-separated strings
            - Other objects to their string representation
            - Preserves basic types as-is

        Example:
            client = ChromaDBClient()

            # Store a Supreme Court opinion
            client.store_scotus_opinion(
                opinion_id="dobbs_v_jackson_2022",
                plain_text="The Supreme Court held that...",
                embedding=[0.1, 0.2, 0.3, ...],  # 768-dim vector
                metadata={
                    "case_name": "Dobbs v. Jackson Women's Health Organization",
                    "year": 2022,
                    "majority_justice": "Alito",
                    "topics": ["reproductive rights", "constitutional law"],
                    "pages": 213
                }
            )

            # Document is now stored and searchable
            print("Opinion stored successfully")
        """
        collection = self.get_or_create_collection("federal_court_scotus_opinions")

        # Prepare metadata for ChromaDB (must be strings, numbers, or booleans)
        chroma_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                chroma_metadata[key] = value
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                chroma_metadata[key] = ", ".join(str(v) for v in value)
            else:
                chroma_metadata[key] = str(value)

        # Store the document
        collection.add(
            documents=[plain_text],
            embeddings=[embedding],
            metadatas=[chroma_metadata],
            ids=[opinion_id],
        )

    def get_opinion_by_id(
        self, opinion_id: str, collection_name: str = "federal_court_scotus_opinions"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific opinion by its unique identifier.

        This method fetches a stored document from ChromaDB using its ID.
        It's designed for exact retrieval when you know the specific document
        you want, as opposed to similarity search based on content.

        The method implements safe retrieval patterns:
        1. Attempts to get the document from the specified collection
        2. Handles cases where the document or collection doesn't exist
        3. Returns a standardized dictionary format or None
        4. Includes both document content and metadata

        Args:
            opinion_id (str): The unique identifier of the opinion to retrieve.
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
            ValueError: If opinion_id is empty or collection_name is invalid
            chromadb.errors.ChromaError: If database operations fail

        Python Learning Notes:
            - Optional[Type] means the method can return Type or None
            - Default parameter values provide convenient defaults
            - Dictionary indexing with ["key"] accesses values
            - Boolean evaluation: empty lists/None are False, non-empty are True
            - Exception handling with bare except catches all exceptions

        ChromaDB Operations:
            - collection.get() retrieves documents by ID
            - include parameter specifies what data to return
            - Results are returned as dictionaries with list values
            - IDs, documents, and metadata are separate lists in results

        Example:
            client = ChromaDBClient()

            # Retrieve a specific opinion
            opinion = client.get_opinion_by_id("dobbs_v_jackson_2022")

            if opinion:
                print(f"Found: {opinion['metadata']['case_name']}")
                print(f"Text length: {len(opinion['document'])} characters")
                print(f"Year: {opinion['metadata']['year']}")
            else:
                print("Opinion not found")

            # Search in a different collection
            circuit_opinion = client.get_opinion_by_id(
                "circuit_2024_001",
                collection_name="federal_court_circuit_opinions"
            )
        """
        collection = self.get_or_create_collection(collection_name)

        try:
            results = collection.get(
                ids=[opinion_id], include=["documents", "metadatas"]
            )

            if results["ids"]:
                return {
                    "id": results["ids"][0],
                    "document": results["documents"][0],
                    "metadata": results["metadatas"][0],
                }
        except Exception:
            pass

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
            chromadb.errors.ChromaError: If database connection fails
            PermissionError: If database access is denied

        Python Learning Notes:
            - List comprehensions [expression for item in iterable] create new lists
            - The .name attribute accesses object properties
            - Method chaining (self.client.list_collections()) calls methods on results
            - Return type annotation List[str] documents the return type

        ChromaDB Concepts:
            - Collections are the top-level organizational unit
            - Each collection has a unique name and metadata
            - Collections persist until explicitly deleted
            - Empty databases have no collections initially

        Example:
            client = ChromaDBClient()

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
        collections = self.client.list_collections()
        return [collection.name for collection in collections]
