"""
Configuration management for refactor-mcp server.

Loads configuration from environment variables and config files.
"""

import os
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LspServerConfig(BaseModel):
    """Configuration for a single LSP server."""

    command: str = Field(description="LSP server command")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    workspace_folders: bool = Field(
        default=True, description="Whether server supports workspace folders"
    )


class Config(BaseSettings):
    """Main application configuration."""

    # Server settings
    server_name: str = Field(default="refactor-mcp", description="Server name")
    server_version: str = Field(default="2.0.0", description="Server version")
    log_level: str = Field(default="INFO", description="Logging level")

    # Security settings
    allowed_root_paths: List[str] = Field(
        default_factory=lambda: [
            str(Path.home() / "projects"),
            "/workspace",
        ],
        description="Allowed root paths for file access",
    )

    # Cache settings
    cache_max_size_mb: int = Field(
        default=4096, description="Maximum cache size in MB"
    )
    cache_ttl_seconds: int = Field(
        default=3600, description="Cache TTL in seconds"
    )

    # Roslyn settings
    roslyn_cli_path: str | None = Field(
        default=None,
        description="Path to Roslyn CLI executable (for C#/VB.NET support)",
    )
    roslyn_timeout_seconds: int = Field(
        default=120, description="Roslyn operation timeout"
    )

    # LSP server configurations
    lsp_servers: Dict[str, LspServerConfig] = Field(
        default_factory=lambda: {
            "typescript": LspServerConfig(
                command="typescript-language-server",
                args=["--stdio"],
            ),
            "python": LspServerConfig(
                command="pyright-langserver",
                args=["--stdio"],
            ),
            "go": LspServerConfig(
                command="gopls",
                args=[],
            ),
            "cpp": LspServerConfig(
                command="clangd",
                args=["--background-index"],
            ),
            "java": LspServerConfig(
                command="jdtls",
                args=[],
            ),
            "rust": LspServerConfig(
                command="rust-analyzer",
                args=[],
            ),
        },
        description="LSP server configurations by language",
    )

    # OAuth settings (FastMCP handles these automatically)
    github_client_id: str | None = Field(default=None, description="GitHub OAuth client ID")
    github_client_secret: str | None = Field(
        default=None, description="GitHub OAuth client secret"
    )
    google_client_id: str | None = Field(default=None, description="Google OAuth client ID")
    google_client_secret: str | None = Field(
        default=None, description="Google OAuth client secret"
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(
        default=100, description="Requests per minute limit"
    )
    rate_limit_burst_size: int = Field(default=20, description="Burst size")

    # Observability
    enable_metrics: bool = Field(default=True, description="Enable metrics")
    enable_tracing: bool = Field(default=True, description="Enable tracing")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="REFACTOR_MCP_",
        case_sensitive=False,
    )

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment and config files."""
        # Try to find Roslyn CLI automatically
        roslyn_cli_path = cls._find_roslyn_cli()

        config = cls()

        if roslyn_cli_path and not config.roslyn_cli_path:
            config.roslyn_cli_path = str(roslyn_cli_path)

        return config

    @staticmethod
    def _find_roslyn_cli() -> Path | None:
        """Try to find Roslyn CLI automatically."""
        # Check common locations
        search_paths = [
            # Relative to Python project (published self-contained)
            Path(__file__).parent.parent.parent / "roslyn_cli" / "bin" / "roslyn-cli",
            Path(__file__).parent.parent.parent / "roslyn_cli" / "bin" / "roslyn-cli.exe",
            # Relative to Python project (dotnet build output)
            Path(__file__).parent.parent.parent / "roslyn_cli" / "bin" / "Release" / "net8.0" / "roslyn-cli",
            Path(__file__).parent.parent.parent / "roslyn_cli" / "bin" / "Debug" / "net8.0" / "roslyn-cli",
            # Legacy name (for backwards compatibility)
            Path(__file__).parent.parent.parent / "roslyn_cli" / "bin" / "RoslynCLI",
            Path(__file__).parent.parent.parent / "roslyn_cli" / "bin" / "RoslynCLI.exe",
            # In PATH
            *[Path(p) / "roslyn-cli" for p in os.environ.get("PATH", "").split(os.pathsep) if p],
        ]

        for path in search_paths:
            if path.exists() and path.is_file():
                return path

        return None

    def get_lsp_config(self, language: str) -> LspServerConfig | None:
        """Get LSP server configuration for a language."""
        return self.lsp_servers.get(language)
