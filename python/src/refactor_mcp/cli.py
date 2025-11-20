#!/usr/bin/env python3
"""
CLI entry point for refactor-mcp server.

Usage:
    python -m refactor_mcp.cli
    refactor-mcp (if installed)
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .server import create_server


def setup_logging(level: str = "INFO") -> None:
    """
    Configure logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
        ],
    )


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Refactor MCP - Multi-language semantic refactoring server"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--no-rate-limit",
        action="store_true",
        help="Disable rate limiting",
    )

    parser.add_argument(
        "--no-metrics",
        action="store_true",
        help="Disable metrics and tracing",
    )

    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for SSE transport (default: 8000)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    logger = logging.getLogger(__name__)
    logger.info("Starting refactor-mcp server...")

    # Create server
    server = create_server(
        auth_provider=None,  # Can be configured via environment
        enable_metrics=not args.no_metrics,
        enable_rate_limiting=not args.no_rate_limit,
    )

    # Run server
    try:
        if args.transport == "stdio":
            logger.info("Running with stdio transport")
            server.run(transport="stdio")
        else:
            logger.info(f"Running with SSE transport on port {args.port}")
            server.run(transport="sse", port=args.port)
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
