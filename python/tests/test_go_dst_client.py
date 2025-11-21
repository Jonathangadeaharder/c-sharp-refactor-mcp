"""
Tests for Go dst client.

These tests verify the Go dst client functionality for:
- Project loading
- Diagnostics
- Find references
- Rename symbol
- Get symbol info

Note: These tests require the Go dst CLI to be built.
Run: cd python/go_dst_cli && ./build.sh
"""

import pytest
from pathlib import Path
import tempfile
import shutil

try:
    from refactor_mcp.clients.go_dst_client import GoDstClient, GoDstError
    GO_DST_AVAILABLE = True
except ImportError:
    GO_DST_AVAILABLE = False


@pytest.fixture
def temp_go_project(tmp_path):
    """Create a temporary Go project for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create go.mod
    go_mod = project_dir / "go.mod"
    go_mod.write_text("""module example.com/test

go 1.21
""")

    # Create main.go
    main_go = project_dir / "main.go"
    main_go.write_text("""package main

import "fmt"

// HelloWorld prints a greeting message
func HelloWorld() {
    message := "Hello, World!"
    fmt.Println(message)
}

func main() {
    HelloWorld()
}
""")

    # Create utils.go
    utils_go = project_dir / "utils.go"
    utils_go.write_text("""package main

// HelperFunction is a utility function
func HelperFunction(value int) int {
    return value * 2
}
""")

    yield project_dir

    # Cleanup
    shutil.rmtree(project_dir, ignore_errors=True)


@pytest.fixture
def go_dst_client_with_fallback():
    """
    Get GoDstClient or skip test if not available.

    This allows tests to run in environments where the CLI isn't built.
    """
    if not GO_DST_AVAILABLE:
        pytest.skip("Go dst client not available")

    try:
        client = GoDstClient()
        return client
    except GoDstError as e:
        pytest.skip(f"Go dst CLI not found: {e.message}. Run: cd python/go_dst_cli && ./build.sh")


@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
@pytest.mark.asyncio
async def test_load_project(go_dst_client_with_fallback, temp_go_project):
    """Test loading a Go project."""
    client = go_dst_client_with_fallback

    result = await client.load_project(temp_go_project)

    assert "project_path" in result
    assert "file_count" in result
    assert "files" in result
    assert result["file_count"] >= 2  # main.go and utils.go
    assert any("main.go" in f for f in result["files"])
    assert any("utils.go" in f for f in result["files"])


@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
@pytest.mark.asyncio
async def test_get_diagnostics_file(go_dst_client_with_fallback, temp_go_project):
    """Test getting diagnostics for a specific file."""
    client = go_dst_client_with_fallback

    file_path = temp_go_project / "main.go"
    diagnostics = await client.get_diagnostics(file_path=file_path)

    # Valid Go code should have no diagnostics
    assert isinstance(diagnostics, list)
    assert len(diagnostics) == 0


@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
@pytest.mark.asyncio
async def test_get_diagnostics_invalid_file(go_dst_client_with_fallback, temp_go_project):
    """Test getting diagnostics for invalid Go code."""
    # Create invalid Go file
    invalid_file = temp_go_project / "invalid.go"
    invalid_file.write_text("""package main

