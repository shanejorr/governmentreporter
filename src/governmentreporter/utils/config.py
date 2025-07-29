"""Configuration management for GovernmentReporter."""

import os
from typing import Optional


def get_court_listener_token() -> str:
    """Get Court Listener API token from environment variables.

    Returns:
        str: The API token

    Raises:
        ValueError: If token is not found
    """
    token = os.getenv("COURT_LISTENER_API_TOKEN")
    if not token:
        raise ValueError(
            "COURT_LISTENER_API_TOKEN not found in environment variables. "
            "Please set it in your .env file."
        )
    return token


def get_federal_register_token() -> Optional[str]:
    """Get Federal Register API token from environment variables."""
    return os.getenv("FEDERAL_REGISTER_API_TOKEN")


def get_congress_gov_token() -> Optional[str]:
    """Get Congress.gov API token from environment variables."""
    return os.getenv("CONGRESS_GOV_API_TOKEN")


def get_google_gemini_api_key() -> str:
    """Get Google Gemini API key from environment variables.

    Returns:
        str: The API key

    Raises:
        ValueError: If key is not found
    """
    key = os.getenv("GOOGLE_GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "GOOGLE_GEMINI_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )
    return key
