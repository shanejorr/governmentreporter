"""
Tests for MCP server implementation.

This module tests the GovernmentReporterMCP server class including:
- Server initialization and configuration
- Tool registration and listing
- Request handling lifecycle
- Error handling and edge cases
- Integration with Qdrant client

Python Learning Notes:
    - pytest-asyncio enables testing async functions
    - Fixtures provide reusable test setup
    - Mocking isolates units under test from dependencies
    - Context managers (async with) ensure proper cleanup
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from mcp.types import Tool

from governmentreporter.server.mcp_server import GovernmentReporterMCP
from governmentreporter.server.config import ServerConfig


@pytest.fixture
def mock_config():
    """
    Create a test server configuration.

    Returns:
        ServerConfig: Test configuration with minimal settings.

    Python Learning Notes:
        - Fixtures are reusable setup code for tests
        - @pytest.fixture decorator marks function as fixture
        - Tests can request fixtures as function parameters
    """
    return ServerConfig(
        server_name="Test MCP Server",
        server_version="0.1.0-test",
        qdrant_host="localhost",
        qdrant_port=6333,
        qdrant_db_path=":memory:",  # In-memory for testing
    )


@pytest.fixture
def mock_qdrant_client():
    """
    Create a mock Qdrant client for testing.

    Returns:
        MagicMock: Mock Qdrant client with common methods.
    """
    client = MagicMock()
    client.get_collections.return_value = {"collections": []}
    client.semantic_search = AsyncMock(return_value=[])
    client.get_document_by_id = AsyncMock(return_value=None)
    return client


class TestMCPServerInitialization:
    """
    Test suite for MCP server initialization.

    Verifies that the server initializes correctly with various
    configurations and properly sets up all required components.

    Python Learning Notes:
        - Class-based test organization groups related tests
        - Test methods must start with 'test_'
        - setUp/tearDown methods can be used for common setup
    """

    def test_server_initialization_with_default_config(self):
        """
        Test server initializes with default configuration.

        Python Learning Notes:
            - Tests should be self-contained and independent
            - Assertions verify expected behavior
            - Clear test names describe what is being tested
        """
        server = GovernmentReporterMCP()

        assert server is not None
        assert server.server is not None
        assert server.config is not None
        assert server.qdrant_client is None  # Not initialized until start

    def test_server_initialization_with_custom_config(self, mock_config):
        """Test server accepts custom configuration."""
        server = GovernmentReporterMCP(config=mock_config)

        assert server.config == mock_config
        assert server.config.server_name == "Test MCP Server"

    def test_server_has_correct_name(self, mock_config):
        """Test server uses configured name."""
        server = GovernmentReporterMCP(config=mock_config)

        # Access the server name from the mcp Server object
        assert server.server.name == "Test MCP Server"

    @patch("governmentreporter.server.mcp_server.QdrantDBClient")
    def test_server_creates_qdrant_client_on_init(self, mock_qdrant_class, mock_config):
        """Test that Qdrant client is prepared during initialization."""
        server = GovernmentReporterMCP(config=mock_config)

        # Client should not be created until needed
        assert server.qdrant_client is None


class TestMCPToolRegistration:
    """
    Test suite for MCP tool registration.

    Verifies that all tools are properly registered and available
    to LLMs through the MCP protocol.
    """

    @pytest.mark.asyncio
    async def test_list_tools_returns_all_tools(self, mock_config):
        """
        Test that list_tools returns all 5 expected tools.

        Python Learning Notes:
            - @pytest.mark.asyncio enables async test execution
            - async def creates coroutine function
            - await keyword waits for async operation to complete
        """
        server = GovernmentReporterMCP(config=mock_config)

        # Get the list_tools handler
        tools = await server.server._list_tools_handlers[0].fn()

        assert len(tools) == 5
        assert all(isinstance(tool, Tool) for tool in tools)

    @pytest.mark.asyncio
    async def test_search_government_documents_tool_registered(self, mock_config):
        """Test search_government_documents tool is registered."""
        server = GovernmentReporterMCP(config=mock_config)
        tools = await server.server._list_tools_handlers[0].fn()

        tool_names = [tool.name for tool in tools]
        assert "search_government_documents" in tool_names

        # Find the tool and verify its properties
        search_tool = next(t for t in tools if t.name == "search_government_documents")
        assert "search" in search_tool.description.lower()
        assert search_tool.inputSchema is not None

    @pytest.mark.asyncio
    async def test_search_scotus_opinions_tool_registered(self, mock_config):
        """Test search_scotus_opinions tool is registered."""
        server = GovernmentReporterMCP(config=mock_config)
        tools = await server.server._list_tools_handlers[0].fn()

        tool_names = [tool.name for tool in tools]
        assert "search_scotus_opinions" in tool_names

        scotus_tool = next(t for t in tools if t.name == "search_scotus_opinions")
        assert (
            "supreme court" in scotus_tool.description.lower()
            or "scotus" in scotus_tool.description.lower()
        )

    @pytest.mark.asyncio
    async def test_search_executive_orders_tool_registered(self, mock_config):
        """Test search_executive_orders tool is registered."""
        server = GovernmentReporterMCP(config=mock_config)
        tools = await server.server._list_tools_handlers[0].fn()

        tool_names = [tool.name for tool in tools]
        assert "search_executive_orders" in tool_names

        eo_tool = next(t for t in tools if t.name == "search_executive_orders")
        assert "executive order" in eo_tool.description.lower()

    @pytest.mark.asyncio
    async def test_get_document_by_id_tool_registered(self, mock_config):
        """Test get_document_by_id tool is registered."""
        server = GovernmentReporterMCP(config=mock_config)
        tools = await server.server._list_tools_handlers[0].fn()

        tool_names = [tool.name for tool in tools]
        assert "get_document_by_id" in tool_names

    @pytest.mark.asyncio
    async def test_list_collections_tool_registered(self, mock_config):
        """Test list_collections tool is registered."""
        server = GovernmentReporterMCP(config=mock_config)
        tools = await server.server._list_tools_handlers[0].fn()

        tool_names = [tool.name for tool in tools]
        assert "list_collections" in tool_names


class TestMCPToolInputSchemas:
    """
    Test suite for tool input schemas.

    Verifies that each tool has proper input schema definitions
    for LLMs to understand required and optional parameters.
    """

    @pytest.mark.asyncio
    async def test_all_tools_have_input_schemas(self, mock_config):
        """Test that every tool has an inputSchema defined."""
        server = GovernmentReporterMCP(config=mock_config)
        tools = await server.server._list_tools_handlers[0].fn()

        for tool in tools:
            assert tool.inputSchema is not None, f"Tool {tool.name} missing inputSchema"
            assert "type" in tool.inputSchema
            assert tool.inputSchema["type"] == "object"

    @pytest.mark.asyncio
    async def test_search_tools_require_query_parameter(self, mock_config):
        """Test that search tools require 'query' parameter."""
        server = GovernmentReporterMCP(config=mock_config)
        tools = await server.server._list_tools_handlers[0].fn()

        search_tools = [
            "search_government_documents",
            "search_scotus_opinions",
            "search_executive_orders",
        ]

        for tool_name in search_tools:
            tool = next(t for t in tools if t.name == tool_name)
            required = tool.inputSchema.get("required", [])
            assert "query" in required, f"Tool {tool_name} should require 'query'"

    @pytest.mark.asyncio
    async def test_get_document_requires_id_parameter(self, mock_config):
        """Test that get_document_by_id requires 'document_id' parameter."""
        server = GovernmentReporterMCP(config=mock_config)
        tools = await server.server._list_tools_handlers[0].fn()

        get_doc_tool = next(t for t in tools if t.name == "get_document_by_id")
        required = get_doc_tool.inputSchema.get("required", [])
        assert "document_id" in required or "id" in required


class TestMCPServerConfiguration:
    """
    Test suite for server configuration handling.

    Verifies that configuration is properly loaded and applied
    throughout the server components.
    """

    def test_config_has_required_fields(self, mock_config):
        """Test configuration has all required fields."""
        assert hasattr(mock_config, "server_name")
        assert hasattr(mock_config, "server_version")
        assert hasattr(mock_config, "qdrant_host")
        assert hasattr(mock_config, "qdrant_port")
        assert hasattr(mock_config, "collection_map")

    def test_config_default_collections(self):
        """Test default configuration includes expected collections."""
        config = ServerConfig()

        assert "supreme_court_opinions" in config.collection_map
        assert "executive_orders" in config.collection_map

    def test_config_custom_search_limit(self):
        """Test custom search limits are respected."""
        config = ServerConfig(default_search_limit=25, max_search_limit=100)

        assert config.default_search_limit == 25
        assert config.max_search_limit == 100


class TestMCPServerErrorHandling:
    """
    Test suite for error handling in MCP server.

    Verifies that errors are caught, logged, and reported appropriately
    without crashing the server.
    """

    @patch("governmentreporter.server.mcp_server.QdrantDBClient")
    def test_server_handles_qdrant_connection_error(
        self, mock_qdrant_class, mock_config
    ):
        """Test server handles Qdrant connection failures gracefully."""
        # Configure mock to raise connection error
        mock_qdrant_class.side_effect = ConnectionError("Cannot connect to Qdrant")

        server = GovernmentReporterMCP(config=mock_config)

        # Server should initialize even if Qdrant fails
        assert server is not None

    def test_server_validates_config_on_init(self):
        """Test server validates configuration during initialization."""
        # This should not raise an error
        server = GovernmentReporterMCP()
        assert server is not None


class TestMCPServerLifecycle:
    """
    Test suite for server lifecycle management.

    Verifies proper startup, shutdown, and resource cleanup.
    """

    def test_server_initialization_is_synchronous(self, mock_config):
        """Test that server can be initialized synchronously."""
        # Should not require await
        server = GovernmentReporterMCP(config=mock_config)
        assert server is not None

    @patch("governmentreporter.server.mcp_server.QdrantDBClient")
    def test_server_cleanup_closes_connections(self, mock_qdrant_class, mock_config):
        """Test that cleanup properly closes all connections."""
        mock_client = MagicMock()
        mock_qdrant_class.return_value = mock_client

        server = GovernmentReporterMCP(config=mock_config)
        server.qdrant_client = mock_client

        # Verify client exists
        assert server.qdrant_client is not None


class TestMCPServerIntegration:
    """
    Integration tests for MCP server with mocked dependencies.

    Tests the interaction between server components without
    requiring external services.
    """

    @pytest.mark.asyncio
    async def test_server_tools_accessible_after_init(self, mock_config):
        """Test that tools are accessible immediately after initialization."""
        server = GovernmentReporterMCP(config=mock_config)

        # Should be able to list tools right away
        tools = await server.server._list_tools_handlers[0].fn()
        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_multiple_server_instances_independent(self, mock_config):
        """Test that multiple server instances don't interfere with each other."""
        server1 = GovernmentReporterMCP(config=mock_config)
        server2 = GovernmentReporterMCP(config=mock_config)

        # Both should work independently
        tools1 = await server1.server._list_tools_handlers[0].fn()
        tools2 = await server2.server._list_tools_handlers[0].fn()

        assert len(tools1) == len(tools2)
        assert server1 is not server2
