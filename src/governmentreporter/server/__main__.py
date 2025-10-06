#!/usr/bin/env python3
"""
Enable running the MCP server as a Python module.

This module allows the MCP server to be run using:
    python -m governmentreporter.server

It executes the main server functionality.
"""

import sys
import os

# Execute the server.py file directly
server_py_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py"
)

# Execute the server.py script
exec(compile(open(server_py_path).read(), server_py_path, "exec"))
