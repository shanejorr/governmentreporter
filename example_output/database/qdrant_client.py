"""
Example output for qdrant_client.py methods with return values.

This file demonstrates the methods in qdrant_client.py that return output
and can be run in the main guard pattern.
"""

import json
import os
import sys
import tempfile
from typing import Any, Dict, List

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.governmentreporter.database.qdrant_client import QdrantDBClient


def main():
    """Run examples of qdrant_client.py methods that return output."""
    results = {}

    try:
        # Create a temporary directory for the test database
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test_qdrant_db")

            # Initialize client with test database
            client = QdrantDBClient(db_path=db_path)

            # Test list_collections (should be empty initially)
            try:
                collections = client.list_collections()
                results["list_collections_initial"] = {
                    "method": "QdrantDBClient.list_collections()",
                    "result": collections,
                }
            except Exception as e:
                results["list_collections_initial"] = {
                    "method": "QdrantDBClient.list_collections()",
                    "error": str(e),
                }

            # Test get_or_create_collection
            try:
                success = client.get_or_create_collection("test_collection")
                results["get_or_create_collection"] = {
                    "method": "QdrantDBClient.get_or_create_collection()",
                    "result": success,
                }
            except Exception as e:
                results["get_or_create_collection"] = {
                    "method": "QdrantDBClient.get_or_create_collection()",
                    "error": str(e),
                }

            # Test list_collections again (should now have our collection)
            try:
                collections = client.list_collections()
                results["list_collections_after_create"] = {
                    "method": "QdrantDBClient.list_collections()",
                    "result": collections,
                }
            except Exception as e:
                results["list_collections_after_create"] = {
                    "method": "QdrantDBClient.list_collections()",
                    "error": str(e),
                }

            # Test store_document
            try:
                # Create sample embedding (1536 dimensions for OpenAI text-embedding-3-small)
                sample_embedding = [0.1] * 1536  # Simple test embedding

                client.store_document(
                    document_id="test_doc_001",
                    text="This is a test document for the RAG system.",
                    embedding=sample_embedding,
                    metadata={
                        "title": "Test Document",
                        "date": "2024-01-15",
                        "type": "test",
                        "author": "Test System",
                    },
                    collection_name="test_collection",
                )

                results["store_document"] = {
                    "method": "QdrantDBClient.store_document()",
                    "result": "Document stored successfully",
                }
            except Exception as e:
                results["store_document"] = {
                    "method": "QdrantDBClient.store_document()",
                    "error": str(e),
                }

            # Test get_document_by_id
            try:
                retrieved_doc = client.get_document_by_id(
                    document_id="test_doc_001", collection_name="test_collection"
                )

                if retrieved_doc:
                    results["get_document_by_id"] = {
                        "method": "QdrantDBClient.get_document_by_id()",
                        "result": {
                            "id": retrieved_doc["id"],
                            "document_preview": retrieved_doc["document"][:50] + "...",
                            "metadata": retrieved_doc["metadata"],
                        },
                    }
                else:
                    results["get_document_by_id"] = {
                        "method": "QdrantDBClient.get_document_by_id()",
                        "result": None,
                    }
            except Exception as e:
                results["get_document_by_id"] = {
                    "method": "QdrantDBClient.get_document_by_id()",
                    "error": str(e),
                }

            # Test semantic_search
            try:
                # Use the same embedding for search (should find our document)
                search_embedding = [0.1] * 1536

                search_results = client.semantic_search(
                    query_embedding=search_embedding,
                    collection_name="test_collection",
                    limit=5,
                    score_threshold=0.5,
                )

                formatted_results = []
                for doc_data, score in search_results:
                    formatted_results.append(
                        {
                            "id": doc_data["id"],
                            "score": score,
                            "document_preview": doc_data["document"][:50] + "...",
                            "metadata": doc_data["metadata"],
                        }
                    )

                results["semantic_search"] = {
                    "method": "QdrantDBClient.semantic_search()",
                    "result": {
                        "count": len(formatted_results),
                        "results": formatted_results,
                    },
                }
            except Exception as e:
                results["semantic_search"] = {
                    "method": "QdrantDBClient.semantic_search()",
                    "error": str(e),
                }

            # Test get_collection_info
            try:
                collection_info = client.get_collection_info("test_collection")
                results["get_collection_info"] = {
                    "method": "QdrantDBClient.get_collection_info()",
                    "result": collection_info,
                }
            except Exception as e:
                results["get_collection_info"] = {
                    "method": "QdrantDBClient.get_collection_info()",
                    "error": str(e),
                }

            # Test batch_upsert
            try:
                documents = [
                    {
                        "id": "batch_doc_001",
                        "text": "First batch document content.",
                        "metadata": {"title": "Batch Doc 1", "type": "batch_test"},
                    },
                    {
                        "id": "batch_doc_002",
                        "text": "Second batch document content.",
                        "metadata": {"title": "Batch Doc 2", "type": "batch_test"},
                    },
                ]

                embeddings = [[0.2] * 1536, [0.3] * 1536]  # Two different embeddings

                client.batch_upsert(
                    documents=documents,
                    embeddings=embeddings,
                    collection_name="test_collection",
                )

                results["batch_upsert"] = {
                    "method": "QdrantDBClient.batch_upsert()",
                    "result": f"Successfully batch upserted {len(documents)} documents",
                }
            except Exception as e:
                results["batch_upsert"] = {
                    "method": "QdrantDBClient.batch_upsert()",
                    "error": str(e),
                }

            # Test delete_collection
            try:
                deleted = client.delete_collection("test_collection")
                results["delete_collection"] = {
                    "method": "QdrantDBClient.delete_collection()",
                    "result": deleted,
                }
            except Exception as e:
                results["delete_collection"] = {
                    "method": "QdrantDBClient.delete_collection()",
                    "error": str(e),
                }

    except Exception as e:
        results["client_initialization"] = {
            "method": "QdrantDBClient.__init__()",
            "error": str(e),
        }

    # Print results in pretty JSON format
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
