"""
Go dst client for Go code refactoring.

Uses the Go dst CLI tool (python/go_dst_cli) to perform refactoring operations
on Go code using the dst (Decorated Syntax Tree) library, which preserves
comments and formatting.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from ..models import (
    DiagnosticInfo,
    DiagnosticSeverity,
    Language,
    ReferenceInfo,
    RenameResult,
    SymbolInfo,
    SymbolKind,
)

logger = logging.getLogger(__name__)


class GoDstError(Exception):
    """Go dst operation error."""

    def __init__(self, message: str, code: str = "GO_DST_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class GoDstClient:
    """
    Client for Go code refactoring using dst library.

    This client communicates with the Go dst CLI tool via JSON stdin/stdout.
    The CLI tool uses the dst library to preserve comments and formatting
    during refactoring operations.

    Performance: ~20-30ms overhead for subprocess communication.
    """

    def __init__(self, cli_path: Path | None = None):
        """
        Initialize the Go dst client.

        Args:
            cli_path: Path to the go-dst-cli executable.
                     If None, uses python/go_dst_cli/bin/go-dst-cli
        """
        if cli_path is None:
            # Default to the CLI in the project
            cli_path = Path(__file__).parent.parent.parent.parent / "go_dst_cli" / "bin" / "go-dst-cli"

        self.cli_path = cli_path

        if not self.cli_path.exists():
            raise GoDstError(
                f"Go dst CLI not found at {self.cli_path}. "
                f"Build it with: cd python/go_dst_cli && ./build.sh",
                "CLI_NOT_FOUND"
            )

        logger.info(f"Go dst client initialized with CLI at {self.cli_path}")

    async def _execute_command(self, command: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a command via the Go dst CLI.

        Args:
            command: Command name (e.g., "rename_symbol")
            parameters: Command parameters

        Returns:
            Command result dictionary

        Raises:
            GoDstError: If the command fails
        """
        request = {
            "command": command,
            "parameters": parameters
        }

        try:
            process = await asyncio.create_subprocess_exec(
                str(self.cli_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate(json.dumps(request).encode())

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise GoDstError(
                    f"Go dst CLI failed: {error_msg}",
                    "CLI_ERROR"
                )

            response = json.loads(stdout.decode())

            if not response.get("success"):
                error = response.get("error", {})
                raise GoDstError(
                    error.get("message", "Unknown error"),
                    error.get("code", "UNKNOWN_ERROR")
                )

            return response.get("result", {})

        except json.JSONDecodeError as e:
            raise GoDstError(f"Invalid JSON response: {e}", "INVALID_RESPONSE")
        except Exception as e:
            if isinstance(e, GoDstError):
                raise
            raise GoDstError(f"Failed to execute command: {e}", "EXECUTION_ERROR")

    async def load_project(self, project_path: str | Path) -> dict[str, Any]:
        """
        Load a Go project and return information about it.

        Args:
            project_path: Path to the Go project (module root)

        Returns:
            Dictionary with project information:
            - project_path: Resolved project path
            - file_count: Number of .go files
            - files: List of .go file paths
        """
        project_path = str(Path(project_path).resolve())

        result = await self._execute_command("load_project", {
            "project_path": project_path
        })

        logger.info(f"Loaded Go project: {result.get('file_count', 0)} files")
        return result

    async def get_diagnostics(
        self,
        project_path: str | Path | None = None,
        file_path: str | Path | None = None
    ) -> list[DiagnosticInfo]:
        """
        Get diagnostics (errors/warnings) for a file or project.

        Args:
            project_path: Path to the project (for project-wide diagnostics)
            file_path: Path to specific file (for file-level diagnostics)

        Returns:
            List of diagnostic information
        """
        params = {}
        if project_path:
            params["project_path"] = str(Path(project_path).resolve())
        if file_path:
            params["file_path"] = str(Path(file_path).resolve())

        result = await self._execute_command("get_diagnostics", params)

        diagnostics = []
        for diag in result.get("diagnostics", []):
            diagnostics.append(DiagnosticInfo(
                file_path=diag["file_path"],
                line=diag["line"],
                column=diag["column"],
                end_line=diag.get("end_line", diag["line"]),
                end_column=diag.get("end_column", diag["column"] + 1),
                severity=DiagnosticSeverity(diag.get("severity", "error")),
                message=diag["message"],
                code=diag.get("code"),
            ))

        return diagnostics

    async def find_references(
        self,
        project_path: str | Path,
        file_path: str | Path,
        line: int,
        column: int
    ) -> list[ReferenceInfo]:
        """
        Find all references to a symbol.

        Args:
            project_path: Path to the project root
            file_path: Path to the file containing the symbol
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            List of reference locations
        """
        result = await self._execute_command("find_references", {
            "project_path": str(Path(project_path).resolve()),
            "file_path": str(Path(file_path).resolve()),
            "line": line,
            "column": column,
        })

        references = []
        for ref in result.get("references", []):
            references.append(ReferenceInfo(
                file_path=ref["file_path"],
                line=ref["line"],
                column=ref["column"],
                line_text=ref.get("line_text", ""),
                is_definition=ref.get("is_definition", False),
            ))

        return references

    async def rename_symbol(
        self,
        project_path: str | Path,
        file_path: str | Path,
        line: int,
        column: int,
        new_name: str
    ) -> RenameResult:
        """
        Rename a symbol across the entire project.

        Uses dst to preserve comments and formatting.

        Args:
            project_path: Path to the project root
            file_path: Path to the file containing the symbol
            line: Line number (1-based)
            column: Column number (1-based)
            new_name: New name for the symbol

        Returns:
            RenameResult with file changes
        """
        result = await self._execute_command("rename_symbol", {
            "project_path": str(Path(project_path).resolve()),
            "file_path": str(Path(file_path).resolve()),
            "line": line,
            "column": column,
            "new_name": new_name,
        })

        # Extract file changes
        file_changes = {}
        for change in result.get("changes", []):
            file_changes[change["file_path"]] = {
                "old_text": change.get("original_text", ""),
                "new_text": change.get("modified_text", ""),
            }

        return RenameResult(
            success=True,
            new_name=new_name,
            file_changes=file_changes,
            message=f"Renamed to '{new_name}' in {len(file_changes)} file(s)"
        )

    async def get_symbol_info(
        self,
        project_path: str | Path,
        file_path: str | Path,
        line: int,
        column: int
    ) -> SymbolInfo:
        """
        Get information about a symbol at a specific location.

        Args:
            project_path: Path to the project root
            file_path: Path to the file
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            Symbol information
        """
        result = await self._execute_command("get_symbol_info", {
            "project_path": str(Path(project_path).resolve()),
            "file_path": str(Path(file_path).resolve()),
            "line": line,
            "column": column,
        })

        # Map Go kinds to our SymbolKind enum
        kind_map = {
            "function": SymbolKind.FUNCTION,
            "variable": SymbolKind.VARIABLE,
            "constant": SymbolKind.CONSTANT,
            "type": SymbolKind.CLASS,  # Go types map to class
            "package": SymbolKind.NAMESPACE,
            "identifier": SymbolKind.VARIABLE,
        }

        go_kind = result.get("kind", "identifier")
        kind = kind_map.get(go_kind, SymbolKind.VARIABLE)

        return SymbolInfo(
            name=result.get("name", ""),
            kind=kind,
            location={
                "file_path": result.get("file_path", ""),
                "line": result.get("line", 0),
                "column": result.get("column", 0),
            },
            documentation=result.get("documentation"),
        )


# Module-level instance for convenience (optional)
_go_dst_client: GoDstClient | None = None


def get_go_dst_client() -> GoDstClient:
    """Get or create the global Go dst client instance."""
    global _go_dst_client
    if _go_dst_client is None:
        _go_dst_client = GoDstClient()
    return _go_dst_client
