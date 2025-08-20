"""Utility modules for GovernmentReporter.

This package contains shared utilities and helper functions that support the core
functionality of the GovernmentReporter MCP server. The utilities are organized
into specialized modules for different concerns:

- config.py: Environment variable management for API keys and tokens
- embeddings.py: Text embedding generation using Google's AI models
- citations.py: Legal citation formatting utilities
- __init__.py: Centralized imports and common utilities like logging

Integration Points:
    - The config module provides secure access to API credentials for all
      external services (Court Listener, Federal Register, Congress.gov, Google)
    - The embeddings module generates vector representations of legal documents
      for storage in ChromaDB and semantic search capabilities
    - The citations module formats legal references according to Bluebook standards
    - The logger utility ensures consistent log formatting across all modules

Python Learning Notes:
    - This __init__.py file serves as a package initializer and public API
    - The __all__ list at the bottom controls what gets imported with "from utils import *"
    - Type hints (Optional[str], logging.Logger) help with code clarity and IDE support
    - The logging configuration follows Python's standard logging module patterns
"""

import logging
from typing import Optional

from .citations import build_bluebook_citation
from .config import (get_congress_gov_token, get_court_listener_token,
                     get_federal_register_token, get_google_gemini_api_key)
from .embeddings import GoogleEmbeddingsClient


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance with consistent configuration across the application.
    
    This function provides a standardized logging setup that ensures all modules
    in the GovernmentReporter system use consistent log formatting and output.
    It prevents duplicate handler creation and sets sensible defaults.
    
    The logging configuration includes:
    - Timestamp for when the log entry was created
    - Logger name (usually the module name) for source identification
    - Log level (INFO, ERROR, DEBUG, etc.) for message categorization
    - The actual log message
    
    Integration with GovernmentReporter:
        This logger is used throughout the system for:
        - API request/response logging in the APIs modules
        - Database operation logging in ChromaDB interactions
        - Error tracking during document processing
        - Debug information during development
    
    Python Learning Notes:
        - logging.getLogger() creates or retrieves a logger by name
        - The 'name or __name__' pattern uses Python's truthiness:
          if name is provided, use it; otherwise use the current module's name
        - logger.handlers is a list of output destinations (console, file, etc.)
        - The formatter defines how log messages appear in output
        - Setting the log level to INFO means DEBUG messages won't be shown
    
    Args:
        name (Optional[str]): Logger name to use. If None, uses the calling
            module's __name__ attribute. This helps identify which module
            generated each log message.
        
    Returns:
        logging.Logger: A configured logger instance ready for use. The logger
            will output to the console with formatted timestamps and level info.
            
    Example Usage:
        ```python
        # In any module
        from governmentreporter.utils import get_logger
        
        logger = get_logger(__name__)
        logger.info("Starting document processing")
        logger.error("Failed to connect to API")
        ```
    """
    # Get or create a logger with the specified name
    # If name is None, __name__ will be the current module's name
    logger = logging.getLogger(name or __name__)
    
    # Only configure the logger if it doesn't already have handlers
    # This prevents duplicate log messages when the function is called multiple times
    if not logger.handlers:
        # Create a handler that outputs to the console (stdout/stderr)
        handler = logging.StreamHandler()
        
        # Define the format for log messages
        # %(asctime)s - timestamp when the log was created
        # %(name)s - the logger's name (usually the module name)
        # %(levelname)s - the log level (INFO, ERROR, etc.)
        # %(message)s - the actual log message
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Apply the formatter to the handler
        handler.setFormatter(formatter)
        
        # Add the handler to the logger
        logger.addHandler(handler)
        
        # Set the minimum log level to INFO
        # This means DEBUG messages won't be shown unless the level is changed
        logger.setLevel(logging.INFO)
    
    return logger


__all__ = [
    "get_court_listener_token",
    "get_federal_register_token",
    "get_congress_gov_token",
    "get_google_gemini_api_key",
    "GoogleEmbeddingsClient",
    "build_bluebook_citation",
    "get_logger",
]
