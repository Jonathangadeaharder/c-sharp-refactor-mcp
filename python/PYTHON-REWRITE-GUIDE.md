# Python Rewrite Implementation Guide

## Overview

This guide provides the complete implementation plan for rewriting c-sharp-refactor-mcp in Python using FastMCP 2.0.

**Status:** Foundation created (40% complete)
**Remaining Work:** 60% (estimated 4-6 weeks for complete rewrite)

---

## ✅ What's Already Implemented

### 1. Project Structure (`pyproject.toml`)
- FastMCP 2.0 dependency
- Pydantic for models
- Development tools (pytest, black, ruff, mypy)
- Optional Roslyn integration via pythonnet

### 2. Core Server (`src/refactor_mcp/server.py`)
- FastMCP server creation with lifespan management
- OAuth configuration (GitHub, Google, Azure)
- Rate limiting and observability
- Tool registration system

### 3. Data Models (`src/refactor_mcp/models.py`)
- All Pydantic models for requests/responses
- DiagnosticsInfo, ReferencesInfo, RenameResult, etc.
- AppContext for dependency injection
- Language and severity enums

### 4. Configuration (`src/refactor_mcp/config.py`)
- Environment-based configuration
- LSP server configs
- Security settings
- Auto-discovery of Roslyn CLI

### 5. Roslyn Client (`src/refactor_mcp/clients/roslyn.py`)
- Complete subprocess-based Roslyn client
- All refactoring operations
- Caching support
- Error handling

---

## 🚧 What Needs to Be Implemented

### Phase 1: Core Infrastructure (Week 1-2)

#### 1.1 LSP Client (`src/refactor_mcp/clients/lsp.py`)

```python
"""Generic LSP client for all language servers."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LspClient:
    """Generic LSP client following Language Server Protocol."""

    def __init__(self, command: str, args: list[str], workspace_root: str):
        self.command = command
        self.args = args
        self.workspace_root = workspace_root
        self._process: Optional[asyncio.subprocess.Process] = None
        self._message_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}

    async def start(self) -> None:
        """Start LSP server process."""
        self._process = await asyncio.create_subprocess_exec(
            self.command,
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Start reading responses
        asyncio.create_task(self._read_responses())

        # Initialize
        await self._initialize()

    async def stop(self) -> None:
        """Stop LSP server process."""
        if self._process:
            await self._send_notification("shutdown", {})
            await self._send_notification("exit", {})
            self._process.terminate()
            await self._process.wait()

    async def _initialize(self) -> None:
        """Send initialize request."""
        result = await self._send_request("initialize", {
            "processId": None,
            "rootUri": f"file://{self.workspace_root}",
            "capabilities": {
                "textDocument": {
                    "rename": {"prepareSupport": True},
                    "references": {},
                    "hover": {},
                },
                "workspace": {
                    "workspaceFolders": True,
                }
            }
        })

        await self._send_notification("initialized", {})

    async def rename(self, uri: str, line: int, column: int, new_name: str) -> Dict:
        """Rename symbol via LSP."""
        return await self._send_request("textDocument/rename", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
            "newName": new_name,
        })

    async def find_references(self, uri: str, line: int, column: int) -> list:
        """Find references via LSP."""
        return await self._send_request("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
            "context": {"includeDeclaration": True},
        })

    async def hover(self, uri: str, line: int, column: int) -> Dict:
        """Get hover info (symbol information)."""
        return await self._send_request("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": column},
        })

    async def _send_request(self, method: str, params: Dict) -> Any:
        """Send LSP request and wait for response."""
        self._message_id += 1
        request_id = self._message_id

        future = asyncio.Future()
        self._pending_requests[request_id] = future

        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        await self._write_message(message)
        return await future

    async def _send_notification(self, method: str, params: Dict) -> None:
        """Send LSP notification (no response expected)."""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        await self._write_message(message)

    async def _write_message(self, message: Dict) -> None:
        """Write JSON-RPC message with Content-Length header."""
        content = json.dumps(message).encode("utf-8")
        header = f"Content-Length: {len(content)}\r\n\r\n".encode("utf-8")

        self._process.stdin.write(header + content)
        await self._process.stdin.drain()

    async def _read_responses(self) -> None:
        """Read responses from LSP server."""
        while self._process:
            try:
                # Read Content-Length header
                header = await self._process.stdout.readline()
                if not header:
                    break

                # Parse content length
                content_length = int(header.decode().split(":")[1].strip())

                # Skip empty line
                await self._process.stdout.readline()

                # Read content
                content = await self._process.stdout.readexactly(content_length)
                message = json.loads(content)

                # Handle response
                if "id" in message and message["id"] in self._pending_requests:
                    future = self._pending_requests.pop(message["id"])
                    if "result" in message:
                        future.set_result(message["result"])
                    elif "error" in message:
                        future.set_exception(Exception(message["error"]["message"]))

            except Exception as e:
                logger.error(f"Error reading LSP response: {e}")
                break


class LspClientPool:
    """Pool of LSP clients for multiple languages."""

    def __init__(self, config):
        self.config = config
        self._clients: Dict[str, LspClient] = {}

    async def start(self) -> None:
        """Start client pool (clients created on-demand)."""
        pass

    async def stop(self) -> None:
        """Stop all clients."""
        for client in self._clients.values():
            await client.stop()

    async def get_client(self, language: str, workspace_root: str) -> LspClient:
        """Get or create LSP client for language."""
        key = f"{language}:{workspace_root}"

        if key not in self._clients:
            lsp_config = self.config.get_lsp_config(language)
            if not lsp_config:
                raise ValueError(f"No LSP config for language: {language}")

            client = LspClient(
                command=lsp_config.command,
                args=lsp_config.args,
                workspace_root=workspace_root,
            )
            await client.start()
            self._clients[key] = client

        return self._clients[key]
```

