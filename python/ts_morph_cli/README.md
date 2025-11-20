# TypeScript Morph CLI

Standalone TypeScript refactoring CLI using [ts-morph](https://ts-morph.com/) for the MCP server.

## Overview

This tool provides **Roslyn-level refactoring capabilities** for TypeScript projects, wrapping the TypeScript Compiler API via ts-morph. It communicates using a JSON protocol over stdin/stdout, matching the same interface as the Roslyn CLI.

## Features

### Supported Operations

- ✅ **load_project** - Load TypeScript project from tsconfig.json
- ✅ **get_diagnostics** - Get compilation errors and warnings
- ✅ **find_references** - Find all references to a symbol (project-wide)
- ✅ **rename_symbol** - Rename symbol across entire project
- ✅ **get_symbol_info** - Get symbol information and documentation
- ✅ **extract_method** - Extract selected code into a new function

### Advantages Over LSP

1. **Format Preservation** - ts-morph maintains formatting, comments, and whitespace
2. **Semantic Understanding** - Full TypeScript compiler type checking
3. **Project-Wide Refactoring** - Automatically handles all affected files
4. **Extract Method Support** - Not available in most LSP servers
5. **No Language Server Required** - Direct compiler API access

## Prerequisites

- Node.js 18 or higher
- npm 8 or higher

## Building

### Unix/macOS/Linux

```bash
chmod +x build.sh
./build.sh
```

### Windows

```cmd
build.bat
```

## Testing

### Unix/macOS/Linux

```bash
chmod +x test.sh
./test.sh
```

### Windows

```cmd
echo {"command":"version","parameters":{}} | node dist\index.js
```

## Usage

The CLI reads JSON from stdin and writes JSON to stdout.

### Request Format

```json
{
  "command": "command_name",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

### Response Format

**Success:**
```json
{
  "success": true,
  "result": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "message": "Error description",
    "code": "ERROR_CODE"
  }
}
```

## Commands

### version

Get CLI and TypeScript version information.

```bash
echo '{"command":"version","parameters":{}}' | node dist/index.js
```

**Response:**
```json
{
  "success": true,
  "result": {
    "version": "1.0.0",
    "ts_morph_version": "^21.0.1",
    "typescript_version": "^5.3.3"
  }
}
```

### load_project

Load a TypeScript project from its tsconfig.json.

```bash
echo '{
  "command": "load_project",
  "parameters": {
    "project_path": "/path/to/typescript/project"
  }
}' | node dist/index.js
```

**Response:**
```json
{
  "success": true,
  "result": {
    "project_path": "/absolute/path/to/project",
    "file_count": 42,
    "files": ["file1.ts", "file2.ts", ...]
  }
}
```

### get_diagnostics

Get TypeScript compilation diagnostics (errors, warnings).

```bash
# All files
echo '{
  "command": "get_diagnostics",
  "parameters": {
    "project_path": "/path/to/project"
  }
}' | node dist/index.js

