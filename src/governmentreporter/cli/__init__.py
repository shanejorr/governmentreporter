"""
Command-line interface for GovernmentReporter.

This module provides CLI commands for:
- Running the MCP server
- Ingesting government documents
- Querying the vector database

Usage:
    governmentreporter server      # Start MCP server
    governmentreporter ingest      # Ingest documents
    governmentreporter query       # Search documents
"""

from .ingest import ingest
from .main import main
from .query import query
from .server import server

__all__ = ["main", "ingest", "server", "query"]
