#!/usr/bin/env python3
"""
Enable running the MCP server as a Python module.

This module allows the MCP server to be run using:
    python -m governmentreporter.server

It executes the main server functionality.
"""

import asyncio
import logging

from .mcp_server import create_and_run_server

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the server
    asyncio.run(create_and_run_server())
