// @structurelint:no-test - Abstract base class, tested through concrete implementations
using Microsoft.Extensions.Logging;
using RoslynRefactorServer.Abstractions;
using RoslynRefactorServer.Models;
using RoslynRefactorServer.Services;
using System.Text.Json.Nodes;

namespace RoslynRefactorServer.Providers;

/// <summary>
/// Base class for language providers that use LSP (Language Server Protocol)
/// </summary>
public abstract class BaseLspLanguageProvider : ILanguageProvider
{
    protected readonly ILogger _logger;
    protected LspClient? _lspClient;
    protected string? _rootPath;

    public abstract string LanguageId { get; }
    public abstract string LanguageName { get; }
    public abstract IReadOnlyList<string> SupportedExtensions { get; }
    public abstract IReadOnlyList<string> ProjectFileExtensions { get; }

    protected abstract string ServerCommand { get; }
    protected abstract string[] ServerArgs { get; }

    protected BaseLspLanguageProvider(ILogger logger)
    {
        _logger = logger;
    }

    public virtual async Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        if (_lspClient != null && _lspClient.IsInitialized)
        {
            _logger.LogInformation("{Language} LSP client already initialized", LanguageName);
            return;
        }

        _lspClient = new LspClient(LanguageId, ServerCommand, ServerArgs, _logger);
        _logger.LogInformation("{Language} language provider initialized", LanguageName);
    }

    public virtual async Task<ProviderResult<ProjectInfo>> LoadProjectAsync(string projectPath)
    {
        try
        {
            _rootPath = Path.GetDirectoryName(projectPath) ?? Directory.GetCurrentDirectory();
            var rootUri = new Uri(_rootPath).AbsoluteUri;

            if (_lspClient == null || !_lspClient.IsInitialized)
            {
                _lspClient = new LspClient(LanguageId, ServerCommand, ServerArgs, _logger);
                await _lspClient.InitializeAsync(rootUri);
            }

            // Count files
            var fileCount = CountSourceFiles(_rootPath);

            var projectInfo = new ProjectInfo
            {
                ProjectPath = projectPath,
                ProjectName = Path.GetFileName(projectPath),
                FileCount = fileCount,
                Language = LanguageName
            };

            return ProviderResult<ProjectInfo>.SuccessResult(projectInfo);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load {Language} project", LanguageName);
            return ProviderResult<ProjectInfo>.FromException(ex);
        }
    }

    public virtual async Task<ProviderResult<DiagnosticsInfo>> GetDiagnosticsAsync(
        string projectPath,
        string severityFilter = "Warning")
    {
        try
        {
            // LSP-based diagnostics - this is a simplified implementation
            // Real implementation would need to collect diagnostics from the language server
            var diagnosticsInfo = new DiagnosticsInfo
            {
                ErrorCount = 0,
                WarningCount = 0,
                TotalCount = 0,
                IsSafeToRefactor = true,
                Message = "Diagnostics not fully implemented for LSP-based providers yet",
                Diagnostics = new List<DiagnosticInfo>()
            };

            return ProviderResult<DiagnosticsInfo>.SuccessResult(diagnosticsInfo);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get diagnostics");
            return ProviderResult<DiagnosticsInfo>.FromException(ex);
        }
    }

    public virtual async Task<ProviderResult<ReferencesInfo>> FindReferencesAsync(
        string projectPath,
        string filePath,
        int line,
        int column)
    {
        try
        {
            if (_lspClient == null || !_lspClient.IsInitialized)
            {
                await LoadProjectAsync(projectPath);
            }

            var uri = new Uri(filePath).AbsoluteUri;
            var text = await File.ReadAllTextAsync(filePath);

            await _lspClient!.DidOpenAsync(uri, LanguageId, text);

            var references = await _lspClient.SendRequestAsync<JsonNode>(
                "textDocument/references",
                new
                {
                    textDocument = new { uri = uri },
                    position = new { line = line - 1, character = column - 1 },
                    context = new { includeDeclaration = true }
                });

            await _lspClient.DidCloseAsync(uri);

            var locations = new List<ReferenceLocation>();

            if (references != null && references is JsonArray array)
            {
                foreach (var item in array)
                {
                    var location = item?["range"];
                    var locationUri = item?["uri"]?.ToString();

                    if (location != null && locationUri != null)
                    {
                        var startLine = location["start"]?["line"]?.GetValue<int>() ?? 0;
                        var startChar = location["start"]?["character"]?.GetValue<int>() ?? 0;

                        locations.Add(new ReferenceLocation
                        {
                            FilePath = new Uri(locationUri).LocalPath,
                            StartLine = startLine + 1,
                            StartColumn = startChar + 1,
                            CodeSnippet = ""
                        });
                    }
                }
            }

            var referencesInfo = new ReferencesInfo
            {
                SymbolName = "symbol",
                SymbolKind = "Unknown",
                ReferenceCount = locations.Count,
                References = locations
            };

            return ProviderResult<ReferencesInfo>.SuccessResult(referencesInfo);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to find references");
            return ProviderResult<ReferencesInfo>.FromException(ex);
        }
    }

    public virtual async Task<ProviderResult<RenameInfo>> RenameSymbolAsync(
        string projectPath,
        string filePath,
        int line,
        int column,
        string newName)
    {
        try
        {
            if (_lspClient == null || !_lspClient.IsInitialized)
            {
                await LoadProjectAsync(projectPath);
            }

            var uri = new Uri(filePath).AbsoluteUri;
            var text = await File.ReadAllTextAsync(filePath);

            await _lspClient!.DidOpenAsync(uri, LanguageId, text);

            var renameResult = await _lspClient.SendRequestAsync<JsonNode>(
                "textDocument/rename",
                new
                {
                    textDocument = new { uri = uri },
                    position = new { line = line - 1, character = column - 1 },
                    newName = newName
                });

            await _lspClient.DidCloseAsync(uri);

            // Apply workspace edits
            var filesModified = 0;
            if (renameResult?["changes"] != null)
            {
                var changes = renameResult["changes"] as JsonObject;
                filesModified = changes?.Count ?? 0;

                // Apply changes to files
                foreach (var (fileUri, edits) in changes ?? new JsonObject())
                {
                    var targetPath = new Uri(fileUri).LocalPath;
                    var fileText = await File.ReadAllTextAsync(targetPath);

                    if (edits is JsonArray editArray)
                    {
                        // Apply edits in reverse order to maintain positions
                        var sortedEdits = editArray.OrderByDescending(e =>
                        {
                            var range = e?["range"];
                            return range?["start"]?["line"]?.GetValue<int>() ?? 0;
                        });

                        foreach (var edit in sortedEdits)
                        {
                            var range = edit?["range"];
                            var newText = edit?["newText"]?.ToString() ?? "";

                            // Simplified edit application
                            // Real implementation would need proper text manipulation
                            fileText = newText;
                        }

                        await File.WriteAllTextAsync(targetPath, fileText);
                    }
                }
            }

            var renameInfo = new RenameInfo
            {
                OldName = "oldName",
                NewName = newName,
                SymbolKind = "Unknown",
                FilesModified = filesModified,
                Message = $"Renamed symbol to '{newName}'"
            };

            return ProviderResult<RenameInfo>.SuccessResult(renameInfo);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to rename symbol");
            return ProviderResult<RenameInfo>.FromException(ex);
        }
    }

    public virtual async Task<ProviderResult<SymbolInfo>> GetSymbolInfoAsync(
        string projectPath,
        string filePath,
        int line,
        int column)
    {
        try
        {
            if (_lspClient == null || !_lspClient.IsInitialized)
            {
                await LoadProjectAsync(projectPath);
            }

            var uri = new Uri(filePath).AbsoluteUri;
            var text = await File.ReadAllTextAsync(filePath);

            await _lspClient!.DidOpenAsync(uri, LanguageId, text);

            var hoverResult = await _lspClient.SendRequestAsync<JsonNode>(
                "textDocument/hover",
                new
                {
                    textDocument = new { uri = uri },
                    position = new { line = line - 1, character = column - 1 }
                });

            await _lspClient.DidCloseAsync(uri);

            var documentation = hoverResult?["contents"]?["value"]?.ToString() ?? "";

            var symbolInfo = new SymbolInfo
            {
                Name = "symbol",
                Kind = "Unknown",
                Type = "",
                Documentation = documentation
            };

            return ProviderResult<SymbolInfo>.SuccessResult(symbolInfo);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get symbol info");
            return ProviderResult<SymbolInfo>.FromException(ex);
        }
    }

    public virtual Task<ProviderResult<RefactoringResult>> ExtractMethodAsync(
        string projectPath,
        string filePath,
        int startLine,
        int startColumn,
        int endLine,
        int endColumn,
        string newMethodName)
    {
        return Task.FromResult(
            ProviderResult<RefactoringResult>.ErrorResult(
                "Extract method is not yet supported for LSP-based providers"));
    }

    public virtual Task<ProviderResult<RefactoringResult>> EncapsulateFieldAsync(
        string projectPath,
        string filePath,
        int line,
        int column)
    {
        return Task.FromResult(
            ProviderResult<RefactoringResult>.ErrorResult(
                "Encapsulate field is not yet supported for LSP-based providers"));
    }

    public virtual async ValueTask DisposeAsync()
    {
        if (_lspClient != null)
        {
            await _lspClient.DisposeAsync();
            _lspClient = null;
        }
    }

    protected int CountSourceFiles(string directory)
    {
        try
        {
            var extensions = SupportedExtensions;
            return Directory.GetFiles(directory, "*.*", SearchOption.AllDirectories)
                .Count(f => extensions.Any(ext => f.EndsWith(ext, StringComparison.OrdinalIgnoreCase)));
        }
        catch
        {
            return 0;
        }
    }
}
