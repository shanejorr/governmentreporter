"""ChromaDB client for managing document embeddings and metadata."""

import chromadb
from chromadb.config import Settings
from typing import Dict, Any, List, Optional
import uuid


class ChromaDBClient:
    """Client for interacting with ChromaDB for document storage."""
    
    def __init__(self, db_path: str = "./chroma_db"):
        """Initialize ChromaDB client.
        
        Args:
            db_path: Path to the ChromaDB database directory
        """
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
    def get_or_create_collection(self, collection_name: str):
        """Get or create a ChromaDB collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            ChromaDB collection object
        """
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            # Collection doesn't exist, create it
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": f"Collection for {collection_name}"}
            )
        return collection
        
    def store_scotus_opinion(
        self,
        opinion_id: str,
        plain_text: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        """Store a Supreme Court opinion with its embedding and metadata.
        
        Args:
            opinion_id: Unique identifier for the opinion
            plain_text: Full text of the opinion
            embedding: Vector embedding of the text
            metadata: Additional metadata about the opinion
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
            ids=[opinion_id]
        )
        
    def search_similar_opinions(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        collection_name: str = "federal_court_scotus_opinions"
    ) -> Dict[str, Any]:
        """Search for similar opinions using vector similarity.
        
        Args:
            query_embedding: Vector embedding of the search query
            n_results: Number of results to return
            collection_name: Name of the collection to search
            
        Returns:
            Dict containing search results
        """
        collection = self.get_or_create_collection(collection_name)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        return results
        
    def get_opinion_by_id(
        self,
        opinion_id: str,
        collection_name: str = "federal_court_scotus_opinions"
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a specific opinion by its ID.
        
        Args:
            opinion_id: The opinion ID to retrieve
            collection_name: Name of the collection
            
        Returns:
            Dict containing the opinion data, or None if not found
        """
        collection = self.get_or_create_collection(collection_name)
        
        try:
            results = collection.get(
                ids=[opinion_id],
                include=["documents", "metadatas"]
            )
            
            if results["ids"]:
                return {
                    "id": results["ids"][0],
                    "document": results["documents"][0],
                    "metadata": results["metadatas"][0]
                }
        except Exception:
            pass
            
        return None
        
    def list_collections(self) -> List[str]:
        """List all available collections.
        
        Returns:
            List of collection names
        """
        collections = self.client.list_collections()
        return [collection.name for collection in collections]