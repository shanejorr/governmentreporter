"""
Unit tests for abstract base classes and data models in the APIs module.

This module provides comprehensive tests for the base API infrastructure, including
the Document dataclass and GovernmentAPIClient abstract base class. These tests
ensure the foundational contracts are properly enforced and that all API clients
have a consistent interface.

Test Categories:
    - Document dataclass: Validation, field handling, equality checks
    - Abstract base class: Interface enforcement, concrete method testing
    - Mock implementations: Verify abstract class usage patterns
    - Edge cases: Boundary conditions, None values, type validation

Python Learning Notes:
    - Testing abstract classes requires mock implementations
    - dataclass testing verifies automatic method generation
    - ABC testing ensures subclass contracts are enforced
    - Type validation tests help catch runtime errors early
"""

import pytest
from dataclasses import FrozenInstanceError, fields, is_dataclass
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch, call
from abc import ABC

from governmentreporter.apis.base import Document, GovernmentAPIClient


class TestDocumentDataclass:
    """
    Test suite for the Document dataclass.

    This class tests all aspects of the Document dataclass, including field
    validation, automatic method generation, and proper handling of optional
    fields. The Document class is fundamental to the entire system as it
    represents all government documents uniformly.

    Python Learning Notes:
        - Dataclasses automatically generate __init__, __repr__, __eq__
        - Field order matters: required fields must come before optional
        - Type hints are not enforced at runtime by default
    """

    def test_document_creation_with_required_fields(self):
        """
        Test creating a Document with only required fields.

        Verifies that a Document can be created with just the mandatory fields,
        and that optional fields default to None as expected.

        Python Learning Notes:
            - Required fields have no default values
            - Optional fields should have None as default
            - isinstance() checks object type
        """
        # Arrange & Act: Create document with required fields only
        doc = Document(
            id="test-123",
            title="Test Document",
            date="2024-01-15",
            type="test_type",
            source="test_source",
        )

        # Assert: Required fields are set correctly
        assert doc.id == "test-123"
        assert doc.title == "Test Document"
        assert doc.date == "2024-01-15"
        assert doc.type == "test_type"
        assert doc.source == "test_source"

        # Assert: Optional fields default to None
        assert doc.content is None
        assert doc.metadata is None
        assert doc.url is None

        # Assert: Document is instance of correct class
        assert isinstance(doc, Document)

    def test_document_creation_with_all_fields(self):
        """
        Test creating a Document with all fields populated.

        Ensures that all fields, both required and optional, can be set
        during initialization and are stored correctly.

        Python Learning Notes:
            - Keyword arguments make code more readable
            - Dict[str, Any] allows flexible metadata storage
        """
        # Arrange: Prepare test data
        metadata = {
            "court": "Supreme Court",
            "docket": "20-123",
            "judges": ["Roberts", "Thomas"],
        }

        # Act: Create fully populated document
        doc = Document(
            id="full-456",
            title="Complete Test Case",
            date="2024-03-20",
            type="scotus_opinion",
            source="courtlistener",
            content="This is the full text content of the opinion.",
            metadata=metadata,
            url="https://example.com/opinion/456",
        )

        # Assert: All fields are set correctly
        assert doc.id == "full-456"
        assert doc.title == "Complete Test Case"
        assert doc.date == "2024-03-20"
        assert doc.type == "scotus_opinion"
        assert doc.source == "courtlistener"
        assert doc.content == "This is the full text content of the opinion."
        assert doc.metadata == metadata
        assert doc.metadata["court"] == "Supreme Court"
        assert doc.url == "https://example.com/opinion/456"

    def test_document_is_dataclass(self):
        """
        Test that Document is properly configured as a dataclass.

        Verifies that the @dataclass decorator is applied and working,
        providing all expected dataclass functionality.

        Python Learning Notes:
            - is_dataclass() checks if class uses @dataclass
            - fields() returns dataclass field definitions
            - Dataclasses provide automatic special methods
        """
        # Assert: Document is a dataclass
        assert is_dataclass(Document)

        # Assert: Has expected number of fields
        doc_fields = fields(Document)
        assert len(doc_fields) == 8

        # Assert: Field names are correct
        field_names = [f.name for f in doc_fields]
        expected_fields = [
            "id",
            "title",
            "date",
            "type",
            "source",
            "content",
            "metadata",
            "url",
        ]
        assert field_names == expected_fields

        # Assert: Check field types
        field_types = {f.name: f.type for f in doc_fields}
        assert field_types["id"] == str
        assert field_types["content"] == Optional[str]
        assert field_types["metadata"] == Optional[Dict[str, Any]]

    def test_document_equality(self):
        """
        Test Document equality comparison (__eq__ method).

        Dataclasses automatically generate __eq__ that compares all fields.
        This test ensures equality works as expected.

        Python Learning Notes:
            - __eq__ is auto-generated by @dataclass
            - Equality compares all fields by default
            - == operator uses __eq__ method
        """
        # Arrange: Create two identical documents
        doc1 = Document(
            id="eq-test",
            title="Equality Test",
            date="2024-01-01",
            type="test",
            source="test",
        )

        doc2 = Document(
            id="eq-test",
            title="Equality Test",
            date="2024-01-01",
            type="test",
            source="test",
        )

        # Act & Assert: Documents are equal
        assert doc1 == doc2
        assert not (doc1 != doc2)

        # Modify one field
        doc3 = Document(
            id="eq-test-different",  # Different ID
            title="Equality Test",
            date="2024-01-01",
            type="test",
            source="test",
        )

        # Assert: Different documents are not equal
        assert doc1 != doc3
        assert not (doc1 == doc3)

    def test_document_repr(self):
        """
        Test Document string representation (__repr__ method).

        Dataclasses generate a useful __repr__ that shows all field values,
        helpful for debugging and logging.

        Python Learning Notes:
            - __repr__ should return unambiguous representation
            - repr() calls object's __repr__ method
            - Good for debugging and logging
        """
        # Arrange & Act: Create document
        doc = Document(
            id="repr-123",
            title="Repr Test",
            date="2024-02-15",
            type="test_type",
            source="test_source",
        )

        # Act: Get string representation
        repr_str = repr(doc)

        # Assert: Repr contains class name and all fields
        assert "Document" in repr_str
        assert "id='repr-123'" in repr_str
        assert "title='Repr Test'" in repr_str
        assert "date='2024-02-15'" in repr_str
        assert "type='test_type'" in repr_str
        assert "source='test_source'" in repr_str
        assert "content=None" in repr_str
        assert "metadata=None" in repr_str
        assert "url=None" in repr_str

    def test_document_with_empty_strings(self):
        """
        Test Document creation with empty strings for required fields.

        Empty strings are valid string values, so they should be accepted
        even though they might not be semantically valid.

        Python Learning Notes:
            - Empty strings are truthy for type checking
            - Validation logic would be separate from dataclass
        """
        # Act: Create document with empty strings
        doc = Document(id="", title="", date="", type="", source="")

        # Assert: Empty strings are accepted
        assert doc.id == ""
        assert doc.title == ""
        assert doc.date == ""
        assert doc.type == ""
        assert doc.source == ""

    def test_document_metadata_manipulation(self):
        """
        Test that Document metadata can be manipulated after creation.

        Since Document uses regular dataclass (not frozen), fields can be
        modified after instantiation.

        Python Learning Notes:
            - Mutable dataclasses allow field modification
            - frozen=True would make dataclass immutable
            - Dictionary fields remain mutable even in frozen dataclasses
        """
        # Arrange: Create document with metadata
        doc = Document(
            id="meta-test",
            title="Metadata Test",
            date="2024-01-01",
            type="test",
            source="test",
            metadata={"initial": "value"},
        )

        # Act: Modify metadata
        doc.metadata["new_key"] = "new_value"
        doc.metadata.update({"another": "field"})

        # Assert: Metadata is modified
        assert doc.metadata["initial"] == "value"
        assert doc.metadata["new_key"] == "new_value"
        assert doc.metadata["another"] == "field"
        assert len(doc.metadata) == 3

        # Act: Replace entire metadata
        doc.metadata = {"completely": "different"}

        # Assert: Metadata is replaced
        assert doc.metadata == {"completely": "different"}

    def test_document_field_modification(self):
        """
        Test that Document fields can be modified after creation.

        Regular dataclasses allow field updates, which is useful for
        populating content lazily or updating metadata.

        Python Learning Notes:
            - Attribute assignment uses setattr internally
            - Mutable objects are common in Python
        """
        # Arrange: Create document
        doc = Document(
            id="mod-test",
            title="Original Title",
            date="2024-01-01",
            type="original_type",
            source="original_source",
        )

        # Act: Modify fields
        doc.title = "Modified Title"
        doc.content = "Now has content"
        doc.url = "https://modified.url"

        # Assert: Fields are modified
        assert doc.title == "Modified Title"
        assert doc.content == "Now has content"
        assert doc.url == "https://modified.url"

        # Original fields unchanged
        assert doc.id == "mod-test"
        assert doc.date == "2024-01-01"

    def test_document_none_metadata_access(self):
        """
        Test accessing metadata when it's None.

        This test ensures proper handling of None metadata to avoid
        AttributeError when trying to access dictionary methods.

        Python Learning Notes:
            - None has no dictionary methods
            - Need to check for None before dictionary operations
        """
        # Arrange: Create document without metadata
        doc = Document(
            id="none-meta",
            title="No Metadata",
            date="2024-01-01",
            type="test",
            source="test",
        )

        # Assert: Metadata is None
        assert doc.metadata is None

        # Act & Assert: Accessing None metadata would raise TypeError
        with pytest.raises(TypeError):
            doc.metadata["key"]  # This will fail

        # Safe way to check metadata
        value = doc.metadata.get("key") if doc.metadata else None
        assert value is None

    def test_document_type_hints_not_enforced(self):
        """
        Test that type hints are not enforced at runtime.

        Python's type hints are for static analysis and documentation,
        not runtime type checking by default.

        Python Learning Notes:
            - Type hints are not enforced at runtime
            - Use mypy or similar for static type checking
            - Runtime type checking requires additional code
        """
        # Act: Create document with wrong types (this works!)
        doc = Document(
            id=123,  # Should be str
            title=None,  # Should be str
            date=["2024", "01", "01"],  # Should be str
            type=True,  # Should be str
            source={"source": "dict"},  # Should be str
        )

        # Assert: Wrong types are accepted (no runtime validation)
        assert doc.id == 123
        assert doc.title is None
        assert doc.date == ["2024", "01", "01"]
        assert doc.type is True
        assert doc.source == {"source": "dict"}

        # This shows why validation logic is important!

    def test_document_copy(self):
        """
        Test creating a copy of a Document.

        Verifies that documents can be copied and that the copy is
        independent of the original.

        Python Learning Notes:
            - copy module provides shallow and deep copy
            - Dataclasses work with standard copy operations
        """
        import copy

        # Arrange: Create original document
        original = Document(
            id="copy-test",
            title="Original",
            date="2024-01-01",
            type="test",
            source="test",
            metadata={"key": "value"},
        )

        # Act: Create shallow copy
        shallow = copy.copy(original)

        # Assert: Copy has same values
        assert shallow.id == original.id
        assert shallow.title == original.title
        assert shallow.metadata == original.metadata

        # Act: Modify shallow copy
        shallow.title = "Modified Copy"
        shallow.metadata["new"] = "data"

        # Assert: Title change doesn't affect original (string is immutable)
        assert original.title == "Original"
        assert shallow.title == "Modified Copy"

        # Assert: Metadata change DOES affect original (shallow copy)
        assert original.metadata["new"] == "data"

        # Act: Create deep copy
        deep = copy.deepcopy(original)
        deep.metadata["deep"] = "change"

        # Assert: Deep copy changes don't affect original
        assert "deep" not in original.metadata
        assert deep.metadata["deep"] == "change"


