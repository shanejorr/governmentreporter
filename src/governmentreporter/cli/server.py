"""
MCP server CLI command.

Starts the Model Context Protocol server for LLM integration.
"""

import asyncio
import logging
import sys
from pathlib import Path

import click

from ..server.mcp_server import create_and_run_server


@click.command()
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="Set logging level",
)
def server(log_level):
    """
    Start the MCP server for LLM integration.

    This server exposes semantic search tools for government documents
    to Large Language Models via the Model Context Protocol.

    Example:
        governmentreporter server
        governmentreporter server --log-level DEBUG
    """
    # Configure logging to FILE ONLY (not console) for MCP stdio compatibility
    # MCP uses stdin/stdout for JSON-RPC, so console logging breaks the protocol
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Remove ALL existing handlers from root logger and all child loggers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Also remove handlers from all existing loggers
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        logger_obj = logging.getLogger(logger_name)
        if hasattr(logger_obj, "handlers"):
            for handler in logger_obj.handlers[:]:
                logger_obj.removeHandler(handler)

    # Add file handler only
    file_handler = logging.FileHandler(logs_dir / "mcp_server.log", mode="a")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root_logger.addHandler(file_handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent propagation of logging to stderr
    logging.raiseExceptions = False

    try:
        # Run the async server
        asyncio.run(create_and_run_server())
    except KeyboardInterrupt:
        click.echo("\n\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
