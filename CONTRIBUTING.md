# Contributing to Roslyn-MCP Server

Thank you for your interest in contributing to the Roslyn-MCP Server project! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- .NET 8.0 SDK or later
- Git
- A C# IDE (Visual Studio, VS Code with C# extension, or Rider)
- Basic understanding of Roslyn and the Model Context Protocol

### Getting Started

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/roslyn-refactor-server.git
   cd roslyn-refactor-server
   ```

2. **Build the Project**
   ```bash
   dotnet restore
   dotnet build
   ```

3. **Configure Security**
   Edit `appsettings.json` to add your development directories to `AllowedRootPaths`.

4. **Test with Sample Project**
   ```bash
   # In one terminal, run the server
   dotnet run

   # The server will wait for MCP input on stdin
   # Configure your AI client to connect to it
   ```

## Project Structure

```
RoslynRefactorServer/
├── Models/                 # Data transfer objects
│   ├── ReferenceLocation.cs
│   └── DiagnosticInfo.cs
├── Services/              # Core services
│   ├── RoslynWorkspaceService.cs  # Workspace management
│   └── PathSecurityService.cs     # Security validation
├── Tools/                 # MCP tool implementations
│   ├── RefactoringTools.cs        # Basic tools
│   └── AdvancedRefactoringTools.cs # Complex refactorings
├── Program.cs             # Entry point and DI setup
├── appsettings.json       # Configuration
└── test-project/          # Test solution
```

## Adding a New Tool

### 1. Choose the Right Class

- **RefactoringTools**: Simple, read-only operations or high-level Roslyn APIs
- **AdvancedRefactoringTools**: Complex operations requiring custom rewriters

### 2. Implement the Tool

```csharp
[McpTool]
[Description("Clear description of what this tool does. " +
             "The AI reads this to decide when to call it.")]
public async Task<string> my_new_tool(
    [Description("What this parameter is for")] string solutionPath,
    [Description("What this parameter is for")] string documentPath,
    [Description("What this parameter is for")] int someValue)
{
    try
    {
        _logger.LogInformation("Starting my_new_tool");

        // 1. Security validation
        _securityService.ValidateSolutionFile(solutionPath);
        _securityService.ValidateDocumentFile(documentPath);

        // 2. Load solution
        var solution = await _workspaceService.LoadOrRefreshSolutionAsync(solutionPath);

        // 3. Perform analysis or transformation
        // ... your logic here ...

        // 4. For write operations: commit changes
        if (isWriteOperation)
        {
            await _workspaceService.UpdateAndApplyChangesAsync(solutionPath, newSolution);
        }

        // 5. Return JSON result
        return JsonSerializer.Serialize(new
        {
            success = true,
            message = "Operation completed",
            // ... other data ...
        }, new JsonSerializerOptions { WriteIndented = true });
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Failed to execute my_new_tool");
        return JsonSerializer.Serialize(new { success = false, error = ex.Message });
    }
}
```

### 3. Key Principles

✅ **DO:**
- Use semantic APIs (SemanticModel, ISymbol, etc.)
- Validate paths with PathSecurityService
- Use RoslynWorkspaceService for all solution access
- Return structured JSON (with `success` field)
- Log operations for debugging
- Handle exceptions gracefully

❌ **DON'T:**
- Use string manipulation or regex on code
- Access files directly (use Roslyn APIs)
- Modify the workspace without UpdateAndApplyChangesAsync
- Return plain text (always use JSON)
- Assume the code compiles (check diagnostics when needed)

## Testing Guidelines

### Manual Testing

1. **Start the server:**
   ```bash
   dotnet run
   ```

2. **Test with the sample project:**
   - Use the `test-project/` solution
   - Follow test scenarios in `test-project/README.md`

3. **Verify thread safety:**
   - Make multiple concurrent requests
   - Ensure no data corruption

### Unit Testing (Future)

We plan to add unit tests. Contributions welcome!

```csharp
[Fact]
public async Task RenameSymbol_ShouldUpdateAllReferences()
{
    // Arrange
    var workspace = CreateTestWorkspace();
    var service = new RoslynWorkspaceService(logger);

    // Act
    var result = await tools.rename_symbol(solutionPath, ...);

    // Assert
    Assert.Contains("success", result);
}
```

## Common Pitfalls

### 1. Position Confusion (0-based vs 1-based)

MCP tools use **1-based** line/column (user-friendly), but Roslyn uses **0-based** positions:

```csharp
// Convert 1-based to 0-based
var position = text.Lines[line - 1].Start + (column - 1);
```

### 2. Forgetting to Update Cache

Always use `UpdateAndApplyChangesAsync`:

```csharp
// ❌ WRONG
_workspace.TryApplyChanges(newSolution);

// ✅ CORRECT
await _workspaceService.UpdateAndApplyChangesAsync(solutionPath, newSolution);
```

### 3. Concurrent Writes

Write operations **must** be atomic:

```csharp
// The service handles locking, but you must use it:
await _workspaceService.UpdateAndApplyChangesAsync(solutionPath, newSolution);
```

### 4. Assuming Clean Compilation

Always check for errors first:

```csharp
var compilation = await project.GetCompilationAsync();
if (compilation.GetDiagnostics().Any(d => d.Severity == DiagnosticSeverity.Error))
{
    return JsonSerializer.Serialize(new {
        success = false,
        error = "Project has compilation errors"
    });
}
```

## Code Style

- **Formatting**: Use default C# formatting (4 spaces, no tabs)
- **Naming**: PascalCase for public members, _camelCase for private fields
- **Async**: All I/O operations must be async
- **Logging**: Use ILogger for all important operations
- **Comments**: Document WHY, not WHAT

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/my-new-tool
   ```

2. **Make your changes**
   - Follow code style
   - Add logging
   - Test thoroughly

3. **Update documentation**
   - Add tool to README.md
   - Update ARCHITECTURE.md if needed
   - Add examples

4. **Commit with clear messages**
   ```bash
   git commit -m "Add tool for inline method refactoring"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/my-new-tool
   ```

6. **PR Description Template**
   ```markdown
   ## Description
   Brief description of the change

   ## New Tool Added
   - Tool name: `my_new_tool`
   - Purpose: What it does
   - Roslyn APIs used: SemanticModel, Renamer, etc.

   ## Testing
   - [ ] Tested with sample project
   - [ ] Handles errors gracefully
   - [ ] Thread-safe
   - [ ] Documentation updated

   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Logging added
   - [ ] Security validation included
   - [ ] README updated
   ```

## Feature Ideas

Looking for contribution ideas? Here are some high-value features:

### High Priority
- [ ] **Inline Method**: Reverse of extract method
- [ ] **Move Type to File**: Move class to its own file
- [ ] **Add Parameter**: Add parameter to method and update all calls
- [ ] **Generate Constructor**: From selected fields/properties
- [ ] **Introduce Variable**: Extract expression to local variable

### Medium Priority
- [ ] **Code Metrics**: Cyclomatic complexity, maintainability index
- [ ] **Unused Code Detection**: Find unused methods, classes, etc.
- [ ] **Roslyn Analyzers Integration**: Run built-in analyzers
- [ ] **Code Fixes Integration**: Apply suggested fixes

### Advanced
- [ ] **Roslynator Integration**: Expose 500+ refactorings
- [ ] **Multi-Solution Support**: Operate across multiple solutions
- [ ] **Incremental Compilation**: Cache compilations for speed
- [ ] **Background File Watching**: Auto-detect external changes

## Questions?

- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Architecture**: Read ARCHITECTURE.md for deep dive

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Roslyn-MCP Server! 🎉
