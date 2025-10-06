"""
Unit tests for Pydantic metadata schemas.

This module provides comprehensive tests for the Pydantic models that define
metadata structures for Supreme Court opinions and Executive Orders. Tests
ensure proper validation, serialization, and field constraints.

Test Categories:
    - Happy path: Valid model creation with all fields
    - Edge cases: Minimum/maximum field constraints, optional fields
    - Error handling: Invalid data types, missing required fields
    - Serialization: JSON conversion and round-trip validation

Python Learning Notes:
    - Pydantic models validate data automatically on instantiation
    - ValidationError is raised for invalid data
    - model_dump() converts models to dictionaries
    - model_validate() creates models from dictionaries
"""

import json
from datetime import datetime
from typing import List
import pytest
from pydantic import ValidationError

from governmentreporter.processors.schema import (
    SharedMetadata,
    ChunkMetadata,
    SupremeCourtMetadata,
    ExecutiveOrderMetadata,
    QdrantPayload,
)


class TestSharedMetadata:
    """
    Test suite for SharedMetadata base model.

    Tests the common metadata fields shared across all document types,
    ensuring proper validation and field constraints.

    Python Learning Notes:
        - Pydantic models inherit from BaseModel
        - Field validation happens automatically on instantiation
        - Default factories provide mutable default values safely
    """

    def test_create_valid_shared_metadata(self):
        """
        Test creation of valid SharedMetadata instance.

        Verifies all required and optional fields can be set correctly
        with appropriate data types.
        """
        # Arrange
        metadata_dict = {
            "document_id": "doc-12345",
            "title": "Test Case v. United States",
            "publication_date": "2024-01-15",
            "year": 2024,
            "source": "CourtListener",
            "type": "Supreme Court Opinion",
            "url": "https://example.com/doc-12345",
            "plain_language_summary": "The Court held that testing is important.",
            "constitution_cited": ["First Amendment", "Fourth Amendment"],
            "federal_statutes_cited": ["42 U.S.C. § 1983"],
            "federal_regulations_cited": ["40 C.F.R. Part 60"],
            "cases_cited": ["Brown v. Board, 347 U.S. 483 (1954)"],
            "topics_or_policy_areas": [
                "civil rights",
                "free speech",
                "education",
                "testing",
                "law",
            ],
        }

        # Act
        metadata = SharedMetadata(**metadata_dict)

        # Assert - Verify model creation and key fields
        assert metadata.document_id == "doc-12345"
        assert metadata.title == "Test Case v. United States"
        assert metadata.year == 2024
        assert len(metadata.constitution_cited) == 2
        assert len(metadata.topics_or_policy_areas) == 5
        assert metadata.federal_statutes_cited == ["42 U.S.C. § 1983"]
        assert "40 C.F.R. Part 60" in metadata.federal_regulations_cited

    def test_shared_metadata_missing_required_field(self):
        """
        Test that missing required fields raise ValidationError.

        Ensures Pydantic properly validates required fields and
        provides helpful error messages.
        """
        # Arrange - Missing 'title' field
        incomplete_dict = {
            "document_id": "doc-12345",
            # "title": missing!
            "publication_date": "2024-01-15",
            "year": 2024,
            "source": "CourtListener",
            "type": "Supreme Court Opinion",
            "url": "https://example.com/doc-12345",
            "plain_language_summary": "Test summary",
        }

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            SharedMetadata(**incomplete_dict)

        # Verify error mentions missing field
        assert "title" in str(exc_info.value)

    def test_shared_metadata_topics_validation(self):
        """
        Test validation of topics_or_policy_areas field constraints.

        Verifies that the field enforces min/max item constraints
        (5-8 topics required).
        """
        # Test too few topics
        metadata_dict = {
            "document_id": "doc-12345",
            "title": "Test Case",
            "publication_date": "2024-01-15",
            "year": 2024,
            "source": "CourtListener",
            "type": "Supreme Court Opinion",
            "url": "https://example.com",
            "plain_language_summary": "Summary",
            "topics_or_policy_areas": ["topic1", "topic2"],  # Only 2, need 5-8
        }

        with pytest.raises(ValidationError) as exc_info:
            SharedMetadata(**metadata_dict)
        assert "at least 5 items" in str(exc_info.value).lower()

        # Test too many topics
        metadata_dict["topics_or_policy_areas"] = [
            f"topic{i}" for i in range(10)
        ]  # 10 topics

        with pytest.raises(ValidationError) as exc_info:
            SharedMetadata(**metadata_dict)
        assert "at most 8 items" in str(exc_info.value).lower()

        # Test valid number of topics
        metadata_dict["topics_or_policy_areas"] = [
            f"topic{i}" for i in range(6)
        ]  # 6 topics
        metadata = SharedMetadata(**metadata_dict)
        assert len(metadata.topics_or_policy_areas) == 6

    def test_shared_metadata_default_lists(self):
        """
        Test that list fields have proper default empty lists.

        Ensures default_factory provides independent empty lists
        for each instance to avoid mutable default issues.
        """
        # Arrange - Minimal required fields only
        metadata_dict = {
            "document_id": "doc-12345",
            "title": "Test Case",
            "publication_date": "2024-01-15",
            "year": 2024,
            "source": "CourtListener",
            "type": "Supreme Court Opinion",
            "url": "https://example.com",
            "plain_language_summary": "Summary",
            "topics_or_policy_areas": ["t1", "t2", "t3", "t4", "t5"],
        }

        # Act
        metadata = SharedMetadata(**metadata_dict)

        # Assert - List fields should be empty by default
        assert metadata.constitution_cited == []
        assert metadata.federal_statutes_cited == []
        assert metadata.federal_regulations_cited == []
        assert metadata.cases_cited == []

        # Verify lists are independent (not shared)
        metadata.constitution_cited.append("First Amendment")
        metadata2 = SharedMetadata(**metadata_dict)
        assert metadata2.constitution_cited == []  # Should still be empty


