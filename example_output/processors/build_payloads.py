"""
Example output for build_payloads.py methods with return values.

This file demonstrates the methods in build_payloads.py that return output
and can be run in the main guard pattern.
"""

import json
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.governmentreporter.apis.base import Document
from src.governmentreporter.processors.build_payloads import (
    build_payloads_from_document, extract_year_from_date,
    normalize_eo_metadata, normalize_scotus_metadata, validate_payload)


def main():
    """Run examples of build_payloads.py methods that return output."""
    results = {}

    # Test extract_year_from_date
    try:
        test_dates = [
            "2024-01-15",
            "2024/01/15",
            "2024-13-45",  # Invalid date but parseable format
            "invalid-date",
            "",
            None,
        ]

        year_results = {}
        for date_str in test_dates:
            try:
                if date_str is not None:
                    year = extract_year_from_date(date_str)
                    year_results[str(date_str)] = year
                else:
                    year_results["None"] = "Skipped None value"
            except Exception as e:
                year_results[str(date_str)] = f"Error: {str(e)}"

        results["extract_year_from_date"] = {
            "method": "extract_year_from_date()",
            "result": year_results,
        }
    except Exception as e:
        results["extract_year_from_date"] = {
            "method": "extract_year_from_date()",
            "error": str(e),
        }

    # Test normalize_scotus_metadata
    try:
        # Create a sample Supreme Court Document
        scotus_doc = Document(
            id="test_scotus_001",
            title="Sample v. Test Case",
            date="2024-05-16",
            type="Supreme Court Opinion",
            source="CourtListener",
            content="Sample opinion content...",
            metadata={
                "case_name": "Sample v. Test Case",
                "citations": [
                    {"type": 1, "volume": "601", "reporter": "U.S.", "page": "100"}
                ],
                "type": "010combined",
            },
            url="https://example.com/opinion",
        )

        normalized = normalize_scotus_metadata(scotus_doc)
        results["normalize_scotus_metadata"] = {
            "method": "normalize_scotus_metadata()",
            "result": normalized,
        }
    except Exception as e:
        results["normalize_scotus_metadata"] = {
            "method": "normalize_scotus_metadata()",
            "error": str(e),
        }

    # Test normalize_eo_metadata
    try:
        # Create a sample Executive Order Document
        eo_doc = Document(
            id="test_eo_001",
            title="Test Executive Order",
            date="2025-06-11",
            type="Executive Order",
            source="Federal Register",
            content="Executive Order content...",
            metadata={
                "presidential_document_number": "99999",
                "citation": "90 FR 10000",
            },
            url="https://example.com/eo",
        )

        normalized = normalize_eo_metadata(eo_doc)
        results["normalize_eo_metadata"] = {
            "method": "normalize_eo_metadata()",
            "result": normalized,
        }
    except Exception as e:
        results["normalize_eo_metadata"] = {
            "method": "normalize_eo_metadata()",
            "error": str(e),
        }

    # Test validate_payload
    try:
        # Test valid payload
        valid_payload = {
            "id": "test_chunk_001",
            "text": "This is sample chunk text.",
            "metadata": {
                "document_id": "test_doc_001",
                "title": "Test Document",
                "date": "2024-01-15",
                "section_label": "Test Section",
            },
        }

        # Test invalid payloads
        invalid_payloads = [
            {},  # Missing required fields
            {"id": "", "text": "text", "metadata": {}},  # Empty ID
            {"id": "id", "text": "", "metadata": {}},  # Empty text
            {"id": "id", "text": "text", "metadata": "not_dict"},  # Invalid metadata
            {"id": 123, "text": "text", "metadata": {}},  # Non-string ID
        ]

        validation_results = {"valid_payload": validate_payload(valid_payload)}

        for i, payload in enumerate(invalid_payloads):
            validation_results[f"invalid_payload_{i}"] = validate_payload(payload)

        results["validate_payload"] = {
            "method": "validate_payload()",
            "result": validation_results,
        }
    except Exception as e:
        results["validate_payload"] = {"method": "validate_payload()", "error": str(e)}

    # Test build_payloads_from_document (without LLM calls)
    # Note: This will fail on the LLM extraction step without proper API keys,
    # but it will demonstrate the document processing pipeline
    try:
        # Create a test document with minimal content
        test_doc = Document(
            id="test_payload_001",
            title="Test Document for Payloads",
            date="2024-01-15",
            type="Supreme Court Opinion",
            source="CourtListener",
            content="SYLLABUS\n\nTest syllabus content.\n\nJUSTICE TEST delivered the opinion of the Court.\n\nTest opinion content.",
            metadata={"case_name": "Test Case"},
            url="https://example.com/test",
        )

        # This will likely fail on LLM extraction without API keys
        payloads = build_payloads_from_document(test_doc)

        # Format results to avoid overwhelming output
        payload_summary = []
        for payload in payloads[:3]:  # Show first 3 payloads only
            payload_summary.append(
                {
                    "id": payload["id"],
                    "text_preview": (
                        payload["text"][:100] + "..."
                        if len(payload["text"]) > 100
                        else payload["text"]
                    ),
                    "metadata_keys": list(payload["metadata"].keys()),
                    "is_valid": validate_payload(payload),
                }
            )

        results["build_payloads_from_document"] = {
            "method": "build_payloads_from_document()",
            "result": {
                "total_payloads": len(payloads),
                "sample_payloads": payload_summary,
            },
        }
    except Exception as e:
        results["build_payloads_from_document"] = {
            "method": "build_payloads_from_document()",
            "error": str(e),
        }

    # Print results in pretty JSON format
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
