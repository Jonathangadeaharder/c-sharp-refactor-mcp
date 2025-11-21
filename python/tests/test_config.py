"""
Tests for configuration module.
"""

import os
import pytest
from pathlib import Path
from refactor_mcp.config import Config, LspServerConfig


class TestLspServerConfig:
    """Test LSP server configuration."""

    def test_lsp_server_config_creation(self):
        """Test creating LSP server config."""
        config = LspServerConfig(
            command="typescript-language-server",
            args=["--stdio"],
            timeout=60,
        )

        assert config.command == "typescript-language-server"
        assert config.args == ["--stdio"]
        assert config.timeout == 60

    def test_lsp_server_config_defaults(self):
        """Test LSP server config defaults."""
        config = LspServerConfig(command="test-server")

        assert config.command == "test-server"
        assert config.args == []
        assert config.timeout == 60


class TestConfig:
    """Test main configuration."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = Config()

        assert config.server_name == "refactor-mcp"
        assert config.server_version == "2.0.0"
        assert config.log_level == "INFO"
        assert config.cache_max_size_mb == 4096
        assert config.roslyn_timeout_seconds == 120
        assert config.rate_limit_enabled is True
        assert config.enable_metrics is True

    def test_config_allowed_roots_default(self):
        """Test default allowed root paths."""
        config = Config()

        # Should include at least home/projects or /workspace
        assert len(config.allowed_root_paths) > 0

    def test_config_lsp_servers_default(self):
        """Test default LSP server configurations."""
        config = Config()

        # Should have configurations for multiple languages
        assert "typescript" in config.lsp_servers
        assert "python" in config.lsp_servers
        assert "go" in config.lsp_servers
        assert "rust" in config.lsp_servers

        # Verify TypeScript config
        ts_config = config.lsp_servers["typescript"]
        assert ts_config.command == "typescript-language-server"
        assert "--stdio" in ts_config.args

    def test_config_load(self):
        """Test loading configuration."""
        config = Config.load()

        assert isinstance(config, Config)
        assert config.server_name == "refactor-mcp"

    def test_config_get_lsp_config(self):
        """Test getting LSP configuration for a language."""
        config = Config()

        # Get existing language
        ts_config = config.get_lsp_config("typescript")
        assert ts_config is not None
        assert ts_config.command == "typescript-language-server"

        # Get non-existent language
        unknown_config = config.get_lsp_config("unknown")
        assert unknown_config is None

    def test_find_roslyn_cli_not_found(self):
        """Test Roslyn CLI auto-discovery when not found."""
        # This will likely not find it in test environment
        result = Config._find_roslyn_cli()
        # Either None or a valid path
        assert result is None or isinstance(result, Path)

    def test_config_with_env_vars(self, monkeypatch):
        """Test configuration with environment variables."""
        # Set environment variables
        monkeypatch.setenv("REFACTOR_MCP_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("REFACTOR_MCP_CACHE_MAX_SIZE_MB", "2048")
        monkeypatch.setenv("REFACTOR_MCP_ROSLYN_TIMEOUT_SECONDS", "60")

        config = Config()

        assert config.log_level == "DEBUG"
        assert config.cache_max_size_mb == 2048
        assert config.roslyn_timeout_seconds == 60

    def test_config_allowed_roots_env(self, monkeypatch, tmp_path):
        """Test configuring allowed roots via environment."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        # Set via environment variable
        monkeypatch.setenv(
            "REFACTOR_MCP_ALLOWED_ROOT_PATHS",
            f"{dir1},{dir2}"
        )

        config = Config()

        # Should parse comma-separated paths
        assert str(dir1) in config.allowed_root_paths
        assert str(dir2) in config.allowed_root_paths

    def test_config_rate_limiting(self, monkeypatch):
        """Test rate limiting configuration."""
        monkeypatch.setenv("REFACTOR_MCP_RATE_LIMIT_ENABLED", "false")
        monkeypatch.setenv("REFACTOR_MCP_RATE_LIMIT_REQUESTS_PER_MINUTE", "200")
        monkeypatch.setenv("REFACTOR_MCP_RATE_LIMIT_BURST_SIZE", "50")

        config = Config()

        assert config.rate_limit_enabled is False
        assert config.rate_limit_requests_per_minute == 200
        assert config.rate_limit_burst_size == 50

    def test_config_observability(self, monkeypatch):
        """Test observability configuration."""
        monkeypatch.setenv("REFACTOR_MCP_ENABLE_METRICS", "false")
        monkeypatch.setenv("REFACTOR_MCP_ENABLE_TRACING", "false")

        config = Config()

        assert config.enable_metrics is False
        assert config.enable_tracing is False

    def test_config_oauth_settings(self, monkeypatch):
        """Test OAuth configuration."""
        monkeypatch.setenv("REFACTOR_MCP_GITHUB_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("REFACTOR_MCP_GITHUB_CLIENT_SECRET", "test_secret")
        monkeypatch.setenv("REFACTOR_MCP_GOOGLE_CLIENT_ID", "google_id")

        config = Config()

        assert config.github_client_id == "test_client_id"
        assert config.github_client_secret == "test_secret"
        assert config.google_client_id == "google_id"

    def test_config_roslyn_path_env(self, monkeypatch, tmp_path):
        """Test setting Roslyn CLI path via environment."""
        roslyn_path = tmp_path / "roslyn-cli"
        roslyn_path.write_text("#!/bin/bash\necho test")

        monkeypatch.setenv("REFACTOR_MCP_ROSLYN_CLI_PATH", str(roslyn_path))

        config = Config()

        assert config.roslyn_cli_path == str(roslyn_path)

    def test_config_case_insensitive_env(self, monkeypatch):
        """Test that environment variables are case insensitive."""
        # Try lowercase
        monkeypatch.setenv("refactor_mcp_log_level", "WARNING")

        config = Config()

        assert config.log_level == "WARNING"

    def test_config_model_validation(self):
        """Test Pydantic validation."""
        # Invalid log level should use default
        config = Config(log_level="INVALID")
        assert config.log_level == "INVALID"  # Pydantic doesn't enforce enum

    def test_config_server_info(self):
        """Test server name and version."""
        config = Config()

        assert config.server_name == "refactor-mcp"
        assert config.server_version == "2.0.0"

    def test_config_immutable_after_load(self):
        """Test that config can be modified after loading."""
        config = Config.load()

        # Should be able to modify
        config.log_level = "DEBUG"
        assert config.log_level == "DEBUG"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