class MockGovernmentAPIClient(GovernmentAPIClient):
    """
    Mock implementation of GovernmentAPIClient for testing.

    This concrete implementation allows us to test the abstract base class
    behavior and verify that the template method pattern works correctly.

    Python Learning Notes:
        - Must implement all abstract methods to instantiate
        - Can override concrete methods if needed
        - Used to test base class functionality
    """

    def _get_base_url(self) -> str:
        """Return mock base URL."""
        return "https://mock.api.gov/v1"

    def _get_rate_limit_delay(self) -> float:
        """Return mock rate limit delay."""
        return 0.5

    def search_documents(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
    ) -> list:
        """Mock search implementation."""
        return [
            Document(
                id=f"mock-{i}",
                title=f"Mock Result {i}",
                date="2024-01-01",
                type="mock",
                source="mock_api",
            )
            for i in range(min(3, limit))
        ]

    def get_document(self, document_id: str) -> Document:
        """Mock get document implementation."""
        return Document(
            id=document_id,
            title=f"Mock Document {document_id}",
            date="2024-01-01",
            type="mock",
            source="mock_api",
            content=f"Mock content for {document_id}",
        )

    def get_document_text(self, document_id: str) -> str:
        """Mock get document text implementation."""
        return f"Mock text content for document {document_id}"