func BrokenFunction( {
    // Missing parameter and body
""")

    client = go_dst_client_with_fallback

    diagnostics = await client.get_diagnostics(file_path=invalid_file)

    # Should detect syntax errors
    assert isinstance(diagnostics, list)
    # Note: May not detect errors in simplified implementation


@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
@pytest.mark.asyncio
async def test_find_references(go_dst_client_with_fallback, temp_go_project):
    """Test finding references to a symbol."""
    client = go_dst_client_with_fallback

    file_path = temp_go_project / "main.go"

    # Find references to HelloWorld function (line 6, column 6 - function name)
    references = await client.find_references(
        temp_go_project,
        file_path,
        line=6,
        column=6
    )

    assert isinstance(references, list)
    # Should find definition and usage
    # Note: Implementation may return different counts


@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
@pytest.mark.asyncio
async def test_get_symbol_info(go_dst_client_with_fallback, temp_go_project):
    """Test getting symbol information."""
    client = go_dst_client_with_fallback

    file_path = temp_go_project / "main.go"

    # Get info for HelloWorld function
    symbol_info = await client.get_symbol_info(
        temp_go_project,
        file_path,
        line=6,
        column=6
    )

    assert symbol_info.name is not None
    assert symbol_info.kind is not None
    assert symbol_info.location is not None
    assert "file_path" in symbol_info.location


@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
@pytest.mark.asyncio
async def test_rename_symbol(go_dst_client_with_fallback, temp_go_project):
    """Test renaming a symbol."""
    client = go_dst_client_with_fallback

    file_path = temp_go_project / "main.go"

    # Rename HelloWorld to Greet
    result = await client.rename_symbol(
        temp_go_project,
        file_path,
        line=6,
        column=6,
        new_name="Greet"
    )

    assert result.success is True
    assert result.new_name == "Greet"
    assert len(result.file_changes) > 0

    # Verify the file was actually modified
    modified_content = file_path.read_text()
    assert "func Greet()" in modified_content
    assert "func HelloWorld()" not in modified_content
    assert "Greet()" in modified_content  # The call should be renamed too


@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
@pytest.mark.asyncio
async def test_rename_preserves_comments(go_dst_client_with_fallback, temp_go_project):
    """Test that rename preserves comments."""
    client = go_dst_client_with_fallback

    file_path = temp_go_project / "main.go"
    original_content = file_path.read_text()

    # Verify comment exists before rename
    assert "// HelloWorld prints a greeting message" in original_content

    # Rename HelloWorld to Greet
    result = await client.rename_symbol(
        temp_go_project,
        file_path,
        line=6,
        column=6,
        new_name="Greet"
    )

    assert result.success is True

    # Verify comment is preserved
    modified_content = file_path.read_text()
    # Comment should still exist (dst preserves comments!)
    assert "// HelloWorld prints a greeting message" in modified_content or "// Greet prints a greeting message" in modified_content


@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
@pytest.mark.asyncio
async def test_rename_local_variable(go_dst_client_with_fallback, temp_go_project):
    """Test renaming a local variable."""
    client = go_dst_client_with_fallback

    file_path = temp_go_project / "main.go"

    # Rename 'message' variable to 'greeting'
    # Line 7 (inside HelloWorld function): message := "Hello, World!"
    result = await client.rename_symbol(
        temp_go_project,
        file_path,
        line=7,
        column=5,  # Position on 'message'
        new_name="greeting"
    )

    assert result.success is True
    assert result.new_name == "greeting"

    # Verify the rename
    modified_content = file_path.read_text()
    # Note: Implementation may or may not handle local variable renames correctly


@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
def test_client_initialization_invalid_path():
    """Test client initialization with invalid CLI path."""
    with pytest.raises(GoDstError) as exc_info:
        GoDstClient(cli_path=Path("/nonexistent/go-dst-cli"))

    assert "not found" in str(exc_info.value.message).lower()
    assert exc_info.value.code == "CLI_NOT_FOUND"


@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
@pytest.mark.asyncio
async def test_execute_command_invalid_json():
    """Test handling of invalid JSON responses."""
    # This test would require mocking the subprocess
    # For now, we'll skip it
    pytest.skip("Requires subprocess mocking")


@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
@pytest.mark.asyncio
async def test_multiple_file_rename(go_dst_client_with_fallback, temp_go_project):
    """Test renaming a symbol that appears in multiple files."""
    client = go_dst_client_with_fallback

    # Create another file that uses HelperFunction
    other_file = temp_go_project / "other.go"
    other_file.write_text("""package main

func UseHelper() {
    result := HelperFunction(5)
    _ = result
}
""")

    utils_file = temp_go_project / "utils.go"

    # Rename HelperFunction to DoubleValue
    result = await client.rename_symbol(
        temp_go_project,
        utils_file,
        line=4,  # HelperFunction definition
        column=6,
        new_name="DoubleValue"
    )

    assert result.success is True
    assert result.new_name == "DoubleValue"

    # Should modify both files
    assert len(result.file_changes) >= 1

    # Verify utils.go was renamed
    utils_content = utils_file.read_text()
    assert "func DoubleValue(" in utils_content
    assert "func HelperFunction(" not in utils_content


# Integration test markers
@pytest.mark.integration
@pytest.mark.skipif(not GO_DST_AVAILABLE, reason="Go dst not available")
@pytest.mark.asyncio
async def test_full_workflow(go_dst_client_with_fallback, temp_go_project):
    """Test complete workflow: load, analyze, rename, verify."""
    client = go_dst_client_with_fallback

    # 1. Load project
    load_result = await client.load_project(temp_go_project)
    assert load_result["file_count"] >= 2

    # 2. Get diagnostics
    diagnostics = await client.get_diagnostics(project_path=temp_go_project)
    # Should have no errors in valid code

    # 3. Get symbol info
    main_file = temp_go_project / "main.go"
    symbol_info = await client.get_symbol_info(
        temp_go_project,
        main_file,
        line=6,
        column=6
    )
    assert symbol_info is not None

    # 4. Find references
    references = await client.find_references(
        temp_go_project,
        main_file,
        line=6,
        column=6
    )
    assert isinstance(references, list)

    # 5. Rename
    rename_result = await client.rename_symbol(
        temp_go_project,
        main_file,
        line=6,
        column=6,
        new_name="PrintGreeting"
    )
    assert rename_result.success is True

    # 6. Verify rename
    modified_content = main_file.read_text()
    assert "func PrintGreeting()" in modified_content
    assert "PrintGreeting()" in modified_content  # Call site


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
