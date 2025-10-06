"""
MCP server CLI command.

Starts the Model Context Protocol server for LLM integration.
"""

import asyncio
import logging
import sys

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
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        # Run the async server
        asyncio.run(create_and_run_server())
    except KeyboardInterrupt:
        click.echo("\n\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
