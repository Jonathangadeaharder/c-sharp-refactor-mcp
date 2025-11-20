"""
Tests for TypeScript ts-morph client integration.
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from refactor_mcp.clients.ts_morph import TsMorphClient, TsMorphError


@pytest.fixture
def mock_cli_path(tmp_path):
    """Create a mock CLI path."""
    cli_path = tmp_path / "ts_morph_cli" / "dist" / "index.js"
    cli_path.parent.mkdir(parents=True)
    cli_path.write_text("// mock CLI")
    return cli_path


@pytest.fixture
def ts_morph_client(mock_cli_path):
    """Create ts-morph client with mock CLI path."""
    return TsMorphClient(cli_path=mock_cli_path)


@pytest.mark.asyncio
async def test_get_version(ts_morph_client):
    """Test getting CLI version."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        # Mock process
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(
                json.dumps({
                    "success": True,
                    "result": {
                        "version": "1.0.0",
                        "ts_morph_version": "^21.0.1",
                        "typescript_version": "^5.3.3"
                    }
                }).encode(),
                b""
            )
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        result = await ts_morph_client.get_version()

        assert result["version"] == "1.0.0"
        assert "ts_morph_version" in result
        assert "typescript_version" in result


@pytest.mark.asyncio
async def test_load_project(ts_morph_client):
    """Test loading a TypeScript project."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(
                json.dumps({
                    "success": True,
                    "result": {
                        "project_path": "/test/project",
                        "file_count": 10,
                        "files": ["file1.ts", "file2.ts"]
                    }
                }).encode(),
                b""
            )
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        result = await ts_morph_client.load_project("/test/project")

        assert result["project_path"] == "/test/project"
        assert result["file_count"] == 10
        assert len(result["files"]) == 2


@pytest.mark.asyncio
async def test_get_diagnostics(ts_morph_client):
    """Test getting TypeScript diagnostics."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(
                json.dumps({
                    "success": True,
                    "result": {
                        "diagnostics": [
                            {
                                "file_path": "/test/file.ts",
                                "line": 10,
                                "column": 5,
                                "end_line": 10,
                                "end_column": 15,
                                "severity": "error",
                                "message": "Type 'string' is not assignable to type 'number'",
                                "code": "2322"
                            }
                        ]
                    }
                }).encode(),
                b""
            )
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        diagnostics = await ts_morph_client.get_diagnostics("/test/project", "/test/file.ts")

        assert len(diagnostics) == 1
        assert diagnostics[0].severity == "error"
        assert diagnostics[0].code == "2322"


@pytest.mark.asyncio
async def test_find_references(ts_morph_client):
    """Test finding references to a symbol."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(
                json.dumps({
                    "success": True,
                    "result": {
                        "references": [
                            {
                                "file_path": "/test/file1.ts",
                                "line": 5,
                                "column": 10,
                                "line_text": "const x = myFunction();",
                                "is_definition": False
                            },
                            {
                                "file_path": "/test/file2.ts",
                                "line": 20,
                                "column": 15,
                                "line_text": "function myFunction() {",
                                "is_definition": True
                            }
                        ]
                    }
                }).encode(),
                b""
            )
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        references = await ts_morph_client.find_references(
            "/test/project", "/test/file.ts", 10, 15
        )

        assert len(references) == 2
        assert references[0].file_path == "/test/file1.ts"
        assert references[1].is_definition is True


@pytest.mark.asyncio
async def test_rename_symbol(ts_morph_client):
    """Test renaming a symbol."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(
                json.dumps({
                    "success": True,
                    "result": {
                        "changes": [
                            {
                                "file_path": "/test/file1.ts",
                                "original_text": "function oldName() {}",
                                "modified_text": "function newName() {}"
                            },
                            {
                                "file_path": "/test/file2.ts",
                                "original_text": "oldName();",
                                "modified_text": "newName();"
                            }
                        ]
                    }
                }).encode(),
                b""
            )
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        result = await ts_morph_client.rename_symbol(
            "/test/project", "/test/file.ts", 10, 15, "newName"
        )

        assert result.success is True
        assert len(result.changes) == 2
        assert result.changes[0]["file_path"] == "/test/file1.ts"


@pytest.mark.asyncio
async def test_get_symbol_info(ts_morph_client):
    """Test getting symbol information."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(
                json.dumps({
                    "success": True,
                    "result": {
                        "name": "myFunction",
                        "kind": "FunctionDeclaration",
                        "file_path": "/test/file.ts",
                        "line": 10,
                        "column": 15,
                        "definition_file": "/test/file.ts",
                        "definition_line": 5,
                        "definition_column": 10,
                        "documentation": "This is my function"
                    }
                }).encode(),
                b""
            )
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        symbol_info = await ts_morph_client.get_symbol_info(
            "/test/project", "/test/file.ts", 10, 15
        )

        assert symbol_info.name == "myFunction"
        assert symbol_info.kind == "FunctionDeclaration"
        assert symbol_info.documentation == "This is my function"


@pytest.mark.asyncio
async def test_extract_method(ts_morph_client):
    """Test extracting a method."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(
                json.dumps({
                    "success": True,
                    "result": {
                        "changes": [
                            {
                                "file_path": "/test/file.ts",
                                "original_text": "function foo() { const x = 1; const y = 2; }",
                                "modified_text": "function foo() { extracted(); }\n\nfunction extracted() { const x = 1; const y = 2; }"
                            }
                        ],
                        "extracted_method_name": "extracted"
                    }
                }).encode(),
                b""
            )
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        result = await ts_morph_client.extract_method(
            "/test/project", "/test/file.ts",
            10, 5, 12, 10, "extracted"
        )

        assert result.success is True
        assert len(result.changes) == 1
        assert result.extracted_method_name == "extracted"


@pytest.mark.asyncio
async def test_cli_error_handling(ts_morph_client):
    """Test error handling when CLI returns error."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(
                json.dumps({
                    "success": False,
                    "error": {
                        "message": "Symbol not found",
                        "code": "SYMBOL_NOT_FOUND"
                    }
                }).encode(),
                b""
            )
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        with pytest.raises(TsMorphError) as exc_info:
            await ts_morph_client.get_symbol_info(
                "/test/project", "/test/file.ts", 10, 15
            )

        assert exc_info.value.code == "SYMBOL_NOT_FOUND"
        assert "Symbol not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cli_not_found():
    """Test error when CLI is not found."""
    with pytest.raises(TsMorphError) as exc_info:
        TsMorphClient(cli_path=Path("/nonexistent/path"))

    assert exc_info.value.code == "CLI_NOT_FOUND"


@pytest.mark.asyncio
async def test_invalid_json_response(ts_morph_client):
    """Test error handling for invalid JSON response."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"invalid json", b"")
        )
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        with pytest.raises(TsMorphError) as exc_info:
            await ts_morph_client.get_version()

        assert exc_info.value.code == "INVALID_JSON"


@pytest.mark.asyncio
async def test_node_not_found(ts_morph_client):
    """Test error when Node.js is not installed."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_exec.side_effect = FileNotFoundError("node not found")

        with pytest.raises(TsMorphError) as exc_info:
            await ts_morph_client.get_version()

        assert exc_info.value.code == "NODE_NOT_FOUND"
