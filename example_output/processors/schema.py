"""
Example output for schema.py methods with return values.

This file demonstrates the methods in schema.py that return output
and can be run in the main guard pattern.
"""

import json
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.governmentreporter.processors.schema import (
    ChunkMetadata, ExecutiveOrderMetadata, QdrantPayload, SharedMetadata,
    SupremeCourtMetadata, create_eo_chunk_metadata,
    create_scotus_chunk_metadata)


def main():
    """Run examples of schema.py methods that return output."""
    results = {}

    # Test SharedMetadata creation
    try:
        shared_metadata = SharedMetadata(
            document_id="test_doc_001",
            title="Test Document",
            publication_date="2024-01-15",
            year=2024,
            source="Test Source",
            type="Test Type",
            url="https://example.com/doc",
            citation_bluebook="123 Test 456 (2024)",
            plain_language_summary="This is a test document for demonstration purposes.",
            constitution_cited=["U.S. Const. amend. I"],
            federal_statutes_cited=["42 U.S.C. § 1983"],
            federal_regulations_cited=["14 C.F.R. § 91.817"],
            cases_cited=["Brown v. Board, 347 U.S. 483 (1954)"],
            topics_or_policy_areas=[
                "civil rights",
                "education",
                "constitutional law",
                "equal protection",
                "segregation",
            ],
        )

        results["SharedMetadata_creation"] = {
            "method": "SharedMetadata.__init__()",
            "result": shared_metadata.dict(),
        }
    except Exception as e:
        results["SharedMetadata_creation"] = {
            "method": "SharedMetadata.__init__()",
            "error": str(e),
        }

    # Test ChunkMetadata creation
    try:
        chunk_metadata = ChunkMetadata(
            chunk_id="test_doc_001_chunk_0", chunk_index=0, section_label="Test Section"
        )

        results["ChunkMetadata_creation"] = {
            "method": "ChunkMetadata.__init__()",
            "result": chunk_metadata.dict(),
        }
    except Exception as e:
        results["ChunkMetadata_creation"] = {
            "method": "ChunkMetadata.__init__()",
            "error": str(e),
        }

    # Test SupremeCourtMetadata creation
    try:
        scotus_metadata = SupremeCourtMetadata(
            document_id="scotus_001",
            title="Brown v. Board of Education",
            publication_date="1954-05-17",
            year=1954,
            source="CourtListener",
            type="Supreme Court Opinion",
            url="https://example.com/opinion",
            citation_bluebook="347 U.S. 483 (1954)",
            plain_language_summary="The Court held that separate educational facilities are inherently unequal.",
            constitution_cited=["U.S. Const. amend. XIV, § 1"],
            federal_statutes_cited=[],
            federal_regulations_cited=[],
            cases_cited=["Plessy v. Ferguson, 163 U.S. 537 (1896)"],
            topics_or_policy_areas=[
                "civil rights",
                "education",
                "equal protection",
                "racial segregation",
                "constitutional law",
            ],
            case_name="Brown v. Board of Education",
            opinion_type="majority",
            holding_plain="Separate educational facilities are inherently unequal and violate the Equal Protection Clause.",
            outcome_simple="Petitioners won - segregation in public schools declared unconstitutional.",
            issue_plain="Does racial segregation in public schools violate the Equal Protection Clause?",
            reasoning="The Court found that segregation generates a feeling of inferiority that affects children's motivation to learn and deprives them of equal educational opportunities.",
        )

        results["SupremeCourtMetadata_creation"] = {
            "method": "SupremeCourtMetadata.__init__()",
            "result": scotus_metadata.dict(),
        }
    except Exception as e:
        results["SupremeCourtMetadata_creation"] = {
            "method": "SupremeCourtMetadata.__init__()",
            "error": str(e),
        }

    # Test ExecutiveOrderMetadata creation
    try:
        eo_metadata = ExecutiveOrderMetadata(
            document_id="eo_14304",
            title="Leading the World in Supersonic Flight",
            publication_date="2025-01-15",
            year=2025,
            source="Federal Register",
            type="Executive Order",
            url="https://example.com/eo",
            citation_bluebook="90 FR 5000",
            plain_language_summary="Establishes new requirements for federal agencies to advance supersonic flight technology.",
            constitution_cited=[],
            federal_statutes_cited=["49 U.S.C. § 106"],
            federal_regulations_cited=["14 C.F.R. § 91.817"],
            cases_cited=[],
            topics_or_policy_areas=[
                "aviation",
                "transportation",
                "technology",
                "federal regulation",
                "supersonic flight",
            ],
            eo_number="14304",
            agencies_impacted=[
                "Department of Transportation",
                "Federal Aviation Administration",
                "NASA",
            ],
        )

        results["ExecutiveOrderMetadata_creation"] = {
            "method": "ExecutiveOrderMetadata.__init__()",
            "result": eo_metadata.dict(),
        }
    except Exception as e:
        results["ExecutiveOrderMetadata_creation"] = {
            "method": "ExecutiveOrderMetadata.__init__()",
            "error": str(e),
        }

    # Test QdrantPayload creation
    try:
        payload = QdrantPayload(
            id="test_chunk_001",
            text="This is sample chunk text for testing the Qdrant payload structure.",
            metadata={
                "document_id": "test_doc_001",
                "title": "Test Document",
                "section_label": "Test Section",
                "chunk_index": 0,
            },
        )

        results["QdrantPayload_creation"] = {
            "method": "QdrantPayload.__init__()",
            "result": payload.dict(),
        }
    except Exception as e:
        results["QdrantPayload_creation"] = {
            "method": "QdrantPayload.__init__()",
            "error": str(e),
        }

    # Test create_scotus_chunk_metadata
    try:
        # Use the previously created objects
        if (
            "SupremeCourtMetadata_creation" in results
            and "result" in results["SupremeCourtMetadata_creation"]
        ):
            scotus_meta = SupremeCourtMetadata(
                **results["SupremeCourtMetadata_creation"]["result"]
            )
        else:
            # Fallback if creation failed
            scotus_meta = SupremeCourtMetadata(
                document_id="scotus_001",
                title="Test Case",
                publication_date="2024-01-15",
                year=2024,
                source="CourtListener",
                type="Supreme Court Opinion",
                url="https://example.com/opinion",
                plain_language_summary="Test summary",
                topics_or_policy_areas=["test", "law", "court", "opinion", "case"],
                case_name="Test v. Case",
                holding_plain="Test holding",
                outcome_simple="Test outcome",
                issue_plain="Test issue",
                reasoning="Test reasoning",
            )

        chunk_meta = ChunkMetadata(
            chunk_id="scotus_001_chunk_0",
            chunk_index=0,
            section_label="Majority Opinion",
        )

        combined = create_scotus_chunk_metadata(scotus_meta, chunk_meta)

        results["create_scotus_chunk_metadata"] = {
            "method": "create_scotus_chunk_metadata()",
            "result": {
                "field_count": len(combined),
                "has_document_fields": "document_id" in combined
                and "title" in combined,
                "has_chunk_fields": "chunk_id" in combined
                and "chunk_index" in combined,
                "sample_fields": {
                    k: v for k, v in list(combined.items())[:5]
                },  # Show first 5 fields
            },
        }
    except Exception as e:
        results["create_scotus_chunk_metadata"] = {
            "method": "create_scotus_chunk_metadata()",
            "error": str(e),
        }

    # Test create_eo_chunk_metadata
    try:
        # Use the previously created objects
        if (
            "ExecutiveOrderMetadata_creation" in results
            and "result" in results["ExecutiveOrderMetadata_creation"]
        ):
            eo_meta = ExecutiveOrderMetadata(
                **results["ExecutiveOrderMetadata_creation"]["result"]
            )
        else:
            # Fallback if creation failed
            eo_meta = ExecutiveOrderMetadata(
                document_id="eo_001",
                title="Test Executive Order",
                publication_date="2024-01-15",
                year=2024,
                source="Federal Register",
                type="Executive Order",
                url="https://example.com/eo",
                plain_language_summary="Test summary",
                topics_or_policy_areas=[
                    "test",
                    "policy",
                    "government",
                    "executive",
                    "order",
                ],
                eo_number="14001",
            )

        chunk_meta = ChunkMetadata(
            chunk_id="eo_001_chunk_0", chunk_index=0, section_label="Sec. 1"
        )

        combined = create_eo_chunk_metadata(eo_meta, chunk_meta)

        results["create_eo_chunk_metadata"] = {
            "method": "create_eo_chunk_metadata()",
            "result": {
                "field_count": len(combined),
                "has_document_fields": "document_id" in combined
                and "title" in combined,
                "has_chunk_fields": "chunk_id" in combined
                and "chunk_index" in combined,
                "has_eo_specific": "eo_number" in combined,
                "sample_fields": {
                    k: v for k, v in list(combined.items())[:5]
                },  # Show first 5 fields
            },
        }
    except Exception as e:
        results["create_eo_chunk_metadata"] = {
            "method": "create_eo_chunk_metadata()",
            "error": str(e),
        }

    # Test validation by creating objects with invalid data
    try:
        # Test validation - too few topics
        try:
            invalid_metadata = SharedMetadata(
                document_id="invalid_001",
                title="Invalid Document",
                publication_date="2024-01-15",
                year=2024,
                source="Test Source",
                type="Test Type",
                url="https://example.com/doc",
                plain_language_summary="Invalid summary",
                topics_or_policy_areas=["only", "three", "topics"],  # Should have 5-8
            )
            validation_result = "Validation passed unexpectedly"
        except Exception as validation_error:
            validation_result = (
                f"Validation failed as expected: {str(validation_error)}"
            )

        results["pydantic_validation"] = {
            "method": "Pydantic validation testing",
            "result": validation_result,
        }
    except Exception as e:
        results["pydantic_validation"] = {
            "method": "Pydantic validation testing",
            "error": str(e),
        }

    # Print results in pretty JSON format
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