class TestChunkMetadata:
    """
    Test suite for ChunkMetadata model.

    Tests chunk-specific metadata that tracks position and context
    within the source document.

    Python Learning Notes:
        - Optional fields can be None or have values
        - Type hints ensure proper data types
    """

    def test_create_valid_chunk_metadata(self):
        """
        Test creation of valid ChunkMetadata instance.

        Verifies chunk-level metadata fields work correctly.
        """
        # Arrange
        chunk_dict = {
            "chunk_id": "doc123_chunk_0",
            "chunk_index": 0,
            "section_label": "Syllabus",
        }

        # Act
        chunk_meta = ChunkMetadata(**chunk_dict)

        # Assert
        assert chunk_meta.chunk_id == "doc123_chunk_0"
        assert chunk_meta.chunk_index == 0
        assert chunk_meta.section_label == "Syllabus"

    def test_chunk_metadata_optional_fields(self):
        """
        Test that chunk_id and section_label are required fields.

        ChunkMetadata requires chunk_id, chunk_index, and section_label.
        """
        # Test that all fields are required
        with pytest.raises(ValidationError):
            ChunkMetadata(chunk_index=2)  # Missing chunk_id and section_label

    def test_chunk_metadata_validation(self):
        """
        Test validation of chunk metadata fields.

        Ensures proper type validation for chunk fields.
        """
        # Test invalid chunk_index type
        with pytest.raises(ValidationError):
            ChunkMetadata(
                chunk_id="test", chunk_index="not_an_int", section_label="Section"
            )

        # Test negative chunk_index (should be allowed)
        chunk = ChunkMetadata(chunk_id="test", chunk_index=-1, section_label="Section")
        assert chunk.chunk_index == -1  # Pydantic allows negative by default

        # Test invalid section_label type
        with pytest.raises(ValidationError):
            ChunkMetadata(chunk_id="test", chunk_index=0, section_label=123)


