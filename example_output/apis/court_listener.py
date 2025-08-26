"""
Example output for court_listener.py methods with return values.

This file demonstrates the methods in court_listener.py that return output
and can be run in the main guard pattern.
"""

import json
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.governmentreporter.apis.court_listener import CourtListenerClient


def main():
    """Run examples of court_listener.py methods that return output."""
    results = {}
    
    # Check if API token is available
    api_token = os.getenv("COURT_LISTENER_API_TOKEN")
    if not api_token:
        results["api_token_missing"] = {
            "method": "All CourtListenerClient methods",
            "error": "COURT_LISTENER_API_TOKEN not set in environment variables"
        }
        print(json.dumps(results, indent=2))
        return
    
    try:
        # Initialize client
        client = CourtListenerClient(token=api_token)
        
        # Test _get_base_url()
        results["_get_base_url"] = {
            "method": "CourtListenerClient._get_base_url()",
            "result": client._get_base_url()
        }
        
        # Test _get_rate_limit_delay()
        results["_get_rate_limit_delay"] = {
            "method": "CourtListenerClient._get_rate_limit_delay()",
            "result": client._get_rate_limit_delay()
        }
        
        # Test extract_basic_metadata with sample data
        sample_opinion_data = {
            "id": 123456,
            "resource_uri": "/api/rest/v4/opinions/123456/",
            "cluster_id": 78910,
            "date_created": "2024-01-15T10:30:00Z",
            "plain_text": "Sample opinion text...",
            "author_id": 111,
            "type": "010combined",
            "page_count": 25,
            "download_url": "https://example.com/download"
        }
        
        try:
            metadata = client.extract_basic_metadata(sample_opinion_data)
            results["extract_basic_metadata"] = {
                "method": "CourtListenerClient.extract_basic_metadata()",
                "result": metadata
            }
        except Exception as e:
            results["extract_basic_metadata"] = {
                "method": "CourtListenerClient.extract_basic_metadata()",
                "error": str(e)
            }
        
        # Note: The following methods require actual API calls and valid IDs
        # They are included here for completeness but may fail without valid test data
        
        # Test get_document_text with a hypothetical ID
        try:
            # This will likely fail without a real opinion ID
            text = client.get_document_text("9973155")  # Example ID from docs
            results["get_document_text"] = {
                "method": "CourtListenerClient.get_document_text()",
                "result": text[:200] + "..." if len(text) > 200 else text
            }
        except Exception as e:
            results["get_document_text"] = {
                "method": "CourtListenerClient.get_document_text()",
                "error": f"Expected error with test ID: {str(e)}"
            }
        
        # Test search_documents with a basic search (limiting results to avoid overwhelming)
        try:
            # Basic search with minimal results
            documents = client.search_documents(
                query="constitution",
                start_date="2024-01-01",
                limit=2,
                full_content=False  # Avoid extra API calls
            )
            
            # Format results for display
            search_results = []
            for doc in documents:
                search_results.append({
                    "id": doc.id,
                    "title": doc.title,
                    "date": doc.date,
                    "type": doc.type,
                    "source": doc.source,
                    "has_content": bool(doc.content),
                    "url": doc.url
                })
            
            results["search_documents"] = {
                "method": "CourtListenerClient.search_documents()",
                "result": {
                    "count": len(search_results),
                    "documents": search_results
                }
            }
        except Exception as e:
            results["search_documents"] = {
                "method": "CourtListenerClient.search_documents()",
                "error": str(e)
            }
            
    except Exception as e:
        results["client_initialization"] = {
            "method": "CourtListenerClient.__init__()",
            "error": str(e)
        }
    
    # Print results in pretty JSON format
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()