"""
Python Rope client for native Python refactoring.

This client uses the Rope refactoring library directly (no subprocess!),
providing Roslyn-level refactoring capabilities for Python projects.

Rope advantages:
- Pure Python (no subprocess overhead!)
- Most advanced Python refactoring library
- Format-preserving (maintains style)
- Extract method, rename, find references, etc.
"""

import logging
from pathlib import Path
from typing import List, Optional, Any, Dict

try:
    from rope.base.project import Project
    from rope.base import libutils
    from rope.refactor.rename import Rename
    from rope.refactor.extract import ExtractMethod, ExtractVariable
    from rope.contrib import findit
    ROPE_AVAILABLE = True
except ImportError:
    ROPE_AVAILABLE = False

from ..models.refactoring import (
    DiagnosticInfo,
    ReferenceInfo,
    RenameResult,
    SymbolInfo,
)

logger = logging.getLogger(__name__)


class RopeError(Exception):
    """Exception raised for Rope client errors."""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class RopeClient:
    """
    Client for Python refactoring using Rope library.

    Direct integration with Rope - no subprocess needed!
    Much faster than ts-morph or Roslyn CLI approaches.
    """

    def __init__(self):
        """
        Initialize Rope client.

        Raises:
            RopeError: If Rope library is not installed
        """
        if not ROPE_AVAILABLE:
            raise RopeError(
                "Rope library not installed. Install with: pip install rope",
                "ROPE_NOT_INSTALLED",
            )

        self._projects: Dict[str, Project] = {}
        logger.info("Rope client initialized for Python refactoring")

    def _get_project(self, project_path: str | Path) -> Project:
        """
        Get or create a Rope project.

        Args:
            project_path: Path to Python project directory

        Returns:
            Rope Project instance
        """
        project_path = str(Path(project_path).resolve())

        if project_path not in self._projects:
            logger.debug(f"Creating new Rope project: {project_path}")
            self._projects[project_path] = Project(project_path)

        return self._projects[project_path]

    def close_project(self, project_path: str | Path) -> None:
        """
        Close a Rope project and free resources.

        Args:
            project_path: Path to project to close
        """
        project_path = str(Path(project_path).resolve())

        if project_path in self._projects:
            self._projects[project_path].close()
            del self._projects[project_path]
            logger.debug(f"Closed Rope project: {project_path}")

    def close_all_projects(self) -> None:
        """Close all open Rope projects."""
        for project in list(self._projects.values()):
            project.close()
        self._projects.clear()
        logger.debug("Closed all Rope projects")

    async def get_version(self) -> Dict[str, str]:
        """
        Get Rope version information.

        Returns:
            Version info dictionary
        """
        import rope

        return {
            "rope_version": rope.VERSION,
            "client": "rope_client",
            "version": "2.0.0",
        }

    async def load_project(self, project_path: str | Path) -> Dict[str, Any]:
        """
        Load a Python project.

        Args:
            project_path: Path to Python project directory

        Returns:
            Project info with file count
        """
        try:
            project = self._get_project(project_path)
            python_files = project.get_python_files()

            return {
                "project_path": str(Path(project_path).resolve()),
                "file_count": len(python_files),
                "files": [str(f.path) for f in python_files[:100]],  # Limit for performance
            }

        except Exception as e:
            raise RopeError(f"Failed to load project: {str(e)}", "PROJECT_LOAD_ERROR")

    async def find_references(
        self, project_path: str | Path, file_path: str | Path, offset: int
    ) -> List[ReferenceInfo]:
        """
        Find all references to a symbol.

        Args:
            project_path: Path to Python project
            file_path: File containing the symbol
            offset: Character offset in file (0-based)

        Returns:
            List of references
        """
        try:
            project = self._get_project(project_path)
            resource = libutils.path_to_resource(project, str(file_path))

            if resource is None:
                raise RopeError(f"File not found in project: {file_path}", "FILE_NOT_FOUND")

            # Find occurrences
            occurrences = findit.find_occurrences(project, resource, offset)

            references = []
            for occurrence in occurrences:
                try:
                    # Get line and column from offset
                    resource_text = occurrence.resource.read()
                    line = resource_text[:occurrence.offset].count('\n') + 1
                    line_start = resource_text.rfind('\n', 0, occurrence.offset) + 1
                    column = occurrence.offset - line_start + 1

                    # Get line text
                    line_end = resource_text.find('\n', occurrence.offset)
                    if line_end == -1:
                        line_end = len(resource_text)
                    line_text = resource_text[line_start:line_end].strip()

                    references.append(
                        ReferenceInfo(
                            file_path=str(occurrence.resource.path),
                            line=line,
                            column=column,
                            line_text=line_text,
                            is_definition=False,  # Rope doesn't distinguish
                        )
                    )
                except Exception as e:
                    logger.warning(f"Error processing occurrence: {e}")
                    continue

            return references

        except RopeError:
            raise
        except Exception as e:
            raise RopeError(f"Failed to find references: {str(e)}", "FIND_REFERENCES_ERROR")

    async def rename_symbol(
        self,
        project_path: str | Path,
        file_path: str | Path,
        offset: int,
        new_name: str,
    ) -> RenameResult:
        """
        Rename a symbol across the entire project.

        Args:
            project_path: Path to Python project
            file_path: File containing the symbol
            offset: Character offset in file (0-based)
            new_name: New name for the symbol

        Returns:
            Rename result with file changes
        """
        try:
            project = self._get_project(project_path)
            resource = libutils.path_to_resource(project, str(file_path))

            if resource is None:
                raise RopeError(f"File not found in project: {file_path}", "FILE_NOT_FOUND")

            # Create rename refactoring
            renamer = Rename(project, resource, offset)

            # Get old name
            old_name = renamer.get_old_name()

            # Get changes
            changes = renamer.get_changes(new_name)

            # Collect file changes
            file_changes = []
            for change in changes.changes:
                file_changes.append({
                    "file_path": str(change.resource.path),
                    "original_text": change.resource.read(),
                    "modified_text": change.get_new_contents(),
                })

            # Apply changes
            project.do(changes)

            return RenameResult(
                success=True,
                symbol_name=old_name,
                new_name=new_name,
                files_modified=len(file_changes),
                locations_modified=len(changes.changes),
                changes=file_changes,
            )

        except RopeError:
            raise
        except Exception as e:
            raise RopeError(f"Failed to rename symbol: {str(e)}", "RENAME_ERROR")

    async def get_symbol_info(
        self, project_path: str | Path, file_path: str | Path, offset: int
    ) -> SymbolInfo:
        """
        Get detailed information about a symbol.

        Args:
            project_path: Path to Python project
            file_path: File containing the symbol
            offset: Character offset in file (0-based)

        Returns:
            Symbol information
        """
        try:
            project = self._get_project(project_path)
            resource = libutils.path_to_resource(project, str(file_path))

            if resource is None:
                raise RopeError(f"File not found in project: {file_path}", "FILE_NOT_FOUND")

            # Get pyname at offset
            from rope.base.evaluate import eval_location

            pymodule = project.get_pymodule(resource)
            pyname = eval_location(pymodule, offset)

            if pyname is None:
                raise RopeError("No symbol found at position", "NO_SYMBOL")

            # Get line and column
            resource_text = resource.read()
            line = resource_text[:offset].count('\n') + 1
            line_start = resource_text.rfind('\n', 0, offset) + 1
            column = offset - line_start + 1

            # Get symbol information
            name = pyname.get_name() if hasattr(pyname, 'get_name') else "unknown"
            kind = pyname.get_kind() if hasattr(pyname, 'get_kind') else "unknown"

            # Try to get documentation
            doc = None
            if hasattr(pyname, 'get_doc'):
                doc = pyname.get_doc()

            return SymbolInfo(
                name=name,
                kind=kind,
                file_path=str(file_path),
                line=line,
                column=column,
                type="unknown",
                documentation=doc,
            )

        except RopeError:
            raise
        except Exception as e:
            raise RopeError(f"Failed to get symbol info: {str(e)}", "SYMBOL_INFO_ERROR")

    async def extract_method(
        self,
        project_path: str | Path,
        file_path: str | Path,
        start_offset: int,
        end_offset: int,
        method_name: str,
    ) -> RenameResult:
        """
        Extract selected code into a new method/function.

        Args:
            project_path: Path to Python project
            file_path: File containing the code
            start_offset: Start character offset (0-based)
            end_offset: End character offset (0-based)
            method_name: Name for the extracted method

        Returns:
            Result with file changes
        """
        try:
            project = self._get_project(project_path)
            resource = libutils.path_to_resource(project, str(file_path))

            if resource is None:
                raise RopeError(f"File not found in project: {file_path}", "FILE_NOT_FOUND")

            # Create extract method refactoring
            extractor = ExtractMethod(project, resource, start_offset, end_offset)

            # Get changes
            changes = extractor.get_changes(method_name)

            # Collect file changes
            file_changes = []
            for change in changes.changes:
                file_changes.append({
                    "file_path": str(change.resource.path),
                    "original_text": change.resource.read(),
                    "modified_text": change.get_new_contents(),
                })

            # Apply changes
            project.do(changes)

            return RenameResult(
                success=True,
                changes=file_changes,
                extracted_method_name=method_name,
                files_modified=len(file_changes),
                locations_modified=1,
            )

        except RopeError:
            raise
        except Exception as e:
            raise RopeError(f"Failed to extract method: {str(e)}", "EXTRACT_METHOD_ERROR")

    async def get_diagnostics(
        self, project_path: str | Path, file_path: Optional[str | Path] = None
    ) -> List[DiagnosticInfo]:
        """
        Get Python diagnostics (syntax errors, etc.).

        Note: Rope doesn't provide comprehensive diagnostics.
        For full linting, use pylint/flake8/mypy via LSP.

        Args:
            project_path: Path to Python project
            file_path: Optional specific file to check

        Returns:
            List of diagnostics (basic syntax checking only)
        """
        diagnostics = []

        try:
            project = self._get_project(project_path)

            if file_path:
                # Check specific file
                resource = libutils.path_to_resource(project, str(file_path))
                if resource:
                    try:
                        # Try to parse - will raise SyntaxError if invalid
                        project.get_pymodule(resource)
                    except SyntaxError as e:
                        diagnostics.append(
                            DiagnosticInfo(
                                file_path=str(file_path),
                                line=e.lineno or 1,
                                column=e.offset or 1,
                                end_line=e.lineno or 1,
                                end_column=(e.offset or 1) + 1,
                                severity="error",
                                message=str(e.msg),
                                code="SyntaxError",
                            )
                        )
            else:
                # Check all Python files
                for py_file in project.get_python_files()[:50]:  # Limit for performance
                    try:
                        project.get_pymodule(py_file)
                    except SyntaxError as e:
                        diagnostics.append(
                            DiagnosticInfo(
                                file_path=str(py_file.path),
                                line=e.lineno or 1,
                                column=e.offset or 1,
                                end_line=e.lineno or 1,
                                end_column=(e.offset or 1) + 1,
                                severity="error",
                                message=str(e.msg),
                                code="SyntaxError",
                            )
                        )

        except Exception as e:
            logger.warning(f"Error getting diagnostics: {e}")

        return diagnostics