class TestSupremeCourtMetadata:
    """
    Test suite for SupremeCourtMetadata model.

    Tests Supreme Court opinion-specific metadata fields
    that extend the SharedMetadata base class.

    Python Learning Notes:
        - Inheritance allows extending base models
        - Super().__init__() is handled by Pydantic
    """

    def test_create_valid_scotus_metadata(self):
        """
        Test creation of valid Supreme Court metadata.

        Verifies all SCOTUS-specific fields work correctly
        alongside inherited shared fields.
        """
        # Arrange
        scotus_dict = {
            # Shared fields
            "document_id": "scotus-123",
            "title": "Miranda v. Arizona",
            "publication_date": "1966-06-13",
            "year": 1966,
            "source": "CourtListener",
            "type": "Supreme Court Opinion",
            "url": "https://example.com/miranda",
            "plain_language_summary": "Police must inform suspects of their rights.",
            "topics_or_policy_areas": [
                "criminal law",
                "civil rights",
                "police",
                "confession",
                "Fifth Amendment",
            ],
            # SCOTUS-specific fields
            "docket_number": "759",
            "case_name_short": "Miranda",
            "holding_plain": "Police must give Miranda warnings before interrogation.",
            "outcome_simple": "Conviction reversed",
            "issue_plain": "Are confessions without warnings admissible?",
            "reasoning": "The Fifth Amendment requires informing suspects of rights.",
            "majority_author": "Warren",
            "vote_majority": 5,
            "vote_minority": 4,
            "argued_date": "1966-02-28",
            "decided_date": "1966-06-13",
        }

        # Act
        metadata = SupremeCourtMetadata(**scotus_dict)

        # Assert
        assert metadata.case_name_short == "Miranda"
        assert metadata.majority_author == "Warren"
        assert metadata.vote_majority == 5
        assert metadata.vote_minority == 4
        assert (
            metadata.holding_plain
            == "Police must give Miranda warnings before interrogation."
        )

    def test_scotus_metadata_optional_fields(self):
        """
        Test that SCOTUS optional fields can be omitted.

        Ensures fields like vote counts and dates are optional.
        """
        # Arrange - Minimal SCOTUS metadata
        scotus_dict = {
            # Required shared fields
            "document_id": "scotus-123",
            "title": "Test Case",
            "publication_date": "2024-01-15",
            "year": 2024,
            "source": "CourtListener",
            "type": "Supreme Court Opinion",
            "url": "https://example.com",
            "plain_language_summary": "Summary",
            "topics_or_policy_areas": ["t1", "t2", "t3", "t4", "t5"],
            # Required SCOTUS fields
            "holding_plain": "The Court held...",
            "outcome_simple": "Affirmed",
            "issue_plain": "Whether...",
            "reasoning": "Because...",
        }

        # Act
        metadata = SupremeCourtMetadata(**scotus_dict)

        # Assert - Optional fields should be None
        assert metadata.docket_number is None
        assert metadata.case_name_short is None
        assert metadata.majority_author is None
        assert metadata.vote_majority is None
        assert metadata.vote_minority is None

    def test_scotus_metadata_inheritance(self):
        """
        Test that SCOTUS metadata properly inherits from SharedMetadata.

        Verifies inheritance chain and field availability.
        """
        # Arrange
        scotus_dict = {
            "document_id": "scotus-123",
            "title": "Test v. Case",
            "publication_date": "2024-01-15",
            "year": 2024,
            "source": "CourtListener",
            "type": "Supreme Court Opinion",
            "url": "https://example.com",
            "plain_language_summary": "Summary",
            "constitution_cited": ["First Amendment"],  # Inherited field
            "topics_or_policy_areas": ["t1", "t2", "t3", "t4", "t5"],
            "holding_plain": "Held...",
            "outcome_simple": "Reversed",
            "issue_plain": "Issue...",
            "reasoning": "Reasoning...",
        }

        # Act
        metadata = SupremeCourtMetadata(**scotus_dict)

        # Assert - Both inherited and specific fields work
        assert metadata.constitution_cited == ["First Amendment"]  # Inherited
        assert metadata.holding_plain == "Held..."  # SCOTUS-specific
        assert isinstance(metadata, SharedMetadata)  # Is-a relationship