#### 1.2 Security Utility (`src/refactor_mcp/utils/security.py`)

```python
"""Path security validation."""

from pathlib import Path


class PathSecurityService:
    """Validates file paths against allowed roots."""

    def __init__(self, allowed_roots: list[str]):
        self.allowed_roots = [Path(root).resolve() for root in allowed_roots]

    def validate_path(self, path: str) -> Path:
        """Validate and normalize a path."""
        normalized = Path(path).resolve()

        # Check if path is under allowed roots
        if not any(str(normalized).startswith(str(root)) for root in self.allowed_roots):
            raise ValueError(
                f"Path not allowed: {path}. "
                f"Must be under one of: {[str(r) for r in self.allowed_roots]}"
            )

        return normalized

    def validate_project_file(self, path: str) -> Path:
        """Validate project file path."""
        validated = self.validate_path(path)

        if not validated.exists():
            raise FileNotFoundError(f"Project file not found: {path}")

        return validated

    def validate_source_file(self, path: str) -> Path:
        """Validate source file path."""
        validated = self.validate_path(path)

        if not validated.exists():
            raise FileNotFoundError(f"Source file not found: {path}")

        return validated
```

#### 1.3 Cache Utility (`src/refactor_mcp/utils/cache.py`)

```python
"""Caching utilities."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional


class CacheManager:
    """In-memory cache with TTL."""

    def __init__(self, max_size_mb: int = 4096, default_ttl: int = 3600):
        self.max_size_mb = max_size_mb
        self.default_ttl = default_ttl
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if datetime.now() < expires_at:
                    return value
                else:
                    del self._cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)

        async with self._lock:
            self._cache[key] = (value, expires_at)

            # TODO: Implement LRU eviction if cache too large

    async def delete(self, key: str) -> None:
        """Delete from cache."""
        async with self._lock:
            self._cache.pop(key, None)

    async def clear_namespace(self, namespace: str) -> None:
        """Clear all keys in namespace."""
        async with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(f"{namespace}:")]
            for key in keys_to_delete:
                del self._cache[key]
```

### Phase 2: Refactoring Tools (Week 2-3)

#### 2.1 Core Refactoring Tools (`src/refactor_mcp/tools/refactoring.py`)