class TestGovernmentAPIClient:
    """
    Test suite for the GovernmentAPIClient abstract base class.

    This class tests the abstract base class functionality, including the
    template method pattern in __init__, concrete method implementations,
    and proper enforcement of the abstract interface.

    Python Learning Notes:
        - Abstract base classes cannot be instantiated directly
        - Concrete methods in ABCs can be tested via mock implementations
        - Template method pattern provides common initialization
    """

    def test_cannot_instantiate_abstract_class(self):
        """
        Test that GovernmentAPIClient cannot be instantiated directly.

        Abstract base classes with unimplemented abstract methods should
        raise TypeError when instantiated.

        Python Learning Notes:
            - ABC prevents instantiation of abstract classes
            - TypeError is raised with list of abstract methods
            - Forces proper implementation in subclasses
        """
        # Act & Assert: Cannot create instance of abstract class
        with pytest.raises(TypeError) as exc_info:
            client = GovernmentAPIClient()

        # Assert: Error message mentions abstract methods
        error_msg = str(exc_info.value)
        assert "abstract" in error_msg.lower()
        # The error lists the abstract methods that need implementation

    def test_mock_implementation_initialization(self):
        """
        Test that mock implementation initializes correctly.

        Verifies the template method pattern works, with __init__ calling
        abstract methods that are implemented in the subclass.

        Python Learning Notes:
            - Template method pattern: base class defines algorithm
            - Subclasses provide specific implementations
            - self refers to actual instance (subclass)
        """
        # Act: Create mock implementation
        client = MockGovernmentAPIClient(api_key="test-key-123")

        # Assert: Initialization set attributes correctly
        assert client.api_key == "test-key-123"
        assert client.base_url == "https://mock.api.gov/v1"
        assert client.rate_limit_delay == 0.5

        # Assert: Instance is of correct types
        assert isinstance(client, MockGovernmentAPIClient)
        assert isinstance(client, GovernmentAPIClient)
        assert isinstance(client, ABC)

    def test_initialization_without_api_key(self):
        """
        Test initialization without providing an API key.

        Some APIs don't require authentication, so api_key should be
        optional and default to None.

        Python Learning Notes:
            - Optional parameters with None default
            - None is a valid value for api_key
        """
        # Act: Create client without API key
        client = MockGovernmentAPIClient()

        # Assert: API key is None
        assert client.api_key is None
        assert client.base_url == "https://mock.api.gov/v1"
        assert client.rate_limit_delay == 0.5

    def test_validate_date_format_valid_dates(self):
        """
        Test validate_date_format with valid date strings.

        This concrete method should accept dates in YYYY-MM-DD format
        and reject all other formats.

        Python Learning Notes:
            - Regular expressions for pattern matching
            - Concrete methods are inherited by all subclasses
        """
        # Arrange: Create client instance
        client = MockGovernmentAPIClient()

        # Act & Assert: Valid dates return True
        assert client.validate_date_format("2024-01-01") is True
        assert client.validate_date_format("2024-12-31") is True
        assert client.validate_date_format("2000-01-01") is True
        assert client.validate_date_format("2099-06-15") is True
        assert client.validate_date_format("1999-09-09") is True

        # Edge cases that are format-valid
        assert (
            client.validate_date_format("0000-00-00") is True
        )  # Invalid date, valid format
        assert (
            client.validate_date_format("9999-99-99") is True
        )  # Invalid date, valid format

    def test_validate_date_format_invalid_dates(self):
        """
        Test validate_date_format with invalid date strings.

        Should reject dates not in YYYY-MM-DD format, including common
        alternative formats and malformed strings.

        Python Learning Notes:
            - Pattern matching is strict
            - Different date formats need conversion
        """
        # Arrange: Create client instance
        client = MockGovernmentAPIClient()

        # Act & Assert: Invalid formats return False
        assert client.validate_date_format("2024-1-1") is False  # Missing zeros
        assert client.validate_date_format("2024-01-1") is False  # Missing zero in day
        assert (
            client.validate_date_format("2024-1-01") is False
        )  # Missing zero in month
        assert client.validate_date_format("01/01/2024") is False  # Wrong delimiter
        assert client.validate_date_format("01-01-2024") is False  # Wrong order
        assert client.validate_date_format("2024/01/01") is False  # Slashes not hyphens
        assert client.validate_date_format("2024.01.01") is False  # Dots not hyphens
        assert client.validate_date_format("January 1, 2024") is False  # Text format
        assert client.validate_date_format("2024") is False  # Year only
        assert client.validate_date_format("2024-01") is False  # Year-month only
        assert client.validate_date_format("") is False  # Empty string
        assert client.validate_date_format("not-a-date") is False  # Random string
        assert (
            client.validate_date_format("2024-13-01") is True
        )  # Invalid month, valid format

    def test_validate_date_format_edge_cases(self):
        """
        Test validate_date_format with edge cases.

        Tests unusual inputs that might cause issues, including None,
        special characters, and very long strings.

        Python Learning Notes:
            - Always test None inputs
            - Regular expressions can have performance implications
        """
        # Arrange: Create client instance
        client = MockGovernmentAPIClient()

        # Act & Assert: Edge cases
        # Note: This will raise TypeError since re.match expects string
        with pytest.raises(TypeError):
            client.validate_date_format(None)

        # Extra characters
        assert client.validate_date_format("2024-01-01 ") is False  # Trailing space
        assert client.validate_date_format(" 2024-01-01") is False  # Leading space
        assert (
            client.validate_date_format("2024-01-01T00:00:00") is False
        )  # ISO datetime
        assert client.validate_date_format("2024-01-01Z") is False  # With timezone

        # SQL injection attempt (should just return False)
        assert client.validate_date_format("2024-01-01'; DROP TABLE--") is False

        # Very long string (should not cause issues)
        assert client.validate_date_format("2024-01-01" * 1000) is False

    def test_mock_search_documents(self):
        """
        Test the mock implementation of search_documents.

        Verifies that our mock implementation works correctly for testing
        other components that depend on GovernmentAPIClient.

        Python Learning Notes:
            - Mock implementations help test integrations
            - Return predictable data for testing
        """
        # Arrange: Create client
        client = MockGovernmentAPIClient()

        # Act: Search with various parameters
        results = client.search_documents("test query")

        # Assert: Returns expected mock results
        assert len(results) == 3
        assert all(isinstance(doc, Document) for doc in results)
        assert results[0].id == "mock-0"
        assert results[1].title == "Mock Result 1"

        # Act: Search with limit
        limited_results = client.search_documents("test", limit=2)

        # Assert: Respects limit
        assert len(limited_results) == 2

        # Act: Search with dates (ignored in mock)
        date_results = client.search_documents(
            "test", start_date="2024-01-01", end_date="2024-12-31"
        )

        # Assert: Dates don't affect mock results
        assert len(date_results) == 3

    def test_mock_get_document(self):
        """
        Test the mock implementation of get_document.

        Verifies that document retrieval works correctly in the mock
        implementation.

        Python Learning Notes:
            - Mock should behave like real implementation
            - Consistent return types are important
        """
        # Arrange: Create client
        client = MockGovernmentAPIClient()

        # Act: Get document
        doc = client.get_document("test-123")

        # Assert: Returns correct document
        assert isinstance(doc, Document)
        assert doc.id == "test-123"
        assert doc.title == "Mock Document test-123"
        assert doc.content == "Mock content for test-123"
        assert doc.type == "mock"
        assert doc.source == "mock_api"

    def test_mock_get_document_text(self):
        """
        Test the mock implementation of get_document_text.

        Verifies that text retrieval works correctly in the mock
        implementation.

        Python Learning Notes:
            - Simple methods can return formatted strings
            - f-strings make string formatting clear
        """
        # Arrange: Create client
        client = MockGovernmentAPIClient()

        # Act: Get document text
        text = client.get_document_text("text-456")

        # Assert: Returns correct text
        assert isinstance(text, str)
        assert text == "Mock text content for document text-456"
        assert "text-456" in text

    def test_subclass_with_different_init(self):
        """
        Test that subclasses can extend initialization.

        Subclasses might need additional initialization parameters while
        still calling the parent __init__.

        Python Learning Notes:
            - super().__init__() calls parent initializer
            - Subclasses can add their own parameters
        """

        class ExtendedMockClient(MockGovernmentAPIClient):
            """Mock client with extended initialization."""

            def __init__(self, api_key=None, custom_param="default"):
                super().__init__(api_key)
                self.custom_param = custom_param

        # Act: Create extended client
        client = ExtendedMockClient(api_key="extended-key", custom_param="custom-value")

        # Assert: Both parent and child attributes are set
        assert client.api_key == "extended-key"
        assert client.base_url == "https://mock.api.gov/v1"
        assert client.custom_param == "custom-value"

    def test_incomplete_implementation_raises_error(self):
        """
        Test that incomplete implementations cannot be instantiated.

        If a subclass doesn't implement all abstract methods, it should
        raise TypeError on instantiation.

        Python Learning Notes:
            - All abstract methods must be implemented
            - Partial implementations are still abstract
        """

        class IncompleteClient(GovernmentAPIClient):
            """Incomplete implementation missing some methods."""

            def _get_base_url(self) -> str:
                return "https://incomplete.api"

            def _get_rate_limit_delay(self) -> float:
                return 1.0

            # Missing: search_documents, get_document, get_document_text

        # Act & Assert: Cannot instantiate incomplete implementation
        with pytest.raises(TypeError) as exc_info:
            client = IncompleteClient()

        # Assert: Error mentions missing methods
        error_msg = str(exc_info.value)
        assert "abstract" in error_msg.lower()


