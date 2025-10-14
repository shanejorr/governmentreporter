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
                        "Perform semantic search across ALL government documents (Supreme Court opinions "
                        "AND Executive Orders by default). Returns hierarchically-chunked text segments "
                        "with rich legal metadata ranked by semantic relevance. Each chunk preserves document "
                        "structure (opinion type, section labels, justice attribution). Use this tool for broad "
                        "searches across document types or when the user doesn't specify a document type. "
                        "For specialized filtering (by justice, president, agencies, opinion type, dates), "
                        "use document-specific search tools instead. Results include document context, "
                        "citations, structural information, and relevance scores."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query to find semantically relevant documents",
                            },
                            "document_types": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["scotus", "executive_orders"],
                                },
                                "description": (
                                    "Optional: Restrict search to specific document types. "
                                    "Options are 'scotus' (Supreme Court opinions) or 'executive_orders'. "
                                    "Default: searches both types."
                                ),
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10, max: 50)",
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
                        "Search Supreme Court opinions with advanced filtering capabilities. "
                        "Returns hierarchically-chunked opinion segments with rich legal metadata including "
                        "case names, vote breakdowns, constitutional provisions cited, statutes interpreted, "
                        "holdings, section labels, and justice attribution. Use this tool when you need "
                        "SCOTUS-specific filtering (opinion type, justice, date) beyond the general search. "
                        "Supports filtering by: opinion_type (majority/concurring/dissenting/syllabus), "
                        "justice (last name like 'Roberts' or 'Sotomayor'), and date range (decision date). "
                        "Results ranked by semantic relevance to the query."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query for semantic matching within SCOTUS opinions",
                            },
                            "opinion_type": {
                                "type": "string",
                                "enum": [
                                    "majority",
                                    "concurring",
                                    "dissenting",
                                    "syllabus",
                                ],
                                "description": (
                                    "Optional: Filter by opinion type. 'majority' = main Court opinion, "
                                    "'concurring' = agreeing but separate reasoning, 'dissenting' = disagreeing opinion, "
                                    "'syllabus' = official case summary."
                                ),
                            },
                            "justice": {
                                "type": "string",
                                "description": (
                                    "Optional: Filter by authoring justice. Use last name only "
                                    "(e.g., 'Roberts', 'Sotomayor', 'Kagan'). Applies to majority, concurring, "
                                    "and dissenting opinions."
                                ),
                            },
                            "start_date": {
                                "type": "string",
                                "format": "date",
                                "description": (
                                    "Optional: Filter opinions decided on or after this date (YYYY-MM-DD format). "
                                    "Filters on the decision_date field."
                                ),
                            },
                            "end_date": {
                                "type": "string",
                                "format": "date",
                                "description": (
                                    "Optional: Filter opinions decided on or before this date (YYYY-MM-DD format). "
                                    "Filters on the decision_date field."
                                ),
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10, max: 50)",
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
                        "Search Executive Orders with advanced filtering capabilities. "
                        "Returns hierarchically-chunked order segments with rich policy metadata including "
                        "EO numbers, signing dates, presidents, impacted agencies, policy topics, "
                        "legal authorities cited, economic sectors, and section structure. Use this tool when "
                        "you need EO-specific filtering (president, agencies, policy topics, dates) beyond "
                        "general search. Supports filtering by: president (last name), agencies (federal agency "
                        "codes), policy_topics (topic strings matching indexed values), and date range (signing date). "
                        "Results ranked by semantic relevance to the query."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query for semantic matching within Executive Orders",
                            },
                            "president": {
                                "type": "string",
                                "description": (
                                    "Optional: Filter by president. Use last name only "
                                    "(e.g., 'Biden', 'Trump', 'Obama'). Case-sensitive."
                                ),
                            },
                            "agencies": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Optional: Filter by impacted federal agencies. Provide array of agency codes "
                                    "(e.g., ['EPA', 'DOJ', 'NASA', 'HHS', 'DOD']). Matches orders affecting ANY "
                                    "of the specified agencies."
                                ),
                            },
                            "policy_topics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Optional: Filter by policy topics. Provide array of topic strings "
                                    "(e.g., ['environment', 'healthcare', 'national security', 'immigration']). "
                                    "Matches orders tagged with ANY of the specified topics."
                                ),
                            },
                            "start_date": {
                                "type": "string",
                                "format": "date",
                                "description": (
                                    "Optional: Filter orders signed on or after this date (YYYY-MM-DD format). "
                                    "Filters on the signing_date field."
                                ),
                            },
                            "end_date": {
                                "type": "string",
                                "format": "date",
                                "description": (
                                    "Optional: Filter orders signed on or before this date (YYYY-MM-DD format). "
                                    "Filters on the signing_date field."
                                ),
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10, max: 50)",
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
                        "Retrieve a specific document chunk by its ID (obtained from search results). "
                        "By default, returns the stored chunk with metadata. Set full_document=true to fetch "
                        "the complete, unabridged document text directly from government APIs in real-time "
                        "(CourtListener for SCOTUS opinions, Federal Register for Executive Orders). "
                        "Use this tool to: (1) get additional context beyond a retrieved chunk, "
                        "(2) access the full document when chunks are insufficient for the user's needs, or "
                        "(3) retrieve the complete text of a specific document the user references. "
                        "Note: full_document=true may have higher latency due to API fetch."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": (
                                    "The unique document/chunk ID to retrieve. Obtain this from search results "
                                    "(appears in metadata or result IDs)."
                                ),
                            },
                            "collection": {
                                "type": "string",
                                "description": (
                                    "The collection containing the document. Use 'supreme_court_opinions' for "
                                    "SCOTUS opinions or 'executive_orders' for Executive Orders."
                                ),
                                "enum": ["supreme_court_opinions", "executive_orders"],
                            },
                            "full_document": {
                                "type": "boolean",
                                "description": (
                                    "Optional: If true, fetches the complete unabridged document from government APIs "
                                    "instead of just the stored chunk. Default: false. Set to true when the user needs "
                                    "the full document text or when chunk context is insufficient."
                                ),
                            },
                        },
                        "required": ["document_id", "collection"],
                    },
                ),
                Tool(
                    name="list_collections",
                    description=(
                        "List all available document collections with database statistics (total chunks, "
                        "vector counts, vector dimensions, available metadata fields). Use this tool ONLY "
                        "when the user explicitly asks about: (1) what collections are available, "
                        "(2) database contents or statistics, (3) system capabilities or indexed documents, or "
                        "(4) what metadata fields can be filtered on. DO NOT use this tool for regular document "
                        "searches - use the search tools instead. This is a diagnostic/informational tool."
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
                # Then check for remote host/port (only if explicitly configured and NOT localhost)
                elif self.config.qdrant_host and self.config.qdrant_host != "localhost":
                    self.qdrant_client = QdrantDBClient(
                        host=self.config.qdrant_host,
                        port=self.config.qdrant_port,
                        api_key=self.config.qdrant_api_key,
                    )
                # Default to local file-based storage
                else:
                    db_path = getattr(
                        self.config, "qdrant_db_path", "./data/qdrant/qdrant_db"
                    )
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
        # Then check for remote host/port (only if explicitly configured and NOT localhost)
        elif self.config.qdrant_host and self.config.qdrant_host != "localhost":
            self.qdrant_client = QdrantDBClient(
                host=self.config.qdrant_host,
                port=self.config.qdrant_port,
                api_key=self.config.qdrant_api_key,
            )
        # Default to local file-based storage
        else:
            db_path = getattr(self.config, "qdrant_db_path", "./data/qdrant/qdrant_db")
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
                        resources=ResourcesCapability(
                            subscribe=False, listChanged=False
                        ),
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