```python
"""Core refactoring tools exposed as MCP tools."""

from fastmcp import Context

from ..models import AppContext, Language


def register_refactoring_tools(mcp):
    """Register all refactoring tools."""

    @mcp.tool()
    async def load_project(
        project_path: str,
        ctx: Context[AppContext, None],
    ) -> dict:
        """
        Load a project for refactoring.

        Supports C#, VB.NET, TypeScript, Python, Go, C++, Java, Rust.
        """
        # Validate path
        ctx.info(f"Loading project: {project_path}")
        validated_path = ctx.app_context.security.validate_project_file(project_path)

        # Detect language
        language = _detect_language(validated_path)

        # Load based on language
        if language in (Language.CSHARP, Language.VBNET):
            if not ctx.app_context.roslyn_client:
                return {"error": "Roslyn CLI not configured"}

            result = await ctx.app_context.roslyn_client.load_project(str(validated_path))
            return {"success": True, "language": language.value, **result}

        else:
            # For LSP languages, just return project info
            return {
                "success": True,
                "language": language.value,
                "projectPath": str(validated_path),
                "message": f"{language.value} project loaded via LSP",
            }

    @mcp.tool()
    async def rename_symbol(
        project_path: str,
        file_path: str,
        line: int,
        column: int,
        new_name: str,
        ctx: Context[AppContext, None],
    ) -> dict:
        """
        Rename a symbol (semantic, scope-aware).

        Works across all supported languages.
        """
        # Validate paths
        ctx.app_context.security.validate_project_file(project_path)
        ctx.app_context.security.validate_source_file(file_path)

        # Detect language
        language = _detect_language(Path(project_path))

        await ctx.report_progress(0.2, 1.0)

        # Route to appropriate client
        if language in (Language.CSHARP, Language.VBNET):
            if not ctx.app_context.roslyn_client:
                return {"error": "Roslyn CLI not configured"}

            result = await ctx.app_context.roslyn_client.rename_symbol(
                project_path, file_path, line, column, new_name
            )

            await ctx.report_progress(1.0, 1.0)
            return result.model_dump()

        else:
            # Use LSP
            workspace_root = Path(project_path).parent
            client = await ctx.app_context.lsp_pool.get_client(
                language.value, str(workspace_root)
            )

            uri = f"file://{file_path}"
            workspace_edit = await client.rename(uri, line - 1, column - 1, new_name)

            # Apply workspace edit
            # TODO: Apply edits to files

            await ctx.report_progress(1.0, 1.0)

            return {
                "success": True,
                "newName": new_name,
                "filesModified": len(workspace_edit.get("changes", {})),
            }

    # More tools...
    @mcp.tool()
    async def find_references(
        project_path: str,
        file_path: str,
        line: int,
        column: int,
        ctx: Context[AppContext, None],
    ) -> dict:
        """Find all references to a symbol."""
        # Similar pattern to rename_symbol
        pass

    @mcp.tool()
    async def get_symbol_info(
        project_path: str,
        file_path: str,
        line: int,
        column: int,
        ctx: Context[AppContext, None],
    ) -> dict:
        """Get detailed symbol information."""
        pass

    @mcp.tool()
    async def extract_method(
        project_path: str,
        file_path: str,
        start_line: int,
        start_column: int,
        end_line: int,
        end_column: int,
        method_name: str,
        ctx: Context[AppContext, None],
    ) -> dict:
        """Extract selected code into a new method."""
        pass


def _detect_language(path: Path) -> Language:
    """Detect language from project file extension."""
    ext = path.suffix.lower()

    if ext in (".sln", ".csproj"):
        return Language.CSHARP
    elif ext == ".vbproj":
        return Language.VBNET
    elif ext in ("tsconfig.json", "package.json"):
        return Language.TYPESCRIPT
    elif ext in ("pyproject.toml", "setup.py"):
        return Language.PYTHON
    elif ext == "go.mod":
        return Language.GO
    elif ext in ("CMakeLists.txt", "compile_commands.json"):
        return Language.CPP
    elif ext in ("pom.xml", "build.gradle"):
        return Language.JAVA
    elif ext == "Cargo.toml":
        return Language.RUST
    else:
        raise ValueError(f"Unknown project type: {ext}")
```

### Phase 3: Testing & Deployment (Week 3-4)

#### 3.1 Tests (`tests/test_server.py`)

```python
"""Tests for FastMCP server."""

import pytest
from fastmcp.testing import MockMCPClient

from refactor_mcp.server import create_server


@pytest.fixture
def server():
    """Create test server."""
    return create_server(auth_provider=None, enable_metrics=False)


@pytest.fixture
async def client(server):
    """Create test client."""
    return MockMCPClient(server)


@pytest.mark.asyncio
async def test_load_project_csharp(client):
    """Test loading C# project."""
    result = await client.call_tool("load_project", {
        "projectPath": "/test/MyApp.sln"
    })

    assert result["success"] is True
    assert result["language"] == "csharp"


@pytest.mark.asyncio
async def test_rename_symbol(client):
    """Test renaming symbol."""
    result = await client.call_tool("rename_symbol", {
        "projectPath": "/test/MyApp.sln",
        "filePath": "/test/Class1.cs",
        "line": 10,
        "column": 15,
        "newName": "NewName",
    })

    assert result["success"] is True
```

#### 3.2 Docker (`Dockerfile`)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    dotnet-sdk-8.0 \\
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY src/ src/
COPY roslyn_cli/ roslyn_cli/

# Install Python dependencies
RUN pip install uv && uv pip install --system .

# Build Roslyn CLI
RUN cd roslyn_cli && dotnet publish -c Release -o bin

# Set environment
ENV REFACTOR_MCP_ROSLYN_CLI_PATH=/app/roslyn_cli/bin/RoslynCLI

# Run server
CMD ["refactor-mcp"]
```

#### 3.3 CLI (`src/refactor_mcp/cli.py`)

```python
"""CLI entry point."""

import argparse
import logging

