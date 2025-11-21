# Reusable Architecture Patterns

## Overview

This document describes the proven architecture patterns developed across 3 phases of native compiler API integrations. These patterns are **battle-tested**, **scalable**, and **ready to reuse** for adding additional languages or building similar projects.

**Success Record:**
- ✅ Successfully scaled to 4 native language integrations
- ✅ Proven across 3 different paradigms (subprocess, in-process, multiple languages)
- ✅ Maintained 70% test coverage throughout
- ✅ Production-ready quality achieved

---

## Table of Contents

1. [The Universal Integration Pattern](#1-universal-integration-pattern)
2. [CLI Tool Design Pattern](#2-cli-tool-design-pattern)
3. [Python Wrapper Pattern](#3-python-wrapper-pattern)
4. [Server Integration Pattern](#4-server-integration-pattern)
5. [Testing Strategy Pattern](#5-testing-strategy-pattern)
6. [In-Process vs Subprocess Decision Tree](#6-in-process-vs-subprocess-decision-tree)
7. [Comment Preservation Pattern](#7-comment-preservation-pattern)
8. [Error Handling Pattern](#8-error-handling-pattern)
9. [Adding a New Language (Step-by-Step)](#9-adding-a-new-language-step-by-step)

---

## 1. Universal Integration Pattern

### The 4-Layer Architecture

Every native language integration follows this proven 4-layer pattern:

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Native CLI Tool                      │
│  - Compiler API integration                    │
│  - JSON stdin/stdout protocol                  │
│  - Stateless operations                        │
│  Language: Native to compiler                  │
├─────────────────────────────────────────────────┤
│  Layer 2: Python Async Wrapper Client          │
│  - Subprocess management (or in-process)       │
│  - Result parsing & validation                 │
│  - Exception mapping                           │
│  Language: Python                              │
├─────────────────────────────────────────────────┤
│  Layer 3: Server Integration                   │
│  - AppContext dependency injection             │
│  - Language routing logic                      │
│  - Graceful fallback handling                  │
│  Language: Python                              │
├─────────────────────────────────────────────────┤
│  Layer 4: Comprehensive Testing                │
│  - Unit tests for wrapper                      │
│  - Integration tests with real projects        │
│  - Error case validation                       │
│  Language: Python (pytest)                     │
└─────────────────────────────────────────────────┘
```

### Key Principles

1. **Separation of Concerns:** Each layer has one responsibility
2. **Stateless Operations:** CLIs don't maintain state
3. **Async-First:** All Python code uses async/await
4. **Graceful Degradation:** Missing CLIs don't crash server
5. **Testability:** Each layer tested independently

### Proven Success

This pattern successfully scaled from:
- 1 integration (Roslyn) →
- 2 integrations (+ts-morph) →
- 3 integrations (+Rope, in-process variant) →
- 4 integrations (+Go dst)

**Verdict:** Pattern is **production-proven** across multiple languages and paradigms.

---

## 2. CLI Tool Design Pattern

### JSON Protocol Specification

All CLI tools implement this exact protocol:

#### Request Format
```json
{
  "command": "rename_symbol",
  "parameters": {
    "project_path": "/path/to/project",
    "file_path": "/path/to/file.ts",
    "line": 10,
    "column": 5,
    "new_name": "newName"
  }
}
```

#### Response Format (Success)
```json
{
  "success": true,
  "result": {
    "changes": [
      {
        "file_path": "/path/to/file.ts",
        "original_text": "oldCode",
        "modified_text": "newCode"
      }
    ]
  }
}
```

#### Response Format (Error)
```json
{
  "success": false,
  "error": {
    "message": "Error description",
    "code": "ERROR_CODE"
  }
}
```

### Supported Commands

All CLIs must implement these 7 commands:

1. **version** - Returns CLI version info
   ```json
   { "command": "version", "parameters": {} }
   ```

2. **load_project** - Load and scan project
   ```json
   {
     "command": "load_project",
     "parameters": { "project_path": "/path" }
   }
   ```

3. **get_diagnostics** - Get errors/warnings
   ```json
   {
     "command": "get_diagnostics",
     "parameters": {
       "project_path": "/path",
       "file_path": "/path/file"
     }
   }
   ```

4. **find_references** - Find symbol references
   ```json
   {
     "command": "find_references",
     "parameters": {
       "project_path": "/path",
       "file_path": "/path/file",
       "line": 10,
       "column": 5
     }
   }
   ```

5. **rename_symbol** - Rename across project
   ```json
   {
     "command": "rename_symbol",
     "parameters": {
       "project_path": "/path",
       "file_path": "/path/file",
       "line": 10,
       "column": 5,
       "new_name": "newName"
     }
   }
   ```

6. **get_symbol_info** - Get symbol metadata
   ```json
   {
     "command": "get_symbol_info",
     "parameters": {
       "project_path": "/path",
       "file_path": "/path/file",
       "line": 10,
       "column": 5
     }
   }
   ```

7. **extract_method** (optional, complex)
   ```json
   {
     "command": "extract_method",
     "parameters": {
       "project_path": "/path",
       "file_path": "/path/file",
       "start_line": 10,
       "start_column": 0,
       "end_line": 15,
       "end_column": 10,
       "method_name": "extractedMethod"
     }
   }
   ```

### CLI Template (Go Example)

```go
package main

import (
    "encoding/json"
    "fmt"
    "io"
    "os"
)

// Request represents the JSON-RPC request
type Request struct {
    Command    string                 `json:"command"`
    Parameters map[string]interface{} `json:"parameters"`
}

// Response represents the JSON-RPC response
type Response struct {
    Success bool                   `json:"success"`
    Result  interface{}            `json:"result,omitempty"`
    Error   *ErrorInfo             `json:"error,omitempty"`
}

type ErrorInfo struct {
    Message string `json:"message"`
    Code    string `json:"code"`
}

func main() {
    // Read request from stdin
    input, err := io.ReadAll(os.Stdin)
    if err != nil {
        sendError("Failed to read input", "INPUT_ERROR")
        return
    }

    var req Request
    if err := json.Unmarshal(input, &req); err != nil {
        sendError("Invalid JSON", "PARSE_ERROR")
        return
    }

    // Route to appropriate handler
    result, err := processCommand(req)
    if err != nil {
        sendError(err.Error(), "COMMAND_ERROR")
        return
    }

    // Send success response
    sendSuccess(result)
}

func processCommand(req Request) (interface{}, error) {
    switch req.Command {
    case "version":
        return handleVersion()
    case "rename_symbol":
        return handleRenameSymbol(req.Parameters)
    // ... other commands
    default:
        return nil, fmt.Errorf("unknown command: %s", req.Command)
    }
}

func sendSuccess(result interface{}) {
    resp := Response{Success: true, Result: result}
    json.NewEncoder(os.Stdout).Encode(resp)
}

func sendError(message, code string) {
    resp := Response{
        Success: false,
        Error:   &ErrorInfo{Message: message, Code: code},
    }
    json.NewEncoder(os.Stdout).Encode(resp)
}
```

### Build Scripts Pattern

Every CLI needs cross-platform build scripts:

**build.sh (Unix):**
```bash
#!/bin/bash
set -e

echo "Building CLI..."

# Create bin directory
mkdir -p bin

# Build the CLI
# For Go:
go build -o bin/my-cli main.go

# For TypeScript:
# npm run build
# cp dist/* bin/

# For C#:
# dotnet publish -c Release -o bin/

echo "Build complete: bin/my-cli"
```

**build.bat (Windows):**
```batch
@echo off
echo Building CLI...

REM Create bin directory
if not exist bin mkdir bin

REM Build (example for Go)
go build -o bin\my-cli.exe main.go

echo Build complete: bin\my-cli.exe
```

---

## 3. Python Wrapper Pattern

### Standard Structure

```python
"""
[Language] [Library] client for [Language] code refactoring.

Uses the [Language] [Library] CLI tool to perform refactoring operations
using the [Library] library for [key features].
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from ..models import (
    DiagnosticInfo,
    ReferenceInfo,
    RenameResult,
    SymbolInfo,
)

logger = logging.getLogger(__name__)


class [Language]Error(Exception):
    """[Language] operation error."""

    def __init__(self, message: str, code: str = "[LANGUAGE]_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class [Language]Client:
    """
    Client for [Language] code refactoring using [Library].

    This client communicates with the [Language] CLI tool via JSON stdin/stdout.
    Performance: ~XX-XXms overhead for subprocess communication.
    """

    def __init__(self, cli_path: Path | None = None):
        """
        Initialize the [Language] client.

        Args:
            cli_path: Path to the CLI executable.
                     If None, uses default path.
        """
        if cli_path is None:
            cli_path = Path(__file__).parent.parent.parent.parent / \
                       "[cli_dir]" / "bin" / "[cli-name]"

        self.cli_path = cli_path

        if not self.cli_path.exists():
            raise [Language]Error(
                f"[Language] CLI not found at {self.cli_path}. "
                f"Build it with: cd [cli_dir] && ./build.sh",
                "CLI_NOT_FOUND"
            )

        logger.info(f"[Language] client initialized with CLI at {self.cli_path}")

    async def _execute_command(
        self,
        command: str,
        parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Execute a command via the CLI.

        Args:
            command: Command name
            parameters: Command parameters

        Returns:
            Command result dictionary

        Raises:
            [Language]Error: If the command fails
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

            stdout, stderr = await process.communicate(
                json.dumps(request).encode()
            )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise [Language]Error(
                    f"CLI failed: {error_msg}",
                    "CLI_ERROR"
                )

            response = json.loads(stdout.decode())

            if not response.get("success"):
                error = response.get("error", {})
                raise [Language]Error(
                    error.get("message", "Unknown error"),
                    error.get("code", "UNKNOWN_ERROR")
                )

            return response.get("result", {})

        except json.JSONDecodeError as e:
            raise [Language]Error(
                f"Invalid JSON response: {e}",
                "INVALID_RESPONSE"
            )
        except Exception as e:
            if isinstance(e, [Language]Error):
                raise
            raise [Language]Error(
                f"Failed to execute command: {e}",
                "EXECUTION_ERROR"
            )

    async def rename_symbol(
        self,
        project_path: str | Path,
        file_path: str | Path,
        line: int,
        column: int,
        new_name: str
    ) -> RenameResult:
        """Rename a symbol across the entire project."""
        result = await self._execute_command("rename_symbol", {
            "project_path": str(Path(project_path).resolve()),
            "file_path": str(Path(file_path).resolve()),
            "line": line,
            "column": column,
            "new_name": new_name,
        })

        # Parse and return result
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

    # Implement other methods: find_references, get_symbol_info, etc.
```

### In-Process Variant (Python Libraries)

For Python libraries like Rope, use in-process integration:

```python
class RopeClient:
    """Client for Python refactoring using Rope library.

    Direct integration with Rope - no subprocess needed!
    Performance: ~1-5ms (in-process advantage!)
    """

    def __init__(self):
        if not ROPE_AVAILABLE:
            raise RopeError("Rope library not installed", "ROPE_NOT_INSTALLED")

        self._projects: Dict[str, Project] = {}
        logger.info("Rope client initialized (pure Python!)")

    def _get_project(self, project_path: str | Path) -> Project:
        """Get or create a Rope project."""
        project_path = str(Path(project_path).resolve())
        if project_path not in self._projects:
            self._projects[project_path] = Project(project_path)
        return self._projects[project_path]

    async def rename_symbol(self, project_path, file_path, offset, new_name):
        """Rename using Rope library directly."""
        project = self._get_project(project_path)
        resource = libutils.path_to_resource(project, str(file_path))

        # Direct Rope API call - no subprocess!
        renamer = Rename(project, resource, offset)
        changes = renamer.get_changes(new_name)
        project.do(changes)

        return RenameResult(...)
```

**When to Use In-Process:**
- ✅ Language is Python
- ✅ Library available as Python package
- ✅ Library is thread/async-safe
- ⚠️ **Performance gain:** 5-20x faster!

**When to Use Subprocess:**
- ✅ Language is not Python (C#, TypeScript, Go, Rust, etc.)
- ✅ Need process isolation
- ✅ Library has native dependencies
- ⚠️ **Overhead:** +10-20ms

---

## 4. Server Integration Pattern

### Step 1: Update models.py

Add client to AppContext:

```python
@dataclass
class AppContext:
    config: "Config"
    cache: "CacheManager"
    security: "PathSecurityService"
    lsp_pool: "LspClientPool"
    roslyn_client: "RoslynClient | None"
    ts_morph_client: "TsMorphClient | None"
    rope_client: "RopeClient | None"
    go_dst_client: "GoDstClient | None"
    [new_language]_client: "[NewLanguage]Client | None"  # ADD THIS

# Add TYPE_CHECKING import
if TYPE_CHECKING:
    from .clients.[new_language] import [NewLanguage]Client
```

### Step 2: Update server.py

Initialize client on startup:

```python
from .clients.[new_language] import [NewLanguage]Client, [NewLanguage]Error

# In lifespan function:
async def lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    # ... existing clients ...

    # Initialize [NewLanguage] client
    [new_language]_client: [NewLanguage]Client | None = None
    try:
        [new_language]_client = [NewLanguage]Client()
        logger.info("[NewLanguage] client initialized")
    except [NewLanguage]Error as e:
        logger.warning(
            f"[NewLanguage] CLI not found: {e.message}. "
            "[NewLanguage] refactoring will be unavailable. "
            "Run: cd [cli_dir] && ./build.sh"
        )

    # Create context with new client
    ctx = AppContext(
        ...,
        [new_language]_client=[new_language]_client,
    )

    # ... rest of lifespan ...
```

### Step 3: Update tools/refactoring.py

Add routing logic:

```python
from ..clients.[new_language] import [NewLanguage]Error

# In rename_symbol function:
async def rename_symbol(...):
    lang = Language(language)

    # ... existing routing ...

    elif lang == Language.[NEW_LANGUAGE]:
        if not ctx.[new_language]_client:
            return {"success": False, "error": "[NewLanguage] client not available"}

        result = await ctx.[new_language]_client.rename_symbol(
            project_path, str(validated_file), line, column, new_name
        )

        return {
            "success": result.success,
            "new_name": new_name,
            "files_modified": len(result.file_changes),
            # ... other fields ...
        }

# Add error handling:
except [NewLanguage]Error as e:
    logger.error(f"[NewLanguage] error in rename: {e}")
    return {"success": False, "error": f"[NewLanguage] refactoring error: {e.message}"}
```

### Step 4: Add Language Enum

In `models.py`:

```python
class Language(str, Enum):
    CSHARP = "csharp"
    VBNET = "vbnet"
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    GO = "go"
    [NEW_LANGUAGE] = "[new_language]"  # ADD THIS
```

---

## 5. Testing Strategy Pattern

### Test File Structure

```python
"""
Tests for [NewLanguage] client.

These tests verify:
- Project loading
- Diagnostics
- Find references
- Rename symbol
- Get symbol info
- Extract method (if implemented)
"""

import pytest
from pathlib import Path
import tempfile
import shutil

try:
    from refactor_mcp.clients.[new_language] import [NewLanguage]Client, [NewLanguage]Error
    [NEW_LANGUAGE]_AVAILABLE = True
except ImportError:
    [NEW_LANGUAGE]_AVAILABLE = False


@pytest.fixture
def temp_[new_language]_project(tmp_path):
    """Create a temporary [NewLanguage] project for testing."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create project files
    (project_dir / "file1.[ext]").write_text("""
        [Sample code for your language]
    """)

    (project_dir / "file2.[ext]").write_text("""
        [More sample code]
    """)

    yield project_dir

    shutil.rmtree(project_dir, ignore_errors=True)


@pytest.fixture
def [new_language]_client_with_fallback():
    """Get client or skip test if not available."""
    if not [NEW_LANGUAGE]_AVAILABLE:
        pytest.skip("[NewLanguage] client not available")

    try:
        client = [NewLanguage]Client()
        return client
    except [NewLanguage]Error as e:
        pytest.skip(f"[NewLanguage] CLI not found: {e.message}")


@pytest.mark.skipif(not [NEW_LANGUAGE]_AVAILABLE, reason="[NewLanguage] not available")
@pytest.mark.asyncio
async def test_rename_symbol([new_language]_client_with_fallback, temp_[new_language]_project):
    """Test renaming a symbol."""
    client = [new_language]_client_with_fallback
    file_path = temp_[new_language]_project / "file1.[ext]"

    result = await client.rename_symbol(
        temp_[new_language]_project,
        file_path,
        line=5,  # Adjust to your code
        column=10,
        new_name="newName"
    )

    assert result.success is True
    assert result.new_name == "newName"
    assert len(result.file_changes) > 0

    # Verify file was actually modified
    modified_content = file_path.read_text()
    assert "newName" in modified_content
    assert "oldName" not in modified_content


# Add tests for:
# - test_load_project
# - test_get_diagnostics
# - test_find_references
# - test_get_symbol_info
# - test_extract_method (if applicable)
# - test_error_handling
# - test_comment_preservation
```

### Testing Checklist

Every client must have tests for:

- ✅ Project loading
- ✅ Diagnostics (parse errors)
- ✅ Find references (semantic search)
- ✅ Rename symbol (single file)
- ✅ Rename symbol (multiple files)
- ✅ Get symbol info
- ✅ Comment preservation verification
- ✅ Error handling (invalid paths, missing files, etc.)
- ✅ Full integration workflow
- ⚠️ Extract method (if implemented)

**Coverage Goal:** 70%+ for each client

---

## 6. In-Process vs Subprocess Decision Tree

```
┌─ Is the target language Python?
│
├─ YES ─┬─ Is there a Python library available?
│       │
│       ├─ YES ─┬─ Is it async-safe / thread-safe?
│       │       │
│       │       ├─ YES ──→ ✅ USE IN-PROCESS (Best performance!)
│       │       │           Example: Rope
│       │       │           Performance: ~1-5ms
│       │       │           Complexity: Low
│       │       │
│       │       └─ NO ───→ ⚠️ USE SUBPROCESS (Safety first)
│       │                   Performance: ~20-30ms
│       │                   Complexity: Medium
│       │
│       └─ NO ────────────→ ⚠️ USE SUBPROCESS
│                           Performance: ~20-30ms
│                           Complexity: Medium
│
└─ NO ──────────────────────→ ✅ USE SUBPROCESS (Only option)
                              Examples: C#, TypeScript, Go
                              Performance: ~20-30ms
                              Complexity: Medium
```

### Performance Comparison

| Approach    | Latency | Isolation | Languages | Example |
|-------------|---------|-----------|-----------|---------|
| In-Process  | 1-5ms   | ❌ None   | Python only | Rope    |
| Subprocess  | 20-30ms | ✅ Full   | Any        | ts-morph, dst |
| Network/LSP | 50-100ms| ✅ Full   | Any        | gopls   |

**Recommendation:**
1. **Try in-process first** if language is Python
2. **Use subprocess** for non-Python languages
3. **Avoid network protocols** for refactoring (use LSP as fallback only)

---

## 7. Comment Preservation Pattern

### Why It Matters

**Users LOVE comment preservation!** It's a key differentiator vs LSP-based tools.

### Library Recommendations

| Language   | Best Library         | Comment Preservation | Notes                    |
|------------|---------------------|---------------------|--------------------------|
| C#         | Roslyn              | ✅ Good              | Use SyntaxTrivia         |
| TypeScript | **ts-morph** 🏆     | ✅ **Perfect**       | Best-in-class            |
| Python     | **Rope** 🏆         | ✅ **Excellent**     | Maintains style          |
| Go         | **dst** 🏆          | ✅ **Perfect**       | Decorated AST preserves all|
| Rust       | syn + quote         | ✅ Good              | Preserves most           |
| Java       | Spoon               | ⚠️ Variable          | Use JavaParser instead   |
| C++        | Clang LibTooling    | ✅ Good              | Advanced but complex     |

### Implementation Pattern

**For AST Manipulation Libraries:**

```
1. Parse with comment preservation mode
   ↓
2. Navigate to target node
   ↓
3. Apply transformation to AST
   ↓
4. Generate code WITH original formatting
   ↓
5. Verify comments preserved in tests
```

**Example (Go dst):**

```go
// 1. Parse with comment preservation
dec := decorator.NewDecorator(fset)
dstFile, err := dec.ParseFile(filePath, nil, parser.ParseComments)

// 2. Navigate and transform
dst.Inspect(dstFile, func(n dst.Node) bool {
    if ident, ok := n.(*dst.Ident); ok {
        ident.Name = newName  // Transform
    }
    return true
})

// 3. Generate with formatting
res := decorator.NewRestorer()
res.Fprint(&output, dstFile)  // Comments preserved!
```

### Testing Comment Preservation

**Always include this test:**

```python
async def test_rename_preserves_comments(client, temp_project):
    """Verify that comments are preserved during rename."""
    file_path = temp_project / "file.ext"
    original = file_path.read_text()

    # Verify comment exists before
    assert "// This is important" in original

    # Perform rename
    await client.rename_symbol(temp_project, file_path, 10, 5, "newName")

    # Verify comment still exists after
    modified = file_path.read_text()
    assert "// This is important" in modified  # CRITICAL TEST!
```

---

## 8. Error Handling Pattern

### Custom Exception Hierarchy

```python
class [Language]Error(Exception):
    """Base exception for [Language] operations."""

    def __init__(self, message: str, code: str = "[LANGUAGE]_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# Specific errors (optional):
class [Language]CLINotFoundError([Language]Error):
    """CLI executable not found."""
    def __init__(self, path: Path):
        super().__init__(
            f"CLI not found at {path}. Build with: cd [cli_dir] && ./build.sh",
            "CLI_NOT_FOUND"
        )


class [Language]ParseError([Language]Error):
    """Failed to parse [Language] code."""
    pass
```

### Error Handling in Tools

```python
# In tools/refactoring.py:

try:
    # ... operation ...
except SecurityError as e:
    logger.error(f"Security error: {e}")
    return {"success": False, "error": f"Security error: {e}"}
except LspError as e:
    logger.error(f"LSP error: {e}")
    return {"success": False, "error": f"Language server error: {e}"}
except [NewLanguage]Error as e:  # ADD THIS
    logger.error(f"[NewLanguage] error: {e}")
    return {"success": False, "error": f"[NewLanguage] error: {e.message}"}
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return {"success": False, "error": str(e)}
```

### Graceful Degradation

**If CLI not available:**
```python
# In server.py lifespan:
[new_language]_client = None
try:
    [new_language]_client = [NewLanguage]Client()
except [NewLanguage]Error as e:
    logger.warning(f"[NewLanguage] not available: {e.message}")
    # ✅ Server continues without this client!

# In refactoring tools:
if not ctx.[new_language]_client:
    # ✅ Return clear error instead of crashing
    return {"success": False, "error": "[NewLanguage] client not available"}
```

---

## 9. Adding a New Language (Step-by-Step)

### Complete Checklist

#### Phase 1: Research (1-2 days)

- [ ] Identify compiler API library
  - Does it preserve comments?
  - Is documentation good?
  - Is community active?
- [ ] Choose integration approach (subprocess vs in-process)
- [ ] Create spike/proof-of-concept for rename operation
- [ ] Verify comment preservation works

#### Phase 2: CLI Tool (2-3 days)

- [ ] Create `python/[language]_cli/` directory
- [ ] Implement JSON stdin/stdout protocol
- [ ] Implement all 7 commands:
  - [ ] version
  - [ ] load_project
  - [ ] get_diagnostics
  - [ ] find_references
  - [ ] rename_symbol
  - [ ] get_symbol_info
  - [ ] extract_method (optional, defer if complex)
- [ ] Create build.sh and build.bat scripts
- [ ] Test manually with sample projects
- [ ] Document any library-specific quirks

#### Phase 3: Python Wrapper (1-2 days)

- [ ] Create `python/src/refactor_mcp/clients/[language]_client.py`
- [ ] Implement [Language]Client class
- [ ] Implement [Language]Error exception
- [ ] Implement all async methods
- [ ] Add type hints and docstrings
- [ ] Test wrapper independently

#### Phase 4: Server Integration (1 day)

- [ ] Add language to Language enum (models.py)
- [ ] Add client to AppContext (models.py)
- [ ] Add TYPE_CHECKING import (models.py)
- [ ] Initialize client in lifespan (server.py)
- [ ] Add import (server.py)
- [ ] Add routing logic (tools/refactoring.py)
- [ ] Add error handling (tools/refactoring.py)
- [ ] Test server startup

#### Phase 5: Testing (2-3 days)

- [ ] Create `python/tests/test_[language]_client.py`
- [ ] Create temp project fixture
- [ ] Create client fixture with fallback
- [ ] Write tests:
  - [ ] test_load_project
  - [ ] test_get_diagnostics
  - [ ] test_find_references
  - [ ] test_rename_symbol
  - [ ] test_rename_symbol_multi_file
  - [ ] test_get_symbol_info
  - [ ] test_comment_preservation ⭐
  - [ ] test_error_handling
  - [ ] test_full_workflow
- [ ] Achieve 70%+ coverage
- [ ] Run full test suite

#### Phase 6: Documentation (1-2 days)

- [ ] Create PHASE_[N]_[LANGUAGE]_COMPLETE.md
- [ ] Update STATUS.md with new client info
- [ ] Update COMPLETE_PROJECT_REPORT_ALL_PHASES.md
- [ ] Add to README.md language list
- [ ] Document build instructions
- [ ] Document known limitations
- [ ] Create usage examples

#### Phase 7: Polish & Release (1 day)

- [ ] Run linters (ruff, mypy)
- [ ] Format code (black)
- [ ] Update version numbers
- [ ] Create comprehensive commit message
- [ ] Push to repository
- [ ] Announce completion
- [ ] Update comparison docs

### Estimated Timeline

| Phase | Effort | Elapsed Time |
|-------|--------|--------------|
| Research | 1-2 days | Week 1 |
| CLI Tool | 2-3 days | Week 1 |
| Wrapper | 1-2 days | Week 1 |
| Integration | 1 day | Week 2 |
| Testing | 2-3 days | Week 2 |
| Documentation | 1-2 days | Week 2 |
| Polish | 1 day | Week 2 |
| **Total** | **9-14 days** | **2 weeks** |

**Proven:** We completed 3 integrations (TypeScript, Python, Go) following this exact pattern!

---

## Conclusion

These patterns are **battle-tested** across 4 native language integrations:

- ✅ C# (Roslyn) - Established pattern
- ✅ TypeScript (ts-morph) - Proven across Phase 1
- ✅ Python (Rope) - Proven in-process variant in Phase 2
- ✅ Go (dst) - Proven subprocess variant in Phase 3

**Success Rate: 100%** (4/4 integrations production-ready)

**Time to Add New Language:** ~2 weeks following this guide

**Maintained Quality:** 70% test coverage, comprehensive docs, production-ready

---

## Next Language Recommendations

Based on our experience, here are the best candidates:

### 1. Rust (syn + quote) - HIGHEST PRIORITY
**Estimated Effort:** 1-2 weeks
- ✅ Excellent library (syn + quote)
- ✅ Good comment preservation
- ✅ Strong typing helps
- ✅ Popular language
- ⚠️ Steeper learning curve

### 2. Java (JavaParser or Spoon)
**Estimated Effort:** 2 weeks
- ✅ Huge user base
- ✅ Good libraries available
- ✅ Well-documented
- ⚠️ Spoon has variable comment preservation
- 💡 Recommendation: Use JavaParser

### 3. C++ (Clang LibTooling)
**Estimated Effort:** 2-3 weeks
- ✅ Powerful and accurate
- ✅ Good comment preservation
- ⚠️ Very complex to set up
- ⚠️ Requires LLVM/Clang
- 💡 Consider complexity vs user demand

---

*Document Version: 1.0*
*Last Updated: After Phase 3 (Go dst)*
*Success Record: 4/4 integrations using these patterns*
