# Multi-Language Refactor MCP Server

A semantic bridge between AI agents and your code, providing **safe, compiler-aware refactoring** across multiple programming languages through the Model Context Protocol (MCP).

## Overview

This server transforms AI-driven development by combining semantic analysis engines with AI agents. Instead of having AI generate refactored code (which is error-prone), this architecture allows agents to **request** refactorings that are executed by language-specific semantic engines:

- **C#**: Roslyn (.NET Compiler Platform)
- **VB.NET**: Roslyn (.NET Compiler Platform)
- **TypeScript**: TypeScript Language Server
- **Python**: Pyright (Python Type Checker & Language Server)
- **Go**: gopls
- **C++**: clangd
- **Java**: Eclipse JDT Language Server
- **Rust**: rust-analyzer

### Key Features

- **Multi-Language Support**: C#, VB.NET, TypeScript, Python, Go, C++, Java, and Rust
- **Semantic Safety**: All refactorings use language-specific semantic models, not text manipulation
- **Automatic Language Detection**: Detects language from project files
- **Unified API**: Same MCP tools work across all languages
- **Hybrid Architecture**: Roslyn for .NET languages, LSP for others
- **Project-Wide Operations**: Refactorings work across entire projects and all references
- **Path Security**: Validates all file access against configured allowed directories
- **MCP Protocol**: Standard protocol supported by Claude, GitHub Copilot, and other AI tools

## Architecture

### Core Components

1. **Language Provider Abstraction** (`ILanguageProvider`)
   - Unified interface for all language-specific operations
   - Plugin architecture for extensibility
   - Supports both Roslyn and LSP-based providers

2. **Language Providers**
   - **CSharpLanguageProvider**: Uses Roslyn for semantic analysis
   - **TypeScriptLanguageProvider**: Uses typescript-language-server via LSP
   - **GoLanguageProvider**: Uses gopls via LSP
   - **CppLanguageProvider**: Uses clangd via LSP
   - **JavaLanguageProvider**: Uses Eclipse JDT via LSP
   - **RustLanguageProvider**: Uses rust-analyzer via LSP

3. **LanguageDetectorService**
   - Automatically detects language from project files
   - Maps file extensions to language providers
   - Supports characteristic file detection (go.mod, Cargo.toml, etc.)

4. **LspClient**
   - Generic LSP (Language Server Protocol) client
   - Manages communication with language servers
   - Handles initialization, requests, and notifications

5. **PathSecurityService**
   - Validates all file paths against allowed directories
   - Prevents path traversal attacks
   - Configurable via `appsettings.json`

6. **UnifiedRefactoringTools**
   - Language-agnostic MCP tools
   - Automatically delegates to appropriate language provider
   - Consistent API across all languages

### Why This Architecture?

| Operation | Unsafe (Regex/Text) | Safe (Semantic Analysis) |
|-----------|---------------------|--------------------------|
| **Rename Symbol** | Breaks on same-named symbols in different scopes | Correctly handles scope, overloads, cross-file references |
| **Find References** | Finds text matches (including comments, strings) | Finds only true semantic references |
| **Extract Method** | Cannot determine correct signature | Uses data flow analysis for correct signature |

**Multi-Language Support:**
- **C#**: Full Roslyn integration with MSBuild workspace support
- **VB.NET**: Full Roslyn integration with MSBuild workspace support
- **TypeScript/JavaScript**: LSP-based with TypeScript compiler API backing
- **Python**: LSP-based with Pyright type checker and semantic analysis
- **Go**: LSP-based with gopls semantic analysis
- **C++**: LSP-based with clangd (LLVM) semantic analysis
- **Java**: LSP-based with Eclipse JDT compiler
- **Rust**: LSP-based with rust-analyzer semantic analysis

## Available Tools

### 1. `load_project`
Loads a project into memory. **Must be called first** before any other operations. Automatically detects the language.

**Supported Project Files:**
- C#: `.sln`, `.csproj`
- VB.NET: `.sln`, `.vbproj`
- TypeScript: `tsconfig.json`, `package.json`
- Python: `pyproject.toml`, `setup.py`, `requirements.txt`
- Go: `go.mod`
- C++: `CMakeLists.txt`, `compile_commands.json`
- Java: `pom.xml`, `build.gradle`
- Rust: `Cargo.toml`

**Parameters:**
- `projectPath` (string): Absolute path to project file

**Example:**
```json
{
  "name": "load_project",
  "arguments": {
    "projectPath": "/home/user/projects/MyProject/MyProject.sln"
  }
}
```

```json
{
  "name": "load_project",
  "arguments": {
    "projectPath": "/home/user/projects/my-app/tsconfig.json"
  }
}
```

### 2. `get_diagnostics`
Gets compilation diagnostics (errors, warnings). **Critical safety check** before refactoring.

**Parameters:**
- `solutionPath` (string): Path to solution
- `severityFilter` (string): "Error", "Warning", "Info", or "All" (default: "Warning")

**Returns:**
- `isSafeToRefactor` (bool): false if compilation errors exist
- `diagnostics` (array): List of issues with location and message

