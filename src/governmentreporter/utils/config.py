"""Configuration management for GovernmentReporter.

This module provides secure access to API credentials and configuration values
through environment variables. It acts as the central configuration hub for
all external service integrations in the GovernmentReporter system.

The module follows security best practices by:
- Never hardcoding sensitive credentials in source code
- Reading credentials from environment variables at runtime
- Providing clear error messages when required credentials are missing
- Supporting both required and optional API credentials

Integration with GovernmentReporter:
    This module is imported by all components that need external API access:
    - APIs module: Uses tokens to authenticate with government data sources
    - Metadata module: Uses Google Gemini API key for AI-powered metadata generation
    - Database module: May use credentials for cloud database connections
    - MCP server: Validates all required credentials at startup

Environment Variable Setup:
    Create a .env file in the project root with these variables:
    ```
    COURT_LISTENER_API_TOKEN=your_court_listener_token_here
    GOOGLE_GEMINI_API_KEY=your_google_api_key_here
    FEDERAL_REGISTER_API_TOKEN=optional_future_use
    CONGRESS_GOV_API_TOKEN=optional_future_use
    ```

Python Learning Notes:
    - os.getenv() safely reads environment variables without raising errors
    - The module uses type hints to indicate which functions return Optional values
    - ValueError is raised for missing required credentials to fail fast
    - The pattern of checking "if not token" works because empty strings are falsy
"""

import os
from typing import Optional


def get_court_listener_token() -> str:
    """Get Court Listener API token from environment variables.
    
    Court Listener is a comprehensive legal database that provides access to
    millions of legal documents including Supreme Court cases, circuit court
    decisions, and district court filings. This token enables authenticated
    access to their REST API.
    
    Integration with GovernmentReporter:
        The Court Listener API is one of the primary data sources for legal
        documents. This token is used by:
        - CourtListenerClient in the APIs module to fetch case data
        - Document indexing processes to retrieve full case text
        - Real-time document updates to ensure fresh legal content
    
    Security Notes:
        - Store the token in a .env file, never commit it to version control
        - The token should be kept secure as it may have usage limits
        - Consider using different tokens for development and production
    
    Python Learning Notes:
        - os.getenv() returns None if the environment variable doesn't exist
        - The "if not token" check works because None and empty strings are falsy
        - Raising ValueError immediately prevents the application from starting
          with invalid configuration, following the "fail fast" principle
    
    Returns:
        str: The Court Listener API token for authenticated requests.
            This token should be included in the Authorization header
            of HTTP requests to the Court Listener API.

    Raises:
        ValueError: If the COURT_LISTENER_API_TOKEN environment variable
            is not set or is empty. This is a required credential for
            the system to function properly.
            
    Example Usage:
        ```python
        from governmentreporter.utils.config import get_court_listener_token
        
        try:
            token = get_court_listener_token()
            headers = {"Authorization": f"Token {token}"}
            # Use headers in API requests
        except ValueError as e:
            print(f"Configuration error: {e}")
        ```
    """
    # Attempt to read the token from environment variables
    token = os.getenv("COURT_LISTENER_API_TOKEN")
    
    # Check if the token was found and is not empty
    if not token:
        # Raise a descriptive error that helps users fix the problem
        raise ValueError(
            "COURT_LISTENER_API_TOKEN not found in environment variables. "
            "Please set it in your .env file."
        )
    
    return token


def get_federal_register_token() -> Optional[str]:
    """Get Federal Register API token from environment variables.

    The Federal Register is the daily journal of the United States government,
    containing proposed rules, final rules, and public notices from federal
    agencies. This function retrieves the API token for accessing their data.
    
    Current Status:
        This integration is planned for future development but not yet implemented.
        The function is provided as a placeholder to maintain a consistent
        configuration interface as the system grows.
    
    Future Integration Plans:
        When implemented, this token will enable access to:
        - Daily Federal Register publications
        - Proposed and final federal regulations
        - Presidential documents and proclamations
        - Public notices and agency announcements
    
    Integration with GovernmentReporter:
        Once implemented, this token will be used by:
        - A future FederalRegisterClient in the APIs module
        - Document indexing processes for regulatory content
        - Real-time updates for new federal regulations
    
    Python Learning Notes:
        - The return type Optional[str] means this function can return either
          a string or None, indicating the token is not required
        - os.getenv() with just the variable name returns None if not found
        - No error is raised here because this integration is optional/future
        - The function maintains interface consistency for future expansion
    
    Returns:
        Optional[str]: The Federal Register API token if set in environment
            variables, or None if not configured. None is acceptable since
            this integration is not yet active.

    Example Usage:
        ```python
        from governmentreporter.utils.config import get_federal_register_token
        
        token = get_federal_register_token()
        if token:
            print("Federal Register token configured")
            # Use token for API requests
        else:
            print("Federal Register integration not configured")
        ```
    """
    # NOTE: Federal Register API integration is planned but not yet implemented.
    # This function serves as a placeholder for future development.
    return os.getenv("FEDERAL_REGISTER_API_TOKEN")


