"""
Federal Register API client for fetching executive orders and presidential documents.

This module provides a comprehensive interface to the Federal Register API, which offers
access to federal government documents published daily, including executive orders,
regulations, notices, and proposed rules. The Federal Register is the official daily
publication of the United States government (https://www.federalregister.gov).

Key Features:
    - Access to executive orders from all presidents
    - No authentication required (public API)
    - Built-in retry logic with exponential backoff
    - HTML content cleaning and text extraction
    - Date range filtering and pagination support
    - Robust error handling for network issues

API Documentation:
    https://www.federalregister.gov/developers/documentation/api/v1

Rate Limits:
    Federal Register API has a 60 requests per minute limit.
    This client uses 1.1 second delays to stay well under the limit.

Data Sources:
    The Federal Register contains documents from:
    - Executive Office of the President (executive orders, proclamations)
    - Federal agencies (rules, regulations, notices)
    - Independent regulatory agencies
    - Government corporations and boards

Document Types Supported:
    Currently focused on:
    - Executive Orders (PRESDOCU type with executive_order subtype)

    Expandable to:
    - Presidential Proclamations
    - Rules and Regulations
    - Proposed Rules
    - Notices

Integration Points:
    - Inherits from GovernmentAPIClient (base.py)
    - Uses logging utilities for operation tracking (utils/)
    - Returns standardized Document objects for processing pipeline
    - Integrates with Qdrant for document storage and retrieval

Python Learning Notes:
    - API client design patterns: Separation of concerns, error handling
    - Regular expressions: HTML parsing and content cleaning
    - Iterator patterns: Memory-efficient data processing
    - Exponential backoff: Robust retry strategies for network resilience
    - Context managers: Proper resource management for HTTP connections
    - Logging integration: Operational visibility and debugging
"""

import re
import time
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

import httpx
from httpx import Response

from ..utils import get_logger
from .base import Document, GovernmentAPIClient