class TestDocumentUsagePatterns:
    """
    Test common usage patterns for Document objects.

    These tests demonstrate how Document objects are typically used
    in the application, including serialization, filtering, and
    collection operations.

    Python Learning Notes:
        - Real-world usage patterns help design better APIs
        - Collections of dataclass objects are common
    """

    def test_document_collection_operations(self):
        """
        Test working with collections of Document objects.

        Documents are often processed in batches, filtered, and sorted.
        This test verifies these operations work correctly.

        Python Learning Notes:
            - List comprehensions for filtering
            - sorted() with key functions
            - all() and any() for collection checks
        """
        # Arrange: Create collection of documents
        documents = [
            Document(
                id=f"doc-{i}",
                title=f"Document {i}",
                date=f"2024-01-{i:02d}",
                type="opinion" if i % 2 == 0 else "order",
                source="courtlistener",
            )
            for i in range(1, 6)
        ]

        # Act: Filter by type
        opinions = [doc for doc in documents if doc.type == "opinion"]
        orders = [doc for doc in documents if doc.type == "order"]

        # Assert: Filtering works correctly
        assert len(opinions) == 2  # doc-2, doc-4
        assert len(orders) == 3  # doc-1, doc-3, doc-5
        assert all(doc.type == "opinion" for doc in opinions)
        assert all(doc.type == "order" for doc in orders)

        # Act: Sort by date
        sorted_docs = sorted(documents, key=lambda d: d.date)

        # Assert: Sorting works correctly
        assert sorted_docs[0].id == "doc-1"
        assert sorted_docs[-1].id == "doc-5"

        # Act: Check if any document has content
        has_content = any(doc.content is not None for doc in documents)

        # Assert: No documents have content
        assert has_content is False

    def test_document_to_dict_conversion(self):
        """
        Test converting Document objects to dictionaries.

        Common when serializing for JSON APIs or storage systems.
        Dataclasses work well with asdict() function.

        Python Learning Notes:
            - dataclasses.asdict() converts to dictionary
            - Useful for JSON serialization
            - Nested objects are also converted
        """
        from dataclasses import asdict

        # Arrange: Create document with all fields
        doc = Document(
            id="dict-test",
            title="Dictionary Test",
            date="2024-01-01",
            type="test",
            source="test",
            content="Test content",
            metadata={"nested": {"data": "value"}},
            url="https://example.com",
        )

        # Act: Convert to dictionary
        doc_dict = asdict(doc)

        # Assert: Dictionary has all fields
        assert isinstance(doc_dict, dict)
        assert doc_dict["id"] == "dict-test"
        assert doc_dict["title"] == "Dictionary Test"
        assert doc_dict["metadata"]["nested"]["data"] == "value"
        assert set(doc_dict.keys()) == {
            "id",
            "title",
            "date",
            "type",
            "source",
            "content",
            "metadata",
            "url",
        }

    def test_document_from_dict_creation(self):
        """
        Test creating Document objects from dictionaries.

        Common when deserializing from JSON APIs or databases.
        The ** operator unpacks dictionaries as keyword arguments.

        Python Learning Notes:
            - ** unpacks dictionary as keyword arguments
            - Useful for API response processing
            - Extra keys would cause TypeError
        """
        # Arrange: Dictionary with document data
        doc_data = {
            "id": "from-dict",
            "title": "From Dictionary",
            "date": "2024-01-01",
            "type": "test",
            "source": "api",
            "content": "Content from API",
            "metadata": {"api_version": "v1"},
            "url": "https://api.example.com/doc",
        }

        # Act: Create document from dictionary
        doc = Document(**doc_data)

        # Assert: Document created correctly
        assert doc.id == "from-dict"
        assert doc.title == "From Dictionary"
        assert doc.metadata["api_version"] == "v1"

        # Test with partial data (only required fields)
        partial_data = {
            "id": "partial",
            "title": "Partial Data",
            "date": "2024-01-01",
            "type": "test",
            "source": "api",
        }

        partial_doc = Document(**partial_data)
        assert partial_doc.id == "partial"
        assert partial_doc.content is None

    def test_document_as_cache_key(self):
        """
        Test using Document ID as cache key.

        Documents are often cached, and the ID field serves as a
        natural cache key.

        Python Learning Notes:
            - Dictionary keys must be hashable
            - Strings are immutable and hashable
            - Document objects are not hashable by default
        """
        # Arrange: Create documents
        doc1 = Document(
            id="cache-1",
            title="Cached Document 1",
            date="2024-01-01",
            type="test",
            source="cache",
        )

        doc2 = Document(
            id="cache-2",
            title="Cached Document 2",
            date="2024-01-02",
            type="test",
            source="cache",
        )

        # Act: Use IDs as cache keys
        cache = {}
        cache[doc1.id] = doc1
        cache[doc2.id] = doc2

        # Assert: Cache works correctly
        assert len(cache) == 2
        assert cache["cache-1"].title == "Cached Document 1"
        assert cache["cache-2"].title == "Cached Document 2"

        # Note: Document objects themselves are not hashable
        with pytest.raises(TypeError):
            cache[doc1] = "This won't work"