class TestExecutiveOrderMetadata:
    """
    Test suite for ExecutiveOrderMetadata model.

    Tests Executive Order-specific metadata fields
    that extend the SharedMetadata base class.

    Python Learning Notes:
        - Different document types have different metadata needs
        - Pydantic ensures type safety across all fields
    """

    def test_create_valid_eo_metadata(self):
        """
        Test creation of valid Executive Order metadata.

        Verifies all EO-specific fields work correctly.
        """
        # Arrange
        eo_dict = {
            # Shared fields
            "document_id": "eo-14123",
            "title": "Executive Order on Climate Action",
            "publication_date": "2024-01-20",
            "year": 2024,
            "source": "Federal Register",
            "type": "Executive Order",
            "url": "https://federalregister.gov/eo-14123",
            "plain_language_summary": "Requires federal agencies to reduce emissions.",
            "topics_or_policy_areas": [
                "climate",
                "environment",
                "energy",
                "federal operations",
                "sustainability",
            ],
            # EO-specific fields
            "executive_order_number": "14123",
            "president": "Test President",
            "plain_summary": "Federal climate action order",
            "action_plain": "Mandates carbon neutrality by 2030",
            "impact_simple": "All agencies must use renewable energy",
            "implementation_requirements": "Quarterly reports required",
            "agencies_or_entities": ["EPA", "DOE", "DOD"],
            "signing_date": "2024-01-20",
            "effective_date": "2024-02-01",
            "federal_register_number": "2024-12345",
            "revokes": ["EO 13990", "EO 13834"],
        }

        # Act
        metadata = ExecutiveOrderMetadata(**eo_dict)

        # Assert
        assert metadata.executive_order_number == "14123"
        assert metadata.president == "Test President"
        assert len(metadata.agencies_or_entities) == 3
        assert "EPA" in metadata.agencies_or_entities
        assert len(metadata.revokes) == 2

    def test_eo_metadata_optional_fields(self):
        """
        Test that EO optional fields can be omitted.

        Ensures fields like revokes and dates are optional.
        """
        # Arrange - Minimal EO metadata
        eo_dict = {
            # Required shared fields
            "document_id": "eo-123",
            "title": "Test Order",
            "publication_date": "2024-01-15",
            "year": 2024,
            "source": "Federal Register",
            "type": "Executive Order",
            "url": "https://example.com",
            "plain_language_summary": "Summary",
            "topics_or_policy_areas": ["t1", "t2", "t3", "t4", "t5"],
            # Required EO fields
            "plain_summary": "Summary",
            "action_plain": "Action",
            "impact_simple": "Impact",
            "implementation_requirements": "Requirements",
        }

        # Act
        metadata = ExecutiveOrderMetadata(**eo_dict)

        # Assert - Optional fields should be None or empty
        assert metadata.executive_order_number is None
        assert metadata.president is None
        assert metadata.agencies_or_entities == []
        assert metadata.revokes == []
        assert metadata.signing_date is None

    def test_eo_metadata_list_validation(self):
        """
        Test validation of list fields in EO metadata.

        Ensures list fields properly handle various inputs.
        """
        # Arrange
        eo_dict = {
            "document_id": "eo-123",
            "title": "Test Order",
            "publication_date": "2024-01-15",
            "year": 2024,
            "source": "Federal Register",
            "type": "Executive Order",
            "url": "https://example.com",
            "plain_language_summary": "Summary",
            "topics_or_policy_areas": ["t1", "t2", "t3", "t4", "t5"],
            "plain_summary": "Summary",
            "action_plain": "Action",
            "impact_simple": "Impact",
            "implementation_requirements": "Requirements",
            "agencies_or_entities": ["EPA", "DOE", "DOD", "NASA", "NOAA"],
            "revokes": [],  # Empty list is valid
        }

        # Act
        metadata = ExecutiveOrderMetadata(**eo_dict)

        # Assert
        assert len(metadata.agencies_or_entities) == 5
        assert metadata.revokes == []


