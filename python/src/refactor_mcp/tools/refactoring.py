"""
Refactoring tools for MCP server.

Implements core refactoring operations: load_project, rename_symbol,
find_references, get_symbol_info, extract_method.
"""

import logging
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP

from ..clients.lsp import LspError
from ..clients.ts_morph import TsMorphError
from ..models import AppContext, Language
from ..utils.security import SecurityError

logger = logging.getLogger(__name__)


def register_refactoring_tools(mcp: FastMCP) -> None:
    """
    Register all refactoring tools with FastMCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def load_project(
        project_path: Annotated[str, "Path to .sln, .csproj, .vbproj, or project directory"],
        ctx: AppContext,
    ) -> dict:
        """
        Load a C#/VB.NET project or solution for analysis.

        This tool loads a project and prepares it for refactoring operations.
        It validates the project structure and returns project information.

        Args:
            project_path: Path to .sln, .csproj, .vbproj file, or project directory
            ctx: Application context (injected)

        Returns:
            Project information including document count and languages
        """
        try:
            # Validate path
            validated_path = ctx.security.validate_project_path(project_path)
            logger.info(f"Loading project: {validated_path}")

            # Use Roslyn for C#/VB.NET projects
            if ctx.roslyn_client:
                result = await ctx.roslyn_client.load_project(str(validated_path))
                return {
                    "success": True,
                    "project_path": str(validated_path),
                    "document_count": result.get("documentCount", 0),
                    "project_count": result.get("projectCount", 1),
                    "language": result.get("language", "csharp"),
                }
            else:
                return {
                    "success": False,
                    "error": "Roslyn client not available",
                }

        except SecurityError as e:
            logger.error(f"Security error loading project: {e}")
            return {"success": False, "error": f"Security error: {e}"}
        except Exception as e:
            logger.error(f"Error loading project: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def rename_symbol(
        project_path: Annotated[str, "Path to project/solution"],
        file_path: Annotated[str, "Path to source file containing symbol"],
        line: Annotated[int, "Line number (1-based)"],
        column: Annotated[int, "Column number (1-based)"],
        new_name: Annotated[str, "New symbol name"],
        language: Annotated[str, "Language: csharp, vbnet, typescript, python, go, rust, java, cpp"] = "csharp",
        ctx: AppContext = None,
    ) -> dict:
        """
        Rename a symbol (variable, method, class, etc.) across entire codebase.

        This is a semantic, scope-aware rename that updates all references to the
        symbol throughout the project. Supports C#, VB.NET, TypeScript, Python, Go,
        Rust, Java, and C++.

        Args:
            project_path: Path to project/solution
            file_path: Path to source file containing the symbol
            line: Line number where symbol is located (1-based)
            column: Column number where symbol is located (1-based)
            new_name: New name for the symbol
            language: Programming language of the file
            ctx: Application context (injected)

        Returns:
            Rename result with success status and modification counts
        """
        try:
            # Validate paths
            ctx.security.validate_project_path(project_path)
            validated_file = ctx.security.validate_source_file(file_path)

            logger.info(f"Renaming symbol at {file_path}:{line}:{column} to '{new_name}'")

            # Route to appropriate client
            lang = Language(language)

            if lang in [Language.CSHARP, Language.VBNET]:
                # Use Roslyn for .NET languages
                if not ctx.roslyn_client:
                    return {"success": False, "error": "Roslyn client not available"}

                result = await ctx.roslyn_client.rename_symbol(
                    project_path, str(validated_file), line, column, new_name
                )

                return {
                    "success": result.success,
                    "symbol_name": result.symbol_name,
                    "new_name": result.new_name,
                    "files_modified": result.files_modified,
                    "locations_modified": result.locations_modified,
                    "error": result.error,
                }
            elif lang == Language.TYPESCRIPT:
                # Use ts-morph for TypeScript (native compiler API)
                if not ctx.ts_morph_client:
                    return {"success": False, "error": "ts-morph client not available"}

                result = await ctx.ts_morph_client.rename_symbol(
                    project_path, str(validated_file), line, column, new_name
                )

                return {
                    "success": result.success,
                    "symbol_name": result.symbol_name or "unknown",
                    "new_name": new_name,
                    "files_modified": len(result.changes),
                    "locations_modified": sum(
                        change["original_text"].count(new_name) for change in result.changes
                    ),
                    "error": result.error,
                }
            else:
                # Use LSP for other languages
                client = await ctx.lsp_pool.get_client(lang, Path(project_path).parent)
                result = await client.rename_symbol(validated_file, line, column, new_name)

                return {
                    "success": result.success,
                    "symbol_name": result.symbol_name,
                    "new_name": result.new_name,
                    "files_modified": result.files_modified,
                    "locations_modified": result.locations_modified,
                    "error": result.error,
                }

        except SecurityError as e:
            logger.error(f"Security error in rename: {e}")
            return {"success": False, "error": f"Security error: {e}"}
        except LspError as e:
            logger.error(f"LSP error in rename: {e}")
            return {"success": False, "error": f"Language server error: {e}"}
        except TsMorphError as e:
            logger.error(f"ts-morph error in rename: {e}")
            return {"success": False, "error": f"TypeScript compiler error: {e.message}"}
        except Exception as e:
            logger.error(f"Error in rename: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def find_references(
        project_path: Annotated[str, "Path to project/solution"],
        file_path: Annotated[str, "Path to source file"],
        line: Annotated[int, "Line number (1-based)"],
        column: Annotated[int, "Column number (1-based)"],
        language: Annotated[str, "Language: csharp, vbnet, typescript, python, go, rust, java, cpp"] = "csharp",
        ctx: AppContext = None,
    ) -> dict:
        """
        Find all references to a symbol in the codebase.

        Performs semantic search to find all locations where a symbol is referenced,
        including declarations, usages, and implementations.

        Args:
            project_path: Path to project/solution
            file_path: Path to source file
            line: Line number (1-based)
            column: Column number (1-based)
            language: Programming language
            ctx: Application context (injected)

        Returns:
            List of reference locations with file paths, lines, and previews
        """
        try:
            # Validate paths
            ctx.security.validate_project_path(project_path)
            validated_file = ctx.security.validate_source_file(file_path)

            logger.info(f"Finding references at {file_path}:{line}:{column}")

            # Route to appropriate client
            lang = Language(language)

            if lang in [Language.CSHARP, Language.VBNET]:
                if not ctx.roslyn_client:
                    return {"success": False, "error": "Roslyn client not available"}

                result = await ctx.roslyn_client.find_references(
                    project_path, str(validated_file), line, column
                )
            elif lang == Language.TYPESCRIPT:
                if not ctx.ts_morph_client:
                    return {"success": False, "error": "ts-morph client not available"}

                references = await ctx.ts_morph_client.find_references(
                    project_path, str(validated_file), line, column
                )
                # Convert to expected format
                from ..models.refactoring import ReferencesInfo, ReferenceLocation
                result = ReferencesInfo(
                    symbol_name="symbol",  # ts-morph doesn't provide this separately
                    reference_count=len(references),
                    references=[
                        ReferenceLocation(
                            file_path=ref.file_path,
                            line=ref.line,
                            column=ref.column,
                            preview=ref.line_text
                        )
                        for ref in references
                    ]
                )
            else:
                client = await ctx.lsp_pool.get_client(lang, Path(project_path).parent)
                result = await client.find_references(validated_file, line, column)

            return {
                "success": True,
                "symbol_name": result.symbol_name,
                "reference_count": result.reference_count,
                "references": [
                    {
                        "file_path": ref.file_path,
                        "line": ref.line,
                        "column": ref.column,
                        "preview": ref.preview,
                    }
                    for ref in result.references
                ],
            }

        except SecurityError as e:
            logger.error(f"Security error in find_references: {e}")
            return {"success": False, "error": f"Security error: {e}"}
        except LspError as e:
            logger.error(f"LSP error in find_references: {e}")
            return {"success": False, "error": f"Language server error: {e}"}
        except TsMorphError as e:
            logger.error(f"ts-morph error in find_references: {e}")
            return {"success": False, "error": f"TypeScript compiler error: {e.message}"}
        except Exception as e:
            logger.error(f"Error in find_references: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_symbol_info(
        project_path: Annotated[str, "Path to project/solution"],
        file_path: Annotated[str, "Path to source file"],
        line: Annotated[int, "Line number (1-based)"],
        column: Annotated[int, "Column number (1-based)"],
        language: Annotated[str, "Language: csharp, vbnet, typescript, python, go, rust, java, cpp"] = "csharp",
        ctx: AppContext = None,
    ) -> dict:
        """
        Get detailed information about a symbol.

        Returns comprehensive information including symbol kind, type, accessibility,
        containing namespace/type, and documentation.

        Args:
            project_path: Path to project/solution
            file_path: Path to source file
            line: Line number (1-based)
            column: Column number (1-based)
            language: Programming language
            ctx: Application context (injected)

        Returns:
            Symbol information dictionary
        """
        try:
            # Validate paths
            ctx.security.validate_project_path(project_path)
            validated_file = ctx.security.validate_source_file(file_path)

            logger.info(f"Getting symbol info at {file_path}:{line}:{column}")

            # Route to appropriate client
            lang = Language(language)

            if lang in [Language.CSHARP, Language.VBNET]:
                if not ctx.roslyn_client:
                    return {"success": False, "error": "Roslyn client not available"}

                result = await ctx.roslyn_client.get_symbol_info(
                    project_path, str(validated_file), line, column
                )
            elif lang == Language.TYPESCRIPT:
                if not ctx.ts_morph_client:
                    return {"success": False, "error": "ts-morph client not available"}

                result = await ctx.ts_morph_client.get_symbol_info(
                    project_path, str(validated_file), line, column
                )
            else:
                client = await ctx.lsp_pool.get_client(lang, Path(project_path).parent)
                result = await client.get_symbol_info(validated_file, line, column)

            return {
                "success": True,
                "name": result.name,
                "kind": result.kind,
                "type": result.type,
                "containing_type": result.containing_type,
                "containing_namespace": result.containing_namespace,
                "is_static": result.is_static,
                "is_abstract": result.is_abstract,
                "is_virtual": result.is_virtual,
                "accessibility": result.accessibility,
                "documentation": result.documentation,
            }

        except SecurityError as e:
            logger.error(f"Security error in get_symbol_info: {e}")
            return {"success": False, "error": f"Security error: {e}"}
        except LspError as e:
            logger.error(f"LSP error in get_symbol_info: {e}")
            return {"success": False, "error": f"Language server error: {e}"}
        except TsMorphError as e:
            logger.error(f"ts-morph error in get_symbol_info: {e}")
            return {"success": False, "error": f"TypeScript compiler error: {e.message}"}
        except Exception as e:
            logger.error(f"Error in get_symbol_info: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def extract_method(
        project_path: Annotated[str, "Path to project/solution"],
        file_path: Annotated[str, "Path to source file"],
        start_line: Annotated[int, "Selection start line (1-based)"],
        start_column: Annotated[int, "Selection start column (1-based)"],
        end_line: Annotated[int, "Selection end line (1-based)"],
        end_column: Annotated[int, "Selection end column (1-based)"],
        method_name: Annotated[str, "New method name"],
        language: Annotated[str, "Language (only csharp/vbnet supported)"] = "csharp",
        ctx: AppContext = None,
    ) -> dict:
        """
        Extract selected code into a new method.

        Takes a selection of code and refactors it into a separate method,
        automatically determining parameters and return type.

        Note: Currently only supported for C# and VB.NET via Roslyn.

        Args:
            project_path: Path to project/solution
            file_path: Path to source file
            start_line: Start line of selection (1-based)
            start_column: Start column of selection (1-based)
            end_line: End line of selection (1-based)
            end_column: End column of selection (1-based)
            method_name: Name for the extracted method
            language: Programming language (csharp or vbnet)
            ctx: Application context (injected)

        Returns:
            Extract method result with success status and details
        """
        try:
            # Validate paths
            ctx.security.validate_project_path(project_path)
            validated_file = ctx.security.validate_source_file(file_path)

            logger.info(
                f"Extracting method '{method_name}' from {file_path}:"
                f"{start_line}:{start_column}-{end_line}:{end_column}"
            )

            # Route to appropriate client
            lang = Language(language)

            if lang in [Language.CSHARP, Language.VBNET]:
                if not ctx.roslyn_client:
                    return {"success": False, "error": "Roslyn client not available"}

                result = await ctx.roslyn_client.extract_method(
                    project_path,
                    str(validated_file),
                    start_line,
                    start_column,
                    end_line,
                    end_column,
                    method_name,
                )

                return {
                    "success": result.success,
                    "method_name": result.method_name,
                    "files_modified": result.files_modified,
                    "parameters": result.parameters,
                    "return_type": result.return_type,
                    "error": result.error,
                }

            elif lang == Language.TYPESCRIPT:
                if not ctx.ts_morph_client:
                    return {"success": False, "error": "ts-morph client not available"}

                result = await ctx.ts_morph_client.extract_method(
                    project_path,
                    str(validated_file),
                    start_line,
                    start_column,
                    end_line,
                    end_column,
                    method_name,
                )

                return {
                    "success": result.success,
                    "method_name": method_name,
                    "files_modified": len(result.changes),
                    "parameters": [],  # ts-morph implementation needs enhancement
                    "return_type": "unknown",  # ts-morph implementation needs enhancement
                    "error": result.error,
                }

            else:
                return {
                    "success": False,
                    "error": f"Extract method not yet supported for {language}",
                }

        except SecurityError as e:
            logger.error(f"Security error in extract_method: {e}")
            return {"success": False, "error": f"Security error: {e}"}
        except TsMorphError as e:
            logger.error(f"ts-morph error in extract_method: {e}")
            return {"success": False, "error": f"TypeScript compiler error: {e.message}"}
        except Exception as e:
            logger.error(f"Error in extract_method: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Refactoring tools registered")
