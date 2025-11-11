# Roslyn-MCP Server Architecture

## Executive Summary

This document describes the architecture of a Model Context Protocol (MCP) server that exposes the .NET Compiler Platform (Roslyn) APIs to AI agents for safe, semantic-aware C# refactoring.

## The Problem: AI as Code Maintainer

Large Language Models are excellent code generators but poor code maintainers. They lack:

1. **Stateful semantic understanding** across a solution
2. **Compiler-level accuracy** for scope, types, and references
3. **Deterministic guarantees** for refactoring safety

## The Solution: Semantic Oracle Pattern

This architecture introduces the "Semantic Oracle" pattern:

- **AI Agent**: The "suggester" - decides *what* to refactor
- **Roslyn Server**: The "validator and executor" - performs *how* to refactor safely

The AI never generates refactored code. Instead, it invokes server-side tools that use Roslyn's semantic APIs.

## Core Architectural Principles

### 1. Semantic Safety

All operations use `SemanticModel`, not text manipulation:

```csharp
// ❌ UNSAFE: Text-based
content = content.Replace("oldName", "newName");

// ✅ SAFE: Semantic-based
var newSolution = await Renamer.RenameSymbolAsync(solution, symbol, "newName");
```

### 2. Stateful Workspace

Solutions are loaded once and cached:

```
┌─────────────────────────────────┐
│   RoslynWorkspaceService        │
│   (Singleton)                   │
├─────────────────────────────────┤
│ _solutionCache:                 │
│   "path/to/solution" → Solution │
│                                 │
│ _solutionLocks:                 │
│   "path/to/solution" → Semaphore│
└─────────────────────────────────┘
```

Benefits:
- First load: 10-30 seconds
- Subsequent operations: <1 second
- Memory efficient: One workspace per solution

### 3. Immutable Transformations

Roslyn objects are immutable:

```csharp
// Get current state
var solution = await _workspace.LoadOrRefreshSolutionAsync(path);

// Transform (returns NEW solution, original unchanged)
var newSolution = await Renamer.RenameSymbolAsync(solution, symbol, "newName");

// Commit (atomic update)
await _workspace.UpdateAndApplyChangesAsync(path, newSolution);
```

### 4. Thread Safety

Per-solution write locking:

```csharp
private readonly ConcurrentDictionary<string, SemaphoreSlim> _solutionLocks;

public async Task UpdateAndApplyChangesAsync(string path, Solution newSolution)
{
    var lock = _solutionLocks.GetOrAdd(path, _ => new SemaphoreSlim(1, 1));
    await lock.WaitAsync();
    try
    {
        _workspace.TryApplyChanges(newSolution);
        _solutionCache[path] = newSolution;
    }
    finally
    {
        lock.Release();
    }
}
```

### 5. Stale Cache Detection

Prevents data loss from external edits:

```csharp
public async Task<Solution> LoadOrRefreshSolutionAsync(string path)
{
    if (_solutionCache.TryGetValue(path, out var cached))
    {
        if (await IsCacheStaleAsync(path, cached))
        {
            return await ReloadSolutionAsync(path);
        }
        return cached;
    }
    return await ReloadSolutionAsync(path);
}
```

### 6. Security by Design

Path validation prevents traversal attacks:

```csharp
public string ValidateAndNormalizePath(string path)
{
    var normalized = Path.GetFullPath(path);

    if (!_allowedRootPaths.Any(root => normalized.StartsWith(root)))
    {
        throw new SecurityException($"Access denied: {normalized}");
    }

    return normalized;
}
```

## Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      AI Agent                            │
│              (Claude, Copilot, etc.)                     │
└───────────────────┬─────────────────────────────────────┘
                    │ MCP Protocol (JSON-RPC over stdio)
                    │
┌───────────────────▼─────────────────────────────────────┐
│                  MCP Server Host                         │
│              (Microsoft.Extensions.Hosting)              │
└───────────────────┬─────────────────────────────────────┘
                    │ Dependency Injection
        ┌───────────┼───────────┐
        │           │           │
┌───────▼────┐ ┌───▼───────┐ ┌▼───────────────────┐
│Refactoring │ │ Advanced  │ │RoslynWorkspaceServ │
│   Tools    │ │Refactoring│ │      (Singleton)   │
│  [McpTools]│ │   Tools   │ │                    │
└─────┬──────┘ └─────┬─────┘ └──────┬─────────────┘
      │              │                │
      │              │                │
      └──────────────┴────────────────┘
                     │
      ┌──────────────▼──────────────┐
      │    PathSecurityService      │
      │       (Singleton)            │
      └──────────────┬──────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│         Roslyn APIs                          │
│  • MSBuildWorkspace                          │
│  • SemanticModel                             │
│  • SymbolFinder                              │
│  • Renamer                                   │
│  • DataFlow Analysis                         │
│  • SyntaxRewriter                            │
└──────────────────────────────────────────────┘
```

## Data Flow: Rename Symbol Operation

```
1. AI Agent
   ↓ MCP Request: rename_symbol(path, line, col, "NewName")

2. RefactoringTools.rename_symbol()
   ↓ PathSecurityService.ValidateSolutionFile(path)
   ✓ Path is within allowed roots

3. RoslynWorkspaceService.LoadOrRefreshSolutionAsync(path)
   ↓ Check cache
   ↓ Check if stale (compare file timestamps)
   ← Return: Solution (cached or reloaded)

4. Get SemanticModel and find ISymbol at position
   ↓ document.GetSemanticModelAsync()
   ↓ semanticModel.GetSymbolInfo(node)
   ← ISymbol

