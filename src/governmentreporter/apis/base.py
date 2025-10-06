"""
Abstract Base Classes for Government API Clients.

This module defines the abstract interfaces and common data structures used by all
government API client implementations. It establishes a consistent contract that
ensures all API clients provide the same core functionality, making them interchangeable
and predictable for consuming code.

Key Components:
    - Document: Standardized data class for representing government documents
    - GovernmentAPIClient: Abstract base class defining the API client interface

Design Patterns:
    - Abstract Base Class (ABC): Enforces implementation of required methods
    - Template Method: Common initialization logic with customization points
    - Data Class: Immutable, type-safe document representation

This module serves as the foundation for:
    - CourtListenerClient (court_listener.py)
    - FederalRegisterClient (federal_register.py)
    - Future API client implementations

Python Learning Notes:
    - ABC (Abstract Base Class): Forces subclasses to implement abstract methods
    - @abstractmethod: Decorator marking methods that must be overridden
    - @dataclass: Automatically generates __init__, __repr__, __eq__ methods
    - Type hints: Improves code clarity and enables static type checking
    - Optional[T]: Indicates a value can be of type T or None
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """
    Base class representing a government document.

    This data class provides a standardized structure for representing any type of
    government document across different APIs. It ensures consistent data handling
    throughout the application, regardless of the original data source format.

    The class uses Python's dataclass decorator to automatically generate common
    methods like __init__, __repr__, and __eq__, reducing boilerplate code while
    maintaining type safety and immutability principles.

    Attributes:
        id (str): Unique identifier for the document within its source system.
                 For SCOTUS opinions, this is the CourtListener opinion ID.
                 For Executive Orders, this is the Federal Register document number.

        title (str): Human-readable title of the document.
                    For SCOTUS: Case name (e.g., "Brown v. Board of Education")
                    For EOs: Order title (e.g., "Promoting Access to Voting")

        date (str): Publication or decision date in YYYY-MM-DD format.
                   Standardized format ensures consistent date handling.

        type (str): Document type identifier for categorization.
                   Examples: "scotus_opinion", "executive_order", "federal_rule"

        source (str): API or data source identifier.
                     Examples: "courtlistener", "federal_register"

        content (Optional[str]): Full text content of the document.
                                Defaults to None if not yet retrieved.
                                May be populated lazily to optimize API usage.

        metadata (Optional[Dict[str, Any]]): Additional structured metadata.
                                            Flexible dictionary for API-specific data.
                                            Examples: docket number, judge names, agency codes.

        url (Optional[str]): Web URL for accessing the document online.
                            Provides direct link to official government source.

    Usage Example:
        document = Document(
            id="123456",
            title="Citizens United v. FEC",
            date="2010-01-21",
            type="scotus_opinion",
            source="courtlistener",
            metadata={"docket_number": "08-205", "vote": "5-4"}
        )

    Integration Notes:
        - Used by all API clients as return type
        - Processed by chunkers and processors
        - Stored in Qdrant with embeddings
        - Provides consistent interface for different document types

    Python Learning Notes:
        - @dataclass: Decorator that auto-generates special methods
        - Type annotations: Specify expected types for each field
        - Optional[T]: Union type meaning T or None
        - Default values: Fields with defaults must come after required fields
        - Dict[str, Any]: Dictionary with string keys and any value type
    """

    id: str
    title: str
    date: str
    type: str
    source: str
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    url: Optional[str] = None


class GovernmentAPIClient(ABC):
    """
    Abstract base class for all government API clients.

    This class defines the standard interface that all government API clients must
    implement. It uses the Abstract Base Class pattern to ensure consistency across
    different API implementations while allowing flexibility for API-specific features.

    The class implements the Template Method pattern in __init__, providing common
    initialization logic while delegating API-specific configuration to subclasses
    through abstract methods.

    Subclasses must implement:
        - _get_base_url(): Return the API's base URL
        - _get_rate_limit_delay(): Return delay between requests
        - search_documents(): Search for documents
        - get_document(): Retrieve a specific document
        - get_document_text(): Get plain text content

    Common functionality provided:
        - API key management
        - Date format validation
        - Rate limiting configuration
        - Standard initialization

    Integration Points:
        - Subclassed by CourtListenerClient and FederalRegisterClient
        - Used by processors to retrieve documents
        - Works with utils.config for credential management

    Python Learning Notes:
        - ABC: Abstract Base Class from abc module
        - Abstract methods: Must be overridden in subclasses
        - Template Method pattern: Common algorithm with customization points
        - Instance attributes: Set in __init__ for each object
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the government API client.

        This initialization method implements the Template Method pattern, providing
        common setup logic while delegating API-specific configuration to subclasses.
        It establishes the core attributes needed by all API clients.

        The method calls abstract methods that must be implemented by subclasses,
        ensuring each API client provides necessary configuration while maintaining
        a consistent initialization interface.

        Args:
            api_key (Optional[str]): API key for authenticated endpoints.
                                   Some APIs require authentication (CourtListener),
                                   while others don't (Federal Register).
                                   Defaults to None for public APIs.

        Attributes Set:
            self.api_key: Stores the API key for use in requests
            self.base_url: Base URL for API endpoints (from _get_base_url())
            self.rate_limit_delay: Delay between requests in seconds (from _get_rate_limit_delay())

        Example:
            # With API key (for CourtListener)
            client = CourtListenerClient(api_key="your-token-here")

            # Without API key (for Federal Register)
            client = FederalRegisterClient()

        Python Learning Notes:
            - self: Reference to the current instance
            - Optional parameters: api_key=None provides default value
            - Abstract method calls: Subclasses must implement these
            - Instance variables: Attributes specific to each object
        """
        self.api_key = api_key
        self.base_url = self._get_base_url()
        self.rate_limit_delay = self._get_rate_limit_delay()

    @abstractmethod
    def _get_base_url(self) -> str:
        """
        Return the base URL for the API.

        This abstract method must be implemented by each API client to provide
        the base URL for that specific government API. The base URL is used as
        the foundation for constructing all API endpoint URLs.

        Returns:
            str: Base URL for the API, including protocol and domain.
                Should not include trailing slash.
                Examples:
                - "https://www.courtlistener.com/api/rest/v4"
                - "https://www.federalregister.gov/api/v1"

        Implementation Requirements:
            - Must return a valid HTTPS URL
            - Should include API version if applicable
            - Should not include authentication parameters
            - Should not include trailing slash

        Python Learning Notes:
            - @abstractmethod: Forces subclasses to implement this method
            - -> str: Return type annotation indicating string return
            - pass: Placeholder for abstract methods (no implementation)
        """
        pass

    @abstractmethod
    def _get_rate_limit_delay(self) -> float:
        """
        Return the rate limit delay in seconds between API requests.

        This abstract method must be implemented by each API client to specify
        the appropriate delay between consecutive API requests. This prevents
        overwhelming government servers and respects API usage policies.

        Returns:
            float: Delay in seconds between requests.
                  Should be based on API documentation or terms of service.
                  Examples:
                  - 0.1 for CourtListener (10 requests per second)
                  - 1.1 for Federal Register (safer than 60/minute limit)

        Implementation Considerations:
            - Check API documentation for rate limits
            - Consider being conservative to avoid blocks
            - May need adjustment based on API response headers
            - Some APIs have different limits for different endpoints

        Python Learning Notes:
            - -> float: Return type annotation for floating-point number
            - Rate limiting: Common practice to prevent API abuse
            - float vs int: Use float for fractional seconds (0.1, 0.5, etc.)
        """
        pass

    @abstractmethod
    def search_documents(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
    ) -> List[Document]:
        """
        Search for documents using the government API.

        This abstract method defines the interface for searching government documents.
        Each API client must implement this to provide search functionality specific
        to their data source, translating the generic search parameters into
        API-specific query formats.

        Args:
            query (str): Search query string for full-text search.
                        May include keywords, case names, or other text.
                        API clients should handle query formatting.

            start_date (Optional[str]): Start date for filtering results.
                                       Format: YYYY-MM-DD (e.g., "2024-01-01").
                                       If None, no start date filter applied.
                                       Inclusive of this date.

            end_date (Optional[str]): End date for filtering results.
                                     Format: YYYY-MM-DD (e.g., "2024-12-31").
                                     If None, no end date filter applied.
                                     Inclusive of this date.

            limit (int): Maximum number of results to return.
                        Default is 10 to prevent overwhelming responses.
                        Implementations should respect this limit.

        Returns:
            List[Document]: List of Document objects matching search criteria.
                          May be empty if no matches found.
                          Ordered by relevance or date (API-specific).

        Implementation Requirements:
            - Validate date formats if provided
            - Handle pagination if needed for limit
            - Convert API responses to Document objects
            - Handle API errors gracefully
            - Apply rate limiting between requests

        Example Implementation:
            def search_documents(self, query, start_date=None, end_date=None, limit=10):
                # Build API-specific query parameters
                params = {"q": query, "limit": limit}
                if start_date:
                    params["date_min"] = start_date
                # Make API request and convert to Documents
                response = self._make_request("/search", params)
                return [self._convert_to_document(item) for item in response["results"]]

        Python Learning Notes:
            - List[Document]: Generic type indicating list of Document objects
            - Optional parameters: Default values make them optional
            - Type annotations: Help IDEs and type checkers
            - Abstract method: No implementation, just interface definition
        """
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Document:
        """
        Retrieve a specific document by its unique identifier.

        This abstract method defines the interface for fetching a single document
        from the government API using its unique identifier. Each API client must
        implement this to handle their specific document retrieval endpoints and
        data formats.

        Args:
            document_id (str): Unique identifier for the document.
                             Format varies by API:
                             - CourtListener: Numeric ID (e.g., "123456")
                             - Federal Register: Document number (e.g., "2024-12345")

        Returns:
            Document: Complete Document object with all available fields populated.
                     Should include full text content if available.
                     Metadata field should contain API-specific additional data.

        Raises:
            Should handle these conditions appropriately:
            - Document not found (404)
            - Authentication required (401)
            - Rate limit exceeded (429)
            - API server errors (500+)

        Implementation Requirements:
            - Fetch complete document data from API
            - Include full text content in Document.content
            - Populate all Document fields appropriately
            - Convert API-specific format to Document class
            - Handle errors with meaningful messages

        Example Usage:
            client = CourtListenerClient()
            opinion = client.get_document("9973155")
            print(f"Case: {opinion.title}")
            print(f"Date: {opinion.date}")
            print(f"Content length: {len(opinion.content)} characters")

        Python Learning Notes:
            - Single return type: Document (not Optional)
            - Implies document must exist or error raised
            - document_id parameter: String for flexibility
            - Abstract method: Interface only, no implementation
        """
        pass

    @abstractmethod
    def get_document_text(self, document_id: str) -> str:
        """
        Retrieve only the plain text content of a document.

        This abstract method provides a lightweight way to fetch just the text
        content of a document without metadata or other fields. Useful when
        only the document text is needed for processing or analysis.

        This method may be more efficient than get_document() as it can:
            - Use text-specific API endpoints if available
            - Skip metadata processing
            - Return cached text if available
            - Apply text cleaning and normalization

        Args:
            document_id (str): Unique identifier for the document.
                             Same format as get_document() method.

        Returns:
            str: Plain text content of the document.
                Should be cleaned and normalized:
                - HTML tags removed
                - Special characters decoded
                - Whitespace normalized
                - Encoding issues resolved

        Implementation Considerations:
            - May call get_document() internally and extract content
            - Could use specialized text-only endpoints if available
            - Should cache results to avoid duplicate API calls
            - Must handle documents without text content

        Example Usage:
            client = FederalRegisterClient()
            text = client.get_document_text("2024-12345")
            word_count = len(text.split())
            print(f"Document contains {word_count} words")

        Python Learning Notes:
            - -> str: Always returns string (not Optional[str])
            - May raise exception if document not found
            - Single responsibility: Just returns text
            - Abstraction: Hides complexity of text extraction
        """
        pass

    def validate_date_format(self, date_str: str) -> None:
        r"""
        Validate that a date string follows the YYYY-MM-DD format and is a valid date.

        This concrete method provides date validation functionality to all API clients.
        It ensures consistent date formatting across different government APIs, which
        may have varying native date formats. The YYYY-MM-DD format (ISO 8601) is
        used as the standard throughout the application.

        This method validates both format and date validity. It raises ValueError
        for invalid formats or impossible dates (e.g., 2024-13-01, 2024-02-30).

        Args:
            date_str (str): Date string to validate.
                          Should be in YYYY-MM-DD format.
                          Examples: "2024-01-01", "2024-12-31"

        Raises:
            ValueError: If the date string doesn't match YYYY-MM-DD format or
                       represents an invalid date.

        Examples:
            >>> client.validate_date_format("2024-01-15")  # Valid, no exception
            >>> client.validate_date_format("01/15/2024")  # Raises ValueError
            >>> client.validate_date_format("2024-1-15")  # Raises ValueError
            >>> client.validate_date_format("2024-13-45")  # Raises ValueError

        Implementation Details:
            - First uses regular expression for pattern matching
            - Then uses datetime.strptime to validate the date is real
            - Pattern breakdown:
                ^ : Start of string
                \d{4} : Exactly 4 digits (year)
                - : Literal hyphen
                \d{2} : Exactly 2 digits (month)
                - : Literal hyphen
                \d{2} : Exactly 2 digits (day)
                $ : End of string

        Python Learning Notes:
            - import inside method: Lazy import, only when needed
            - re.match(): Checks if pattern matches from start of string
            - r"" prefix: Raw string, treats backslashes literally
            - datetime.strptime(): Parses string to datetime, validates date
            - Raises ValueError: Indicates validation failure
            - Regular expressions: Powerful pattern matching tool
            - Concrete method: Has implementation (not abstract)
        """
        import re
        from datetime import datetime

        pattern = r"^\d{4}-\d{2}-\d{2}$"
        if not re.match(pattern, date_str):
            raise ValueError(
                f"Date '{date_str}' does not match required format YYYY-MM-DD"
            )

        # Validate the date is actually valid (not 2024-13-45, etc.)
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"Invalid date '{date_str}': {str(e)}") from e