### 3. `find_all_references`
Finds all semantic references to a symbol across the solution.

**Parameters:**
- `solutionPath` (string): Path to solution
- `documentPath` (string): Path to .cs file
- `line` (int): Line number (1-based)
- `column` (int): Column number (1-based)

### 4. `rename_symbol`
Safely renames a symbol across the entire solution using Roslyn's Renamer API.

**Parameters:**
- `solutionPath` (string): Path to solution
- `documentPath` (string): Path to .cs file
- `line` (int): Line number of symbol
- `column` (int): Column number of symbol
- `newName` (string): New name for the symbol

**Safety Features:**
- Handles scope correctly (won't rename unrelated symbols with same name)
- Resolves overload conflicts
- Updates all projects and references
- Validates naming conventions

### 5. `get_symbol_info`
Gets detailed information about a symbol (type, namespace, accessibility, etc.).

**Parameters:**
- `solutionPath`, `documentPath`, `line`, `column`

### 6. `extract_method`
Extracts selected code into a new method with correct signature.

**Parameters:**
- `solutionPath` (string)
- `documentPath` (string)
- `startLine`, `startColumn` (int): Start of selection
- `endLine`, `endColumn` (int): End of selection
- `newMethodName` (string): Name for extracted method

**How It Works:**
1. Performs data flow analysis on selected code
2. Identifies input variables (DataFlowsIn) → method parameters
3. Identifies output variables (DataFlowsOut) → return values
4. Generates method with correct signature
5. Replaces selection with method call

### 7. `encapsulate_field`
Encapsulates a field by creating a property and updating all references.

**Parameters:**
- `solutionPath`, `documentPath`, `line`, `column`

**Process:**
1. Creates public property with get/set accessors
2. Makes field private
3. Finds all references to the field
4. Updates references to use property

## Installation & Setup

### Prerequisites

**Core:**
- .NET 8.0 SDK or later (required)
- MSBuild (installed with .NET SDK, required for C# support)

**Language Servers (install only what you need):**
- TypeScript: `npm install -g typescript-language-server typescript`
- Python: `npm install -g pyright`
- Go: `go install golang.org/x/tools/gopls@latest`
- C++: `apt-get install clangd` or `brew install llvm`
- Java: Eclipse JDT Language Server
- Rust: `rustup component add rust-analyzer`

See [INSTALLATION.md](docs/INSTALLATION.md) for detailed installation instructions.

### Build the Server

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

### Configure Security

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

**Important:** The server will only access files within these directories. This prevents path traversal attacks.

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

## Usage Examples

### AI Agent Workflow

**Recommended workflow for safe refactoring (works for all languages):**

```
1. AI: load_project("/path/to/project-file")
   → Server detects language and loads project
   → Examples: MyProject.sln, tsconfig.json, go.mod, Cargo.toml

2. AI: get_diagnostics("/path/to/project-file", "Error")
   → Server checks for compilation/lint errors
   → If errors found, AI should ask user to fix them first

3. AI: find_all_references("/path/to/project-file", "/path/to/source-file", 10, 15)
   → AI understands impact of changes

4. AI: rename_symbol(..., newName: "BetterName")
   → Server performs safe rename across project
   → All files updated semantically

5. AI: get_diagnostics(...) [Optional verification]
   → Confirms refactoring didn't break compilation
```

### Example Prompts for Different Languages

**C#:**
```
I have a C# solution at /home/user/projects/MyApp/MyApp.sln

Please use the multi-language-refactor tools to:
1. Load the solution
2. Check for compilation errors
3. Find all references to the "ProcessData" method in MyService.cs (line 45)
4. If safe, rename it to "ProcessDataAsync"
5. Verify no errors were introduced
```

**TypeScript:**
```
I have a TypeScript project at /home/user/projects/my-app/tsconfig.json

Please refactor my code:
1. Load the project
2. Find all references to the "getUserData" function in user.service.ts (line 23)
3. Rename it to "fetchUserData"
```

**Go:**
```
I have a Go project at /home/user/projects/my-service/go.mod

Please help me refactor:
1. Load the project
2. Find all references to the "ProcessRequest" function in handler.go (line 56)
3. Rename it to "HandleRequest"
```

**Rust:**
```
I have a Rust project at /home/user/projects/my-crate/Cargo.toml

Please refactor:
1. Load the project
2. Find all references to the "compute_value" function in lib.rs (line 34)
3. Rename it to "calculate_value"
```

## Performance Considerations

### Initial Load Time
- **First `load_solution` call**: Can take 5-30 seconds for large solutions
- **Subsequent operations**: Fast (uses cached workspace)
- **Cache invalidation**: Automatic on external file changes

### Memory Usage
- Loaded solutions stay in memory (1-3 GB for large enterprise solutions)
- Run as persistent process, not per-request
- Cache shared across all AI tool calls

### Concurrency
- Multiple **read** operations (diagnostics, find references): Run in parallel
- Multiple **write** operations (rename, extract): Serialized per solution
- Multiple solutions: Can be processed concurrently

## Code Quality & Structure

### Structurelint

The project uses [structurelint](https://github.com/Jonathangadeaharder/structurelint) to enforce project structure and organization standards. This ensures consistent naming conventions, directory organization, and prevents common issues like committed build artifacts or secrets.

**Running locally:**
```bash
structurelint .
```

See [docs/STRUCTURELINT.md](docs/STRUCTURELINT.md) for detailed configuration and usage.

## Continuous Integration

The project includes a GitHub Actions workflow that:
- ✅ Validates project structure with structurelint
- ✅ Builds the project
- ✅ Runs all tests
- ✅ Captures output to `build-test.log`
- ✅ **Amends the log to your commit** (auto-commits on push)

### Viewing CI Results

After pushing to your branch:

```bash
# Pull the amended commit (force required)
git pull --force

# View the CI log
cat build-test.log
```

Or view `build-test.log` directly on GitHub in your commit.

### Why This Pattern?

Traditional CI logs live in the GitHub Actions UI and expire. This workflow stores the log **in the commit itself**:

- ✅ Permanent record (doesn't expire)
- ✅ Offline access (clone repo, get logs)
- ✅ Version controlled (tied to specific commits)
- ✅ No dashboard needed (just `cat build-test.log`)

### Running Tests Locally

```bash
# Run all tests
dotnet test

# Run tests with detailed output
dotnet test --verbosity detailed

# Run tests with coverage (requires additional tools)
dotnet test /p:CollectCoverage=true
```

📖 **Full CI documentation**: See [docs/CI-WORKFLOW.md](docs/CI-WORKFLOW.md) for details on the amendment process, troubleshooting, and best practices.

## Troubleshooting

### "Failed to register MSBuild"
**Solution:** Install .NET SDK. MSBuild is required.

### "Path validation failed"
**Solution:** Add the solution's directory to `AllowedRootPaths` in `appsettings.json`.

### "No symbol found at specified position"
**Solution:**
- Ensure line/column numbers are 1-based (not 0-based)
- Position cursor directly on symbol name
- Run `get_diagnostics` to ensure code compiles

### Stale cache / "Changes not visible"
The server automatically detects file changes. If issues persist:
1. Reload the solution: Call `load_solution` again
2. The cache will refresh if timestamps changed

### Performance issues
- First load is slow (expected)
- If subsequent operations are slow, check solution size
- Consider splitting very large solutions

## Technical Details

### Protocol
- **Transport:** stdio (standard input/output)
- **Format:** JSON-RPC 2.0
- **Logging:** stderr only (stdout reserved for protocol)

### Roslyn APIs Used
- `MSBuildWorkspace`: Solution loading
- `SemanticModel`: Symbol resolution and semantic analysis
- `SymbolFinder`: Cross-solution reference finding
- `Renamer`: Safe symbol renaming
- `DataFlow Analysis`: Extract method signature generation
- `SyntaxRewriter`: Custom AST transformations
- `SyntaxGenerator`: Code generation

### Thread Safety
- Singleton `RoslynWorkspaceService` with `ConcurrentDictionary` caching
- Per-solution `SemaphoreSlim` locks for write operations
- Roslyn's immutable data structures enable lock-free reads

## Architecture Decisions

### Why MSBuildWorkspace?
- Only Roslyn workspace type that understands .sln and .csproj files
- Resolves project references and NuGet packages
- Required for full semantic model

### Why Stateful Service?
- Loading solutions is extremely expensive (10-30s for large codebases)
- Refactorings produce new `Solution` objects (immutable)
- Must maintain "head state" across operations

### Why MCP Protocol?
- Industry standard (Anthropic, Microsoft)
- Works with Claude, GitHub Copilot, and other tools
- Clean separation between AI (suggester) and compiler (executor)

## Future Enhancements

Potential additions to the tool suite:

1. **Code Analyzers**: Expose Roslyn analyzers for code quality checking
2. **Code Fixes**: Automatically apply compiler-suggested fixes
3. **Roslynator Integration**: Expose 500+ refactorings from Roslynator library
4. **Inline Method**: Reverse of extract method
5. **Move Type to File**: Move class to its own file
6. **Generate Constructor**: From selected fields
7. **Add Parameter**: To method with reference updates

## Contributing

This server implements the architecture described in "A New Architecture for AI-Driven Development: The Roslyn-MCP Server".

### Adding New Tools

1. Add method to `RefactoringTools` or `AdvancedRefactoringTools`
2. Mark with `[McpTool]` attribute
3. Add `[Description]` to method and all parameters
4. Inject `RoslynWorkspaceService` and `PathSecurityService`
5. Follow the pattern: validate → load → analyze → transform → commit

## References

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Roslyn Documentation](https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/)
- [MSBuildWorkspace](https://learn.microsoft.com/en-us/dotnet/api/microsoft.codeanalysis.msbuild.msbuildworkspace)
- [Semantic Model](https://learn.microsoft.com/en-us/dotnet/api/microsoft.codeanalysis.semanticmodel)

## License

MIT License - See [LICENSE](LICENSE) for details.

## Support

For issues, questions, or contributions, please [create an issue] or contact the maintainers.