class TestAPIClientIntegration:
    """
    Integration tests for API client implementations.

    These tests verify that concrete implementations properly integrate
    with the abstract base class and follow expected patterns.

    Python Learning Notes:
        - Integration tests verify components work together
        - Mock implementations simulate real behavior
    """

    def test_rate_limiting_usage_pattern(self):
        """
        Test how rate limiting would be used in practice.

        The rate_limit_delay attribute should be used to space out
        API requests appropriately.

        Python Learning Notes:
            - time.sleep() pauses execution
            - Rate limiting prevents API abuse
        """
        import time

        # Arrange: Create client with known delay
        client = MockGovernmentAPIClient()
        assert client.rate_limit_delay == 0.5

        # Act: Simulate multiple API calls with rate limiting
        start_time = time.time()

        # Make first call
        doc1 = client.get_document("doc1")

        # Sleep for rate limit delay
        time.sleep(client.rate_limit_delay)

        # Make second call
        doc2 = client.get_document("doc2")

        end_time = time.time()
        elapsed = end_time - start_time

        # Assert: Time elapsed includes rate limit delay
        assert elapsed >= client.rate_limit_delay
        assert doc1.id == "doc1"
        assert doc2.id == "doc2"

    def test_api_client_with_mock_responses(self):
        """
        Test API client behavior with mocked HTTP responses.

        Shows how the actual implementations would be tested with
        mocked HTTP clients.

        Python Learning Notes:
            - Mocking HTTP clients isolates tests from network
            - Predictable responses enable reliable testing
        """
        # This demonstrates the testing pattern for real implementations

        class TestableClient(MockGovernmentAPIClient):
            """Client with injected HTTP client for testing."""

            def __init__(self, api_key=None, http_client=None):
                super().__init__(api_key)
                self.http_client = http_client or Mock()

            def search_documents(self, query, **kwargs):
                # Simulate real implementation using HTTP client
                response = self.http_client.get(
                    f"{self.base_url}/search", params={"q": query}
                )
                # Would normally parse response here
                return super().search_documents(query, **kwargs)

        # Arrange: Create client with mock HTTP client
        mock_http = Mock()
        mock_http.get.return_value.json.return_value = {
            "results": [{"id": "1", "title": "Test"}]
        }

        client = TestableClient(http_client=mock_http)

        # Act: Make search call
        results = client.search_documents("test query")

        # Assert: HTTP client was called correctly
        mock_http.get.assert_called_once_with(
            "https://mock.api.gov/v1/search", params={"q": "test query"}
        )
        assert len(results) == 3  # From mock implementation

    def test_error_handling_pattern(self):
        """
        Test error handling patterns in API clients.

        Shows how implementations should handle various error conditions
        from API calls.

        Python Learning Notes:
            - Custom exceptions for different error types
            - Proper error propagation and handling
        """

        class ErrorClient(MockGovernmentAPIClient):
            """Client that simulates various errors."""

            def get_document(self, document_id: str) -> Document:
                if document_id == "not-found":
                    raise ValueError("Document not found")
                elif document_id == "unauthorized":
                    raise PermissionError("API key invalid")
                elif document_id == "rate-limited":
                    raise RuntimeError("Rate limit exceeded")
                else:
                    return super().get_document(document_id)

        # Arrange: Create error-simulating client
        client = ErrorClient(api_key="test-key")

        # Act & Assert: Various error conditions

        # Document not found
        with pytest.raises(ValueError, match="Document not found"):
            client.get_document("not-found")

        # Unauthorized access
        with pytest.raises(PermissionError, match="API key invalid"):
            client.get_document("unauthorized")

        # Rate limit exceeded
        with pytest.raises(RuntimeError, match="Rate limit exceeded"):
            client.get_document("rate-limited")

        # Success case
        doc = client.get_document("valid-id")
        assert doc.id == "valid-id"
