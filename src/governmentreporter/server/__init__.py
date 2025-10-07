"""
GovernmentReporter MCP Server Module.

This module implements the Model Context Protocol (MCP) server for
GovernmentReporter, providing semantic search capabilities for US
government documents to Large Language Models.

The server exposes tools for:
- Semantic search across Supreme Court opinions and Executive Orders
- Document retrieval by ID
- Collection information and statistics
- Specialized searches with metadata filtering

The server also provides resources for:
- Full document access via polymorphic API clients
- Direct retrieval of Supreme Court opinions and Executive Orders
- On-demand fetching from government APIs

Components:
    mcp_server: Main MCP server implementation
    handlers: Tool handlers for processing LLM requests
    resources: Resource handlers for full document access
    query_processor: Formatting and processing of query results
    config: Server configuration and settings

Example Usage:
    >>> from governmentreporter.server import GovernmentReporterMCP, ServerConfig
    >>> config = ServerConfig(default_search_limit=20)
    >>> server = GovernmentReporterMCP(config)
    >>> await server.initialize()
    >>> await server.start()

For command-line usage:
    $ python -m governmentreporter.server
"""

from .config import ServerConfig, get_config, set_config
from .handlers import (
    handle_get_document_by_id,
    handle_list_collections,
    handle_search_executive_orders,
    handle_search_government_documents,
    handle_search_scotus_opinions,
)
from .mcp_server import GovernmentReporterMCP, create_and_run_server
from .query_processor import QueryProcessor
from .resources import (
    format_document_resource,
    get_api_client,
    list_available_resources,
    parse_resource_uri,
    read_resource,
)

__all__ = [
    # Main server class
    "GovernmentReporterMCP",
    "create_and_run_server",
    # Configuration
    "ServerConfig",
    "get_config",
    "set_config",
    # Handlers
    "handle_search_government_documents",
    "handle_search_scotus_opinions",
    "handle_search_executive_orders",
    "handle_get_document_by_id",
    "handle_list_collections",
    # Query processing
    "QueryProcessor",
    # Resources
    "read_resource",
    "list_available_resources",
    "parse_resource_uri",
    "get_api_client",
    "format_document_resource",
]

# Version information
__version__ = "1.0.0"
