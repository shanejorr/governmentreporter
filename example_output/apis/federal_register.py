"""
Example output for federal_register.py methods with return values.

This file demonstrates the methods in federal_register.py that return output
and can be run in the main guard pattern.
"""

import json
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.governmentreporter.apis.federal_register import FederalRegisterClient


def main():
    """Run examples of federal_register.py methods that return output."""
    results = {}
    
    try:
        # Initialize client (no API key needed for Federal Register)
        client = FederalRegisterClient()
        
        # Test _get_base_url()
        results["_get_base_url"] = {
            "method": "FederalRegisterClient._get_base_url()",
            "result": client._get_base_url()
        }
        
        # Test _get_rate_limit_delay()
        results["_get_rate_limit_delay"] = {
            "method": "FederalRegisterClient._get_rate_limit_delay()",
            "result": client._get_rate_limit_delay()
        }
        
        # Test extract_basic_metadata with sample data
        sample_order_data = {
            "document_number": "2024-12345",
            "title": "Sample Executive Order",
            "executive_order_number": 14001,
            "signing_date": "2024-01-15",
            "president": {"name": "Test President"},
            "citation": "89 FR 12345",
            "html_url": "https://example.com/eo",
            "raw_text_url": "https://example.com/raw",
            "publication_date": "2024-01-16",
            "agencies": [{"name": "Department of Test"}]
        }
        
        try:
            metadata = client.extract_basic_metadata(sample_order_data)
            results["extract_basic_metadata"] = {
                "method": "FederalRegisterClient.extract_basic_metadata()",
                "result": metadata
            }
        except Exception as e:
            results["extract_basic_metadata"] = {
                "method": "FederalRegisterClient.extract_basic_metadata()",
                "error": str(e)
            }
        
        # Test get_document_text with a hypothetical ID
        try:
            # This will likely fail without a real document ID
            text = client.get_document_text("2024-12345")  # Example ID
            results["get_document_text"] = {
                "method": "FederalRegisterClient.get_document_text()",
                "result": text[:200] + "..." if len(text) > 200 else text
            }
        except Exception as e:
            results["get_document_text"] = {
                "method": "FederalRegisterClient.get_document_text()",
                "error": f"Expected error with test ID: {str(e)}"
            }
        
        # Test search_documents with a basic search (limiting results to avoid overwhelming)
        try:
            # Basic search with minimal results
            documents = client.search_documents(
                query="climate",
                start_date="2024-01-01",
                end_date="2024-12-31",
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
                    "url": doc.url,
                    "metadata_keys": list(doc.metadata.keys()) if doc.metadata else []
                })
            
            results["search_documents"] = {
                "method": "FederalRegisterClient.search_documents()",
                "result": {
                    "count": len(search_results),
                    "documents": search_results
                }
            }
        except Exception as e:
            results["search_documents"] = {
                "method": "FederalRegisterClient.search_documents()",
                "error": str(e)
            }
        
        # Test list_executive_orders (limiting results to avoid overwhelming)
        try:
            # Get a few executive orders from a small date range
            orders = []
            order_iterator = client.list_executive_orders(
                start_date="2024-01-01", 
                end_date="2024-01-31",
                max_results=3
            )
            
            for order in order_iterator:
                orders.append({
                    "document_number": order.get("document_number"),
                    "title": order.get("title", "")[:100],  # Truncate long titles
                    "executive_order_number": order.get("executive_order_number"),
                    "signing_date": order.get("signing_date"),
                    "president": order.get("president", {}).get("name") if isinstance(order.get("president"), dict) else str(order.get("president", ""))
                })
                
            results["list_executive_orders"] = {
                "method": "FederalRegisterClient.list_executive_orders()",
                "result": {
                    "count": len(orders),
                    "orders": orders
                }
            }
        except Exception as e:
            results["list_executive_orders"] = {
                "method": "FederalRegisterClient.list_executive_orders()",
                "error": str(e)
            }
            
    except Exception as e:
        results["client_initialization"] = {
            "method": "FederalRegisterClient.__init__()",
            "error": str(e)
        }
    
    # Print results in pretty JSON format
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()