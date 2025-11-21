"""
Roslyn client for C# and VB.NET refactoring.

Communicates with standalone Roslyn CLI tool via subprocess.
Provides semantic refactoring operations backed by Microsoft.CodeAnalysis.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import (
    DiagnosticsInfo,
    DiagnosticInfo,
    DiagnosticSeverity,
    ReferenceLocation,
    ReferencesInfo,
    RenameResult,
    SymbolInfo,
    ExtractMethodResult,
)
from ..utils.cache import CacheManager

logger = logging.getLogger(__name__)


class RoslynError(Exception):
    """Roslyn operation error."""

    pass


class RoslynClient:
    """
    Client for interacting with Roslyn CLI tool.

    The CLI tool is a C# executable that wraps Roslyn APIs.
    This client communicates via JSON over stdin/stdout.
    """

    def __init__(
        self,
        cli_path: str | Path,
        timeout: int = 120,
        cache: Optional[CacheManager] = None,
    ):
        """
        Initialize Roslyn client.

        Args:
            cli_path: Path to Roslyn CLI executable
            timeout: Operation timeout in seconds
            cache: Optional cache manager
        """
        self.cli_path = Path(cli_path)
        self.timeout = timeout
        self.cache = cache

        if not self.cli_path.exists():
            raise FileNotFoundError(f"Roslyn CLI not found at: {self.cli_path}")

        logger.info(f"Roslyn client initialized with CLI: {self.cli_path}")

    async def start(self) -> None:
        """Start the Roslyn client (validate CLI works)."""
        try:
            # Test CLI by getting version
            version = await self._execute_command("version", {})
            logger.info(f"Roslyn CLI version: {version.get('version', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to start Roslyn client: {e}")
            raise

    async def stop(self) -> None:
        """Stop the Roslyn client (cleanup resources)."""
        # Clear cache if present
        if self.cache:
            await self.cache.clear_namespace("roslyn")
        logger.info("Roslyn client stopped")

    async def load_project(self, project_path: str) -> Dict[str, Any]:
        """
        Load a C# or VB.NET project/solution.

        Args:
            project_path: Path to .sln, .csproj, or .vbproj file

        Returns:
            Project information dictionary
        """
        logger.info(f"Loading project: {project_path}")

        result = await self._execute_command(
            "load_project",
            {"projectPath": project_path},
        )

        return result

    async def get_diagnostics(
        self,
        project_path: str,
        severity_filter: str = "Warning",
    ) -> DiagnosticsInfo:
        """
        Get compilation diagnostics for a project.

        Args:
            project_path: Path to project/solution
            severity_filter: Minimum severity ("Error", "Warning", "Info", "All")

        Returns:
            Diagnostics information
        """
        logger.info(f"Getting diagnostics for: {project_path}")

        # Check cache
        cache_key = f"diagnostics:{project_path}:{severity_filter}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for diagnostics: {project_path}")
                return DiagnosticsInfo(**cached)

        result = await self._execute_command(
            "get_diagnostics",
            {
                "projectPath": project_path,
                "severityFilter": severity_filter,
            },
        )

        # Parse response
        diagnostics = DiagnosticsInfo(
            error_count=result.get("errorCount", 0),
            warning_count=result.get("warningCount", 0),
            info_count=result.get("infoCount", 0),
            is_safe_to_refactor=result.get("isSafeToRefactor", True),
            diagnostics=[
                DiagnosticInfo(
                    severity=DiagnosticSeverity(d["severity"]),
                    message=d["message"],
                    file_path=d["filePath"],
                    line=d["line"],
                    column=d["column"],
                    diagnostic_id=d.get("diagnosticId"),
                )
                for d in result.get("diagnostics", [])
            ],
        )

        # Cache result
        if self.cache:
            await self.cache.set(cache_key, diagnostics.model_dump(), ttl=300)

        return diagnostics

    async def find_references(
        self,
        project_path: str,
        file_path: str,
        line: int,
        column: int,
    ) -> ReferencesInfo:
        """
        Find all references to a symbol.

        Args:
            project_path: Path to project/solution
            file_path: Path to source file
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            References information
        """
        logger.info(f"Finding references at {file_path}:{line}:{column}")

        result = await self._execute_command(
            "find_references",
            {
                "projectPath": project_path,
                "filePath": file_path,
                "line": line,
                "column": column,
            },
        )

        return ReferencesInfo(
            symbol_name=result.get("symbolName", ""),
            reference_count=result.get("referenceCount", 0),
            references=[
                ReferenceLocation(
                    file_path=ref["filePath"],
                    line=ref["line"],
                    column=ref["column"],
                    preview=ref.get("preview", ""),
                )
                for ref in result.get("references", [])
            ],
        )

    async def rename_symbol(
        self,
        project_path: str,
        file_path: str,
        line: int,
        column: int,
        new_name: str,
    ) -> RenameResult:
        """
        Rename a symbol (semantic, scope-aware).

        Args:
            project_path: Path to project/solution
            file_path: Path to source file
            line: Line number (1-based)
            column: Column number (1-based)
            new_name: New symbol name

        Returns:
            Rename result
        """
        logger.info(f"Renaming symbol at {file_path}:{line}:{column} to '{new_name}'")

        result = await self._execute_command(
            "rename_symbol",
            {
                "projectPath": project_path,
                "filePath": file_path,
                "line": line,
                "column": column,
                "newName": new_name,
            },
        )

        return RenameResult(
            success=result.get("success", False),
            symbol_name=result.get("symbolName", ""),
            new_name=new_name,
            files_modified=result.get("filesModified", 0),
            locations_modified=result.get("locationsModified", 0),
            error=result.get("error"),
        )

    async def get_symbol_info(
        self,
        project_path: str,
        file_path: str,
        line: int,
        column: int,
    ) -> SymbolInfo:
        """
        Get detailed symbol information.

        Args:
            project_path: Path to project/solution
            file_path: Path to source file
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            Symbol information
        """
        logger.info(f"Getting symbol info at {file_path}:{line}:{column}")

        result = await self._execute_command(
            "get_symbol_info",
            {
                "projectPath": project_path,
                "filePath": file_path,
                "line": line,
                "column": column,
            },
        )

        return SymbolInfo(
            name=result.get("name", ""),
            kind=result.get("kind", ""),
            type=result.get("type", ""),
            containing_type=result.get("containingType"),
            containing_namespace=result.get("containingNamespace"),
            is_static=result.get("isStatic", False),
            is_abstract=result.get("isAbstract", False),
            is_virtual=result.get("isVirtual", False),
            accessibility=result.get("accessibility", ""),
            documentation=result.get("documentation"),
        )

    async def extract_method(
        self,
        project_path: str,
        file_path: str,
        start_line: int,
        start_column: int,
        end_line: int,
        end_column: int,
        method_name: str,
    ) -> ExtractMethodResult:
        """
        Extract selected code into a new method.

        Args:
            project_path: Path to project/solution
            file_path: Path to source file
            start_line: Selection start line (1-based)
            start_column: Selection start column (1-based)
            end_line: Selection end line (1-based)
            end_column: Selection end column (1-based)
            method_name: New method name

        Returns:
            Extract method result
        """
        logger.info(
            f"Extracting method '{method_name}' at {file_path}:"
            f"{start_line}:{start_column}-{end_line}:{end_column}"
        )

        result = await self._execute_command(
            "extract_method",
            {
                "projectPath": project_path,
                "filePath": file_path,
                "startLine": start_line,
                "startColumn": start_column,
                "endLine": end_line,
                "endColumn": end_column,
                "methodName": method_name,
            },
        )

        return ExtractMethodResult(
            success=result.get("success", False),
            method_name=method_name,
            files_modified=result.get("filesModified", 0),
            parameters=result.get("parameters", []),
            return_type=result.get("returnType", "void"),
            error=result.get("error"),
        )

    async def _execute_command(
        self,
        command: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a command via Roslyn CLI.

        Args:
            command: Command name
            parameters: Command parameters

        Returns:
            Command result

        Raises:
            RoslynError: If command fails
        """
        request = {
            "command": command,
            "parameters": parameters,
        }

        request_json = json.dumps(request)

        try:
            # Execute CLI process
            process = await asyncio.create_subprocess_exec(
                str(self.cli_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Send request
            stdout, stderr = await asyncio.wait_for(
                process.communicate(request_json.encode("utf-8")),
                timeout=self.timeout,
            )

            # Check exit code
            if process.returncode != 0:
                error_msg = stderr.decode("utf-8")
                logger.error(f"Roslyn CLI error: {error_msg}")
                raise RoslynError(f"CLI failed with code {process.returncode}: {error_msg}")

            # Parse response
            response_json = stdout.decode("utf-8")
            response = json.loads(response_json)

            # Check for error in response
            if not response.get("success", True):
                error_msg = response.get("error", "Unknown error")
                logger.error(f"Roslyn command error: {error_msg}")
                raise RoslynError(error_msg)

            return response.get("result", response)

        except asyncio.TimeoutError:
            logger.error(f"Roslyn command timeout after {self.timeout}s: {command}")
            raise RoslynError(f"Command timeout: {command}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Roslyn response: {e}")
            raise RoslynError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Roslyn command failed: {e}")
            raise RoslynError(f"Command failed: {e}")
