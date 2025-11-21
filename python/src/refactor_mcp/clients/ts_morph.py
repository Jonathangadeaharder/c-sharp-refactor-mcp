"""
TypeScript ts-morph CLI client for native TypeScript refactoring.

This client wraps the ts-morph CLI tool, providing Roslyn-level
refactoring capabilities for TypeScript projects.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.refactoring import (
    DiagnosticInfo,
    ReferenceInfo,
    RenameResult,
    SymbolInfo,
)

logger = logging.getLogger(__name__)


class TsMorphError(Exception):
    """Exception raised for ts-morph CLI errors."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class TsMorphClient:
    """
    Client for TypeScript refactoring using ts-morph.

    Communicates with the Node.js ts-morph CLI via JSON stdin/stdout protocol.
    """

    def __init__(self, cli_path: Optional[Path] = None):
        """
        Initialize ts-morph client.

        Args:
            cli_path: Path to ts-morph CLI executable (auto-detected if not provided)
        """
        self.cli_path = cli_path or self._find_cli_path()
        self._verify_cli()

    def _find_cli_path(self) -> Path:
        """
        Auto-detect ts-morph CLI location.

        Returns:
            Path to CLI executable

        Raises:
            TsMorphError: If CLI not found
        """
        # Try relative to this file
        current_dir = Path(__file__).parent.parent.parent.parent
        candidates = [
            current_dir / "ts_morph_cli" / "dist" / "index.js",
            Path.cwd() / "ts_morph_cli" / "dist" / "index.js",
            Path.home() / ".refactor-mcp" / "ts_morph_cli" / "dist" / "index.js",
        ]

        for candidate in candidates:
            if candidate.exists():
                logger.info(f"Found ts-morph CLI at: {candidate}")
                return candidate

        raise TsMorphError(
            "ts-morph CLI not found. Please run: cd python/ts_morph_cli && ./build.sh",
            "CLI_NOT_FOUND",
        )

    def _verify_cli(self) -> None:
        """
        Verify CLI is executable.

        Raises:
            TsMorphError: If CLI is not valid
        """
        if not self.cli_path.exists():
            raise TsMorphError(
                f"ts-morph CLI not found at: {self.cli_path}", "CLI_NOT_FOUND"
            )

        if not self.cli_path.is_file():
            raise TsMorphError(
                f"ts-morph CLI path is not a file: {self.cli_path}", "INVALID_CLI"
            )

    async def _execute_command(
        self, command: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a command via the ts-morph CLI.

        Args:
            command: Command name
            parameters: Command parameters

        Returns:
            Result dictionary

        Raises:
            TsMorphError: If command fails
        """
        request = {"command": command, "parameters": parameters}
        request_json = json.dumps(request)

        logger.debug(f"Executing ts-morph command: {command}")
        logger.debug(f"Request: {request_json}")

        try:
            # Execute CLI with Node.js
            process = await asyncio.create_subprocess_exec(
                "node",
                str(self.cli_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate(request_json.encode())

            if stderr:
                logger.warning(f"ts-morph CLI stderr: {stderr.decode()}")

            if process.returncode != 0:
                raise TsMorphError(
                    f"ts-morph CLI exited with code {process.returncode}: {stderr.decode()}",
                    "CLI_ERROR",
                )

            # Parse response
            response_text = stdout.decode()
            logger.debug(f"Response: {response_text}")

            try:
                response = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise TsMorphError(
                    f"Invalid JSON response from CLI: {response_text}", "INVALID_JSON"
                ) from e

            # Check for error response
            if not response.get("success"):
                error = response.get("error", {})
                raise TsMorphError(
                    error.get("message", "Unknown error"),
                    error.get("code", "UNKNOWN_ERROR"),
                )

            return response.get("result", {})

        except FileNotFoundError:
            raise TsMorphError(
                "Node.js not found. Please install Node.js 18+", "NODE_NOT_FOUND"
            )
        except Exception as e:
            if isinstance(e, TsMorphError):
                raise
            raise TsMorphError(f"Failed to execute ts-morph CLI: {str(e)}") from e

    async def get_version(self) -> Dict[str, str]:
        """
        Get ts-morph CLI version information.

        Returns:
            Version info dictionary
        """
        return await self._execute_command("version", {})

    async def load_project(self, project_path: str | Path) -> Dict[str, Any]:
        """
        Load a TypeScript project from its tsconfig.json.

        Args:
            project_path: Path to TypeScript project directory

        Returns:
            Project info with file count and file list
        """
        return await self._execute_command(
            "load_project", {"project_path": str(project_path)}
        )

    async def get_diagnostics(
        self, project_path: str | Path, file_path: Optional[str | Path] = None
    ) -> List[DiagnosticInfo]:
        """
        Get TypeScript compilation diagnostics.

        Args:
            project_path: Path to TypeScript project
            file_path: Optional specific file to check (None for entire project)

        Returns:
            List of diagnostics
        """
        params = {"project_path": str(project_path)}
        if file_path:
            params["file_path"] = str(file_path)

        result = await self._execute_command("get_diagnostics", params)

        diagnostics = []
        for diag in result.get("diagnostics", []):
            diagnostics.append(
                DiagnosticInfo(
                    file_path=diag["file_path"],
                    line=diag["line"],
                    column=diag["column"],
                    end_line=diag["end_line"],
                    end_column=diag["end_column"],
                    severity=diag["severity"],
                    message=diag["message"],
                    code=diag["code"],
                )
            )

        return diagnostics

    async def find_references(
        self, project_path: str | Path, file_path: str | Path, line: int, column: int
    ) -> List[ReferenceInfo]:
        """
        Find all references to a symbol across the project.

        Args:
            project_path: Path to TypeScript project
            file_path: File containing the symbol
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            List of references
        """
        result = await self._execute_command(
            "find_references",
            {
                "project_path": str(project_path),
                "file_path": str(file_path),
                "line": line,
                "column": column,
            },
        )

        references = []
        for ref in result.get("references", []):
            references.append(
                ReferenceInfo(
                    file_path=ref["file_path"],
                    line=ref["line"],
                    column=ref["column"],
                    line_text=ref["line_text"],
                    is_definition=ref.get("is_definition", False),
                )
            )

        return references

    async def rename_symbol(
        self,
        project_path: str | Path,
        file_path: str | Path,
        line: int,
        column: int,
        new_name: str,
    ) -> RenameResult:
        """
        Rename a symbol across the entire project.

        Args:
            project_path: Path to TypeScript project
            file_path: File containing the symbol
            line: Line number (1-based)
            column: Column number (1-based)
            new_name: New name for the symbol

        Returns:
            Rename result with file changes
        """
        result = await self._execute_command(
            "rename_symbol",
            {
                "project_path": str(project_path),
                "file_path": str(file_path),
                "line": line,
                "column": column,
                "new_name": new_name,
            },
        )

        return RenameResult(
            success=True,
            changes=[
                {
                    "file_path": change["file_path"],
                    "original_text": change["original_text"],
                    "modified_text": change["modified_text"],
                }
                for change in result.get("changes", [])
            ],
        )

    async def get_symbol_info(
        self, project_path: str | Path, file_path: str | Path, line: int, column: int
    ) -> SymbolInfo:
        """
        Get detailed information about a symbol.

        Args:
            project_path: Path to TypeScript project
            file_path: File containing the symbol
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            Symbol information
        """
        result = await self._execute_command(
            "get_symbol_info",
            {
                "project_path": str(project_path),
                "file_path": str(file_path),
                "line": line,
                "column": column,
            },
        )

        return SymbolInfo(
            name=result["name"],
            kind=result["kind"],
            file_path=result["file_path"],
            line=result["line"],
            column=result["column"],
            definition_file=result.get("definition_file"),
            definition_line=result.get("definition_line"),
            definition_column=result.get("definition_column"),
            documentation=result.get("documentation"),
        )

    async def extract_method(
        self,
        project_path: str | Path,
        file_path: str | Path,
        start_line: int,
        start_column: int,
        end_line: int,
        end_column: int,
        method_name: str,
    ) -> RenameResult:
        """
        Extract selected code into a new method/function.

        Args:
            project_path: Path to TypeScript project
            file_path: File containing the code
            start_line: Start line (1-based)
            start_column: Start column (1-based)
            end_line: End line (1-based)
            end_column: End column (1-based)
            method_name: Name for the extracted method

        Returns:
            Result with file changes
        """
        result = await self._execute_command(
            "extract_method",
            {
                "project_path": str(project_path),
                "file_path": str(file_path),
                "start_line": start_line,
                "start_column": start_column,
                "end_line": end_line,
                "end_column": end_column,
                "method_name": method_name,
            },
        )

        return RenameResult(
            success=True,
            changes=[
                {
                    "file_path": change["file_path"],
                    "original_text": change["original_text"],
                    "modified_text": change["modified_text"],
                }
                for change in result.get("changes", [])
            ],
            extracted_method_name=result.get("extracted_method_name"),
        )
