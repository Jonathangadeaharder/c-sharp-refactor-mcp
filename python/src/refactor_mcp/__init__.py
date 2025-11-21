"""
Refactor MCP - Multi-language refactoring MCP server.

Production-ready server powered by FastMCP 2.0.
"""

from .server import create_server

__version__ = "2.0.0"
__all__ = ["create_server"]
