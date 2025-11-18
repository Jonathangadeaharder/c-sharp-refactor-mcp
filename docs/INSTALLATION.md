# Installation Guide

This guide will help you install and configure the Multi-Language Refactor MCP Server.

## Prerequisites

### Core Requirements

- **.NET 8.0 SDK or later** - Required for running the server and C# support
- **MSBuild** - Installed with .NET SDK, required for C# support

### Language Server Requirements (Optional)

Install language servers for the languages you want to use:

#### TypeScript
```bash
npm install -g typescript-language-server typescript
```

#### Go
```bash
go install golang.org/x/tools/gopls@latest
```

#### C++
Ubuntu/Debian:
```bash
sudo apt-get install clangd
```

macOS:
```bash
brew install llvm
```

#### Java
Download and install Eclipse JDT Language Server:
```bash
# Download from https://download.eclipse.org/jdtls/snapshots/
# Or use your distribution's package manager
```

#### Rust
```bash
rustup component add rust-analyzer
```

## Building the Server

```bash
# Clone the repository
cd /path/to/multi-language-refactor-server

# Restore dependencies
dotnet restore

# Build the project
dotnet build

# Optional: Publish as self-contained executable
dotnet publish -c Release -o ./publish
```

## Configuration

### 1. Security Configuration

Edit `appsettings.json` to set allowed root directories:

```json
{
  "Security": {
    "AllowedRootPaths": [
      "/home/user/projects",
      "/workspace",
      "C:\\dev",
      "C:\\Users\\YourName\\source"
    ]
  }
}
```

**Important:** The server will only access files within these directories to prevent path traversal attacks.

### 2. Language Server Configuration

You can customize language server commands in `appsettings.json`:

```json
{
  "LanguageServers": {
    "TypeScript": {
      "Command": "typescript-language-server",
      "Args": ["--stdio"]
    },
    "Go": {
      "Command": "gopls",
      "Args": []
    }
  }
}
```

## Client Configuration

### For Claude Desktop (Anthropic)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "multi-language-refactor": {
      "command": "dotnet",
      "args": [
        "run",
        "--project",
        "/absolute/path/to/RoslynRefactorServer.csproj"
      ]
    }
  }
}
```

Or if using published executable:

```json
{
  "mcpServers": {
    "multi-language-refactor": {
      "command": "/absolute/path/to/publish/RoslynRefactorServer"
    }
  }
}
```

### For VS Code / GitHub Copilot

Create `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "multi-language-refactor": {
      "type": "stdio",
      "command": "dotnet",
      "args": [
        "run",
        "--project",
        "/absolute/path/to/RoslynRefactorServer.csproj"
      ]
    }
  }
}
```

## Verification

After installation, test the server by loading a project:

```
load_project("/path/to/your/project.sln")  # C#
load_project("/path/to/your/tsconfig.json")  # TypeScript
load_project("/path/to/your/go.mod")  # Go
load_project("/path/to/your/Cargo.toml")  # Rust
```

## Troubleshooting

### "Failed to register MSBuild"
**Solution:** Install .NET SDK. C# support requires MSBuild.

### "Language server not found"
**Solution:** Install the corresponding language server for the language you want to use. The server will work with other languages even if one language server is missing.

### "Path validation failed"
**Solution:** Add the project's directory to `AllowedRootPaths` in `appsettings.json`.

### Language server crashes
**Solution:** Check that the language server is properly installed and accessible in your PATH. Check stderr logs for details.

## Platform-Specific Notes

### Windows
- Use backslashes in paths or escape forward slashes
- Ensure language servers are in your PATH
- Some language servers may require additional setup on Windows

### macOS/Linux
- Use forward slashes in paths
- Ensure language servers have execute permissions
- Some language servers may need to be added to PATH

## Next Steps

See the [README](../README.md) for usage examples and available tools.
