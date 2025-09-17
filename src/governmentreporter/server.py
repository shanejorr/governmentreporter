#!/usr/bin/env python3
"""
Main entry point for the GovernmentReporter MCP Server.

This script starts the MCP (Model Context Protocol) server that provides
semantic search capabilities for US government documents to Large Language
Models. It can be run directly or imported as a module.

Usage:
    Direct execution:
        $ python -m governmentreporter.server

    With uv:
        $ uv run python -m governmentreporter.server

    As a script:
        $ ./server.py

The server will:
1. Initialize connections to the Qdrant vector database
2. Set up MCP tool handlers for document search
3. Listen for and respond to LLM requests
4. Provide semantic search across Supreme Court opinions and Executive Orders

Environment Variables:
    OPENAI_API_KEY: Required for generating query embeddings
    MCP_SERVER_NAME: Optional server name override
    MCP_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
    QDRANT_HOST: Qdrant server host (default: localhost)
    QDRANT_PORT: Qdrant server port (default: 6333)

Example:
    >>> import asyncio
    >>> from governmentreporter.server import main
    >>> asyncio.run(main())
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from governmentreporter.server.mcp_server import GovernmentReporterMCP
from governmentreporter.server.config import ServerConfig, get_config, set_config
from governmentreporter.utils.config import get_openai_api_key

# Configure logging
def setup_logging(log_level: str = "INFO") -> None:
    """
    Set up logging configuration for the server.

    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR).
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            # Optionally add file handler
            # logging.FileHandler('mcp_server.log')
        ]
    )


async def main(config: Optional[ServerConfig] = None) -> None:
    """
    Main entry point for the MCP server.

    This function:
    1. Validates required environment variables
    2. Creates and configures the MCP server
    3. Starts the server and handles shutdown

    Args:
        config: Optional ServerConfig instance. Uses factory singleton if not provided.

    Raises:
        EnvironmentError: If required environment variables are missing.
    """
    # Use provided config or get singleton from factory
    if config is None:
        config = get_config()
    else:
        # If custom config provided, set it as the singleton
        set_config(config)

    # Set up logging
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("GovernmentReporter MCP Server")
    logger.info(f"Version: {config.server_version}")
    logger.info("=" * 60)

    # Validate environment
    try:
        api_key = get_openai_api_key()
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable is required")
        logger.info("✓ OpenAI API key found")
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        logger.error("Please set required environment variables in .env file")
        sys.exit(1)

    # Create MCP server instance
    server = GovernmentReporterMCP(config)

    # Set up signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {sig}, initiating shutdown...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize server
        logger.info("Initializing MCP server...")
        await server.initialize()
        logger.info("✓ Server initialized successfully")

        # Start server
        logger.info("Starting MCP server...")
        logger.info(f"Server is ready to accept connections")
        logger.info("-" * 60)

        # Run server with shutdown handling
        server_task = asyncio.create_task(server.start())
        shutdown_task = asyncio.create_task(shutdown_event.wait())

        # Wait for either server error or shutdown signal
        done, pending = await asyncio.wait(
            [server_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Graceful shutdown
        logger.info("Shutting down server...")
        await server.shutdown()
        logger.info("✓ Server shutdown complete")


def run_server() -> None:
    """
    Synchronous wrapper to run the async server.

    This function provides a simple way to start the server
    from synchronous code or scripts.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"\n✗ Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    """
    Script entry point when run directly.

    Examples:
        $ python server.py
        $ python -m governmentreporter.server
    """
    print("\n" + "=" * 60)
    print("Starting GovernmentReporter MCP Server")
    print("=" * 60 + "\n")

    # Check for help flag
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print(__doc__)
        sys.exit(0)

    # Run the server
    run_server()