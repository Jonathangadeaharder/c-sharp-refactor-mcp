# Refactor MCP - Python Edition

🚀 **Production-ready multi-language refactoring MCP server powered by FastMCP 2.0**

## Overview

This is a complete Python rewrite of the c-sharp-refactor-mcp project, leveraging FastMCP 2.0's production-ready features while maintaining the hybrid Roslyn + LSP architecture.

### Why Python?

- ✅ **FastMCP 2.0** - Production-ready with OAuth, testing, and deployment built-in
- ✅ **Faster Development** - 2-4 weeks to production vs 3-4 months in C#
- ✅ **Better Ecosystem** - Largest MCP community in 2025
- ✅ **Easy Contributions** - More accessible to contributors

### Architecture

```
FastMCP Server (Python)
├── OAuth Authentication (Google, GitHub, Azure) - Built-in
├── Testing Utilities - Built-in MockMCPClient
├── Deployment - FastMCP Cloud ready
└── Language Handlers
    ├── C#/VB.NET → Roslyn CLI (subprocess, 20-30ms overhead)
    ├── TypeScript → typescript-language-server (LSP)
    ├── Python → pyright + LibCST (native)
    ├── Go → gopls (LSP)
    ├── Rust → rust-analyzer (LSP)
    ├── C++ → clangd (LSP)
    └── Java → Eclipse JDT (LSP)
```

## Features

### Production-Ready (FastMCP 2.0)

- 🔐 **Zero-config OAuth** - Google, GitHub, Azure, Auth0, WorkOS, Descope
- 🧪 **Testing utilities** - MockMCPClient for integration tests
- 🚀 **Deployment** - FastMCP Cloud or self-hosted
- 📊 **Observability** - Metrics, tracing, logging built-in
- ⚡ **Rate limiting** - Prevent abuse
- 🔒 **Security** - Path validation, input sanitization

### Multi-Language Support (8 Languages)

- **C#** - Roslyn semantic analysis via CLI
- **VB.NET** - Roslyn semantic analysis via CLI
- **TypeScript** - typescript-language-server (LSP)
- **Python** - Pyright + LibCST (native)
- **Go** - gopls (LSP)
- **C++** - clangd (LSP)
- **Java** - Eclipse JDT (LSP)
- **Rust** - rust-analyzer (LSP)

### Refactoring Operations

- ✅ Rename symbol (semantic, scope-aware)
- ✅ Find all references (project-wide)
- ✅ Get diagnostics (errors, warnings)
- ✅ Get symbol information (metadata)
- ✅ Extract method (data flow analysis)
- ✅ Encapsulate field (property generation)
- ✅ Inline method (reverse of extract)
- ✅ Extract interface
- ✅ Move method to class

## Installation

### Prerequisites

**Core:**
- Python 3.11+
- pip or uv

**Language Servers (install only what you need):**
```bash
# TypeScript
npm install -g typescript-language-server typescript

# Python
npm install -g pyright

# Go
go install golang.org/x/tools/gopls@latest

# C++
apt-get install clangd  # or brew install llvm

# Java
# Download from https://download.eclipse.org/jdtls/

# Rust
rustup component add rust-analyzer
```

**Roslyn CLI (for C#/VB.NET):**
```bash
# Option 1: Use existing C# project's Roslyn CLI
cd ../roslyn-cli && dotnet build

# Option 2: Build standalone Roslyn CLI (included)
cd roslyn_cli && dotnet publish -c Release -o bin
```

### Quick Start

```bash
# Install with uv (recommended)
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"

# Run server
refactor-mcp

# Or with authentication
refactor-mcp --auth github

# Or deploy to cloud
refactor-mcp deploy
```

## Usage

### With Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "refactor-mcp": {
      "command": "uv",
      "args": ["run", "refactor-mcp"],
      "env": {
        "GITHUB_CLIENT_ID": "your_client_id",
        "GITHUB_CLIENT_SECRET": "your_secret"
      }
    }
  }
}
```

### With VS Code / GitHub Copilot

Create `.vscode/mcp.json`:

```json
{
  "servers": {
    "refactor-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "refactor-mcp"]
    }
  }
}
```

## Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov

# Specific test file
pytest tests/test_roslyn_client.py

# Watch mode
pytest-watch
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

### Project Structure

```
python/
├── src/refactor_mcp/
│   ├── __init__.py
│   ├── server.py           # Main FastMCP server
│   ├── cli.py              # CLI entry point
│   ├── config.py           # Configuration
│   ├── models.py           # Pydantic models
│   ├── clients/
│   │   ├── roslyn.py       # Roslyn CLI client (subprocess)
│   │   ├── lsp.py          # Generic LSP client
│   │   └── language_specific/
│   │       ├── typescript.py
│   │       ├── python.py
│   │       ├── go.py
│   │       └── ...
│   ├── tools/
│   │   ├── refactoring.py  # Core refactoring tools
│   │   ├── analysis.py     # Code analysis tools
│   │   └── diagnostics.py  # Diagnostic tools
│   └── utils/
│       ├── security.py     # Path validation
│       └── cache.py        # Caching utilities
├── tests/
│   ├── test_server.py
│   ├── test_roslyn_client.py
│   ├── test_lsp_client.py
│   └── test_tools.py
├── roslyn_cli/              # Standalone Roslyn CLI (C#)
│   ├── RoslynCLI.csproj
│   └── Program.cs
├── pyproject.toml
└── README.md
```

## Deployment

### FastMCP Cloud

```bash
# Deploy to cloud (zero config)
refactor-mcp deploy

# Deploy with custom domain
refactor-mcp deploy --domain refactor.example.com
```

### Self-Hosted (Docker)

```bash
# Build container
docker build -t refactor-mcp .

# Run with OAuth
docker run -p 8080:8080 \
  -e GITHUB_CLIENT_ID=your_id \
  -e GITHUB_CLIENT_SECRET=your_secret \
  refactor-mcp
```

### Azure Container Apps

```bash
# Deploy to Azure
az containerapp create \
  --name refactor-mcp \
  --resource-group mcp-servers \
  --image ghcr.io/yourusername/refactor-mcp:latest \
  --environment production \
  --target-port 8080 \
  --ingress external
```

## Performance

- **Roslyn (C#/VB.NET):** 20-30ms subprocess overhead (acceptable for refactoring)
- **LSP (other languages):** Direct process communication, ~10ms
- **Native Python:** Zero overhead
- **Concurrent operations:** Async/await for all I/O

## Comparison to C# Version

| Feature | Python (FastMCP) | C# (.NET) |
|---------|------------------|-----------|
| **OAuth** | ✅ Built-in (zero config) | ⚠️ Manual (3-4 weeks) |
| **Testing** | ✅ MockMCPClient | ⚠️ Manual (1-2 weeks) |
| **Deployment** | ✅ FastMCP Cloud | ⚠️ Manual (2-3 weeks) |
| **Development Speed** | ✅ 2-4 weeks to prod | ⚠️ 3-4 months |
| **Roslyn Access** | ⚠️ Subprocess (20-30ms) | ✅ Native |
| **Community** | ✅ Largest MCP ecosystem | ⚠️ Smaller |
| **Dependencies** | Python 3.11+ | .NET 8 runtime |

## Migration from C# Version

See [MIGRATION.md](MIGRATION.md) for detailed migration guide from the C# version.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](../docs/CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](../LICENSE) for details.

## Acknowledgments

- Built with [FastMCP 2.0](https://github.com/jlowin/fastmcp)
- Roslyn integration inspired by original C# implementation
- LSP integration based on community best practices
