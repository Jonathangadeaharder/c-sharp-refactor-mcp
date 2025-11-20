"""
Main FastMCP server for multi-language refactoring.

This module implements the core MCP server using FastMCP 2.0,
providing production-ready features out of the box.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastmcp import FastMCP
from fastmcp.auth import OAuthProvider
from pydantic import BaseModel, Field

from .clients.lsp_pool import LspClientPool
from .clients.roslyn import RoslynClient
from .clients.ts_morph import TsMorphClient, TsMorphError
from .config import Config
from .models import AppContext
from .tools.refactoring import register_refactoring_tools
from .tools.analysis import register_analysis_tools
from .tools.diagnostics import register_diagnostic_tools
from .utils.security import PathSecurityService
from .utils.cache import CacheManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """
    Application lifespan manager.

    Handles startup and shutdown of resources:
    - LSP client pool
    - Roslyn client
    - Cache manager
    - Security service
    """
    logger.info("Starting refactor-mcp server...")

    # Load configuration
    config = Config.load()

    # Initialize services
    cache = CacheManager(max_size=config.cache_max_size_mb)
    security = PathSecurityService(allowed_roots=config.allowed_root_paths)

    # Initialize language clients
    lsp_pool = LspClientPool(config=config)
    await lsp_pool.start()

    roslyn_client: RoslynClient | None = None
    if config.roslyn_cli_path:
        roslyn_client = RoslynClient(
            cli_path=config.roslyn_cli_path,
            cache=cache,
        )
        await roslyn_client.start()
    else:
        logger.warning(
            "Roslyn CLI path not configured. C#/VB.NET refactoring will be unavailable."
        )

    # Initialize TypeScript ts-morph client
    ts_morph_client: TsMorphClient | None = None
    try:
        ts_morph_client = TsMorphClient()
        logger.info("ts-morph client initialized for TypeScript refactoring")
    except TsMorphError as e:
        logger.warning(
            f"ts-morph CLI not found: {e.message}. TypeScript native refactoring will be unavailable. "
            "Run: cd python/ts_morph_cli && ./build.sh"
        )

    # Create application context
    ctx = AppContext(
        config=config,
        cache=cache,
        security=security,
        lsp_pool=lsp_pool,
        roslyn_client=roslyn_client,
        ts_morph_client=ts_morph_client,
    )

    logger.info("Server started successfully")

    try:
        yield ctx
    finally:
        # Cleanup
        logger.info("Shutting down server...")

        if roslyn_client:
            await roslyn_client.stop()

        await lsp_pool.stop()

        logger.info("Server shut down successfully")


def create_server(
    auth_provider: OAuthProvider | None = None,
    enable_metrics: bool = True,
    enable_rate_limiting: bool = True,
) -> FastMCP:
    """
    Create and configure the FastMCP server.

    Args:
        auth_provider: Optional OAuth provider (GitHub, Google, etc.)
        enable_metrics: Enable observability metrics
        enable_rate_limiting: Enable rate limiting

    Returns:
        Configured FastMCP server instance
    """

    # Create server with lifespan
    mcp = FastMCP(
        "refactor-mcp",
        version="2.0.0",
        description="Multi-language semantic refactoring server",
        lifespan=lifespan,
    )

    # Configure authentication if provided
    if auth_provider:
        logger.info(f"Configuring OAuth with provider: {auth_provider}")
        # FastMCP 2.0 auto-configures OAuth
        mcp.auth = auth_provider

    # Configure observability
    if enable_metrics:
        mcp.enable_metrics = True
        mcp.enable_tracing = True
        logger.info("Metrics and tracing enabled")

    # Configure rate limiting
    if enable_rate_limiting:
        mcp.rate_limit = {
            "requests_per_minute": 100,
            "burst_size": 20,
        }
        logger.info("Rate limiting enabled: 100 req/min, burst 20")

    # Register tools
    register_refactoring_tools(mcp)
    register_analysis_tools(mcp)
    register_diagnostic_tools(mcp)

    logger.info("All tools registered")

    return mcp


# Export for CLI and testing
__all__ = ["create_server", "lifespan"]
