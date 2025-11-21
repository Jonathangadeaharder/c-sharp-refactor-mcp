"""
Tests for Python Rope client integration.
"""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from refactor_mcp.clients.rope_client import RopeClient, RopeError, ROPE_AVAILABLE


@pytest.fixture
def temp_python_project(tmp_path):
    """Create a temporary Python project for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create a simple Python file
    (project_dir / "module.py").write_text("""
def hello_world():
    '''Say hello to the world.'''
    message = "Hello, World!"
    print(message)
    return message

def greet(name):
    '''Greet someone by name.'''
    greeting = f"Hello, {name}!"
    print(greeting)
    return greeting

class MyClass:
    '''A simple class.'''

    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value
""")

    return project_dir


@pytest.mark.skipif(not ROPE_AVAILABLE, reason="Rope not installed")
@pytest.mark.asyncio
async def test_get_version():
    """Test getting Rope version."""
    client = RopeClient()
    version = await client.get_version()

    assert "rope_version" in version
    assert "client" in version
    assert version["client"] == "rope_client"


@pytest.mark.skipif(not ROPE_AVAILABLE, reason="Rope not installed")
@pytest.mark.asyncio
async def test_load_project(temp_python_project):
    """Test loading a Python project."""
    client = RopeClient()
    result = await client.load_project(temp_python_project)

    assert result["project_path"] == str(temp_python_project.resolve())
    assert result["file_count"] >= 1
    assert any("module.py" in f for f in result["files"])

    client.close_all_projects()


@pytest.mark.skipif(not ROPE_AVAILABLE, reason="Rope not installed")
@pytest.mark.asyncio
async def test_find_references(temp_python_project):
    """Test finding references to a symbol."""
    client = RopeClient()

    file_path = temp_python_project / "module.py"
    content = file_path.read_text()

    # Find offset of "message" variable (first occurrence)
    offset = content.find('message = "Hello, World!"')

    references = await client.find_references(
        temp_python_project, file_path, offset
    )

    # Should find at least 2 references (definition and print statement)
    assert len(references) >= 2
    assert all(ref.file_path == str(file_path) for ref in references)

    client.close_all_projects()


@pytest.mark.skipif(not ROPE_AVAILABLE, reason="Rope not installed")
@pytest.mark.asyncio
async def test_rename_symbol(temp_python_project):
    """Test renaming a symbol."""
    client = RopeClient()

    file_path = temp_python_project / "module.py"
    content = file_path.read_text()

    # Find offset of "hello_world" function
    offset = content.find("def hello_world")

    result = await client.rename_symbol(
        temp_python_project, file_path, offset + 4, "say_hello"  # +4 to be on function name
    )

    assert result.success is True
    assert result.new_name == "say_hello"
    assert result.files_modified == 1

    # Verify the rename actually happened
    new_content = file_path.read_text()
    assert "def say_hello" in new_content
    assert "def hello_world" not in new_content

    client.close_all_projects()


@pytest.mark.skipif(not ROPE_AVAILABLE, reason="Rope not installed")
@pytest.mark.asyncio
async def test_get_symbol_info(temp_python_project):
    """Test getting symbol information."""
    client = RopeClient()

    file_path = temp_python_project / "module.py"
    content = file_path.read_text()

    # Find offset of "hello_world" function
    offset = content.find("def hello_world") + 4

    symbol_info = await client.get_symbol_info(
        temp_python_project, file_path, offset
    )

    assert symbol_info.name == "hello_world"
    assert "hello" in symbol_info.name.lower()

    client.close_all_projects()


@pytest.mark.skipif(not ROPE_AVAILABLE, reason="Rope not installed")
@pytest.mark.asyncio
async def test_extract_method(temp_python_project):
    """Test extracting code into a new method."""
    client = RopeClient()

    file_path = temp_python_project / "module.py"
    content = file_path.read_text()

    # Find the lines we want to extract from hello_world
    start = content.find('message = "Hello, World!"')
    end = content.find('print(message)') + len('print(message)')

    result = await client.extract_method(
        temp_python_project, file_path, start, end, "display_message"
    )

    assert result.success is True
    assert result.extracted_method_name == "display_message"
    assert result.files_modified == 1

    # Verify extraction happened
    new_content = file_path.read_text()
    assert "def display_message" in new_content
    assert "display_message()" in new_content

    client.close_all_projects()


@pytest.mark.skipif(not ROPE_AVAILABLE, reason="Rope not installed")
@pytest.mark.asyncio
async def test_get_diagnostics_syntax_error(tmp_path):
    """Test getting diagnostics for file with syntax error."""
    project_dir = tmp_path / "bad_project"
    project_dir.mkdir()

    # Create file with syntax error
    bad_file = project_dir / "bad.py"
    bad_file.write_text("""
def broken_function(
    # Missing closing parenthesis
    print("This will fail")
""")

    client = RopeClient()
    diagnostics = await client.get_diagnostics(project_dir, bad_file)

    # Should detect syntax error
    assert len(diagnostics) > 0
    assert any(d.severity == "error" for d in diagnostics)

    client.close_all_projects()


@pytest.mark.skipif(not ROPE_AVAILABLE, reason="Rope not installed")
@pytest.mark.asyncio
async def test_close_project(temp_python_project):
    """Test closing a Rope project."""
    client = RopeClient()

    # Load project
    await client.load_project(temp_python_project)

    # Close it
    client.close_project(temp_python_project)

    # Should be able to load again
    result = await client.load_project(temp_python_project)
    assert result["file_count"] >= 1

    client.close_all_projects()


@pytest.mark.skipif(not ROPE_AVAILABLE, reason="Rope not installed")
def test_rope_error():
    """Test RopeError exception."""
    error = RopeError("Test error", "TEST_CODE")
    assert error.message == "Test error"
    assert error.code == "TEST_CODE"
    assert str(error) == "Test error"


@pytest.mark.skipif(ROPE_AVAILABLE, reason="Rope is installed")
def test_rope_not_installed():
    """Test error when Rope is not installed."""
    with pytest.raises(RopeError) as exc_info:
        RopeClient()

    assert exc_info.value.code == "ROPE_NOT_INSTALLED"
    assert "pip install rope" in exc_info.value.message