# Specific file
echo '{
  "command": "get_diagnostics",
  "parameters": {
    "project_path": "/path/to/project",
    "file_path": "/path/to/file.ts"
  }
}' | node dist/index.js
```

**Response:**
```json
{
  "success": true,
  "result": {
    "diagnostics": [
      {
        "file_path": "/path/to/file.ts",
        "line": 10,
        "column": 5,
        "end_line": 10,
        "end_column": 15,
        "severity": "error",
        "message": "Type 'string' is not assignable to type 'number'",
        "code": "2322"
      }
    ]
  }
}
```

### find_references

Find all references to a symbol across the entire project.

```bash
echo '{
  "command": "find_references",
  "parameters": {
    "project_path": "/path/to/project",
    "file_path": "/path/to/file.ts",
    "line": 10,
    "column": 15
  }
}' | node dist/index.js
```

**Response:**
```json
{
  "success": true,
  "result": {
    "references": [
      {
        "file_path": "/path/to/file1.ts",
        "line": 5,
        "column": 10,
        "line_text": "const result = myFunction();",
        "is_definition": false
      },
      {
        "file_path": "/path/to/file2.ts",
        "line": 20,
        "column": 8,
        "line_text": "function myFunction() {",
        "is_definition": true
      }
    ]
  }
}
```

### rename_symbol

Rename a symbol across the entire project.

```bash
echo '{
  "command": "rename_symbol",
  "parameters": {
    "project_path": "/path/to/project",
    "file_path": "/path/to/file.ts",
    "line": 10,
    "column": 15,
    "new_name": "betterName"
  }
}' | node dist/index.js
```

**Response:**
```json
{
  "success": true,
  "result": {
    "changes": [
      {
        "file_path": "/path/to/file1.ts",
        "original_text": "...",
        "modified_text": "..."
      },
      {
        "file_path": "/path/to/file2.ts",
        "original_text": "...",
        "modified_text": "..."
      }
    ]
  }
}
```

### get_symbol_info

Get detailed information about a symbol at a specific location.

```bash
echo '{
  "command": "get_symbol_info",
  "parameters": {
    "project_path": "/path/to/project",
    "file_path": "/path/to/file.ts",
    "line": 10,
    "column": 15
  }
}' | node dist/index.js
```

**Response:**
```json
{
  "success": true,
  "result": {
    "name": "myFunction",
    "kind": "FunctionDeclaration",
    "file_path": "/path/to/file.ts",
    "line": 10,
    "column": 15,
    "definition_file": "/path/to/file.ts",
    "definition_line": 5,
    "definition_column": 10,
    "documentation": "This function does something useful"
  }
}
```

### extract_method

Extract selected code into a new function.

```bash
echo '{
  "command": "extract_method",
  "parameters": {
    "project_path": "/path/to/project",
    "file_path": "/path/to/file.ts",
    "start_line": 10,
    "start_column": 5,
    "end_line": 15,
    "end_column": 10,
    "method_name": "extractedFunction"
  }
}' | node dist/index.js
```

**Response:**
```json
{
  "success": true,
  "result": {
    "changes": [
      {
        "file_path": "/path/to/file.ts",
        "original_text": "...",
        "modified_text": "..."
      }
    ],
    "extracted_method_name": "extractedFunction"
  }
}
```

## Integration with Python MCP Server

The Python MCP server wraps this CLI using subprocess communication:

```python
from refactor_mcp.clients.ts_morph import TsMorphClient

# Create client
client = TsMorphClient()

# Load project
await client.load_project("/path/to/typescript/project")

# Rename symbol
result = await client.rename_symbol(
    project_path="/path/to/project",
    file_path="/path/to/file.ts",
    line=10,
    column=15,
    new_name="betterName"
)
```

## Architecture

```
┌─────────────────────┐
│  Python MCP Server  │
└──────────┬──────────┘
           │ JSON via stdin/stdout
           ▼
┌─────────────────────┐
│  ts-morph CLI       │
│  (Node.js)          │
└──────────┬──────────┘
           │ TypeScript Compiler API
           ▼
┌─────────────────────┐
│  TypeScript Project │
│  (tsconfig.json)    │
└─────────────────────┘
```

## Performance

- **Project Loading**: ~500ms for medium projects (100 files)
- **Find References**: ~200ms for typical symbol
- **Rename Symbol**: ~300ms for typical rename
- **Extract Method**: ~100ms

Performance scales linearly with project size. Projects are cached in memory for subsequent operations.

## Limitations

1. **Extract Method**: Current implementation is simplified. A full implementation would analyze variable scope, generate parameters, and handle return values properly.

2. **Memory Usage**: Large TypeScript projects (1000+ files) can use significant memory as the entire project is loaded into memory.

3. **tsconfig.json Required**: Projects must have a valid tsconfig.json file.

## Troubleshooting

**Error: "Source file not found"**
- Ensure the file path is correct and included in tsconfig.json

**Error: "No node found at position"**
- Line and column numbers are 1-based
- Verify the position is on an identifier, not whitespace

**Error: "Symbol at position is not renameable"**
- Position must be on a renameable symbol (variable, function, class, etc.)
- Built-in symbols cannot be renamed

**Performance Issues**
- Consider excluding test files and node_modules in tsconfig.json
- Use specific file operations instead of project-wide when possible

## License

MIT
