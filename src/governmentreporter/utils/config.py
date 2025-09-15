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
    - Metadata module: Uses OpenAI API key for AI-powered metadata generation
    - Database module: May use credentials for cloud database connections
    - MCP server: Validates all required credentials at startup

Environment Variable Setup:
    Create a .env file in the project root with these variables:
    ```
    COURT_LISTENER_API_TOKEN=your_court_listener_token_here
    OPENAI_API_KEY=your_openai_api_key_here
    FEDERAL_REGISTER_API_TOKEN=optional_future_use
    CONGRESS_GOV_API_TOKEN=optional_future_use
    ```

Python Learning Notes:
    - os.getenv() safely reads environment variables without raising errors
    - The module uses type hints to indicate which functions return Optional values
    - ValueError is raised for missing required credentials to fail fast
    - The pattern of checking "if not token" works because empty strings are falsy
"""

import logging
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
            logger = logging.getLogger(__name__)
            logger.error(f"Configuration error: {e}")
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


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment variables.

    OpenAI provides advanced AI models including GPT-4 and text embedding models
    that provide natural language processing capabilities. In GovernmentReporter,
    GPT-4o-mini is used for metadata generation and text-embedding-3-small is used
    for document embeddings.

    Integration with GovernmentReporter:
        The OpenAI API key enables several critical functions:
        - Document metadata generation using AI analysis
        - Text summarization for large legal documents
        - Content classification and tagging
        - Semantic analysis for improved search relevance
        - High-quality text embeddings for vector search

        Specifically used by:
        - LLM extraction functions in the metadata module for AI-powered analysis
        - OpenAIEmbeddingsClient for generating document embeddings
        - Document processing pipelines for content understanding

    API Key Setup:
        1. Visit OpenAI Platform (https://platform.openai.com)
        2. Create an account or sign in
        3. Navigate to API keys section
        4. Create a new API key
        5. Add the key to your .env file as OPENAI_API_KEY

    Security Notes:
        - Keep the API key secure and never commit it to version control
        - Monitor usage to avoid exceeding rate limits or quotas
        - Consider using different keys for development and production
        - The key grants access to OpenAI's AI services and should be protected

    Python Learning Notes:
        - This function follows the same pattern as get_court_listener_token()
        - Required credentials raise ValueError to enforce proper configuration
        - The error message guides users to the solution (setting the .env file)
        - Consistent error handling makes configuration issues easy to debug

    Returns:
        str: The OpenAI API key for authenticated requests to OpenAI's
            AI services. This key is used to access language models and
            embedding generation capabilities.

    Raises:
        ValueError: If the OPENAI_API_KEY environment variable is not
            set or is empty. This is a required credential for AI-powered
            features to function properly.

    Example Usage:
        ```python
        from governmentreporter.utils.config import get_openai_api_key
        from openai import OpenAI

        try:
            api_key = get_openai_api_key()
            client = OpenAI(api_key=api_key)
            # Now you can use OpenAI's services
        except ValueError as e:
            logger = logging.getLogger(__name__)
            logger.error(f"OpenAI API configuration error: {e}")
        ```
    """
    # Attempt to read the API key from environment variables
    key = os.getenv("OPENAI_API_KEY")

    # Check if the key was found and is not empty
    if not key:
        # Raise a descriptive error that helps users fix the problem
        raise ValueError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )

    return key