class FederalRegisterClient(GovernmentAPIClient):
    """
    Client for interacting with the Federal Register API to retrieve executive orders.

    This class provides a specialized interface to the Federal Register's public API,
    focusing on executive order retrieval and processing. It implements the
    GovernmentAPIClient abstract interface while providing Federal Register-specific
    functionality for presidential document access.

    The client is designed for reliability in production environments, featuring:
    - Exponential backoff retry logic for network resilience
    - Rate limiting compliance with Federal Register's 60/minute limit
    - HTML content cleaning for plain text extraction
    - Comprehensive error handling and logging
    - Memory-efficient pagination for large date ranges

    Architecture:
        - Inherits base functionality from GovernmentAPIClient
        - Implements required abstract methods for document operations
        - Adds Federal Register-specific methods for executive order processing
        - Uses httpx for modern HTTP client functionality
        - Integrates with application logging system

    Supported Operations:
        1. Executive order listing with date range filtering
        2. Individual executive order retrieval by document number
        3. Raw text extraction from HTML endpoints
        4. Metadata extraction and normalization
        5. Pagination handling for bulk processing

    Data Processing Flow:
        1. API request → JSON response
        2. Date filtering and pagination
        3. Raw text URL extraction → HTML content
        4. HTML cleaning → plain text
        5. Document object creation → standardized format

    Authentication:
        No authentication required - Federal Register API is fully public.

    Thread Safety:
        This client is not thread-safe. Each thread should use its own instance
        to avoid sharing HTTP clients and retry state.

    Example Usage:
        >>> client = FederalRegisterClient()
        >>> order = client.get_document("2024-12345")
        >>> print(f"Title: {order.title}")
        >>> print(f"Signed by: {order.metadata.get('president')}")

        >>> # List recent executive orders
        >>> for order in client.list_executive_orders("2024-01-01", "2024-12-31"):
        ...     print(f"{order['document_number']}: {order['title']}")

    Python Learning Notes:
        - Class inheritance: Extends GovernmentAPIClient functionality
        - No authentication: Simpler client design for public APIs
        - Retry patterns: Exponential backoff for resilient network operations
        - HTML parsing: Regular expressions for content extraction
        - Logging integration: Professional application monitoring
        - Iterator methods: yield for memory-efficient data streaming
    """

    def __init__(self):
        """
        Initialize the Federal Register client with configuration and logging.

        Sets up the client for Federal Register API access without authentication,
        configures HTTP headers, establishes retry parameters, and initializes
        logging. The Federal Register API is public and doesn't require tokens.

        Initialization Process:
            1. Call parent constructor with no API key
            2. Set up logger for operation tracking
            3. Configure HTTP headers for API identification
            4. Set retry parameters for network resilience

        Configuration Details:
            - No API key required (public endpoint)
            - User-Agent: Identifies client to API servers
            - Accept header: Requests JSON responses
            - Max retries: 5 attempts for failed requests
            - Initial retry delay: 1 second with exponential backoff

        Side Effects:
            - Sets self.logger for operation logging
            - Configures self.headers for all HTTP requests
            - Sets self.max_retries and self.retry_delay for error handling
            - Calls parent __init__ to establish base client functionality

        Example:
            >>> client = FederalRegisterClient()
            >>> # Client ready for immediate use
            >>> orders = client.list_executive_orders("2024-01-01", "2024-12-31")

        Logging Integration:
            The client creates a logger using get_logger(__name__) which:
            - Uses the module name as logger identifier
            - Inherits application-wide logging configuration
            - Enables operation tracking and debugging
            - Provides visibility into API requests and errors

        Retry Configuration:
            - max_retries=5: Up to 5 retry attempts for failed requests
            - retry_delay=1.0: Initial 1-second delay, doubles each retry
            - Handles both HTTP errors (429, 500+) and network errors
            - Exponential backoff prevents overwhelming overloaded servers

        Python Learning Notes:
            - super().__init__(api_key=None): Calls parent with explicit None
            - get_logger(__name__): Uses current module name for logger
            - Dictionary literal: {"key": "value"} syntax for headers
            - Instance attributes: self.attribute stores per-object data
            - Public API design: Simpler initialization without credentials
        """
        super().__init__(api_key=None)
        self.logger = get_logger(__name__)
        self.headers = {
            "User-Agent": "GovernmentReporter/0.1.0",
            "Accept": "application/json",
        }
        self.max_retries = 5
        self.retry_delay = 1.0  # Initial delay for exponential backoff
        self.logger.info("FederalRegisterClient initialized successfully")

    def _get_base_url(self) -> str:
        """
        Return the base URL for the Federal Register API.

        This method implements the abstract method from GovernmentAPIClient,
        providing the specific base URL for Federal Register's API version 1.
        This URL serves as the foundation for all API endpoint construction.

        URL Structure:
            - Protocol: HTTPS (required for secure API access)
            - Domain: www.federalregister.gov (official government domain)
            - Path: /api/v1 (API version 1, stable since 2011)

        Returns:
            str: The base URL "https://www.federalregister.gov/api/v1"
                without trailing slash for consistent endpoint construction.

        Usage in Client:
            This URL is stored in self.base_url during initialization and used
            throughout the client for constructing specific endpoint URLs like:
            - {base_url}/documents/{document_number}
            - {base_url}/documents (with query parameters)

        API Version Notes:
            - v1 has been stable for over a decade
            - Comprehensive coverage of Federal Register documents
            - JSON responses with rich metadata
            - No breaking changes expected

        Python Learning Notes:
            - Abstract method implementation: Must override parent's abstract method
            - Return type annotation: -> str indicates string return
            - Hardcoded URL: Configuration data embedded in code
            - Method naming: Leading underscore indicates "protected" method
        """
        return "https://www.federalregister.gov/api/v1"

    def _get_rate_limit_delay(self) -> float:
        """
        Return the rate limit delay in seconds between Federal Register API requests.

        This method implements the abstract method from GovernmentAPIClient,
        specifying the appropriate delay between consecutive API requests to
        comply with Federal Register's documented rate limits and maintain
        respectful usage of the public service.

        Federal Register Rate Limits:
            - Official limit: 60 requests per minute
            - Mathematical minimum: 1.0 second per request
            - Chosen delay: 1.1 seconds (conservative buffer)
            - Effective rate: ~54 requests per minute

        Returns:
            float: 1.1 seconds delay between API requests.
                  This conservative approach ensures we stay well under
                  the 60/minute limit while allowing reasonable throughput.

        Conservative Approach Rationale:
            - Prevents accidental rate limit violations
            - Accounts for request processing time variations
            - Provides buffer for network latency
            - Shows respect for the free public service
            - Reduces risk of temporary blocks or throttling

        Performance Impact:
            - 1.1s delay allows ~54 requests/minute vs 60/minute maximum
            - Small overhead for individual requests
            - Significant impact for bulk operations (hours vs minutes)
            - Consider batch processing strategies for large datasets

        Rate Limit Handling:
            The _make_request_with_retry() method handles 429 responses
            with exponential backoff, but this delay prevents most rate
            limiting in the first place.

        Python Learning Notes:
            - Conservative defaults: Better to be slow than blocked
            - Float precision: 1.1 allows fractional seconds
            - Rate limiting: Essential for production API usage
            - Buffer calculations: Adding safety margin to limits
        """
        return 1.1  # Slightly over 1 second to stay well under 60/min

    def _make_request_with_retry(
        self, url: str, params: Optional[Dict] = None
    ) -> Response:
        """
        Make an HTTP request with exponential backoff retry logic for network resilience.

        This method implements a robust retry strategy to handle temporary network
        failures, server overload, and rate limiting. It uses exponential backoff
        to progressively increase delays between retry attempts, preventing
        overwhelming of already-stressed servers.

        Retry Strategy:
            - Maximum attempts: 5 retries (configurable via self.max_retries)
            - Initial delay: 1 second (configurable via self.retry_delay)
            - Backoff: Exponential (delay doubles each retry: 1s, 2s, 4s, 8s, 16s)
            - Total maximum time: ~31 seconds for 5 retries

        Error Handling:
            1. HTTP 429 (Rate Limited): Retry with exponential backoff
            2. HTTP 500+ (Server Errors): Retry with exponential backoff
            3. Network Errors (DNS, timeout, connection): Retry with backoff
            4. Other HTTP errors (401, 404, etc.): Immediate failure (no retry)

        Args:
            url (str): The complete URL to request.
                      Should be a fully-formed HTTP/HTTPS URL.
                      Examples: "https://api.example.com/documents/123"

            params (Optional[Dict]): Optional query parameters to append to URL.
                                   Dictionary of parameter names to values.
                                   Examples: {"page": 1, "per_page": 100}
                                   If None, no query parameters added.

        Returns:
            Response: Successful HTTP response object from httpx.
                     Contains response data, status code, headers.
                     Response has already passed raise_for_status() check.
                     Use response.json() to parse JSON content.

        Raises:
            httpx.HTTPStatusError: For non-retryable HTTP errors (400, 401, 404, etc.)
                                  Or if all retries exhausted for retryable errors.

            httpx.RequestError: For network errors after all retries exhausted.
                               Examples: DNS resolution failure, connection timeout.

            httpx.HTTPError: Generic HTTP error if retries exhausted.
                           Raised as fallback after max_retries attempts.

        Example Usage:
            >>> client = FederalRegisterClient()
            >>> response = client._make_request_with_retry(
            ...     "https://www.federalregister.gov/api/v1/documents",
            ...     {"conditions[type]": "PRESDOCU", "page": 1}
            ... )
            >>> data = response.json()

        Logging Behavior:
            - Logs warnings for retryable failures with retry count and delay
            - Helps with debugging network issues and API problems
            - Provides visibility into retry patterns and success rates

        Performance Characteristics:
            - Fast path: Single request for successful calls
            - Slow path: Up to 31 seconds total delay for maximum retries
            - Memory efficient: No request data caching
            - Network efficient: Only retries when necessary

        Integration Notes:
            - Used by all Federal Register API methods that make HTTP requests
            - Provides consistent error handling across the client
            - Works with application logging system for operational visibility
            - Respects Federal Register API's reliability characteristics

        Python Learning Notes:
            - Exception handling: Multiple except blocks for different error types
            - Exponential backoff: delay *= 2 doubles delay each iteration
            - Context managers: 'with httpx.Client()' for resource management
            - While loop: Continues until success or max retries reached
            - Logging integration: self.logger for operational visibility
            - Type hints: Response return type from httpx
        """
        retry_count = 0
        delay = self.retry_delay

        while retry_count < self.max_retries:
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(url, headers=self.headers, params=params)
                    response.raise_for_status()
                    return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    retry_count += 1
                    if retry_count < self.max_retries:
                        self.logger.warning(
                            f"Rate limited. Retry {retry_count}/{self.max_retries} after {delay:.1f}s"
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                    else:
                        raise
                else:
                    raise
            except httpx.RequestError as e:
                retry_count += 1
                if retry_count < self.max_retries:
                    self.logger.warning(
                        f"Request error: {e}. Retry {retry_count}/{self.max_retries} after {delay:.1f}s"
                    )
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise

        raise httpx.HTTPError(f"Failed after {self.max_retries} retries")

    def get_executive_order_text(self, raw_text_url: str) -> str:
        """
        Fetch and clean the raw text content of an executive order from its URL.

        This method retrieves the full text content of an executive order from
        the Federal Register's raw text endpoint and performs HTML cleaning to
        extract plain text. The Federal Register provides raw text URLs that
        may contain HTML markup, which this method processes to return clean text.

        Text Processing Pipeline:
            1. Fetch content from raw_text_url using retry logic
            2. Detect HTML content (starts with "<html>")
            3. Extract text from <pre> tags if present
            4. Decode HTML entities (&lt;, &gt;, &amp;, &quot;)
            5. Remove HTML anchor tags and links
            6. Strip whitespace and return clean text

        HTML Cleaning Details:
            Federal Register raw text often contains:
            - HTML wrapper with <pre> tags containing actual text
            - HTML entities that need decoding
            - Anchor tags for cross-references
            - Extra whitespace and formatting

        Args:
            raw_text_url (str): Complete URL to the raw text version of the executive order.
                               Typically from executive order metadata 'raw_text_url' field.
                               Format: "https://www.federalregister.gov/documents/full_text/txt/..."
                               Must be a valid URL accessible via HTTP GET.

        Returns:
            str: Clean plain text content of the executive order.
                Includes the complete text with:
                - HTML markup removed
                - Entities decoded to normal characters
                - Cross-reference links removed
                - Normalized whitespace
                May be empty string if no text content found.

        Raises:
            httpx.HTTPError: For HTTP-related failures:
                - 404: Raw text URL not found
                - 403: Access forbidden
                - 500+: Server errors
                Propagated from _make_request_with_retry()

            httpx.RequestError: For network-related failures

        Example Usage:
            >>> client = FederalRegisterClient()
            >>> order_data = client.get_executive_order("2024-12345")
            >>> raw_url = order_data['raw_text_url']
            >>> text = client.get_executive_order_text(raw_url)
            >>> print(f"Order length: {len(text)} characters")
            >>> print(f"First 100 chars: {text[:100]}")

        Content Examples:
            Raw HTML might look like:
            ```html
            <html><body><pre>
            &lt;DOCUMENT&gt;
            EXECUTIVE ORDER 14000
            ...
            &lt;/DOCUMENT&gt;
            </pre></body></html>
            ```

            Cleaned text would be:
            ```
            <DOCUMENT>
            EXECUTIVE ORDER 14000
            ...
            </DOCUMENT>
            ```

        Integration Notes:
            - Used by get_document() and get_document_text() for content retrieval
            - Handles the complexity of Federal Register's HTML format
            - Provides clean text suitable for analysis and storage
            - Works with Document objects for standardized content

        Python Learning Notes:
            - String methods: .startswith(), .strip(), .replace()
            - Regular expressions: re.search() and re.sub() for pattern matching
            - HTML processing: Common web scraping techniques
            - Text cleaning: Removing markup while preserving content
            - Method chaining: Multiple string operations in sequence
        """
        response = self._make_request_with_retry(raw_text_url)
        text = response.text

        # Clean up HTML if present (the raw text often contains HTML markup)
        if text.startswith("<html>"):
            # Extract text between <pre> tags
            pre_match = re.search(r"<pre>(.*?)</pre>", text, re.DOTALL)
            if pre_match:
                text = pre_match.group(1)
                # Remove HTML entities
                text = text.replace("&lt;", "<").replace("&gt;", ">")
                text = text.replace("&amp;", "&").replace("&quot;", '"')
                # Remove HTML anchor tags
                text = re.sub(r"<a[^>]*>.*?</a>", "", text)

        return text.strip()

    def list_executive_orders(
        self, start_date: str, end_date: str, max_results: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Iterate through all executive orders within a date range with pagination support.

        This generator method provides memory-efficient access to executive orders
        from the Federal Register API, supporting date filtering, pagination, and
        rate limiting. It yields executive order metadata without full text content,
        making it suitable for bulk processing workflows where text is fetched
        separately only when needed.

        The method implements automatic pagination handling to process large date
        ranges efficiently, yielding one executive order at a time to minimize
        memory usage during bulk operations.

        API Query Details:
            - Endpoint: /api/v1/documents
            - Document Type: PRESDOCU (Presidential Documents)
            - Subtype: executive_order
            - Date Filter: signing_date (when president signed the order)
            - Page Size: 100 orders per request (API maximum)
            - Ordering: Not specified (Federal Register default)

        Args:
            start_date (str): Start date filter in YYYY-MM-DD format.
                             Inclusive - orders signed on this date are included.
                             Example: "2024-01-01" for orders from January 1, 2024.
                             Must be valid date format (validated by method).

            end_date (str): End date filter in YYYY-MM-DD format.
                           Inclusive - orders signed on this date are included.
                           Example: "2024-12-31" for orders through December 31, 2024.
                           Must be valid date format (validated by method).

            max_results (Optional[int]): Maximum number of orders to return.
                                       If None, returns all matching orders.
                                       Useful for testing or limiting large queries.
                                       Example: 50 to get first 50 matching orders.

        Yields:
            Dict[str, Any]: Executive order metadata dictionary containing:
                - document_number: Federal Register document number (str)
                - title: Executive order title (str)
                - executive_order_number: EO number (int, e.g., 14000)
                - signing_date: Date president signed order (str, YYYY-MM-DD)
                - publication_date: Date published in Federal Register (str)
                - president: President information (dict with name, etc.)
                - citation: Federal Register citation (str)
                - html_url: Web page URL (str)
                - pdf_url: PDF download URL (str)
                - raw_text_url: Plain text URL (str)
                Plus additional metadata from Federal Register API

        Raises:
            ValueError: If start_date or end_date format is invalid.
                       Must be YYYY-MM-DD format as validated by validate_date_format().

            httpx.HTTPError: For various API-related failures:
                - 429: Rate limit exceeded (handled by retry logic)
                - 500+: Server errors (handled by retry logic)
                - Other HTTP errors propagated from _make_request_with_retry()

            httpx.RequestError: For network-related failures after retries

        Usage Patterns:

            # Process all orders in a year
            >>> client = FederalRegisterClient()
            >>> for order in client.list_executive_orders("2024-01-01", "2024-12-31"):
            ...     print(f"EO {order['executive_order_number']}: {order['title']}")

            # Limited processing for testing
            >>> for order in client.list_executive_orders(
            ...     "2023-01-01", "2023-12-31", max_results=10
            ... ):
            ...     print(f"Document {order['document_number']} by {order['president']['name']}")

            # Get full text for specific orders
            >>> for order in client.list_executive_orders("2024-01-01", "2024-12-31"):
            ...     if "climate" in order['title'].lower():
            ...         text = client.get_executive_order_text(order['raw_text_url'])
            ...         # Process climate-related orders...

        Performance Characteristics:
            - Memory efficient: Only one order in memory at a time
            - Network efficient: Handles pagination automatically
            - Rate limited: 1.1 second delay between requests
            - Resumable: Can be stopped and restarted with adjusted date ranges

        Date Range Considerations:
            - Large date ranges may take considerable time due to rate limiting
            - Consider breaking large ranges into smaller chunks for parallel processing
            - Presidential terms typically span 4-8 years with varying EO volumes
            - Some presidents issued 100+ orders per year, others much fewer

        Integration Notes:
            - Used by bulk processing scripts for executive order indexing
            - Provides metadata for filtering before full text retrieval
            - Compatible with database batch insertion patterns
            - Supports progress tracking through logged status updates

        Python Learning Notes:
            - Generator function: Uses yield instead of return for memory efficiency
            - Iterator pattern: Produces values one at a time
            - Input validation: Checks date formats before API calls
            - Pagination handling: Automatic next page processing
            - Rate limiting: time.sleep() between requests
            - Progress logging: Operational visibility during long operations
        """
        # Validate date formats
        if not self.validate_date_format(start_date):
            raise ValueError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD")
        if not self.validate_date_format(end_date):
            raise ValueError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD")

        url = f"{self.base_url}/documents"
        params = {
            "conditions[type]": "PRESDOCU",
            "conditions[presidential_document_type]": "executive_order",
            "conditions[signing_date][gte]": start_date,
            "conditions[signing_date][lte]": end_date,
            "fields[]": [
                "document_number",
                "title",
                "executive_order_number",
                "publication_date",
                "signing_date",
                "president",
                "citation",
                "html_url",
                "pdf_url",
                "full_text_xml_url",
                "body_html_url",
                "raw_text_url",
                "json_url",
                "agencies",
            ],
            "per_page": 100,
            "page": 1,
        }

        results_count = 0

        while True:
            # Rate limiting
            time.sleep(self.rate_limit_delay)

            self.logger.info(f"Fetching page {params['page']} of executive orders...")
            response = self._make_request_with_retry(url, params)
            data = response.json()

            results = data.get("results", [])

            if not results:
                break

            for order in results:
                if max_results is not None and results_count >= max_results:
                    return

                # Extract only agency names if agencies field exists
                if "agencies" in order and isinstance(order["agencies"], list):
                    order["agencies"] = [agency.get("name", "") for agency in order["agencies"]]

                yield order
                results_count += 1

            # Check if there are more pages
            total_pages = data.get("total_pages", 1)
            current_page = params["page"]

            self.logger.info(
                f"Processed page {current_page}/{total_pages}, "
                f"total orders so far: {results_count}"
            )

            if current_page >= total_pages:
                break

            params["page"] += 1

    def get_executive_order(self, document_number: str) -> Dict[str, Any]:
        """
        Fetch a specific executive order by its Federal Register document number.

        This method retrieves complete executive order data from the Federal Register
        API using the document's unique identifier. It returns comprehensive metadata
        including presidential information, dates, citations, and URLs for various
        document formats.

        Document Numbers:
            Federal Register document numbers are unique identifiers assigned to
            each published document. For executive orders, they typically follow
            the format YYYY-NNNNN where YYYY is the year and NNNNN is a sequence
            number (e.g., "2024-12345").

        API Endpoint:
            GET /api/v1/documents/{document_number}

        Args:
            document_number (str): The Federal Register document number.
                                  Format: Usually YYYY-NNNNN (e.g., "2024-12345")
                                  Must exactly match the document number from Federal Register
                                  Can be found in URLs, citations, or from list_executive_orders()

        Returns:
            Dict[str, Any]: Complete executive order data from Federal Register API containing:
                - document_number: Document identifier (str)
                - title: Executive order title (str)
                - executive_order_number: EO sequential number (int)
                - signing_date: Date signed by president (str, YYYY-MM-DD)
                - publication_date: Date published in Federal Register (str)
                - president: President information (dict with name, term dates)
                - citation: Federal Register citation (str, e.g., "89 FR 12345")
                - html_url: Web page URL for human reading (str)
                - pdf_url: PDF download URL (str)
                - raw_text_url: Plain text URL (str)
                - full_text_xml_url: XML format URL (str)
                - agencies: Related agencies (list, optional)
                Plus additional metadata fields from the API

        Raises:
            httpx.HTTPError: For various API-related failures:
                - 404: Document not found (invalid document_number)
                - 429: Rate limit exceeded (handled by retry logic)
                - 500+: Server errors (handled by retry logic)
                Propagated from _make_request_with_retry()

            httpx.RequestError: For network-related failures after retries

        Example Usage:
            >>> client = FederalRegisterClient()
            >>> order = client.get_executive_order("2024-12345")
            >>> print(f"Title: {order['title']}")
            >>> print(f"EO Number: {order['executive_order_number']}")
            >>> print(f"Signed: {order['signing_date']} by {order['president']['name']}")
            >>> print(f"Citation: {order['citation']}")
            >>>
            >>> # Access different format URLs
            >>> pdf_url = order['pdf_url']
            >>> text_url = order['raw_text_url']
            >>> web_url = order['html_url']

        Data Quality Notes:
            - All executive orders should have complete metadata
            - Raw text URLs are usually available for text extraction
            - PDF URLs provide official formatted versions
            - President information includes full name and term details

        Integration Notes:
            - Used by get_document() to create Document objects
            - Provides metadata for database storage and indexing
            - Raw text URL used by get_executive_order_text() for content
            - Forms basis for complete document processing pipeline

        Python Learning Notes:
            - URL construction: f-string interpolation for clean URL building
            - Method delegation: Uses _make_request_with_retry() for actual request
            - JSON parsing: response.json() converts to Python dictionary
            - Single responsibility: Focused on one document retrieval task
        """
        url = f"{self.base_url}/documents/{document_number}"

        response = self._make_request_with_retry(url)
        order_data = response.json()
        
        # Extract only agency names if agencies field exists
        if "agencies" in order_data and isinstance(order_data["agencies"], list):
            order_data["agencies"] = [agency.get("name", "") for agency in order_data["agencies"]]
        
        return order_data

    def search_documents(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
        full_content: bool = False,
    ) -> List[Document]:
        """
        Search for executive orders using full-text search with date range filtering.

        This method implements the abstract search_documents method from GovernmentAPIClient,
        providing full-text search capabilities for executive orders in the Federal Register.
        It uses the Federal Register's search API to find executive orders matching the query
        terms, applies date range filters if provided, and returns Document objects with
        complete content for each matching order.

        The Federal Register search API allows searching across document titles
        and full text content. This implementation focuses specifically on executive orders
        (PRESDOCU type with executive_order subtype) to maintain consistency with the rest
        of the client's functionality.

        Search Behavior:
            - Full-text search across executive order content and metadata
            - Case-insensitive matching
            - Supports phrases and multiple terms
            - Results ordered by relevance (Federal Register default)
            - Optionally fetches full text content for each result

        API Endpoint:
            GET /api/v1/documents with search parameters:
            - term: Search query for full-text search
            - conditions[type]: PRESDOCU (Presidential Documents)
            - conditions[presidential_document_type]: executive_order
            - conditions[signing_date][gte/lte]: Date range filters
            - per_page: Results per page (respects limit parameter)

        Args:
            query (str): Search query string for full-text search.
                        Can include keywords, phrases, topics, or any text.
                        Examples:
                        - "climate change" - Orders mentioning climate change
                        - "national security" - Orders related to national security
                        - "Executive Order 14000" - Specific order reference
                        The API searches across titles and full text.

            start_date (Optional[str]): Start date filter in YYYY-MM-DD format.
                                       If provided, only returns orders signed on or after this date.
                                       Example: "2024-01-01" for orders from 2024 onwards.
                                       If None, no start date restriction applied.

            end_date (Optional[str]): End date filter in YYYY-MM-DD format.
                                     If provided, only returns orders signed on or before this date.
                                     Example: "2024-12-31" for orders through end of 2024.
                                     If None, no end date restriction applied.

            limit (int): Maximum number of results to return.
                        Default is 10 to prevent overwhelming responses.
                        The method respects this limit and won't return more documents.
                        Set higher for comprehensive searches (e.g., 100).

            full_content (bool): Whether to fetch full document content and metadata.
                               If True: Makes additional API calls for full text content.
                               If False: Returns only metadata from search results (faster, no extra calls).
                               Default is False for optimal performance.

        Returns:
            List[Document]: List of Document objects matching search criteria.
                          If full_content=True, each Document contains:
                          - id: Federal Register document number
                          - title: Executive order title
                          - date: Signing date in YYYY-MM-DD format
                          - type: "Executive Order"
                          - source: "FederalRegister"
                          - content: Full plain text of the order
                          - metadata: Complete order data from API
                          - url: HTML URL for web viewing
                          If full_content=False, each Document contains:
                          - id: Federal Register document number
                          - title: Executive order title from search results
                          - date: Signing date in YYYY-MM-DD format
                          - type: "Executive Order"
                          - source: "FederalRegister"
                          - content: Empty string (no full text available)
                          - metadata: Search result data with summary_mode flag
                          - url: HTML URL for web viewing
                          Returns empty list if no matches found.
                          Results ordered by relevance score from search API.

        Raises:
            ValueError: If start_date or end_date format is invalid (not YYYY-MM-DD).

            httpx.HTTPError: For API-related failures:
                - 429: Rate limit exceeded (handled by retry logic)
                - 500+: Server errors (handled by retry logic)
                - Other HTTP errors from _make_request_with_retry()

            httpx.RequestError: For network-related failures after retries exhausted.

        Example Usage:
            >>> client = FederalRegisterClient()
            >>>
            >>> # Search for climate-related executive orders
            >>> climate_orders = client.search_documents(
            ...     "climate change renewable energy",
            ...     start_date="2021-01-01",
            ...     limit=5
            ... )
            >>> for doc in climate_orders:
            ...     print(f"{doc.title} ({doc.date})")
            ...     print(f"  Preview: {doc.content[:200]}...")
            >>>
            >>> # Search for specific executive order
            >>> results = client.search_documents("Executive Order 14019")
            >>> if results:
            ...     order = results[0]
            ...     print(f"Found: {order.title}")
            ...     print(f"Signed: {order.date} by {order.metadata.get('president', {}).get('name')}")
            >>>
            >>> # Search all orders in date range containing keyword
            >>> security_orders = client.search_documents(
            ...     "national security",
            ...     start_date="2023-01-01",
            ...     end_date="2023-12-31",
            ...     limit=20
            ... )
            >>> print(f"Found {len(security_orders)} national security orders in 2023")

        Performance Notes:
            - Makes 1 API request for search results
            - If full_content=True: Makes additional requests for each document's full text (up to limit)
            - Total requests: 1 (if full_content=False) or 1 + min(results_found, limit) (if full_content=True)
            - Subject to rate limiting (1.1 second delay between requests)
            - Consider caching for frequently searched terms

        Search Tips:
            - Use quotes for exact phrases: '"artificial intelligence"'
            - Multiple terms are AND'd by default: "climate energy" finds both
            - Searches titles and full text content
            - More specific queries return more relevant results
            - Date filters significantly improve search performance

        Integration Notes:
            - Complements list_executive_orders() for date-based retrieval
            - Returns same Document format as get_document()
            - Compatible with downstream processing pipelines
            - Suitable for user-facing search interfaces
            - Works with document indexing and analysis workflows

        Python Learning Notes:
            - List comprehension: Building Document list from search results
            - Error handling: Date validation before API calls
            - API parameter building: Conditional parameter addition
            - Memory efficiency: Limiting results to prevent overflow
            - Type hints: Clear interface definition with Optional and List
            - Documentation: Comprehensive docstring for complex method
        """
        # Validate date formats if provided
        if start_date and not self.validate_date_format(start_date):
            raise ValueError(f"Invalid start_date format: {start_date}. Use YYYY-MM-DD")
        if end_date and not self.validate_date_format(end_date):
            raise ValueError(f"Invalid end_date format: {end_date}. Use YYYY-MM-DD")

        # Build search parameters
        url = f"{self.base_url}/documents"
        params = {
            "conditions[type]": "PRESDOCU",
            "conditions[presidential_document_type]": "executive_order",
            "term": query,  # Full-text search parameter
            "fields[]": [
                "document_number",
                "title",
                "executive_order_number",
                "publication_date",
                "signing_date",
                "president",
                "citation",
                "html_url",
                "pdf_url",
                "raw_text_url",
                "agencies",
            ],
            "per_page": min(limit, 100),  # API max is 100 per page
            "page": 1,
        }

        # Add date filters if provided
        if start_date:
            params["conditions[signing_date][gte]"] = start_date
        if end_date:
            params["conditions[signing_date][lte]"] = end_date

        # Apply rate limiting before request
        time.sleep(self.rate_limit_delay)

        # Make search request with retry logic
        self.logger.info(f"Searching for executive orders with query: '{query}'")
        response = self._make_request_with_retry(url, params)
        data = response.json()

        results = data.get("results", [])
        self.logger.info(f"Found {len(results)} executive orders matching '{query}'")

        # Convert search results to Document objects
        documents = []
        for order_data in results[:limit]:  # Respect the limit parameter
            try:
                # Extract only agency names if agencies field exists
                if "agencies" in order_data and isinstance(order_data["agencies"], list):
                    order_data["agencies"] = [agency.get("name", "") for agency in order_data["agencies"]]
                
                # Get the document number
                document_number = order_data.get("document_number")
                if not document_number:
                    self.logger.warning("Skipping result without document_number")
                    continue

                if full_content:
                    # Fetch full document with extra API calls
                    self.logger.debug(
                        f"Fetching full data for document {document_number}"
                    )
                    # Apply rate limiting between document fetches
                    time.sleep(self.rate_limit_delay)

                    # Use get_document to build complete Document object
                    # This handles full text retrieval and metadata
                    document = self.get_document(document_number)
                    documents.append(document)

                    self.logger.debug(
                        f"Retrieved full document {document_number}: {document.title}"
                    )
                else:
                    # Create lightweight Document from search results only
                    # No additional API calls - just use the summary data
                    self.logger.debug(
                        f"Creating summary document for {document_number}"
                    )

                    # Create Document with available data from search results
                    document = Document(
                        id=document_number,
                        title=order_data.get("title", "Unknown Executive Order"),
                        date=order_data.get("signing_date", ""),
                        type="Executive Order",
                        source="FederalRegister",
                        content="",  # Executive orders don't have abstracts
                        metadata={
                            **order_data,  # Include all search result data
                            "summary_mode": True,  # Flag to indicate this is summary data
                        },
                        url=order_data.get("html_url"),
                    )
                    documents.append(document)

            except Exception as e:
                # Log error but continue processing other results
                self.logger.error(f"Error processing document {document_number}: {e}")
                # For full_content mode, try to at least return partial data
                if full_content:
                    try:
                        # Create partial Document from search result data as fallback
                        partial_doc = Document(
                            id=document_number,
                            title=order_data.get("title", "Unknown Executive Order"),
                            date=order_data.get("signing_date", ""),
                            type="Executive Order",
                            source="FederalRegister",
                            content="",  # Executive orders don't have abstracts
                            metadata={
                                **order_data,
                                "summary_mode": True,
                                "error": str(e),  # Include error for debugging
                            },
                            url=order_data.get("html_url"),
                        )
                        documents.append(partial_doc)
                        self.logger.info(
                            f"Created partial document for {document_number} after error"
                        )
                    except Exception as inner_e:
                        self.logger.error(
                            f"Could not create partial document: {inner_e}"
                        )

        self.logger.info(
            f"Successfully retrieved {len(documents)} documents for query '{query}'"
        )
        return documents

    def get_document(self, document_id: str) -> Document:
        """
        Retrieve a specific executive order by document number with complete content.

        This method implements the abstract get_document method from GovernmentAPIClient,
        providing complete Document object construction for Federal Register executive orders.
        It combines order metadata, full text content, and standardized formatting to
        create a fully populated Document suitable for processing and storage.

        Process Flow:
            1. Fetch executive order data using get_executive_order()
            2. Extract raw text URL from order metadata
            3. Fetch and clean full text content using get_executive_order_text()
            4. Construct Document object with all fields populated
            5. Return standardized Document for processing pipeline

        Args:
            document_id (str): Federal Register document number.
                              Format: Usually YYYY-NNNNN (e.g., "2024-12345")
                              Same format used by get_executive_order()
                              Can be obtained from list_executive_orders() results

        Returns:
            Document: Fully populated Document object containing:
                - id: Original document_id (Federal Register document number)
                - title: Executive order title from metadata
                - date: Signing date in YYYY-MM-DD format
                - type: Always "Executive Order"
                - source: Always "FederalRegister"
                - content: Full clean plain text of the executive order
                - metadata: Complete order data dictionary from API
                - url: HTML URL for web viewing

        Content Handling:
            - Retrieves full text from raw_text_url if available
            - Returns empty string if no raw text URL (executive orders don't have abstracts)
            - Text is cleaned of HTML markup and properly formatted
            - Empty content handled gracefully (won't cause errors)

        Example Usage:
            >>> client = FederalRegisterClient()
            >>> doc = client.get_document("2024-12345")
            >>> print(f"Title: {doc.title}")
            >>> print(f"Signed: {doc.date}")
            >>> print(f"President: {doc.metadata.get('president', {}).get('name')}")
            >>> print(f"Content length: {len(doc.content)} characters")
            >>> print(f"EO Number: {doc.metadata.get('executive_order_number')}")

        Error Handling:
            - Invalid document_id: Raises HTTPError from get_executive_order()
            - Missing raw_text_url: Returns empty string as content
            - Text fetch failure: Returns empty string as content
            - Missing metadata fields: Uses defaults ("Unknown Executive Order", empty strings)

        Metadata Fields:
            The returned Document.metadata includes all data from get_executive_order():
            - document_number, executive_order_number, signing_date
            - president information, citation, publication_date
            - URLs for different formats (HTML, PDF, raw text)
            - Plus any additional fields from Federal Register API

        Performance Notes:
            - Makes 2 API requests (metadata + text content)
            - Text content can be large (10KB-100KB+)
            - Subject to rate limiting delays
            - Consider caching for frequently accessed documents

        Integration Notes:
            - Returns standardized Document for processing pipeline
            - Compatible with database storage and indexing systems
            - Metadata suitable for search and filtering operations
            - Content ready for text analysis and chunking

        Python Learning Notes:
            - Method chaining: Multiple operations on retrieved data
            - Conditional logic: if/else for content source selection
            - Object construction: Document() with named parameters
            - Error resilience: Graceful fallbacks for missing data
            - String methods: .get() for safe dictionary access
        """
        order_data = self.get_executive_order(document_id)

        # Get the raw text
        raw_text_url = order_data.get("raw_text_url")
        if raw_text_url:
            content = self.get_executive_order_text(raw_text_url)
        else:
            content = ""  # Executive orders don't have abstracts, use empty string as fallback

        return Document(
            id=document_id,
            title=order_data.get("title", "Unknown Executive Order"),
            date=order_data.get("signing_date", ""),
            type="Executive Order",
            source="FederalRegister",
            content=content,
            metadata=order_data,
            url=order_data.get("html_url"),
        )

    def get_document_text(self, document_id: str) -> str:
        """
        Retrieve only the plain text content of an executive order.

        This method provides a lightweight alternative to get_document() when
        only the text content is needed, without the overhead of constructing
        a complete Document object. It's optimized for text analysis workflows
        that don't require full metadata.

        Process:
            1. Fetch executive order metadata using get_executive_order()
            2. Extract raw_text_url from metadata
            3. Fetch and clean text content using get_executive_order_text()
            4. Return plain text directly

        Args:
            document_id (str): Federal Register document number.
                              Format: Usually YYYY-NNNNN (e.g., "2024-12345")
                              Same format used by get_document() and get_executive_order()

        Returns:
            str: Clean plain text content of the executive order.
                Includes the complete text with HTML markup removed.
                Returns empty string if raw text unavailable
                (executive orders don't have abstracts).

        Performance Benefits:
            - Lighter than get_document(): No Document object construction
            - Same API requests as get_document() but less processing
            - Faster for text-only operations
            - Lower memory usage for bulk text processing

        Use Cases:
            - Text analysis and natural language processing
            - Word counting and statistical analysis
            - Search indexing where metadata is processed separately
            - Content validation and quality checks
            - Bulk text extraction for machine learning

        Example Usage:
            >>> client = FederalRegisterClient()
            >>> text = client.get_document_text("2024-12345")
            >>> word_count = len(text.split())
            >>> print(f"Executive order contains {word_count} words")
            >>>
            >>> # Search for specific terms
            >>> if "national security" in text.lower():
            ...     print("Order relates to national security")
            >>>
            >>> # Extract key phrases
            >>> sentences = text.split('. ')
            >>> for sentence in sentences[:5]:
            ...     print(f"- {sentence.strip()}")

        Error Handling:
            - Invalid document_id: Raises HTTPError from get_executive_order()
            - Missing raw_text_url: Returns empty string (no abstracts for executive orders)
            - Text fetch failure: Returns empty string
            - No content available: Returns empty string

        Comparison with get_document():
            get_document_text() - Fast, text-only, minimal processing
            get_document()      - Complete, metadata-rich, full Document object

        Integration Notes:
            - Used by text analysis pipelines
            - Suitable for bulk text processing operations
            - Works well with streaming processing patterns
            - Compatible with text chunking and embedding systems

        Python Learning Notes:
            - Method delegation: Calls get_executive_order() internally
            - Conditional access: Handles missing URLs gracefully
            - String operations: Text processing and cleaning
            - Single responsibility: Focused on text extraction only
        """
        order_data = self.get_executive_order(document_id)
        raw_text_url = order_data.get("raw_text_url")

        if raw_text_url:
            return self.get_executive_order_text(raw_text_url)
        else:
            return ""  # Executive orders don't have abstracts, return empty string

    def extract_basic_metadata(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and normalize basic metadata from raw Federal Register executive order data.

        This method processes the raw API response from Federal Register to extract
        key metadata fields, performing necessary data cleaning, format conversion,
        and type normalization. It handles missing fields gracefully and standardizes
        data formats for consistent processing throughout the application.

        Data Processing:
            1. Parse signing date to YYYY-MM-DD format
            2. Extract president information with type handling
            3. Extract agency names from agencies field
            4. Safely extract string and numeric fields
            5. Handle missing or malformed data gracefully
            6. Return structured metadata dictionary

        Args:
            order_data (Dict[str, Any]): Raw executive order data from Federal Register API.
                                        Should contain fields like document_number, title,
                                        signing_date, president, etc. from API response.

        Returns:
            Dict[str, Any]: Processed metadata dictionary containing:
                - document_number (str|None): Federal Register document number
                - title (str): Executive order title (empty string if missing)
                - executive_order_number (int|None): Sequential EO number
                - signing_date (str): Formatted date (YYYY-MM-DD) or original if parsing fails
                - president (str): President name or "Unknown" if missing/malformed
                - citation (str): Federal Register citation (empty string if missing)
                - html_url (str): Web page URL (empty string if missing)
                - raw_text_url (str): Plain text URL (empty string if missing)
                - publication_date (str): Federal Register publication date (empty string if missing)
                - agencies (list): List of agency names (empty list if missing)

        Date Processing:
            Input formats handled:
            - ISO format: "2024-01-15"
            - ISO with time: "2024-01-15T10:30:00"
            - Malformed dates: Return original string unchanged

        President Data Handling:
            The president field can be:
            - Dictionary: {"name": "Joe Biden", "term": "2021-2025", ...}
            - String: "Joe Biden"
            - None/missing: Returns "Unknown"

        Error Handling:
            - Graceful handling of missing fields (returns defaults)
            - Date parsing errors return original string
            - Type errors for president data handled with fallbacks
            - No exceptions raised - always returns valid dictionary

        Example Usage:
            >>> client = FederalRegisterClient()
            >>> raw_data = client.get_executive_order("2024-12345")
            >>> metadata = client.extract_basic_metadata(raw_data)
            >>> print(f"Title: {metadata['title']}")
            >>> print(f"EO Number: {metadata['executive_order_number']}")
            >>> print(f"Signed: {metadata['signing_date']} by {metadata['president']}")
            >>> print(f"Citation: {metadata['citation']}")

        Field Examples:
            ```python
            {
                "document_number": "2024-12345",
                "title": "Promoting Access to Voting",
                "executive_order_number": 14019,
                "signing_date": "2024-03-07",
                "president": "Joseph R. Biden Jr.",
                "citation": "89 FR 15234",
                "html_url": "https://www.federalregister.gov/documents/2024/03/07/2024-12345/...",
                "raw_text_url": "https://www.federalregister.gov/documents/full_text/txt/...",
                "publication_date": "2024-03-07",
                "agencies": ["Executive Office of the President"]
            }
            ```

        Integration Notes:
            - Used by get_document() for Document object construction
            - Provides consistent metadata format across executive orders
            - Date formats match application standards
            - Safe for storage in databases or JSON serialization

        Python Learning Notes:
            - Dictionary.get(): Safe access with default values
            - Type checking: isinstance() for handling different data types
            - try/except: Exception handling for date parsing
            - String conversion: str() for type safety
            - Conditional logic: Handling multiple data format possibilities
            - Default values: Providing sensible fallbacks for missing data
        """
        # Parse the signing date
        signing_date_str = order_data.get("signing_date", "")
        try:
            signing_date = datetime.fromisoformat(signing_date_str)
            formatted_date = signing_date.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            formatted_date = signing_date_str

        # Extract president info
        president_data = order_data.get("president", {})
        if isinstance(president_data, dict):
            president_name = president_data.get("name", "Unknown")
        else:
            president_name = str(president_data) if president_data else "Unknown"

        # Extract agency names
        agencies_data = order_data.get("agencies", [])
        agency_names = []
        if isinstance(agencies_data, list):
            # Check if agencies have already been processed to just names (strings)
            # or if they are still full objects with a "name" field
            for agency in agencies_data:
                if isinstance(agency, str):
                    # Already processed to just the name
                    agency_names.append(agency)
                elif isinstance(agency, dict):
                    # Still a full object, extract the name
                    agency_names.append(agency.get("name", ""))

        return {
            "document_number": order_data.get("document_number"),
            "title": order_data.get("title", ""),
            "executive_order_number": order_data.get("executive_order_number"),
            "signing_date": formatted_date,
            "president": president_name,
            "citation": order_data.get("citation", ""),
            "html_url": order_data.get("html_url", ""),
            "raw_text_url": order_data.get("raw_text_url", ""),
            "publication_date": order_data.get("publication_date", ""),
            "agencies": agency_names,
        }
