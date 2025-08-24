"""
Court Listener API client for fetching US federal court opinions.

This module provides a comprehensive interface to the Court Listener API, which offers
access to millions of US federal court opinions, particularly Supreme Court decisions.
Court Listener is a free, open-access legal research platform maintained by the
Free Law Project (https://www.courtlistener.com).

Key Features:
    - Access to Supreme Court opinions dating back to 1791
    - Bluebook citation formatting
    - Rate-limited API requests to respect service limits
    - Full text retrieval and metadata extraction
    - Pagination support for large result sets
    - Opinion cluster data for case names and citations

API Documentation:
    https://www.courtlistener.com/api/rest-info/

Authentication:
    Requires API token from Court Listener account settings.
    Token should be stored in environment variable COURT_LISTENER_TOKEN.

Rate Limits:
    Court Listener allows generous API usage but recommends reasonable delays
    between requests. This client uses 0.1 second delays by default.

Data Model:
    Court Listener organizes legal opinions in a hierarchical structure:
    - Opinion: Individual judicial opinion (majority, concurring, dissenting)
    - Cluster: Group of related opinions for a single case
    - Docket: Complete case record including filings and metadata

Integration Points:
    - Inherits from GovernmentAPIClient (base.py)
    - Uses citation utilities for Bluebook formatting (utils/citations.py)
    - Utilizes configuration management (utils/config.py)
    - Returns standardized Document objects for processing pipeline

Python Learning Notes:
    - API client pattern: Encapsulates HTTP requests and data transformation
    - Iterator pattern: yield statements create memory-efficient data streaming
    - Error handling: try/except blocks with specific exception types
    - Type hints: Comprehensive annotations for better code documentation
    - Context managers: 'with' statements for resource management (HTTP clients)
    - Rate limiting: time.sleep() for respectful API usage
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ..utils import get_logger
from ..utils.citations import build_bluebook_citation
from ..utils.config import get_court_listener_token
from .base import Document, GovernmentAPIClient


class CourtListenerClient(GovernmentAPIClient):
    """
    Client for interacting with the Court Listener API.

    This class provides a high-level interface to the Court Listener REST API,
    specializing in Supreme Court opinion retrieval and processing. It implements
    the GovernmentAPIClient abstract interface while providing Court Listener-specific
    functionality for legal document access.

    The client handles authentication, rate limiting, pagination, and data transformation
    to provide a clean Python interface to the Court Listener service. It's designed
    to work seamlessly with the broader GovernmentReporter system for legal document
    indexing and retrieval.

    Architecture:
        - Inherits base functionality from GovernmentAPIClient
        - Implements required abstract methods for document operations
        - Adds Court Listener-specific methods for opinion processing
        - Uses httpx for modern async-capable HTTP requests
        - Integrates with citation formatting utilities

    Supported Operations:
        1. Single opinion retrieval by ID
        2. Supreme Court opinion listing with date filtering
        3. Opinion cluster data fetching for case metadata
        4. Full-text content extraction and cleaning
        5. Bluebook citation generation

    Data Flow:
        1. API request → JSON response
        2. Metadata extraction → structured data
        3. Citation formatting → Bluebook format
        4. Document object creation → standardized format
        5. Content population → full text or metadata-only

    Thread Safety:
        This client is not thread-safe. Each thread should use its own instance
        to avoid sharing HTTP clients and rate limiting state.

    Example Usage:
        >>> client = CourtListenerClient(token="your-api-token")
        >>> opinion = client.get_document("123456")
        >>> print(f"Case: {opinion.title}")
        >>> print(f"Citation: {opinion.metadata.get('citation')}")

        >>> # List recent Supreme Court opinions
        >>> for opinion in client.list_scotus_opinions(since_date="2024-01-01", max_results=10):
        ...     print(f"{opinion['id']}: {opinion.get('plain_text', '')[:100]}...")

    Python Learning Notes:
        - Class inheritance: 'class Child(Parent)' extends parent functionality
        - Constructor chaining: super().__init__() calls parent constructor
        - Method overriding: Implementing abstract methods from parent class
        - Instance variables: self.attribute stores per-object data
        - HTTP client patterns: Using context managers for resource cleanup
        - Iterator methods: yield creates generators for memory efficiency
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Court Listener client with authentication and configuration.

        Sets up the client with necessary authentication headers, API configuration,
        and calls the parent class constructor to establish base functionality.
        The client is configured for Court Listener's specific API requirements.

        Authentication Process:
            1. Accept token parameter or fetch from environment
            2. Create authorization header with "Token" prefix
            3. Add user-agent for API identification
            4. Store configuration for all future requests

        Args:
            token (Optional[str]): Court Listener API token for authentication.
                                 If None, attempts to retrieve from environment
                                 variable COURT_LISTENER_TOKEN via get_court_listener_token().
                                 Token format: alphanumeric string from account settings.

        Raises:
            ValueError: If no token provided and none found in environment
            ConfigurationError: If token is invalid or environment misconfigured

        Side Effects:
            - Configures self.headers with authentication and user agent
            - Calls parent __init__ to set up base API client functionality
            - Parent stores token as self.api_key for standardized access

        Example:
            >>> # With explicit token
            >>> client = CourtListenerClient(token="abc123def456")

            >>> # Using environment variable
            >>> import os
            >>> os.environ['COURT_LISTENER_TOKEN'] = 'your-token'
            >>> client = CourtListenerClient()  # Fetches from environment

        Integration Notes:
            - Token retrieved via utils.config.get_court_listener_token()
            - Headers used in all HTTP requests throughout client lifetime
            - Parent constructor sets base_url and rate_limit_delay

        Python Learning Notes:
            - Optional[str]: Parameter can be string or None
            - Logical OR (or): "a or b" returns first truthy value
            - f-strings: f"Token {self.api_key}" for string interpolation
            - Dictionary literals: {"key": "value"} syntax
            - super(): Calls parent class method
            - Constructor chaining: Calling parent __init__ with parameters
        """
        # Get token and pass to parent for centralized storage
        api_key = token or get_court_listener_token()
        super().__init__(api_key=api_key)

        # Set up logging and headers using parent's api_key
        self.logger = get_logger(__name__)
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "User-Agent": "GovernmentReporter/0.1.0",
        }
        self.logger.info("CourtListenerClient initialized successfully")

    def _get_base_url(self) -> str:
        """
        Return the base URL for the Court Listener API.

        This method implements the abstract method from GovernmentAPIClient,
        providing the specific base URL for Court Listener's REST API version 4.
        This URL serves as the foundation for all API endpoint construction.

        URL Structure:
            - Protocol: HTTPS (required for API security)
            - Domain: www.courtlistener.com (official Court Listener domain)
            - Path: /api/rest/v4 (REST API version 4 endpoint)

        Returns:
            str: The base URL "https://www.courtlistener.com/api/rest/v4"
                without trailing slash for consistent endpoint construction.

        Usage in Client:
            This URL is stored in self.base_url during initialization and used
            throughout the client for constructing specific endpoint URLs like:
            - {base_url}/opinions/{id}/
            - {base_url}/clusters/{id}/

        API Version Notes:
            - v4 is the current stable version as of 2024
            - Provides JSON responses with comprehensive metadata
            - Includes pagination, filtering, and search capabilities
            - Backward compatible with v3 for most operations

        Python Learning Notes:
            - Abstract method implementation: Must override parent's abstract method
            - Return type annotation: -> str indicates string return
            - Hardcoded string: Configuration data embedded in code
            - Method naming: Leading underscore indicates "protected" method
        """
        return "https://www.courtlistener.com/api/rest/v4"

    def _get_rate_limit_delay(self) -> float:
        """
        Return the rate limit delay in seconds between Court Listener API requests.

        This method implements the abstract method from GovernmentAPIClient,
        specifying the appropriate delay between consecutive API requests to
        respect Court Listener's service limits and maintain good API citizenship.

        Rate Limit Analysis:
            - Court Listener doesn't publish strict rate limits
            - Service is designed for reasonable research usage
            - 0.1 seconds allows 10 requests per second maximum
            - Conservative approach prevents overwhelming the service
            - Balances speed with respectful usage

        Returns:
            float: 0.1 seconds delay between API requests.
                  This allows up to 600 requests per minute,
                  which is reasonable for batch processing while
                  being respectful to the free service.

        Performance Considerations:
            - 0.1s delay adds minimal overhead for single requests
            - For bulk operations, consider the total time impact
            - May need adjustment based on API response patterns
            - Could be made configurable for different use cases

        Best Practices:
            - Always respect the service provider's resources
            - Monitor for 429 (Too Many Requests) responses
            - Consider exponential backoff for errors
            - Be extra conservative with free APIs

        Python Learning Notes:
            - Return type float: Allows fractional seconds (0.1, 0.5, etc.)
            - Small delays: Common practice in API clients
            - Rate limiting: Essential for production API usage
            - Conservative defaults: Better to be slow than blocked
        """
        return 0.1

    def get_opinion(self, opinion_id: int) -> Dict[str, Any]:
        """
        Fetch a specific Supreme Court opinion by its unique Court Listener ID.

        This method retrieves detailed opinion data from Court Listener's API,
        including metadata, full text content, and relational information to
        other entities like clusters and dockets. It forms the foundation for
        most document retrieval operations in the client.

        API Endpoint:
            GET /api/rest/v4/opinions/{opinion_id}/

        Request Process:
            1. Construct URL with opinion ID
            2. Make authenticated GET request with headers
            3. Parse JSON response
            4. Return structured data dictionary

        Args:
            opinion_id (int): The unique Court Listener opinion identifier.
                            These are numeric IDs assigned by Court Listener,
                            typically 6-8 digit numbers (e.g., 9973155).
                            Can be found in opinion URLs or search results.

        Returns:
            Dict[str, Any]: Complete opinion data from Court Listener API containing:
                - id: Opinion ID (int)
                - plain_text: Full text content of the opinion (str)
                - date_created: Creation timestamp (str)
                - cluster: URL to related cluster data (str)
                - author_id: ID of authoring judge (int, optional)
                - type: Opinion type (majority/concurring/dissenting) (str)
                - page_count: Number of pages (int, optional)
                - download_url: PDF download link (str, optional)
                Plus additional metadata fields from the API

        Raises:
            httpx.HTTPError: For various HTTP-related failures:
                - 404: Opinion not found (invalid ID)
                - 401: Authentication failed (invalid token)
                - 403: Access forbidden (insufficient permissions)
                - 429: Rate limit exceeded (too many requests)
                - 500+: Server errors (Court Listener issues)

            httpx.RequestError: For network-related failures:
                - Connection timeouts
                - DNS resolution failures
                - Network unreachable

        Example Usage:
            >>> client = CourtListenerClient()
            >>> opinion = client.get_opinion(9973155)
            >>> print(f"Author ID: {opinion['author_id']}")
            >>> print(f"Text length: {len(opinion['plain_text'])} characters")
            >>> print(f"Opinion type: {opinion['type']}")

        Integration Notes:
            - Used by get_document() to retrieve full Document objects
            - Used by get_document_text() for text-only retrieval
            - Returns raw API data that needs processing for Document creation
            - Cluster URL in response used for case name and citation data

        Performance Notes:
            - Single API request per opinion
            - May return large text content (hundreds of KB)
            - Consider caching for frequently accessed opinions
            - Subject to rate limiting delays

        Python Learning Notes:
            - httpx.Client(): Modern HTTP client with context manager
            - response.raise_for_status(): Converts HTTP errors to exceptions
            - response.json(): Parses JSON response to Python dict
            - f-string URL construction: Clean string interpolation
            - Exception propagation: Errors bubble up to calling code
        """
        url = f"{self.base_url}/opinions/{opinion_id}/"

        with httpx.Client() as client:
            response = client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    def search_documents(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10,
        full_content: bool = True,
    ) -> List[Document]:
        """
        Search for Supreme Court opinions using Court Listener's API.

        This method implements comprehensive search functionality for Supreme Court
        opinions, combining text search, date filtering, and optional full document retrieval.
        It handles pagination internally and returns Document objects with either full
        content or just metadata, depending on the full_content parameter.

        Search Process:
            1. Build search parameters with filters
            2. Execute paginated API requests
            3. For each opinion result:
               - If full_content=True: fetch full data, cluster info, and text
               - If full_content=False: return summary data only (no extra API calls)
            4. Build Document objects with available data
            5. Return list of Documents up to limit

        Args:
            query (str): Search query string for full-text search.
                        Searches across opinion content and metadata.
                        Can include case names, legal concepts, citations.
                        Pass empty string "" to retrieve all opinions within date range.

            start_date (Optional[str]): Start date filter in YYYY-MM-DD format.
                                       Limits results to opinions after this date.
                                       Defaults to "1900-01-01" if not provided.

            end_date (Optional[str]): End date filter in YYYY-MM-DD format.
                                     Limits results to opinions before this date.
                                     If not provided, includes all opinions up to present.

            limit (int): Maximum number of results to return.
                        Default of 10 prevents overwhelming responses.
                        Set higher for bulk processing operations.

            full_content (bool): Whether to fetch full document content and metadata.
                               If True: Makes additional API calls for full text and cluster data.
                               If False: Returns only summary data from search results (faster, no extra calls).
                               Default is True for backward compatibility.

        Returns:
            List[Document]: List of Document objects with content and metadata.
                           If full_content=True, each Document contains:
                           - Full opinion text
                           - Case name from cluster data
                           - Bluebook citation
                           - Complete metadata
                           If full_content=False, each Document contains:
                           - Empty content field
                           - Basic metadata from search results
                           - ID for later full retrieval
                           Returns empty list if no matches found.

        Raises:
            httpx.HTTPError: For API request failures (auth, rate limit, server errors)
            httpx.RequestError: For network-related failures

        Example Usage:
            >>> client = CourtListenerClient()
            >>>
            >>> # Search for specific topic
            >>> docs = client.search_documents("freedom of speech", limit=5)
            >>> for doc in docs:
            ...     print(f"{doc.title}: {doc.metadata.get('citation')}")
            >>>
            >>> # Get all opinions in date range
            >>> docs = client.search_documents("", start_date="2024-01-01", end_date="2024-12-31")
            >>>
            >>> # Search with all filters
            >>> docs = client.search_documents(
            ...     query="constitutional",
            ...     start_date="2020-01-01",
            ...     limit=20
            ... )

        Performance Notes:
            - Makes multiple API requests (1 per page + 1-2 per opinion)
            - Full text retrieval can be slow for large result sets
            - Consider smaller limits for interactive use
            - Rate limiting applies between requests

        Python Learning Notes:
            - Complex parameter handling with defaults
            - Pagination with while loops
            - List comprehension could optimize but less readable
            - Exception handling for graceful degradation
            - Building objects from multiple API calls
        """
        # Build API parameters
        url = f"{self.base_url}/opinions/"
        params = {
            "cluster__docket__court": "scotus",  # Supreme Court only
            "order_by": "date_created",
        }

        # Add search query if provided
        if query:
            params["search"] = query

        # Add date filters
        if start_date:
            params["date_created__gte"] = start_date
        else:
            params["date_created__gte"] = "1900-01-01"

        if end_date:
            params["date_created__lte"] = end_date

        documents = []

        with httpx.Client(timeout=30.0) as client:
            while url and len(documents) < limit:
                # Rate limiting
                time.sleep(self._get_rate_limit_delay())

                self.logger.debug(f"Fetching: {url}")
                response = client.get(url, headers=self.headers, params=params)
                response.raise_for_status()

                data = response.json()

                # Process each opinion in the current page
                for opinion_summary in data.get("results", []):
                    if len(documents) >= limit:
                        break

                    try:
                        opinion_id = opinion_summary.get("id")
                        if not opinion_id:
                            continue

                        if full_content:
                            # Fetch full opinion data with extra API calls
                            self.logger.debug(
                                f"Fetching full data for opinion {opinion_id}"
                            )
                            # Use get_document to build complete Document object
                            # This handles cluster data, citations, and full text
                            document = self.get_document(str(opinion_id))
                        else:
                            # Create lightweight Document from search results only
                            # No additional API calls - just use the summary data
                            self.logger.debug(
                                f"Creating summary document for opinion {opinion_id}"
                            )
                            
                            # Extract basic metadata from summary
                            date_str = opinion_summary.get("date_created", "")
                            try:
                                date_created = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                                formatted_date = date_created.strftime("%Y-%m-%d")
                            except (ValueError, AttributeError):
                                formatted_date = ""
                            
                            # Create minimal Document object
                            # Content is empty since we're not fetching full text
                            # The ID is preserved so full content can be fetched later
                            document = Document(
                                id=str(opinion_id),
                                title=opinion_summary.get("snippet", "Opinion " + str(opinion_id))[:100],
                                date=formatted_date,
                                type="Supreme Court Opinion",
                                source="CourtListener",
                                content="",  # Empty content for summary mode
                                metadata={
                                    "id": opinion_id,
                                    "resource_uri": opinion_summary.get("resource_uri"),
                                    "summary_mode": True,  # Flag to indicate this is summary data
                                },
                                url=opinion_summary.get("absolute_url"),
                            )
                        
                        documents.append(document)

                    except Exception as e:
                        self.logger.warning(
                            f"Failed to process opinion {opinion_id}: {str(e)}"
                        )
                        continue

                # Get next page URL
                url = data.get("next")
                # Clear params for subsequent requests (they're included in the next URL)
                params = {}

                self.logger.info(
                    f"Search progress: Retrieved {len(documents)} documents"
                )

        return documents

    def get_document(self, document_id: str) -> Document:
        """
        Retrieve a specific Supreme Court opinion by ID with complete metadata and content.

        This method implements the abstract get_document method from GovernmentAPIClient,
        providing complete Document object construction for Court Listener opinions.
        It combines opinion data, cluster information, and citation formatting to
        create a fully populated Document suitable for processing and storage.

        Process Flow:
            1. Fetch opinion data using get_opinion()
            2. Extract basic metadata from opinion
            3. Retrieve cluster data for case name and citations
            4. Generate Bluebook citation format
            5. Construct Document object with all fields populated

        Args:
            document_id (str): Court Listener opinion ID as string.
                              Must be convertible to integer.
                              Examples: "123456", "9973155"
                              Found in Court Listener URLs or API responses.

        Returns:
            Document: Fully populated Document object containing:
                - id: Original document_id string
                - title: Case name from cluster data (e.g., "Brown v. Board")
                - date: Opinion date in YYYY-MM-DD format
                - type: Always "Supreme Court Opinion"
                - source: Always "CourtListener"
                - content: Full plain text of the opinion
                - metadata: Dictionary with opinion and cluster data
                - url: Download URL for PDF version (if available)

        Error Handling:
            - Invalid document_id: Raises ValueError during int() conversion
            - Opinion not found: Propagates HTTPError from get_opinion()
            - Cluster fetch failure: Logs warning, continues with basic data
            - Missing data fields: Uses defaults ("Unknown Case", empty strings)

        Example Usage:
            >>> client = CourtListenerClient()
            >>> doc = client.get_document("9973155")
            >>> print(f"Case: {doc.title}")
            >>> print(f"Decided: {doc.date}")
            >>> print(f"Citation: {doc.metadata.get('citation')}")
            >>> print(f"Content length: {len(doc.content)} characters")

        Metadata Fields:
            The returned Document.metadata includes:
            - All fields from extract_basic_metadata()
            - case_name: Full case name from cluster
            - citation: Bluebook formatted citation
            - Plus any additional cluster metadata

        Performance Notes:
            - Makes 1-2 API requests (opinion + optional cluster)
            - Cluster requests may fail gracefully
            - Full text content included (can be large)
            - Subject to rate limiting delays

        Integration Notes:
            - Returns standardized Document for processing pipeline
            - Compatible with database storage and indexing
            - Metadata suitable for search and filtering
            - Content ready for text analysis and chunking

        Python Learning Notes:
            - String to int conversion: int(document_id)
            - Exception handling: try/except with specific actions
            - Method chaining: Multiple operations on retrieved data
            - Default values: Using "or" operator for fallbacks
            - Object construction: Document() with named parameters
        """
        opinion_data = self.get_opinion(int(document_id))
        metadata = self.extract_basic_metadata(opinion_data)

        # Get cluster data for case name and citation
        cluster_url = opinion_data.get("cluster")
        case_name = "Unknown Case"
        citation = None

        if cluster_url:
            try:
                cluster_data = self.get_opinion_cluster(cluster_url)
                case_name = cluster_data.get("case_name", "Unknown Case")
                citation = build_bluebook_citation(cluster_data)
                # Add cluster metadata to the opinion metadata
                metadata["case_name"] = case_name
                metadata["citation"] = citation
            except Exception as e:
                self.logger.warning(
                    f"Failed to fetch cluster data for opinion {document_id}: {str(e)}"
                )

        return Document(
            id=document_id,
            title=case_name,
            date=metadata["date"] or "",
            type="Supreme Court Opinion",
            source="CourtListener",
            content=metadata["plain_text"],
            metadata=metadata,
            url=metadata.get("download_url"),
        )

    def get_document_text(self, document_id: str) -> str:
        """Retrieve the plain text content of an opinion.

        Args:
            document_id: Opinion ID from CourtListener

        Returns:
            Plain text content of the opinion
        """
        opinion_data = self.get_opinion(int(document_id))
        return opinion_data.get("plain_text", "")

    def extract_basic_metadata(self, opinion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic metadata from opinion data.

        Args:
            opinion_data: Raw opinion data from API

        Returns:
            Dict with extracted metadata
        """
        # Parse the date_created field
        date_str = opinion_data.get("date_created", "")
        try:
            date_created = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            formatted_date = date_created.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            formatted_date = None

        return {
            "id": opinion_data.get("id"),
            "resource_uri": opinion_data.get("resource_uri"),
            "cluster_id": opinion_data.get("cluster_id"),
            "date": formatted_date,
            "plain_text": opinion_data.get("plain_text", ""),
            "author_id": opinion_data.get("author_id"),
            "type": opinion_data.get("type"),
            "page_count": opinion_data.get("page_count"),
            "download_url": opinion_data.get("download_url"),
        }

    def get_opinion_cluster(self, cluster_url: str) -> Dict[str, Any]:
        """
        Fetch opinion cluster data from cluster URL for case names and citations.

        This method retrieves cluster data from Court Listener, which contains
        case-level information that spans multiple related opinions (majority,
        concurring, dissenting). Clusters provide essential metadata like case
        names, citations, and court information that individual opinions reference.

        Cluster vs Opinion Data:
            - Opinion: Individual judicial writing (text, author, type)
            - Cluster: Case-level data (name, citations, date filed, court)
            - Relationship: One cluster contains multiple related opinions

        Data Retrieved:
            Cluster data includes:
            - case_name: Full case name (e.g., "Brown v. Board of Education")
            - citations: List of citation objects with volume, reporter, page
            - date_filed: When the case was decided
            - court: Court identifier and metadata
            - docket: Related docket information
            - judges: Panel of judges for the case

        Args:
            cluster_url (str): Complete URL to the cluster API endpoint.
                              Typically from opinion data's 'cluster' field.
                              Format: "https://www.courtlistener.com/api/rest/v4/clusters/{id}/"
                              Must be a full URL, not just an ID.

        Returns:
            Dict[str, Any]: Complete cluster data from Court Listener API containing:
                - case_name: Case name string (e.g., "Citizens United v. FEC")
                - citations: List of citation dictionaries with volume/reporter/page
                - date_filed: Filing date in YYYY-MM-DD format
                - court: Court information dictionary
                - docket: Associated docket data
                - judges: List of judge information
                Plus additional cluster-specific metadata from the API

        Raises:
            httpx.HTTPError: For various HTTP-related failures:
                - 404: Cluster not found (invalid URL)
                - 401: Authentication failed
                - 403: Access forbidden
                - 429: Rate limit exceeded
                - 500+: Server errors

            httpx.RequestError: For network-related failures

        Example Usage:
            >>> client = CourtListenerClient()
            >>> opinion = client.get_opinion(123456)
            >>> cluster_url = opinion['cluster']
            >>> cluster = client.get_opinion_cluster(cluster_url)
            >>> print(f"Case: {cluster['case_name']}")
            >>> print(f"Filed: {cluster['date_filed']}")
            >>>
            >>> # Extract citation information
            >>> citations = cluster.get('citations', [])
            >>> if citations:
            ...     primary = citations[0]
            ...     print(f"Citation: {primary['volume']} {primary['reporter']} {primary['page']}")

        Integration Notes:
            - Used by get_document() to populate case names and citations
            - Works with build_bluebook_citation() for formatted citations
            - Provides metadata enrichment for Document objects
            - May be called frequently during bulk processing

        Performance Considerations:
            - Additional API request per opinion (if cluster data needed)
            - Cluster data is relatively small (few KB)
            - Results could be cached to avoid repeated requests
            - Subject to same rate limits as other API calls

        Error Handling in Practice:
            This method is often called from get_document() with try/except
            blocks that gracefully handle failures, allowing document processing
            to continue even if cluster data cannot be retrieved.

        Python Learning Notes:
            - URL parameter: Takes full URL, not just ID
            - HTTP timeout: 30.0 seconds for cluster requests
            - Direct URL usage: No URL construction needed
            - Context manager: Automatic HTTP client cleanup
            - JSON parsing: Converts API response to Python dictionary
        """
        with httpx.Client(timeout=30.0) as client:
            response = client.get(cluster_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
