# Multi-Language Architecture

This document describes the architecture for multi-language support in the refactor MCP server.

## Architecture Overview

The server uses a **hybrid architecture** combining:

1. **Roslyn** for .NET languages (C#, VB.NET)
2. **LSP (Language Server Protocol)** for other languages (TypeScript, Go, C++, Java, Rust)

## Core Abstractions

### ILanguageProvider

The central abstraction that defines operations for any programming language:

```csharp
public interface ILanguageProvider
{
    string LanguageId { get; }
    string LanguageName { get; }
    IReadOnlyList<string> SupportedExtensions { get; }
    IReadOnlyList<string> ProjectFileExtensions { get; }

    Task InitializeAsync(CancellationToken cancellationToken = default);
    Task<ProviderResult<ProjectInfo>> LoadProjectAsync(string projectPath);
    Task<ProviderResult<DiagnosticsInfo>> GetDiagnosticsAsync(string projectPath, string severityFilter);
    Task<ProviderResult<ReferencesInfo>> FindReferencesAsync(string projectPath, string filePath, int line, int column);
    Task<ProviderResult<RenameInfo>> RenameSymbolAsync(string projectPath, string filePath, int line, int column, string newName);
    Task<ProviderResult<SymbolInfo>> GetSymbolInfoAsync(string projectPath, string filePath, int line, int column);
    // ... more operations
}
```

### ProviderResult<T>

Generic result wrapper for language provider operations:

```csharp
public class ProviderResult<T>
{
    public bool Success { get; init; }
    public T? Data { get; init; }
    public string? Error { get; init; }
    public string? ErrorType { get; init; }
}
```

## Language Providers

### C# Language Provider

Uses Microsoft Roslyn for semantic analysis:

- **Workspace**: MSBuildWorkspace for loading .sln/.csproj files
- **Semantic Model**: Full type information and symbol resolution
- **Operations**: Rename, find references, extract method, encapsulate field
- **Advantages**: Most mature, supports advanced refactorings

### TypeScript Language Provider

Uses TypeScript Language Server via LSP:

- **Server**: typescript-language-server
- **Protocol**: LSP over stdio
- **Operations**: Rename, find references, symbol info
- **Advantages**: Leverages official TypeScript compiler

### Go Language Provider

Uses gopls (Go language server):

- **Server**: gopls
- **Protocol**: LSP over stdio
- **Operations**: Rename, find references, symbol info
- **Advantages**: Official Go team tool

### C++ Language Provider

Uses clangd (LLVM-based language server):

- **Server**: clangd
- **Protocol**: LSP over stdio
- **Operations**: Rename, find references, symbol info
- **Advantages**: LLVM-backed semantic analysis

### Java Language Provider

Uses Eclipse JDT Language Server:

- **Server**: jdtls
- **Protocol**: LSP over stdio
- **Operations**: Rename, find references, symbol info
- **Advantages**: Full Java compiler support

### Rust Language Provider

Uses rust-analyzer:

- **Server**: rust-analyzer
- **Protocol**: LSP over stdio
- **Operations**: Rename, find references, symbol info
- **Advantages**: Official Rust tool with macro expansion

## Language Detection

The `LanguageDetectorService` automatically detects languages using:

1. **Project file extensions**: .sln, tsconfig.json, go.mod, Cargo.toml, etc.
2. **Source file extensions**: .cs, .ts, .go, .rs, etc.
3. **Marker files**: package.json, pom.xml, CMakeLists.txt

Detection logic:
```csharp
var provider = languageDetector.DetectFromProjectFile(projectPath);
if (provider == null)
{
    provider = languageDetector.DetectFromDirectory(directoryPath);
}
```

## LSP Client

Generic LSP client for communicating with language servers:

```csharp
public class LspClient : IAsyncDisposable
{
    public async Task InitializeAsync(string rootUri);
    public async Task<TResponse?> SendRequestAsync<TResponse>(string method, object? parameters);
    public async Task SendNotificationAsync(string method, object? parameters);
    public async Task DidOpenAsync(string uri, string languageId, string text);
    public async Task DidCloseAsync(string uri);
}
```

**LSP Request Flow:**
```
1. Start language server process
2. Send initialize request
3. Send initialized notification
4. Open documents (textDocument/didOpen)
5. Send requests (textDocument/rename, textDocument/references, etc.)
6. Close documents (textDocument/didClose)
7. Shutdown (shutdown + exit)
```

## Unified MCP Tools

The `UnifiedRefactoringTools` class provides language-agnostic MCP tools:

```csharp
[McpServerTool]
public async Task<string> load_project(string projectPath)
{
    var provider = _languageDetector.DetectFromProjectFile(projectPath);
    await provider.InitializeAsync();
    var result = await provider.LoadProjectAsync(projectPath);
    return JsonSerializer.Serialize(result);
}
```

**Tool Flow:**
```
MCP Tool Call
    ↓
UnifiedRefactoringTools
    ↓
LanguageDetectorService (detect language)
    ↓
ILanguageProvider (specific provider)
    ↓
Roslyn or LSP Client
    ↓
Language-specific engine
```

## Adding New Languages

To add support for a new language:

1. **Create Language Provider:**
   ```csharp
   public class MyLanguageProvider : BaseLspLanguageProvider
   {
       public override string LanguageId => "mylang";
       public override string LanguageName => "MyLanguage";
       public override IReadOnlyList<string> SupportedExtensions => new[] { ".mylang" };
       protected override string ServerCommand => "mylang-lsp";
   }
   ```

2. **Register in Program.cs:**
   ```csharp
   builder.Services.AddSingleton<ILanguageProvider, MyLanguageProvider>();
   ```

3. **Install Language Server:**
   ```bash
   # Install the language server for the new language
   npm install -g mylang-lsp
   ```

## Performance Considerations

### C# (Roslyn)
- **Initial Load**: 5-30 seconds for large solutions
- **Caching**: Workspace cached in memory
- **Memory**: 1-3 GB for large solutions

### LSP-based Languages
- **Initial Load**: 2-10 seconds (depends on project size)
- **Process Management**: One LSP server process per language
- **Memory**: ~100-500 MB per language server

### Optimization Strategies
1. Lazy initialization (start LSP only when needed)
2. Connection pooling (reuse LSP connections)
3. Workspace caching (Roslyn)
4. Incremental updates (LSP)

## Security

### Path Validation
All file access validated against `AllowedRootPaths`:
```csharp
_securityService.ValidateSolutionFile(projectPath);
_securityService.ValidateDocumentFile(filePath);
```

### Process Isolation
- LSP servers run in separate processes
- No shell command injection (direct process spawn)
- Standard input/output only (no network access)

## Error Handling

### Provider Errors
All operations return `ProviderResult<T>`:
```csharp
if (!result.Success)
{
    return JsonSerializer.Serialize(new {
        success = false,
        error = result.Error
    });
}
```

### LSP Communication Errors
- Connection failures: Return error message
- Timeout: Configurable timeout per request
- Server crashes: Logged and propagated to caller

## Testing

### Unit Tests
- Provider interface mocking
- Language detection logic
- Path security validation

### Integration Tests
- End-to-end MCP tool calls
- LSP communication
- Multi-language scenarios

## Future Enhancements

1. **More Languages**:
   - Python (using Pyright)
   - Kotlin (using Kotlin language server)
   - Swift (using SourceKit-LSP)

2. **Advanced Refactorings**:
   - Extract interface
   - Inline method
   - Move type to file
   - Generate constructor

3. **Performance**:
   - Connection pooling for LSP
   - Incremental compilation (Roslyn)
   - Background indexing

4. **Configuration**:
   - Per-language settings
   - Custom LSP server paths
   - Timeout configuration

## References

- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [Roslyn Documentation](https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