from .server import create_server
from fastmcp.auth import OAuthProvider


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Refactor MCP Server")
    parser.add_argument("--auth", choices=["github", "google", "azure"], help="OAuth provider")
    parser.add_argument("--log-level", default="INFO", help="Log level")
    parser.add_argument("--deploy", action="store_true", help="Deploy to FastMCP Cloud")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=args.log_level)

    # Map auth provider
    auth_provider = None
    if args.auth == "github":
        auth_provider = OAuthProvider.GITHUB
    elif args.auth == "google":
        auth_provider = OAuthProvider.GOOGLE
    elif args.auth == "azure":
        auth_provider = OAuthProvider.AZURE

    # Create server
    server = create_server(auth_provider=auth_provider)

    # Deploy or run
    if args.deploy:
        server.deploy_to_cloud()
    else:
        server.run()


if __name__ == "__main__":
    main()
```

---

## 📋 Complete File Checklist

### Core Files
- [x] `pyproject.toml` - Project configuration
- [x] `README.md` - Documentation
- [x] `src/refactor_mcp/server.py` - FastMCP server
- [x] `src/refactor_mcp/models.py` - Pydantic models
- [x] `src/refactor_mcp/config.py` - Configuration
- [x] `src/refactor_mcp/clients/roslyn.py` - Roslyn client
- [ ] `src/refactor_mcp/clients/lsp.py` - LSP client
- [ ] `src/refactor_mcp/utils/security.py` - Security
- [ ] `src/refactor_mcp/utils/cache.py` - Caching
- [ ] `src/refactor_mcp/tools/refactoring.py` - Refactoring tools
- [ ] `src/refactor_mcp/tools/analysis.py` - Analysis tools
- [ ] `src/refactor_mcp/tools/diagnostics.py` - Diagnostic tools
- [ ] `src/refactor_mcp/cli.py` - CLI
- [ ] `src/refactor_mcp/__init__.py` - Package init
- [ ] `src/refactor_mcp/clients/__init__.py` - Clients init
- [ ] `src/refactor_mcp/utils/__init__.py` - Utils init
- [ ] `src/refactor_mcp/tools/__init__.py` - Tools init

### Tests
- [ ] `tests/test_server.py` - Server tests
- [ ] `tests/test_roslyn_client.py` - Roslyn tests
- [ ] `tests/test_lsp_client.py` - LSP tests
- [ ] `tests/test_tools.py` - Tool tests
- [ ] `tests/conftest.py` - Pytest fixtures

### Deployment
- [ ] `Dockerfile` - Container image
- [ ] `.dockerignore` - Docker ignore
- [ ] `.env.example` - Environment template
- [ ] `docker-compose.yml` - Local deployment

### Roslyn CLI (C# Tool)
- [ ] `roslyn_cli/Program.cs` - CLI implementation
- [ ] `roslyn_cli/RoslynCLI.csproj` - C# project
- [ ] `roslyn_cli/Commands/` - Command implementations

### Documentation
- [x] `PYTHON-REWRITE-GUIDE.md` - This guide
- [ ] `MIGRATION.md` - Migration from C# version
- [ ] `DEPLOYMENT.md` - Deployment guide
- [ ] `DEVELOPMENT.md` - Development guide

---

## 🚀 Next Steps

1. **Implement remaining infrastructure files** (Week 1-2)
   - LSP client
   - Security and cache utilities
   - Init files

2. **Implement all refactoring tools** (Week 2-3)
   - Complete tools/refactoring.py
   - Add tools/analysis.py
   - Add tools/diagnostics.py

3. **Build Roslyn CLI** (Week 3)
   - Standalone C# CLI tool
   - JSON-based protocol
   - All refactoring operations

4. **Write comprehensive tests** (Week 3-4)
   - Unit tests for all components
   - Integration tests for tools
   - End-to-end tests

5. **Create deployment artifacts** (Week 4)
   - Docker image
   - FastMCP Cloud deployment
   - Documentation

6. **Migrate existing features** (Week 4-6)
   - Port C# optimizations (LRU cache, etc.)
   - Ensure feature parity
   - Performance testing

---

## 📊 Estimated Timeline

- **Week 1-2:** Core infrastructure (LSP, utils, tools skeleton)
- **Week 3:** Roslyn CLI + tool implementations
- **Week 4:** Testing + deployment
- **Week 5-6:** Migration, optimization, documentation

**Total:** 4-6 weeks for complete rewrite with feature parity

---

## 🎯 Success Criteria

- [ ] All 8 languages supported (C#, VB.NET, TS, Python, Go, C++, Java, Rust)
- [ ] All 7+ refactoring operations implemented
- [ ] OAuth authentication working (GitHub, Google)
- [ ] 80%+ test coverage
- [ ] Docker deployment working
- [ ] FastMCP Cloud deployment working
- [ ] Performance within 20-30% of C# version for Roslyn operations
- [ ] Migration guide completed

---

## 🔗 Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [Roslyn APIs](https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

This guide provides the complete roadmap for finishing the Python rewrite!
