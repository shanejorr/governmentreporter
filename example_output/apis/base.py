"""
Example output for base.py methods with return values.

This file demonstrates the methods in base.py that return output
and can be run in the main guard pattern.
"""

import json
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.governmentreporter.apis.base import Document


def main():
    """Run examples of base.py methods that return output."""
    results = {}

    # Test Document creation and fields
    try:
        doc = Document(
            id="test_doc_001",
            title="Sample Legal Document",
            date="2024-01-15",
            type="Test Document",
            source="Example API",
            content="This is sample content for testing the Document class.",
            metadata={"author": "John Doe", "pages": 10},
            url="https://example.com/doc",
        )

        results["Document_creation"] = {
            "method": "Document.__init__()",
            "result": {
                "id": doc.id,
                "title": doc.title,
                "date": doc.date,
                "type": doc.type,
                "source": doc.source,
                "content": doc.content,
                "metadata": doc.metadata,
                "url": doc.url,
            },
        }
    except Exception as e:
        results["Document_creation"] = {
            "method": "Document.__init__()",
            "error": str(e),
        }

    # Note: GovernmentAPIClient is abstract, so we can't instantiate it directly
    # But we can test the validate_date_format method if we create a concrete implementation

    class TestAPIClient:
        def validate_date_format(self, date_str: str) -> bool:
            """Copy of the validate_date_format method for testing"""
            import re

            pattern = r"^\d{4}-\d{2}-\d{2}$"
            return bool(re.match(pattern, date_str))

    try:
        test_client = TestAPIClient()

        # Test various date formats
        test_dates = [
            "2024-01-15",  # Valid
            "2024-1-15",  # Invalid (missing zero)
            "01/15/2024",  # Invalid (wrong format)
            "2024-13-45",  # Invalid date but correct format
            "invalid",  # Invalid
            "",  # Empty
        ]

        date_validation_results = {}
        for date_str in test_dates:
            try:
                is_valid = test_client.validate_date_format(date_str)
                date_validation_results[date_str] = is_valid
            except Exception as e:
                date_validation_results[date_str] = f"Error: {str(e)}"

        results["validate_date_format"] = {
            "method": "GovernmentAPIClient.validate_date_format()",
            "result": date_validation_results,
        }
    except Exception as e:
        results["validate_date_format"] = {
            "method": "GovernmentAPIClient.validate_date_format()",
            "error": str(e),
        }

    # Print results in pretty JSON format
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