class TestQdrantPayload:
    """
    Test suite for QdrantPayload model.

    Tests the complete payload structure used for Qdrant storage,
    combining chunk text with metadata.

    Python Learning Notes:
        - QdrantPayload combines text with metadata
        - Used for vector database storage
    """

    def test_create_scotus_payload(self):
        """
        Test creation of Qdrant payload for SCOTUS document.

        Verifies payload structure with Supreme Court metadata.
        """
        # Arrange
        scotus_metadata = {
            "document_id": "scotus-123",
            "title": "Test Case",
            "publication_date": "2024-01-15",
            "year": 2024,
            "source": "CourtListener",
            "type": "Supreme Court Opinion",
            "url": "https://example.com",
            "plain_language_summary": "Summary",
            "topics_or_policy_areas": ["t1", "t2", "t3", "t4", "t5"],
            "holding_plain": "Held...",
            "outcome_simple": "Reversed",
            "issue_plain": "Issue...",
            "reasoning": "Reasoning...",
            "chunk_index": 0,
            "chunk_total": 3,
        }

        payload_dict = {
            "id": "scotus-123-chunk-0",
            "text": "This is the chunk text from the opinion.",
            "metadata": scotus_metadata,
        }

        # Act
        payload = QdrantPayload(**payload_dict)

        # Assert
        assert payload.id == "scotus-123-chunk-0"
        assert payload.text == "This is the chunk text from the opinion."
        assert payload.metadata["document_id"] == "scotus-123"
        assert payload.metadata["chunk_index"] == 0

    def test_create_eo_payload(self):
        """
        Test creation of Qdrant payload for Executive Order.

        Verifies payload structure with EO metadata.
        """
        # Arrange
        eo_metadata = {
            "document_id": "eo-14123",
            "title": "Climate Action Order",
            "publication_date": "2024-01-20",
            "year": 2024,
            "source": "Federal Register",
            "type": "Executive Order",
            "url": "https://federalregister.gov",
            "plain_language_summary": "Climate order",
            "topics_or_policy_areas": [
                "climate",
                "energy",
                "environment",
                "federal",
                "sustainability",
            ],
            "plain_summary": "Summary",
            "action_plain": "Action",
            "impact_simple": "Impact",
            "implementation_requirements": "Requirements",
            "chunk_index": 1,
            "chunk_total": 5,
        }

        payload_dict = {
            "id": "eo-14123-chunk-1",
            "text": "Section 2. Policy. The United States shall...",
            "metadata": eo_metadata,
        }

        # Act
        payload = QdrantPayload(**payload_dict)

        # Assert
        assert payload.id == "eo-14123-chunk-1"
        assert "Section 2" in payload.text
        assert payload.metadata["type"] == "Executive Order"
        assert payload.metadata["chunk_index"] == 1


class TestSchemaSerializationDeserialization:
    """
    Test suite for model serialization and deserialization.

    Tests JSON conversion and round-trip validation to ensure
    models can be properly stored and retrieved.

    Python Learning Notes:
        - model_dump() converts to dictionary
        - model_dump_json() converts to JSON string
        - model_validate() creates from dictionary
        - model_validate_json() creates from JSON string
    """

    def test_shared_metadata_json_round_trip(self):
        """
        Test JSON serialization round-trip for SharedMetadata.

        Verifies model can be converted to JSON and back without loss.
        """
        # Arrange
        original = SharedMetadata(
            document_id="doc-123",
            title="Test Document",
            publication_date="2024-01-15",
            year=2024,
            source="TestSource",
            type="TestType",
            url="https://example.com",
            plain_language_summary="Summary",
            constitution_cited=["First Amendment"],
            topics_or_policy_areas=["t1", "t2", "t3", "t4", "t5"],
        )

        # Act - Convert to JSON and back
        json_str = original.model_dump_json()
        json_data = json.loads(json_str)
        restored = SharedMetadata.model_validate(json_data)

        # Assert
        assert restored.document_id == original.document_id
        assert restored.constitution_cited == original.constitution_cited
        assert restored.topics_or_policy_areas == original.topics_or_policy_areas

    def test_scotus_metadata_dict_conversion(self):
        """
        Test dictionary conversion for SupremeCourtMetadata.

        Verifies model_dump() creates proper dictionary representation.
        """
        # Arrange
        metadata = SupremeCourtMetadata(
            document_id="scotus-123",
            title="Test v. Case",
            publication_date="2024-01-15",
            year=2024,
            source="CourtListener",
            type="Supreme Court Opinion",
            url="https://example.com",
            plain_language_summary="Summary",
            topics_or_policy_areas=["t1", "t2", "t3", "t4", "t5"],
            holding_plain="Held...",
            outcome_simple="Reversed",
            issue_plain="Issue...",
            reasoning="Reasoning...",
            majority_author="Roberts",
            vote_majority=5,
            vote_minority=4,
        )

        # Act
        data_dict = metadata.model_dump()

        # Assert
        assert isinstance(data_dict, dict)
        assert data_dict["document_id"] == "scotus-123"
        assert data_dict["majority_author"] == "Roberts"
        assert data_dict["vote_majority"] == 5

        # Verify optional fields excluded when None
        assert "docket_number" not in data_dict or data_dict["docket_number"] is None

    def test_payload_nested_serialization(self):
        """
        Test serialization of QdrantPayload with nested metadata.

        Verifies complex nested structures serialize correctly.
        """
        # Arrange
        payload = QdrantPayload(
            id="test-chunk-1",
            text="Chunk text content",
            metadata={
                "document_id": "doc-123",
                "title": "Test",
                "publication_date": "2024-01-15",
                "year": 2024,
                "source": "Test",
                "type": "Test",
                "url": "https://example.com",
                "plain_language_summary": "Summary",
                "topics_or_policy_areas": ["t1", "t2", "t3", "t4", "t5"],
                "chunk_index": 0,
                "chunk_total": 1,
            },
        )

        # Act
        json_str = payload.model_dump_json()
        restored_dict = json.loads(json_str)

        # Assert
        assert restored_dict["id"] == "test-chunk-1"
        assert restored_dict["metadata"]["document_id"] == "doc-123"
        assert restored_dict["metadata"]["chunk_index"] == 0


