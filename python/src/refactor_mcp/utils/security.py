"""
Path security and validation utilities.

Prevents path traversal attacks and restricts operations to allowed directories.
"""

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Security validation error."""

    pass


class PathSecurityService:
    """
    Path security validation service.

    Validates that file/project paths are within allowed root directories
    and prevents path traversal attacks.
    """

    def __init__(self, allowed_roots: List[str] | None = None):
        """
        Initialize security service.

        Args:
            allowed_roots: List of allowed root directory paths
                          If None, defaults to user's home directory
        """
        if allowed_roots is None:
            allowed_roots = [str(Path.home())]

        # Resolve and normalize all root paths
        self.allowed_roots = [
            Path(root).resolve() for root in allowed_roots if Path(root).exists()
        ]

        if not self.allowed_roots:
            raise ValueError("No valid allowed root paths configured")

        logger.info(f"Path security initialized with {len(self.allowed_roots)} allowed roots")
        for root in self.allowed_roots:
            logger.info(f"  Allowed root: {root}")

    def validate_path(self, path: str | Path, must_exist: bool = False) -> Path:
        """
        Validate that a path is within allowed roots.

        Args:
            path: Path to validate
            must_exist: If True, path must exist

        Returns:
            Resolved Path object

        Raises:
            SecurityError: If path is outside allowed roots or invalid
        """
        try:
            # Convert to Path and resolve
            resolved_path = Path(path).resolve()

            # Check if path exists (if required)
            if must_exist and not resolved_path.exists():
                raise SecurityError(f"Path does not exist: {path}")

            # Check if path is within any allowed root
            is_allowed = any(
                self._is_subpath(resolved_path, root) for root in self.allowed_roots
            )

            if not is_allowed:
                logger.warning(f"Path outside allowed roots: {path}")
                raise SecurityError(
                    f"Path '{path}' is outside allowed directories. "
                    f"Allowed roots: {[str(r) for r in self.allowed_roots]}"
                )

            logger.debug(f"Path validated: {resolved_path}")
            return resolved_path

        except SecurityError:
            raise
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            raise SecurityError(f"Invalid path: {path}") from e

    def validate_project_path(self, path: str | Path) -> Path:
        """
        Validate a project/solution path.

        Args:
            path: Path to .sln, .csproj, .vbproj, or directory

        Returns:
            Resolved Path object

        Raises:
            SecurityError: If path is invalid or not a valid project
        """
        resolved_path = self.validate_path(path, must_exist=True)

        # Check if it's a valid project file or directory
        if resolved_path.is_file():
            valid_extensions = {".sln", ".csproj", ".vbproj", ".fsproj"}
            if resolved_path.suffix.lower() not in valid_extensions:
                raise SecurityError(
                    f"Not a valid project file: {path}. "
                    f"Expected: {', '.join(valid_extensions)}"
                )
        elif not resolved_path.is_dir():
            raise SecurityError(f"Not a file or directory: {path}")

        return resolved_path

    def validate_source_file(self, path: str | Path) -> Path:
        """
        Validate a source code file path.

        Args:
            path: Path to source file

        Returns:
            Resolved Path object

        Raises:
            SecurityError: If path is invalid or not a source file
        """
        resolved_path = self.validate_path(path, must_exist=True)

        if not resolved_path.is_file():
            raise SecurityError(f"Not a file: {path}")

        # Check for valid source file extensions
        valid_extensions = {
            ".cs",
            ".vb",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".py",
            ".go",
            ".rs",
            ".cpp",
            ".cc",
            ".cxx",
            ".h",
            ".hpp",
            ".java",
        }

        if resolved_path.suffix.lower() not in valid_extensions:
            logger.warning(f"Unusual file extension: {resolved_path.suffix}")
            # Don't block, just warn - might be a valid source file

        return resolved_path

    def is_path_allowed(self, path: str | Path) -> bool:
        """
        Check if a path is within allowed roots (non-throwing).

        Args:
            path: Path to check

        Returns:
            True if path is allowed, False otherwise
        """
        try:
            self.validate_path(path, must_exist=False)
            return True
        except SecurityError:
            return False

    def add_allowed_root(self, root: str | Path) -> None:
        """
        Add a new allowed root directory.

        Args:
            root: Root directory path to add

        Raises:
            ValueError: If root doesn't exist
        """
        root_path = Path(root).resolve()
        if not root_path.exists():
            raise ValueError(f"Root directory does not exist: {root}")

        if root_path not in self.allowed_roots:
            self.allowed_roots.append(root_path)
            logger.info(f"Added allowed root: {root_path}")

    def remove_allowed_root(self, root: str | Path) -> bool:
        """
        Remove an allowed root directory.

        Args:
            root: Root directory path to remove

        Returns:
            True if removed, False if not found
        """
        root_path = Path(root).resolve()
        if root_path in self.allowed_roots:
            self.allowed_roots.remove(root_path)
            logger.info(f"Removed allowed root: {root_path}")
            return True
        return False

    def get_allowed_roots(self) -> List[Path]:
        """
        Get list of allowed root directories.

        Returns:
            List of allowed root paths
        """
        return self.allowed_roots.copy()

    @staticmethod
    def _is_subpath(path: Path, parent: Path) -> bool:
        """
        Check if path is a subpath of parent.

        Args:
            path: Path to check
            parent: Potential parent path

        Returns:
            True if path is under parent
        """
        try:
            # Try to get relative path - will raise ValueError if not relative
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    def __repr__(self) -> str:
        """String representation."""
        return f"PathSecurityService(roots={len(self.allowed_roots)})"
