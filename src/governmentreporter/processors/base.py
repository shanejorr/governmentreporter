"""Abstract base class for document processors."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..database.chroma_client import ChromaDBClient
from ..utils.embeddings import GoogleEmbeddingsClient


@dataclass
class ProcessedChunk:
    """Represents a processed document chunk with embedding."""

    text: str
    embedding: List[float]
    metadata: Dict[str, Any]
    chunk_index: int = 0


class BaseDocumentProcessor(ABC):
    """Abstract base class for document processors."""

    def __init__(
        self,
        embeddings_client: Optional[GoogleEmbeddingsClient] = None,
        db_client: Optional[ChromaDBClient] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the document processor.

        Args:
            embeddings_client: Client for generating embeddings. If None, creates new instance.
            db_client: Database client for storage. If None, creates new instance.
            logger: Logger for verbose output
        """
        self.embeddings_client = embeddings_client or GoogleEmbeddingsClient()
        self.db_client = db_client or ChromaDBClient()
        self.logger = logger

    @abstractmethod
    def process_document(self, document_id: str) -> List[ProcessedChunk]:
        """Process a single document into chunks.

        Args:
            document_id: Unique identifier for the document

        Returns:
            List of processed chunks with embeddings
        """
        pass

    def store_chunks(
        self, chunks: List[ProcessedChunk], collection_name: str, document_id: str
    ) -> int:
        """Store processed chunks in the database.

        Args:
            chunks: List of processed chunks to store
            collection_name: Name of the ChromaDB collection
            document_id: ID of the source document

        Returns:
            Number of chunks successfully stored
        """
        if not chunks:
            return 0

        # Get or create collection
        collection = self.db_client.get_or_create_collection(collection_name)
        
        if self.logger:
            self.logger.debug("=" * 80)
            self.logger.debug("STORING CHUNKS IN CHROMADB")
            self.logger.debug("=" * 80)
            self.logger.info(f"Collection: {collection_name}")
            self.logger.info(f"Document ID: {document_id}")
            self.logger.info(f"Number of chunks to store: {len(chunks)}")

        # Prepare data for batch insertion
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            ids.append(chunk_id)
            embeddings.append(chunk.embedding)
            documents.append(chunk.text)

            # Add chunk index to metadata
            metadata = chunk.metadata.copy()
            metadata["chunk_index"] = chunk.chunk_index
            metadata["source_document_id"] = document_id
            metadatas.append(metadata)
            
            if self.logger:
                self.logger.debug(f"\n--- ChromaDB Entry {i+1}/{len(chunks)} ---")
                self.logger.debug(f"Chunk ID: {chunk_id}")
                self.logger.debug(f"Text length: {len(chunk.text)} characters")
                self.logger.debug(f"Embedding length: {len(chunk.embedding)} dimensions")
                self.logger.debug(f"Metadata keys: {list(metadata.keys())}")
                # Log a few metadata fields for inspection
                for key in ["opinion_type", "justice", "section", "case_name", "legal_topics"]:
                    if key in metadata:
                        self.logger.debug(f"  {key}: {metadata[key]}")

        # Store in ChromaDB
        collection.add(
            ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
        )
        
        if self.logger:
            self.logger.info(f"✅ Successfully stored {len(chunks)} chunks in ChromaDB")

        return len(chunks)

    def process_and_store(
        self, document_id: str, collection_name: str
    ) -> Dict[str, Any]:
        """Process a document and store the chunks.

        Args:
            document_id: Unique identifier for the document
            collection_name: Name of the ChromaDB collection

        Returns:
            Dict with processing results including chunk count and any errors
        """
        try:
            # Process document into chunks
            chunks = self.process_document(document_id)

            # Store chunks
            stored_count = self.store_chunks(chunks, collection_name, document_id)

            return {
                "success": True,
                "document_id": document_id,
                "chunks_processed": len(chunks),
                "chunks_stored": stored_count,
                "error": None,
            }

        except Exception as e:
            return {
                "success": False,
                "document_id": document_id,
                "chunks_processed": 0,
                "chunks_stored": 0,
                "error": str(e),
            }