def get_congress_gov_token() -> Optional[str]:
    """Get Congress.gov API token from environment variables.

    Congress.gov is the official website for U.S. federal legislative information,
    providing access to bills, resolutions, committee reports, and voting records.
    This function retrieves the API token for accessing their data programmatically.
    
    Current Status:
        This integration is planned for future development but not yet implemented.
        The function is provided as a placeholder to maintain a consistent
        configuration interface as the system expands.
    
    Future Integration Plans:
        When implemented, this token will enable access to:
        - Current and historical bills from both chambers of Congress
        - Committee reports and hearing transcripts
        - Voting records and member information
        - Amendment text and legislative history
        - Congressional Research Service reports
    
    Integration with GovernmentReporter:
        Once implemented, this token will be used by:
        - A future CongressGovClient in the APIs module
        - Legislative document indexing and search capabilities
        - Real-time updates for new bills and Congressional activity
        - Integration with legal research workflows
    
    Python Learning Notes:
        - Like get_federal_register_token(), this returns Optional[str]
        - The consistent interface pattern makes it easy to add new integrations
        - Placeholder functions help with forward compatibility
        - No validation is done since the integration isn't active yet
    
    Returns:
        Optional[str]: The Congress.gov API token if set in environment
            variables, or None if not configured. None is acceptable since
            this integration is not yet implemented.

    Example Usage:
        ```python
        from governmentreporter.utils.config import get_congress_gov_token
        
        token = get_congress_gov_token()
        if token:
            print("Congress.gov token configured")
            # Future: Use token for legislative data access
        else:
            print("Congress.gov integration not configured")
        ```
    """
    # NOTE: Congress.gov API integration is planned but not yet implemented.
    # This function serves as a placeholder for future development.
    return os.getenv("CONGRESS_GOV_API_TOKEN")


def get_google_gemini_api_key() -> str:
    """Get Google Gemini API key from environment variables.
    
    Google Gemini is Google's advanced AI model family that provides natural
    language processing capabilities. In GovernmentReporter, Gemini 2.5 Flash-Lite
    is specifically used for generating metadata from legal documents.
    
    Integration with GovernmentReporter:
        The Google Gemini API key enables several critical functions:
        - Document metadata generation using AI analysis
        - Text summarization for large legal documents
        - Content classification and tagging
        - Semantic analysis for improved search relevance
        
        Specifically used by:
        - MetadataGenerator in the metadata module for AI-powered analysis
        - GoogleEmbeddingsClient for generating document embeddings
        - Document processing pipelines for content understanding
    
    API Key Setup:
        1. Visit Google AI Studio (https://makersuite.google.com)
        2. Create a new project or select an existing one
        3. Enable the Generative AI API
        4. Create an API key in the credentials section
        5. Add the key to your .env file as GOOGLE_GEMINI_API_KEY
    
    Security Notes:
        - Keep the API key secure and never commit it to version control
        - Monitor usage to avoid exceeding rate limits or quotas
        - Consider using different keys for development and production
        - The key grants access to Google's AI services and should be protected
    
    Python Learning Notes:
        - This function follows the same pattern as get_court_listener_token()
        - Required credentials raise ValueError to enforce proper configuration
        - The error message guides users to the solution (setting the .env file)
        - Consistent error handling makes configuration issues easy to debug
    
    Returns:
        str: The Google Gemini API key for authenticated requests to Google's
            AI services. This key is used to access language models and
            embedding generation capabilities.

    Raises:
        ValueError: If the GOOGLE_GEMINI_API_KEY environment variable is not
            set or is empty. This is a required credential for AI-powered
            features to function properly.
            
    Example Usage:
        ```python
        from governmentreporter.utils.config import get_google_gemini_api_key
        import google.generativeai as genai
        
        try:
            api_key = get_google_gemini_api_key()
            genai.configure(api_key=api_key)
            # Now you can use Google's AI services
        except ValueError as e:
            print(f"Google API configuration error: {e}")
        ```
    """
    # Attempt to read the API key from environment variables
    key = os.getenv("GOOGLE_GEMINI_API_KEY")
    
    # Check if the key was found and is not empty
    if not key:
        # Raise a descriptive error that helps users fix the problem
        raise ValueError(
            "GOOGLE_GEMINI_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )
    
    return key
