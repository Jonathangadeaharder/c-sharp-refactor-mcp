"""
Tests for path security service.
"""

import pytest
import tempfile
from pathlib import Path
from refactor_mcp.utils.security import PathSecurityService, SecurityError


class TestPathSecurityService:
    """Test path security validation."""

    def test_init_with_allowed_roots(self, tmp_path):
        """Test initialization with allowed roots."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])
        assert len(security.allowed_roots) == 1
        assert security.allowed_roots[0] == tmp_path.resolve()

    def test_init_with_invalid_root(self):
        """Test initialization with non-existent root."""
        security = PathSecurityService(allowed_roots=["/nonexistent/path"])
        # Should filter out non-existent paths
        assert len(security.allowed_roots) == 0

    def test_init_default_home(self):
        """Test default initialization uses home directory."""
        security = PathSecurityService()
        assert len(security.allowed_roots) >= 1
        assert Path.home() in security.allowed_roots

    def test_validate_path_success(self, tmp_path):
        """Test validating a path within allowed roots."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # Should validate successfully
        validated = security.validate_path(test_file, must_exist=True)
        assert validated == test_file.resolve()

    def test_validate_path_outside_roots(self, tmp_path):
        """Test that paths outside allowed roots are blocked."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        security = PathSecurityService(allowed_roots=[str(allowed_dir)])

        # Try to access parent directory
        with pytest.raises(SecurityError) as exc:
            security.validate_path(tmp_path)

        assert "outside allowed directories" in str(exc.value)

    def test_validate_path_traversal_attack(self, tmp_path):
        """Test that path traversal attacks are blocked."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        security = PathSecurityService(allowed_roots=[str(allowed_dir)])

        # Try path traversal
        with pytest.raises(SecurityError):
            security.validate_path(allowed_dir / ".." / ".." / "etc" / "passwd")

    def test_validate_path_nonexistent_when_required(self, tmp_path):
        """Test validation fails for nonexistent path when must_exist=True."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(SecurityError) as exc:
            security.validate_path(nonexistent, must_exist=True)

        assert "does not exist" in str(exc.value)

    def test_validate_path_nonexistent_allowed(self, tmp_path):
        """Test validation succeeds for nonexistent path when must_exist=False."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        nonexistent = tmp_path / "nonexistent.txt"
        validated = security.validate_path(nonexistent, must_exist=False)

        assert validated == nonexistent.resolve()

    def test_validate_project_path_sln(self, tmp_path):
        """Test validating .sln project file."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        # Create a .sln file
        sln_file = tmp_path / "project.sln"
        sln_file.write_text("solution content")

        validated = security.validate_project_path(sln_file)
        assert validated == sln_file.resolve()

    def test_validate_project_path_csproj(self, tmp_path):
        """Test validating .csproj project file."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        # Create a .csproj file
        csproj_file = tmp_path / "project.csproj"
        csproj_file.write_text("project content")

        validated = security.validate_project_path(csproj_file)
        assert validated == csproj_file.resolve()

    def test_validate_project_path_directory(self, tmp_path):
        """Test validating project directory."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        validated = security.validate_project_path(project_dir)
        assert validated == project_dir.resolve()

    def test_validate_project_path_invalid_extension(self, tmp_path):
        """Test that invalid project file extensions are rejected."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        # Create a file with invalid extension
        invalid_file = tmp_path / "project.txt"
        invalid_file.write_text("content")

        with pytest.raises(SecurityError) as exc:
            security.validate_project_path(invalid_file)

        assert "Not a valid project file" in str(exc.value)

    def test_validate_source_file_success(self, tmp_path):
        """Test validating source code files."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        # Test various source file extensions
        for ext in [".cs", ".vb", ".ts", ".py", ".go", ".rs", ".cpp", ".java"]:
            source_file = tmp_path / f"test{ext}"
            source_file.write_text("code")

            validated = security.validate_source_file(source_file)
            assert validated == source_file.resolve()

    def test_validate_source_file_not_file(self, tmp_path):
        """Test that directories are rejected as source files."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        directory = tmp_path / "src"
        directory.mkdir()

        with pytest.raises(SecurityError) as exc:
            security.validate_source_file(directory)

        assert "Not a file" in str(exc.value)

    def test_is_path_allowed(self, tmp_path):
        """Test non-throwing path check."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        # Allowed path
        allowed_file = tmp_path / "test.txt"
        assert security.is_path_allowed(allowed_file) is True

        # Disallowed path
        disallowed_file = tmp_path.parent / "outside.txt"
        assert security.is_path_allowed(disallowed_file) is False

    def test_add_allowed_root(self, tmp_path):
        """Test adding a new allowed root directory."""
        initial_dir = tmp_path / "initial"
        initial_dir.mkdir()

        security = PathSecurityService(allowed_roots=[str(initial_dir)])
        assert len(security.allowed_roots) == 1

        # Add new root
        new_dir = tmp_path / "new"
        new_dir.mkdir()
        security.add_allowed_root(new_dir)

        assert len(security.allowed_roots) == 2
        assert new_dir.resolve() in security.allowed_roots

    def test_add_allowed_root_nonexistent(self):
        """Test that adding nonexistent root raises error."""
        security = PathSecurityService(allowed_roots=[str(Path.home())])

        with pytest.raises(ValueError) as exc:
            security.add_allowed_root("/nonexistent/path")

        assert "does not exist" in str(exc.value)

    def test_remove_allowed_root(self, tmp_path):
        """Test removing an allowed root directory."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        security = PathSecurityService(allowed_roots=[str(dir1), str(dir2)])
        assert len(security.allowed_roots) == 2

        # Remove one
        removed = security.remove_allowed_root(dir1)
        assert removed is True
        assert len(security.allowed_roots) == 1
        assert dir1.resolve() not in security.allowed_roots

    def test_remove_allowed_root_not_found(self, tmp_path):
        """Test removing non-existent root returns False."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        removed = security.remove_allowed_root("/nonexistent/path")
        assert removed is False

    def test_get_allowed_roots(self, tmp_path):
        """Test getting list of allowed roots."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])

        roots = security.get_allowed_roots()
        assert len(roots) == 1
        assert roots[0] == tmp_path.resolve()

        # Should be a copy, not the original
        roots.append(Path("/fake"))
        assert len(security.allowed_roots) == 1

    def test_symlink_handling(self, tmp_path):
        """Test that symlinks are resolved correctly."""
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()

        # Create a file in allowed directory
        real_file = allowed_dir / "real.txt"
        real_file.write_text("content")

        # Create symlink
        symlink = allowed_dir / "link.txt"
        try:
            symlink.symlink_to(real_file)

            security = PathSecurityService(allowed_roots=[str(allowed_dir)])

            # Should resolve symlink and validate
            validated = security.validate_path(symlink, must_exist=True)
            assert validated == symlink.resolve()

        except OSError:
            # Symlinks might not be supported on all systems
            pytest.skip("Symlinks not supported")

    def test_multiple_allowed_roots(self, tmp_path):
        """Test validation with multiple allowed roots."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        security = PathSecurityService(allowed_roots=[str(dir1), str(dir2)])

        # Create files in both directories
        file1 = dir1 / "test1.txt"
        file2 = dir2 / "test2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        # Both should validate
        validated1 = security.validate_path(file1, must_exist=True)
        validated2 = security.validate_path(file2, must_exist=True)

        assert validated1 == file1.resolve()
        assert validated2 == file2.resolve()

    def test_repr(self, tmp_path):
        """Test string representation."""
        security = PathSecurityService(allowed_roots=[str(tmp_path)])
        repr_str = repr(security)

        assert "PathSecurityService" in repr_str
        assert "roots=1" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
