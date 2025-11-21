# Roslyn CLI Tool

Standalone command-line tool that wraps Microsoft Roslyn APIs for C# and VB.NET refactoring operations.

## Overview

This CLI tool communicates via JSON over stdin/stdout, making it easy to integrate with any language.
The Python MCP server uses this tool to provide C#/VB.NET refactoring capabilities.

## Protocol

**Request Format:**
```json
{
  "command": "command_name",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**Response Format:**
```json
{
  "success": true,
  "result": {
    "key": "value"
  }
}
```

**Error Format:**
```json
{
  "success": false,
  "error": "Error message"
}
```

## Supported Commands

### 1. version
Get CLI and Roslyn version information.

**Parameters:** None

**Response:**
```json
{
  "version": "1.0.0",
  "roslyn": "4.11.0"
}
```

### 2. load_project
Load a C#/VB.NET project or solution.

**Parameters:**
- `projectPath` (string): Path to .sln, .csproj, or .vbproj file

**Response:**
```json
{
  "documentCount": 42,
  "projectCount": 3,
  "language": "csharp"
}
```

### 3. get_diagnostics
Get compilation diagnostics (errors, warnings, info messages).

**Parameters:**
- `projectPath` (string): Path to project/solution
- `severityFilter` (string, optional): "Error", "Warning", "Info", "All" (default: "Warning")

**Response:**
```json
{
  "errorCount": 0,
  "warningCount": 5,
  "infoCount": 10,
  "isSafeToRefactor": true,
  "diagnostics": [
    {
      "severity": "Warning",
      "message": "Variable 'x' is assigned but never used",
      "filePath": "/path/to/file.cs",
      "line": 42,
      "column": 5,
      "diagnosticId": "CS0219"
    }
  ]
}
```

### 4. find_references
Find all references to a symbol.

**Parameters:**
- `projectPath` (string): Path to project/solution
- `filePath` (string): Path to source file
- `line` (number): Line number (1-based)
- `column` (number): Column number (1-based)

**Response:**
```json
{
  "symbolName": "MyMethod",
  "referenceCount": 5,
  "references": [
    {
      "filePath": "/path/to/file.cs",
      "line": 10,
      "column": 15,
      "preview": "var result = MyMethod();"
    }
  ]
}
```

### 5. rename_symbol
Rename a symbol (variable, method, class, etc.) across entire codebase.

**Parameters:**
- `projectPath` (string): Path to project/solution
- `filePath` (string): Path to source file
- `line` (number): Line number (1-based)
- `column` (number): Column number (1-based)
- `newName` (string): New symbol name

**Response:**
```json
{
  "success": true,
  "symbolName": "OldName",
  "filesModified": 3,
  "locationsModified": 7
}
```

**Note:** This command modifies files on disk!

### 6. get_symbol_info
Get detailed information about a symbol.

**Parameters:**
- `projectPath` (string): Path to project/solution
- `filePath` (string): Path to source file
- `line` (number): Line number (1-based)
- `column` (number): Column number (1-based)

**Response:**
```json
{
  "name": "MyMethod",
  "kind": "Method",
  "type": "System.String",
  "containingType": "MyClass",
  "containingNamespace": "MyNamespace",
  "isStatic": false,
  "isAbstract": false,
  "isVirtual": false,
  "accessibility": "Public",
  "documentation": "XML documentation string"
}
```

### 7. extract_method
Extract selected code into a new method.

**Status:** Not yet implemented (MVP)

## Building

### Prerequisites
- .NET 8.0 SDK

### Build Release
```bash
dotnet build -c Release
```

### Build and Publish (Self-Contained)
```bash
# For Linux
dotnet publish -c Release -r linux-x64 --self-contained

# For macOS
dotnet publish -c Release -r osx-x64 --self-contained

# For Windows
dotnet publish -c Release -r win-x64 --self-contained
```

The output will be in `bin/Release/net8.0/{runtime}/publish/`

## Usage Example

```bash
# Echo JSON request and pipe to CLI
echo '{"command":"version","parameters":{}}' | ./roslyn-cli

# Or via Python
import subprocess
import json

request = {
    "command": "load_project",
    "parameters": {"projectPath": "/path/to/project.csproj"}
}

process = subprocess.Popen(
    ['./roslyn-cli'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

stdout, stderr = process.communicate(json.dumps(request).encode('utf-8'))
response = json.loads(stdout.decode('utf-8'))
print(response)
```

## Integration with Python MCP Server

The Python MCP server automatically discovers and uses this CLI tool:

1. Place the built executable in `python/roslyn_cli/bin/` or configure `ROSLYN_CLI_PATH` environment variable
2. The server will use subprocess to communicate with the CLI
3. Each refactoring request spawns a new process (20-30ms overhead)
4. Python server handles caching, so CLI remains stateless

## Performance

- Cold start: ~500-1000ms (MSBuildWorkspace initialization)
- Warm operations: ~100-500ms per operation
- Subprocess overhead: ~20-30ms
- Total typical operation: 200-1000ms (acceptable for refactoring)

## Testing

```bash
# Test version command
echo '{"command":"version","parameters":{}}' | dotnet run

# Test with sample project
echo '{"command":"load_project","parameters":{"projectPath":"../../test-project/SampleProject/SampleProject.csproj"}}' | dotnet run
```

## Limitations

1. **Stateless:** Each invocation loads the project from scratch (Python server caches)
2. **Single Operation:** One command per process (can't chain operations)
3. **Extract Method:** Not yet implemented (requires complex code generation)
4. **Memory:** Can be memory-intensive for large solutions (>100 projects)

## Future Enhancements

1. **Persistent Server Mode:** Keep workspace loaded between requests (would eliminate cold start)
2. **Extract Method:** Implement using Roslyn's code generation APIs
3. **Batch Operations:** Support multiple operations in one invocation
4. **Incremental Updates:** Use Roslyn's incremental compilation for faster repeated operations

## Architecture

```
Python MCP Server
    ↓ (subprocess)
Roslyn CLI (this tool)
    ↓ (in-process)
Microsoft.CodeAnalysis (Roslyn)
    ↓
MSBuildWorkspace
    ↓
C#/VB.NET Project Files
```

## License

Same as parent project (MIT)