# Test fixtures for schema tests
@pytest.fixture
def valid_shared_metadata_dict():
    """
    Provide valid SharedMetadata dictionary for testing.

    Returns:
        dict: Complete valid metadata dictionary

    Python Learning Notes:
        - Fixtures provide reusable test data
        - Reduces duplication across tests
    """
    return {
        "document_id": "test-123",
        "title": "Test Document Title",
        "publication_date": "2024-01-15",
        "year": 2024,
        "source": "TestSource",
        "type": "TestType",
        "url": "https://example.com/test",
        "plain_language_summary": "This is a test summary.",
        "constitution_cited": ["First Amendment", "Fourth Amendment"],
        "federal_statutes_cited": ["42 U.S.C. § 1983"],
        "federal_regulations_cited": ["40 C.F.R. Part 60"],
        "cases_cited": ["Test v. Case, 123 U.S. 456 (2024)"],
        "topics_or_policy_areas": ["topic1", "topic2", "topic3", "topic4", "topic5"],
    }


@pytest.fixture
def valid_scotus_metadata_dict(valid_shared_metadata_dict):
    """
    Provide valid SupremeCourtMetadata dictionary for testing.

    Args:
        valid_shared_metadata_dict: Base metadata fixture

    Returns:
        dict: Complete SCOTUS metadata dictionary

    Python Learning Notes:
        - Fixtures can depend on other fixtures
        - Dictionary update modifies in place
    """
    scotus_dict = valid_shared_metadata_dict.copy()
    scotus_dict.update(
        {
            "source": "CourtListener",
            "type": "Supreme Court Opinion",
            "holding_plain": "The Court held that...",
            "outcome_simple": "Reversed and remanded",
            "issue_plain": "Whether the law violates...",
            "reasoning": "The Court reasoned that...",
            "majority_author": "Roberts",
            "vote_majority": 5,
            "vote_minority": 4,
        }
    )
    return scotus_dict


@pytest.fixture
def valid_eo_metadata_dict(valid_shared_metadata_dict):
    """
    Provide valid ExecutiveOrderMetadata dictionary for testing.

    Args:
        valid_shared_metadata_dict: Base metadata fixture

    Returns:
        dict: Complete EO metadata dictionary
    """
    eo_dict = valid_shared_metadata_dict.copy()
    eo_dict.update(
        {
            "source": "Federal Register",
            "type": "Executive Order",
            "plain_summary": "Order summary",
            "action_plain": "Requires agencies to...",
            "impact_simple": "Federal operations must...",
            "implementation_requirements": "Agencies shall submit...",
            "agencies_or_entities": ["EPA", "DOE"],
            "executive_order_number": "14123",
        }
    )
    return eo_dict