5. Perform rename
   ↓ Renamer.RenameSymbolAsync(solution, symbol, "NewName")
   ← newSolution (immutable, all files updated)

6. RoslynWorkspaceService.UpdateAndApplyChangesAsync(path, newSolution)
   ↓ Acquire per-solution lock (SemaphoreSlim)
   ↓ workspace.TryApplyChanges(newSolution) [writes to disk]
   ↓ Update cache: _solutionCache[path] = newSolution
   ↓ Release lock

7. Return success to AI Agent
   ← JSON: { "success": true, "oldName": "...", "newName": "..." }
```

## Concurrency Model

### Read Operations (Parallel)
- `get_diagnostics`
- `find_all_references`
- `get_symbol_info`
- `load_solution` (if not cached)

No locking required - Roslyn's immutable objects are thread-safe for reads.

### Write Operations (Serialized per Solution)
- `rename_symbol`
- `extract_method`
- `encapsulate_field`

Locked per solution path with `SemaphoreSlim(1, 1)`.

### Multi-Solution (Parallel)
Operations on different solutions can run concurrently:
- Solution A rename + Solution B extract = parallel ✓
- Solution A rename + Solution A extract = serialized

## The "Stale State" Problem

**Scenario:**
```
10:00 - AI loads solution → Cache: SolutionV1
10:01 - User edits file in IDE and saves
10:02 - AI renames symbol → Uses stale SolutionV1
        Changes overwrite user's edit ❌
```

**Solution:**
```csharp
private async Task<bool> IsCacheStaleAsync(string path, Solution cached)
{
    foreach (var document in cached.Projects.SelectMany(p => p.Documents))
    {
        var fileTime = File.GetLastWriteTimeUtc(document.FilePath);
        var cachedTime = _fileTimestamps[path][document.FilePath];

        if (fileTime > cachedTime)
            return true; // Stale!
    }
    return false;
}
```

## Performance Characteristics

| Operation | First Call | Cached | Notes |
|-----------|-----------|--------|-------|
| `load_solution` | 10-30s | <1s | Depends on solution size |
| `get_diagnostics` | 3-10s | 1-3s | Full compilation required |
| `find_all_references` | 2-5s | 0.5-2s | Solution-wide search |
| `rename_symbol` | 3-10s | 1-5s | Solution-wide + file writes |
| `extract_method` | 1-3s | 0.5-1s | Single file operation |

**Memory Usage:**
- Small solution (10 projects): ~500 MB
- Medium solution (50 projects): ~1-2 GB
- Large solution (200+ projects): ~3-5 GB

## Error Handling Strategy

### Validation Errors (User-fixable)
```csharp
return JsonSerializer.Serialize(new {
    success = false,
    error = "No symbol found at specified position"
});
```

### Security Errors (Critical)
```csharp
throw new SecurityException("Access denied: path not in allowed roots");
```

### Workspace Errors (Recoverable)
```csharp
catch (Exception ex)
{
    _logger.LogError(ex, "Failed to apply changes");
    _solutionCache.TryRemove(path, out _); // Invalidate cache
    throw;
}
```

## Why Not Use Existing Tools?

### OmniSharp
- **Pros**: Mature, widely used
- **Cons**: Language Server Protocol (not MCP), complex setup, stale cache issues

### RefactorMCP / RoslynMCP
- **Pros**: Already MCP-based
- **Cons**: Limited refactorings, no advanced features, unclear concurrency model

### This Implementation
- **MCP-native**: Works with Claude, Copilot out of the box
- **Comprehensive**: Full suite of refactorings
- **Production-ready**: Thread-safe, secure, performant
- **Extensible**: Easy to add new tools

## Future Architecture Enhancements

### 1. Incremental Compilation
Cache `Compilation` objects per project for faster diagnostics:
```csharp
private ConcurrentDictionary<ProjectId, Compilation> _compilationCache;
```

### 2. Background Refresh
Proactively detect file changes using `FileSystemWatcher`:
```csharp
var watcher = new FileSystemWatcher(solutionDir);
watcher.Changed += (s, e) => InvalidateCache(solutionPath);
```

### 3. Analyzer Integration
Expose Roslyn analyzers as MCP tools:
```csharp
[McpTool]
public async Task<string> run_analyzers(string solutionPath)
{
    var analyzers = solution.Projects
        .SelectMany(p => p.AnalyzerReferences)
        .SelectMany(r => r.GetAnalyzers());
    // ...
}
```

### 4. Multi-Solution Support
Support workspace-wide operations across multiple solutions:
```csharp
[McpTool]
public async Task<string> find_references_in_workspace(
    string[] solutionPaths,
    string symbolName)
```

## References

1. [Roslyn Overview](https://github.com/dotnet/roslyn)
2. [MCP Specification](https://modelcontextprotocol.io/specification)
3. [MSBuildWorkspace API](https://learn.microsoft.com/en-us/dotnet/api/microsoft.codeanalysis.msbuild.msbuildworkspace)
4. [Semantic Model](https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/get-started/semantic-analysis)
5. [SyntaxRewriter Pattern](https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/get-started/syntax-transformation)

## Conclusion

This architecture demonstrates that AI-driven development can be both powerful and safe. By separating the AI's creative suggestions from the compiler's deterministic execution, we achieve:

✓ Semantic correctness
✓ Solution-wide consistency
✓ Thread-safe operations
✓ Security guarantees
✓ Performance through caching

The result is a true "AI pair programmer" that can safely maintain code, not just generate it.
