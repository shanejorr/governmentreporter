"""
API Clients Module for Government Data Sources.

This module provides a unified interface for accessing various US government APIs
to retrieve federal documents including Supreme Court opinions and Executive Orders.
It implements a clean abstraction layer that standardizes how the application
interacts with different government data sources.

The module follows object-oriented design principles with:
    - Abstract base classes defining common interfaces (base.py)
    - Concrete implementations for specific APIs
    - Standardized document representations
    - Built-in rate limiting and error handling
    - Consistent date formatting and validation

Available API Clients:
    - CourtListenerClient: Access to Supreme Court opinions via CourtListener API
    - FederalRegisterClient: Access to Executive Orders via Federal Register API

Usage Example:
    from governmentreporter.apis import CourtListenerClient

    # Initialize client with API token
    client = CourtListenerClient()

    # Fetch a specific Supreme Court opinion
    opinion = client.get_opinion("123456")

    # Search for opinions in date range
    opinions = client.list_scotus_opinions(
        since_date="2024-01-01",
        until_date="2024-12-31"
    )

Integration Points:
    - Used by processors module for document retrieval
    - Works with utils.config for API credential management
    - Provides data to chunkers for hierarchical processing
    - Supplies raw text for metadata extraction

Python Learning Notes:
    - __all__: Controls what's imported with 'from module import *'
    - Relative imports: '.court_listener' imports from same package
    - Module initialization: This file makes 'apis' a package
    - Re-exports: Makes submodule classes available at package level
"""

from .court_listener import CourtListenerClient
from .federal_register import FederalRegisterClient

__all__ = ["CourtListenerClient", "FederalRegisterClient"]
