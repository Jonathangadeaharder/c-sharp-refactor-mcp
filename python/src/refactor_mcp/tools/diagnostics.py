"""
Diagnostics tools for MCP server.

Provides compilation diagnostics, error checking, and refactoring safety validation.
"""

import logging
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP

from ..clients.lsp import LspError
from ..models import AppContext, Language
from ..utils.security import SecurityError

logger = logging.getLogger(__name__)


def register_diagnostic_tools(mcp: FastMCP) -> None:
    """
    Register all diagnostic tools with FastMCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def get_diagnostics(
        project_path: Annotated[str, "Path to project/solution"],
        file_path: Annotated[str | None, "Optional: specific file to check"] = None,
        severity_filter: Annotated[str, "Minimum severity: Error, Warning, Info, All"] = "Warning",
        language: Annotated[str, "Language: csharp, vbnet, typescript, python, go, rust, java, cpp"] = "csharp",
        ctx: AppContext = None,
    ) -> dict:
        """
        Get compilation diagnostics (errors, warnings, info) for a project or file.

        Analyzes code for syntax errors, type errors, warnings, and informational
        messages. Returns aggregated counts and detailed diagnostic information.

        Use this before refactoring to ensure code is in a good state.

        Args:
            project_path: Path to project/solution
            file_path: Optional path to specific file (if None, analyzes entire project)
            severity_filter: Minimum severity level to include
            language: Programming language
            ctx: Application context (injected)

        Returns:
            Diagnostics information with counts and detailed messages
        """
        try:
            # Validate paths
            ctx.security.validate_project_path(project_path)
            if file_path:
                validated_file = ctx.security.validate_source_file(file_path)
            else:
                validated_file = None

            logger.info(f"Getting diagnostics for: {file_path or project_path}")

            # Route to appropriate client
            lang = Language(language)

            if lang in [Language.CSHARP, Language.VBNET]:
                # Use Roslyn for .NET languages
                if not ctx.roslyn_client:
                    return {"success": False, "error": "Roslyn client not available"}

                result = await ctx.roslyn_client.get_diagnostics(
                    project_path, severity_filter
                )

                return {
                    "success": True,
                    "error_count": result.error_count,
                    "warning_count": result.warning_count,
                    "info_count": result.info_count,
                    "is_safe_to_refactor": result.is_safe_to_refactor,
                    "diagnostics": [
                        {
                            "severity": d.severity.value,
                            "message": d.message,
                            "file_path": d.file_path,
                            "line": d.line,
                            "column": d.column,
                            "diagnostic_id": d.diagnostic_id,
                        }
                        for d in result.diagnostics
                    ],
                }
            else:
                # Use LSP for other languages
                if not validated_file:
                    return {
                        "success": False,
                        "error": "file_path required for non-.NET languages",
                    }

                client = await ctx.lsp_pool.get_client(lang, Path(project_path).parent)
                result = await client.get_diagnostics(validated_file)

                return {
                    "success": True,
                    "error_count": result.error_count,
                    "warning_count": result.warning_count,
                    "info_count": result.info_count,
                    "is_safe_to_refactor": result.is_safe_to_refactor,
                    "diagnostics": [
                        {
                            "severity": d.severity.value,
                            "message": d.message,
                            "file_path": d.file_path,
                            "line": d.line,
                            "column": d.column,
                            "diagnostic_id": d.diagnostic_id,
                        }
                        for d in result.diagnostics
                    ],
                }

        except SecurityError as e:
            logger.error(f"Security error in get_diagnostics: {e}")
            return {"success": False, "error": f"Security error: {e}"}
        except LspError as e:
            logger.error(f"LSP error in get_diagnostics: {e}")
            return {"success": False, "error": f"Language server error: {e}"}
        except Exception as e:
            logger.error(f"Error in get_diagnostics: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def check_refactoring_safety(
        project_path: Annotated[str, "Path to project/solution"],
        language: Annotated[str, "Language: csharp, vbnet, typescript, python, go, rust, java, cpp"] = "csharp",
        ctx: AppContext = None,
    ) -> dict:
        """
        Check if project is safe to refactor (no critical errors).

        Performs a quick diagnostic check to determine if refactoring operations
        are likely to succeed. Returns a boolean safety flag and error summary.

        Args:
            project_path: Path to project/solution
            language: Programming language
            ctx: Application context (injected)

        Returns:
            Safety check result with is_safe flag and error summary
        """
        try:
            # Validate path
            ctx.security.validate_project_path(project_path)

            logger.info(f"Checking refactoring safety for: {project_path}")

            # Get diagnostics with Error filter
            lang = Language(language)

            if lang in [Language.CSHARP, Language.VBNET]:
                if not ctx.roslyn_client:
                    return {"success": False, "error": "Roslyn client not available"}

                result = await ctx.roslyn_client.get_diagnostics(project_path, "Error")

                return {
                    "success": True,
                    "is_safe_to_refactor": result.is_safe_to_refactor,
                    "error_count": result.error_count,
                    "warning_count": result.warning_count,
                    "summary": (
                        f"Project is {'safe' if result.is_safe_to_refactor else 'NOT SAFE'} "
                        f"to refactor. Found {result.error_count} errors, {result.warning_count} warnings."
                    ),
                }
            else:
                # For LSP, we'd need to check specific files
                return {
                    "success": True,
                    "is_safe_to_refactor": True,
                    "error_count": 0,
                    "warning_count": 0,
                    "summary": "Safety check not fully implemented for LSP languages yet",
                }

        except SecurityError as e:
            logger.error(f"Security error in check_refactoring_safety: {e}")
            return {"success": False, "error": f"Security error: {e}"}
        except Exception as e:
            logger.error(f"Error in check_refactoring_safety: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_project_stats(
        project_path: Annotated[str, "Path to project/solution"],
        language: Annotated[str, "Language: csharp, vbnet, typescript, python, go, rust, java, cpp"] = "csharp",
        ctx: AppContext = None,
    ) -> dict:
        """
        Get statistics about a project (file counts, diagnostics summary, etc.).

        Provides high-level overview of project health and structure.

        Args:
            project_path: Path to project/solution
            language: Programming language
            ctx: Application context (injected)

        Returns:
            Project statistics dictionary
        """
        try:
            # Validate path
            validated_path = ctx.security.validate_project_path(project_path)

            logger.info(f"Getting project stats for: {project_path}")

            # Get basic stats
            lang = Language(language)

            if lang in [Language.CSHARP, Language.VBNET]:
                if not ctx.roslyn_client:
                    return {"success": False, "error": "Roslyn client not available"}

                # Load project to get document count
                load_result = await ctx.roslyn_client.load_project(str(validated_path))

                # Get diagnostics
                diag_result = await ctx.roslyn_client.get_diagnostics(str(validated_path), "All")

                return {
                    "success": True,
                    "project_path": str(validated_path),
                    "language": language,
                    "document_count": load_result.get("documentCount", 0),
                    "project_count": load_result.get("projectCount", 1),
                    "error_count": diag_result.error_count,
                    "warning_count": diag_result.warning_count,
                    "info_count": diag_result.info_count,
                    "is_safe_to_refactor": diag_result.is_safe_to_refactor,
                }
            else:
                # For LSP languages, provide basic info
                return {
                    "success": True,
                    "project_path": str(validated_path),
                    "language": language,
                    "note": "Detailed stats not yet implemented for LSP languages",
                }

        except SecurityError as e:
            logger.error(f"Security error in get_project_stats: {e}")
            return {"success": False, "error": f"Security error: {e}"}
        except Exception as e:
            logger.error(f"Error in get_project_stats: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Diagnostic tools registered")
