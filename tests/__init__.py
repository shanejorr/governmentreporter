"""
Test suite for GovernmentReporter application.

This package contains all unit and integration tests for the GovernmentReporter
system, organized by module to mirror the source code structure.

Test Organization:
    - test_utils/: Tests for utility functions and helpers
    - test_apis/: Tests for government API clients
    - test_processors/: Tests for document processing and chunking
    - test_database/: Tests for Qdrant database operations
    - test_server/: Tests for MCP server functionality

Python Learning Notes:
    - __init__.py makes this directory a Python package
    - Tests are discovered automatically by pytest
    - Test files should start with test_ prefix
    - Test functions should also start with test_
"""