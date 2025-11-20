"""
LSP client pool for managing multiple language server connections.

Provides connection pooling and lifecycle management for LSP clients.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional

from ..config import Config, LspServerConfig
from ..models import Language
from .lsp import LspClient, LspError

logger = logging.getLogger(__name__)


class LspClientPool:
    """
    Pool of LSP clients for different languages.

    Manages lifecycle of multiple language server connections,
    with lazy initialization and automatic cleanup.
    """

    def __init__(self, config: Config):
        """
        Initialize LSP client pool.

        Args:
            config: Application configuration
        """
        self.config = config
        self._clients: Dict[str, LspClient] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

        logger.info("LSP client pool initialized")

    async def start(self) -> None:
        """Start the pool (pre-initialize clients if needed)."""
        logger.info("LSP client pool started")

    async def stop(self) -> None:
        """Stop all LSP clients and clean up."""
        logger.info("Stopping all LSP clients...")

        # Stop all active clients
        stop_tasks = [client.stop() for client in self._clients.values()]
        await asyncio.gather(*stop_tasks, return_exceptions=True)

        self._clients.clear()
        self._locks.clear()

        logger.info("LSP client pool stopped")

    async def get_client(
        self,
        language: Language | str,
        workspace_root: str | Path,
    ) -> LspClient:
        """
        Get or create an LSP client for a language.

        Args:
            language: Language name
            workspace_root: Workspace root directory

        Returns:
            LSP client instance

        Raises:
            LspError: If language server not configured or unavailable
        """
        language_str = language.value if isinstance(language, Language) else language

        # Get or create lock for this language
        if language_str not in self._locks:
            self._locks[language_str] = asyncio.Lock()

        async with self._locks[language_str]:
            # Check if client already exists
            client_key = f"{language_str}:{workspace_root}"
            if client_key in self._clients:
                logger.debug(f"Reusing existing LSP client: {client_key}")
                return self._clients[client_key]

            # Get server configuration
            server_config = self.config.lsp_servers.get(language_str)
            if not server_config:
                raise LspError(
                    f"Language server not configured for: {language_str}. "
                    f"Please add configuration in LSP_SERVERS environment variable."
                )

            # Create new client
            logger.info(f"Creating new LSP client: {client_key}")
            client = LspClient(
                language=language_str,
                command=server_config.command,
                args=server_config.args,
                workspace_root=workspace_root,
                timeout=server_config.timeout,
            )

            # Start the client
            try:
                await client.start()
                self._clients[client_key] = client
                return client
            except Exception as e:
                logger.error(f"Failed to start LSP client for {language_str}: {e}")
                raise LspError(f"Failed to start language server: {e}")

    async def close_client(self, language: Language | str, workspace_root: str | Path) -> None:
        """
        Close a specific LSP client.

        Args:
            language: Language name
            workspace_root: Workspace root directory
        """
        language_str = language.value if isinstance(language, Language) else language
        client_key = f"{language_str}:{workspace_root}"

        if client_key in self._clients:
            logger.info(f"Closing LSP client: {client_key}")
            client = self._clients.pop(client_key)
            await client.stop()

    async def close_workspace(self, workspace_root: str | Path) -> None:
        """
        Close all LSP clients for a workspace.

        Args:
            workspace_root: Workspace root directory
        """
        workspace_str = str(Path(workspace_root).resolve())
        clients_to_close = [
            key for key in self._clients.keys() if workspace_str in key
        ]

        logger.info(f"Closing {len(clients_to_close)} LSP clients for workspace: {workspace_root}")

        for client_key in clients_to_close:
            client = self._clients.pop(client_key)
            await client.stop()

    def get_active_clients(self) -> Dict[str, LspClient]:
        """
        Get all active LSP clients.

        Returns:
            Dictionary of client_key -> LspClient
        """
        return self._clients.copy()

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all active clients.

        Returns:
            Dictionary of client_key -> is_healthy
        """
        health = {}
        for client_key, client in self._clients.items():
            try:
                # Simple check: is process still running?
                is_healthy = (
                    client._process is not None
                    and client._process.returncode is None
                    and client._initialized
                )
                health[client_key] = is_healthy
            except Exception as e:
                logger.error(f"Health check failed for {client_key}: {e}")
                health[client_key] = False

        return health

    async def restart_client(
        self,
        language: Language | str,
        workspace_root: str | Path,
    ) -> LspClient:
        """
        Restart an LSP client.

        Args:
            language: Language name
            workspace_root: Workspace root directory

        Returns:
            New LSP client instance
        """
        # Close existing client
        await self.close_client(language, workspace_root)

        # Create new client
        return await self.get_client(language, workspace_root)

    def get_supported_languages(self) -> list[str]:
        """
        Get list of supported languages.

        Returns:
            List of language names with configured servers
        """
        return list(self.config.lsp_servers.keys())

    def is_language_supported(self, language: Language | str) -> bool:
        """
        Check if a language is supported.

        Args:
            language: Language name

        Returns:
            True if language server is configured
        """
        language_str = language.value if isinstance(language, Language) else language
        return language_str in self.config.lsp_servers

    def __repr__(self) -> str:
        """String representation."""
        return f"LspClientPool(active={len(self._clients)}, supported={len(self.config.lsp_servers)})"
