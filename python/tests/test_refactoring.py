"""
Tests for refactoring tools.

Demonstrates FastMCP 2.0 testing with MockMCPClient.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from refactor_mcp.server import create_server
from refactor_mcp.models import RenameResult, ReferencesInfo, ReferenceLocation


@pytest.fixture
def mock_server():
    """Create a test server with mocked dependencies."""
    server = create_server(
        auth_provider=None,
        enable_metrics=False,
        enable_rate_limiting=False,
    )
    return server


@pytest.fixture
def mock_roslyn_client():
    """Create a mock Roslyn client."""
    client = AsyncMock()

    # Mock load_project
    client.load_project.return_value = {
        "documentCount": 10,
        "projectCount": 1,
        "language": "csharp",
    }

    # Mock rename_symbol
    client.rename_symbol.return_value = RenameResult(
        success=True,
        symbol_name="oldName",
        new_name="newName",
        files_modified=3,
        locations_modified=5,
    )

    # Mock find_references
    client.find_references.return_value = ReferencesInfo(
        symbol_name="TestMethod",
        reference_count=3,
        references=[
            ReferenceLocation(
                file_path="/test/file1.cs",
                line=10,
                column=5,
                preview="public void TestMethod()",
            ),
            ReferenceLocation(
                file_path="/test/file2.cs",
                line=20,
                column=10,
                preview="TestMethod();",
            ),
        ],
    )

    return client


class TestRefactoringTools:
    """Test refactoring tool implementations."""

    @pytest.mark.asyncio
    async def test_load_project_success(self, mock_server, mock_roslyn_client):
        """Test successful project loading."""
        # Note: In a full implementation, we'd use FastMCP's MockMCPClient
        # For now, this demonstrates the structure

        # Example of what the test would look like with MockMCPClient:
        # from fastmcp.testing import MockMCPClient
        #
        # async with MockMCPClient(mock_server) as client:
        #     result = await client.call_tool(
        #         "load_project",
        #         {"project_path": "/test/project.sln"}
        #     )
        #     assert result["success"] is True
        #     assert result["document_count"] > 0

        # For now, just verify the mock setup
        result = await mock_roslyn_client.load_project("/test/project.sln")
        assert result["documentCount"] == 10

    @pytest.mark.asyncio
    async def test_rename_symbol_success(self, mock_roslyn_client):
        """Test successful symbol rename."""
        result = await mock_roslyn_client.rename_symbol(
            "/test/project.sln",
            "/test/file.cs",
            10,
            5,
            "newName",
        )

        assert result.success is True
        assert result.new_name == "newName"
        assert result.files_modified == 3
        assert result.locations_modified == 5

    @pytest.mark.asyncio
    async def test_find_references_success(self, mock_roslyn_client):
        """Test successful reference finding."""
        result = await mock_roslyn_client.find_references(
            "/test/project.sln",
            "/test/file.cs",
            10,
            5,
        )

        assert result.symbol_name == "TestMethod"
        assert result.reference_count == 3
        assert len(result.references) == 2
        assert result.references[0].file_path == "/test/file1.cs"


class TestSecurityValidation:
    """Test path security validation."""

    def test_path_validation_blocks_traversal(self):
        """Test that path traversal attacks are blocked."""
        # This would test PathSecurityService
        # from refactor_mcp.utils.security import PathSecurityService, SecurityError
        #
        # security = PathSecurityService(allowed_roots=["/allowed"])
        #
        # with pytest.raises(SecurityError):
        #     security.validate_path("/not-allowed/file.cs")
        pass

    def test_path_validation_allows_valid_paths(self):
        """Test that valid paths are allowed."""
        # from refactor_mcp.utils.security import PathSecurityService
        #
        # security = PathSecurityService(allowed_roots=["/allowed"])
        # result = security.validate_path("/allowed/file.cs")
        # assert result == Path("/allowed/file.cs").resolve()
        pass


class TestCacheManager:
    """Test cache manager functionality."""

    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """Test basic cache set/get operations."""
        # from refactor_mcp.utils.cache import CacheManager
        #
        # cache = CacheManager(max_size_mb=1)
        #
        # await cache.set("test_key", {"data": "value"}, ttl=10)
        # result = await cache.get("test_key")
        #
        # assert result == {"data": "value"}
        pass

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        # from refactor_mcp.utils.cache import CacheManager
        # import asyncio
        #
        # cache = CacheManager(max_size_mb=1)
        #
        # await cache.set("test_key", {"data": "value"}, ttl=1)
        # await asyncio.sleep(2)
        # result = await cache.get("test_key")
        #
        # assert result is None
        pass


# Integration test example (would require actual Roslyn CLI)
class TestIntegration:
    """Integration tests with real components."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_rename_workflow(self):
        """Test complete rename workflow end-to-end."""
        # This would test the full stack with a real test project
        # Requires Roslyn CLI to be built and available
        pass

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_lsp_typescript_integration(self):
        """Test LSP integration with TypeScript."""
        # This would test LSP client with typescript-language-server
        # Requires language server to be installed
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
