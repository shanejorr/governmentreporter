"""
MCP (Model Context Protocol) Server for GovernmentReporter.

This module implements the MCP server that exposes semantic search capabilities
for US government documents (Supreme Court opinions and Executive Orders) to
Large Language Models through standardized tools.

The server provides:
- Semantic search across government document collections
- Specialized search tools for SCOTUS opinions and Executive Orders
- Document retrieval by ID
- Collection information utilities

Classes:
    GovernmentReporterMCP: Main MCP server implementation that manages tools
                          and handles requests from LLMs.

Dependencies:
    - mcp: Model Context Protocol SDK for Python
    - qdrant_client: Vector database for semantic search
    - OpenAI API: For generating query embeddings
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    Resource,
    ResourcesCapability,
    ServerCapabilities,
    TextContent,
    Tool,
    ToolsCapability,
)

from ..database.qdrant import QdrantDBClient
from ..processors.embeddings import generate_embedding
from .config import ServerConfig, get_config
from .handlers import (
    handle_get_document_by_id,
    handle_list_collections,
    handle_search_executive_orders,
    handle_search_government_documents,
    handle_search_scotus_opinions,
)
from .resources import list_available_resources, read_resource

# Set up logging
logger = logging.getLogger(__name__)


class GovernmentReporterMCP:
    """
    MCP Server implementation for GovernmentReporter.

    This class manages the MCP server lifecycle and exposes semantic search
    tools for government documents to LLMs. It initializes connections to
    the Qdrant vector database and registers all available tools.

    Attributes:
        server (Server): The MCP server instance.
        qdrant_client (QdrantDBClient): Client for vector database operations.
        config (ServerConfig): Server configuration settings.

    Methods:
        initialize(): Set up the server and register tools.
        start(): Begin serving MCP requests.
        shutdown(): Gracefully close connections and stop the server.

    Example:
        >>> mcp = GovernmentReporterMCP()
        >>> await mcp.initialize()
        >>> await mcp.start()
    """

    def __init__(self, config: Optional[ServerConfig] = None):
        """
        Initialize the MCP server.

        Args:
            config: Optional server configuration. Uses factory singleton if not provided.
        """
        self.config = config or get_config()
        self.server = Server(self.config.server_name)
        self.qdrant_client = None

        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register all MCP tool and resource handlers with the server."""

        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """
            List available resources for the LLM.

            Resources provide direct access to full government documents,
            complementing the search tools with complete document content.

            Returns:
                List of Resource objects describing available resource types.
            """
            return list_available_resources()

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """
            Read a resource by URI.

            Fetches full document content from government APIs using the
            polymorphic GovernmentAPIClient interface.

            Args:
                uri: Resource URI (e.g., "scotus://opinion/12345678")

            Returns:
                Formatted document content with metadata.
            """
            return await read_resource(uri)

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """
            List all available tools for the LLM.

            Returns:
                List of Tool objects describing available search and retrieval tools.
            """
            return [
                Tool(
                    name="search_government_documents",
                    description=(
                        "Search across all US government documents including Supreme Court "
                        "opinions and Executive Orders. Returns relevant document chunks with "
                        "metadata for context-aware responses."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to find relevant documents",
                            },
                            "document_types": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["scotus", "executive_orders"],
                                },
                                "description": "Optional: Types of documents to search (default: both types)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10)",
                                "minimum": 1,
                                "maximum": 50,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="search_scotus_opinions",
                    description=(
                        "Search specifically within Supreme Court opinions with advanced "
                        "filtering by opinion type, justice, date range, and legal topics."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query for SCOTUS opinions",
                            },
                            "opinion_type": {
                                "type": "string",
                                "enum": [
                                    "majority",
                                    "concurring",
                                    "dissenting",
                                    "syllabus",
                                ],
                                "description": "Filter by type of opinion",
                            },
                            "justice": {
                                "type": "string",
                                "description": "Filter by authoring justice name",
                            },
                            "start_date": {
                                "type": "string",
                                "format": "date",
                                "description": "Start date for filtering (YYYY-MM-DD)",
                            },
                            "end_date": {
                                "type": "string",
                                "format": "date",
                                "description": "End date for filtering (YYYY-MM-DD)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 10)",
                                "minimum": 1,
                                "maximum": 50,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="search_executive_orders",
                    description=(
                        "Search specifically within federal Executive Orders with filtering by "
                        "president, agencies, policy topics, and date range."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query for Executive Orders",
                            },
                            "president": {
                                "type": "string",
                                "description": "Filter by president name",
                            },
                            "agencies": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by impacted agency codes (e.g., ['EPA', 'DOJ'])",
                            },
                            "policy_topics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by policy topics",
                            },
                            "start_date": {
                                "type": "string",
                                "format": "date",
                                "description": "Start date for filtering (YYYY-MM-DD)",
                            },
                            "end_date": {
                                "type": "string",
                                "format": "date",
                                "description": "End date for filtering (YYYY-MM-DD)",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 10)",
                                "minimum": 1,
                                "maximum": 50,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="get_document_by_id",
                    description=(
                        "Retrieve a specific document or document chunk by its ID. "
                        "Useful for getting more context about a previously found document."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "The ID of the document to retrieve",
                            },
                            "collection": {
                                "type": "string",
                                "description": "The collection to search in",
                                "enum": ["supreme_court_opinions", "executive_orders"],
                            },
                            "full_document": {
                                "type": "boolean",
                                "description": "Whether to retrieve the full document from the API (default: false)",
                            },
                        },
                        "required": ["document_id", "collection"],
                    },
                ),
                Tool(
                    name="list_collections",
                    description=(
                        "List all available document collections in the vector database "
                        "with statistics about each collection."
                    ),
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """
            Handle tool calls from the LLM.

            Args:
                name: The name of the tool to call.
                arguments: The arguments passed to the tool.

            Returns:
                List of TextContent objects containing the tool response.

            Raises:
                ValueError: If the tool name is not recognized.
            """
            if not self.qdrant_client:
                # Initialize Qdrant client with configured settings
                # Check for cloud URL first (highest priority)
                if hasattr(self.config, "qdrant_url") and self.config.qdrant_url:
                    self.qdrant_client = QdrantDBClient(
                        url=self.config.qdrant_url, api_key=self.config.qdrant_api_key
                    )
                # Then check for remote host/port
                elif (
                    self.config.qdrant_host != "localhost"
                    or self.config.qdrant_port != 6333
                ):
                    self.qdrant_client = QdrantDBClient(
                        host=self.config.qdrant_host,
                        port=self.config.qdrant_port,
                        api_key=self.config.qdrant_api_key,
                    )
                # Default to local file-based storage
                else:
                    db_path = getattr(self.config, "qdrant_db_path", "./qdrant_db")
                    self.qdrant_client = QdrantDBClient(db_path=db_path)

            try:
                if name == "search_government_documents":
                    result = await handle_search_government_documents(
                        self.qdrant_client, arguments
                    )
                elif name == "search_scotus_opinions":
                    result = await handle_search_scotus_opinions(
                        self.qdrant_client, arguments
                    )
                elif name == "search_executive_orders":
                    result = await handle_search_executive_orders(
                        self.qdrant_client, arguments
                    )
                elif name == "get_document_by_id":
                    result = await handle_get_document_by_id(
                        self.qdrant_client, arguments
                    )
                elif name == "list_collections":
                    result = await handle_list_collections(
                        self.qdrant_client, arguments
                    )
                else:
                    raise ValueError(f"Unknown tool: {name}")

                return [TextContent(type="text", text=result)]

            except Exception as e:
                logger.error(f"Error handling tool {name}: {e}")
                error_message = f"Error executing {name}: {str(e)}"
                return [TextContent(type="text", text=error_message)]

    async def initialize(self):
        """
        Initialize the MCP server and set up connections.

        This method:
        1. Initializes the Qdrant client connection
        2. Verifies database connectivity
        3. Logs available collections

        Raises:
            ConnectionError: If unable to connect to Qdrant database.
        """
        logger.info(f"Initializing {self.config.server_name}...")

        # Initialize Qdrant client with configured settings
        # Check for cloud URL first (highest priority)
        if hasattr(self.config, "qdrant_url") and self.config.qdrant_url:
            self.qdrant_client = QdrantDBClient(
                url=self.config.qdrant_url, api_key=self.config.qdrant_api_key
            )
        # Then check for remote host/port
        elif self.config.qdrant_host != "localhost" or self.config.qdrant_port != 6333:
            self.qdrant_client = QdrantDBClient(
                host=self.config.qdrant_host,
                port=self.config.qdrant_port,
                api_key=self.config.qdrant_api_key,
            )
        # Default to local file-based storage
        else:
            db_path = getattr(self.config, "qdrant_db_path", "./qdrant_db")
            self.qdrant_client = QdrantDBClient(db_path=db_path)

        # Verify connection and log available collections
        try:
            collections = self.qdrant_client.list_collections()
            logger.info(f"Connected to Qdrant. Available collections: {collections}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise ConnectionError(f"Cannot initialize MCP server: {e}")

        logger.info("MCP server initialized successfully")

    async def start(self):
        """
        Start the MCP server and begin handling requests.

        This method runs the server's main event loop and blocks until
        the server is shut down.
        """
        logger.info(f"Starting {self.config.server_name}...")

        # Initialize if not already done
        if not self.qdrant_client:
            await self.initialize()

        # Run the server using stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=self.config.server_name,
                    server_version=self.config.server_version,
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability(),
                        resources=ResourcesCapability(subscribe=False, listChanged=False),
                    ),
                ),
            )

    async def shutdown(self):
        """
        Gracefully shut down the MCP server.

        This method:
        1. Closes the Qdrant client connection
        2. Cleans up any server resources
        3. Logs shutdown completion
        """
        logger.info(f"Shutting down {self.config.server_name}...")

        # Close Qdrant connection if exists
        if self.qdrant_client:
            # QdrantDBClient doesn't have explicit close, but we can set to None
            self.qdrant_client = None

        logger.info("MCP server shut down successfully")


async def create_and_run_server():
    """
    Convenience function to create and run the MCP server.

    This function:
    1. Creates a GovernmentReporterMCP instance
    2. Initializes the server
    3. Runs the server until interrupted
    4. Handles graceful shutdown on interruption

    Example:
        >>> asyncio.run(create_and_run_server())
    """
    server = GovernmentReporterMCP()

    try:
        await server.initialize()
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        await server.shutdown()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the server
    asyncio.run(create_and_run_server())
