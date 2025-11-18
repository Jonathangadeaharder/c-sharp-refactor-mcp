// @structurelint:no-test - Integration component requiring full Roslyn workspace
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.FindSymbols;
using Microsoft.CodeAnalysis.Rename;
using Microsoft.CodeAnalysis.Text;
using Microsoft.Extensions.Logging;
using RoslynRefactorServer.Abstractions;
using RoslynRefactorServer.Models;
using RoslynRefactorServer.Services;

namespace RoslynRefactorServer.Providers;

/// <summary>
/// Language provider for VB.NET using Roslyn
/// Based on the vbdotnet-refactor-mcp architecture
/// </summary>
public class VBNetLanguageProvider : ILanguageProvider
{
    private readonly RoslynWorkspaceService _workspaceService;
    private readonly ILogger<VBNetLanguageProvider> _logger;

    public string LanguageId => "vbnet";
    public string LanguageName => "VB.NET";
    public IReadOnlyList<string> SupportedExtensions => new[] { ".vb" };
    public IReadOnlyList<string> ProjectFileExtensions => new[] { ".sln", ".vbproj" };

    public VBNetLanguageProvider(
        RoslynWorkspaceService workspaceService,
        ILogger<VBNetLanguageProvider> logger)
    {
        _workspaceService = workspaceService;
        _logger = logger;
    }

    public Task InitializeAsync(CancellationToken cancellationToken = default)
    {
        // Roslyn workspace is already initialized
        _logger.LogInformation("VB.NET language provider initialized");
        return Task.CompletedTask;
    }

    public async Task<ProviderResult<ProjectInfo>> LoadProjectAsync(string projectPath)
    {
        try
        {
            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(projectPath);

            var vbProjects = solution.Projects.Where(p => p.Language == LanguageNames.VisualBasic).ToList();
            var documentCount = vbProjects.SelectMany(p => p.Documents).Count();

            var projectInfo = new ProjectInfo
            {
                ProjectPath = projectPath,
                ProjectName = Path.GetFileName(projectPath),
                FileCount = documentCount,
                Language = LanguageName,
                SubProjects = vbProjects.Select(p => p.Name).ToList()
            };

            return ProviderResult<ProjectInfo>.SuccessResult(projectInfo);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load VB.NET project");
            return ProviderResult<ProjectInfo>.FromException(ex);
        }
    }

    public async Task<ProviderResult<DiagnosticsInfo>> GetDiagnosticsAsync(string projectPath, string severityFilter = "Warning")
    {
        try
        {
            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(projectPath);
            var allDiagnostics = new List<DiagnosticInfo>();

            var vbProjects = solution.Projects.Where(p => p.Language == LanguageNames.VisualBasic);

            foreach (var project in vbProjects)
            {
                var compilation = await project.GetCompilationAsync();
                if (compilation == null) continue;

                var diagnostics = compilation.GetDiagnostics()
                    .Where(d => ShouldIncludeDiagnostic(d, severityFilter))
                    .Select(d => new DiagnosticInfo
                    {
                        Id = d.Id,
                        Message = d.GetMessage(),
                        Severity = d.Severity.ToString(),
                        FilePath = d.Location.SourceTree?.FilePath ?? "",
                        Line = d.Location.GetLineSpan().StartLinePosition.Line + 1,
                        Column = d.Location.GetLineSpan().StartLinePosition.Character + 1
                    });

                allDiagnostics.AddRange(diagnostics);
            }

            var errorCount = allDiagnostics.Count(d => d.Severity == "Error");
            var warningCount = allDiagnostics.Count(d => d.Severity == "Warning");

            var diagnosticsInfo = new DiagnosticsInfo
            {
                ErrorCount = errorCount,
                WarningCount = warningCount,
                TotalCount = allDiagnostics.Count,
                IsSafeToRefactor = errorCount == 0,
                Message = errorCount > 0
                    ? $"UNSAFE: Found {errorCount} compilation errors. Refactoring is NOT recommended."
                    : "SAFE: No compilation errors found. Safe to proceed with refactoring.",
                Diagnostics = allDiagnostics.Take(100).ToList()
            };

            return ProviderResult<DiagnosticsInfo>.SuccessResult(diagnosticsInfo);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get diagnostics");
            return ProviderResult<DiagnosticsInfo>.FromException(ex);
        }
    }

    public async Task<ProviderResult<ReferencesInfo>> FindReferencesAsync(
        string projectPath,
        string filePath,
        int line,
        int column)
    {
        try
        {
            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(projectPath);
            var document = FindDocument(solution, filePath);

            if (document == null)
            {
                return ProviderResult<ReferencesInfo>.ErrorResult("Document not found in solution");
            }

            var semanticModel = await document.GetSemanticModelAsync();
            var syntaxRoot = await document.GetSyntaxRootAsync();

            if (semanticModel == null || syntaxRoot == null)
            {
                return ProviderResult<ReferencesInfo>.ErrorResult("Failed to get semantic model");
            }

            var text = await document.GetTextAsync();
            var position = text.Lines[line - 1].Start + (column - 1);
            var node = syntaxRoot.FindNode(new TextSpan(position, 0));

            var symbol = semanticModel.GetSymbolInfo(node).Symbol ?? semanticModel.GetDeclaredSymbol(node);
            if (symbol == null)
            {
                return ProviderResult<ReferencesInfo>.ErrorResult(
                    $"No symbol found at {line}:{column}. Make sure the cursor is on a valid symbol.");
            }

            var references = await SymbolFinder.FindReferencesAsync(symbol, solution);
            var locations = new List<ReferenceLocation>();

            foreach (var reference in references)
            {
                foreach (var location in reference.Locations)
                {
                    var refDoc = location.Document;
                    var refText = await refDoc.GetTextAsync();
                    var lineSpan = location.Location.GetLineSpan();

                    var snippet = refText.Lines[lineSpan.StartLinePosition.Line].ToString().Trim();

                    locations.Add(new ReferenceLocation
                    {
                        FilePath = refDoc.FilePath ?? "",
                        StartLine = lineSpan.StartLinePosition.Line + 1,
                        StartColumn = lineSpan.StartLinePosition.Character + 1,
                        EndLine = lineSpan.EndLinePosition.Line + 1,
                        EndColumn = lineSpan.EndLinePosition.Character + 1,
                        CodeSnippet = snippet
                    });
                }
            }

            var referencesInfo = new ReferencesInfo
            {
                SymbolName = symbol.Name,
                SymbolKind = symbol.Kind.ToString(),
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

    public async Task<ProviderResult<RenameInfo>> RenameSymbolAsync(
        string projectPath,
        string filePath,
        int line,
        int column,
        string newName)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(newName))
            {
                return ProviderResult<RenameInfo>.ErrorResult("New name cannot be empty");
            }

            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(projectPath);
            var document = FindDocument(solution, filePath);

            if (document == null)
            {
                return ProviderResult<RenameInfo>.ErrorResult("Document not found in solution");
            }

            var semanticModel = await document.GetSemanticModelAsync();
            var syntaxRoot = await document.GetSyntaxRootAsync();

            if (semanticModel == null || syntaxRoot == null)
            {
                return ProviderResult<RenameInfo>.ErrorResult("Failed to get semantic model");
            }

            var text = await document.GetTextAsync();
            var position = text.Lines[line - 1].Start + (column - 1);
            var node = syntaxRoot.FindNode(new TextSpan(position, 0));
            var symbol = semanticModel.GetSymbolInfo(node).Symbol ?? semanticModel.GetDeclaredSymbol(node);

            if (symbol == null)
            {
                return ProviderResult<RenameInfo>.ErrorResult("No symbol found at specified position");
            }

            var oldName = symbol.Name;

            // Perform the rename using Roslyn's high-level API
            var newSolution = await Renamer.RenameSymbolAsync(
                solution,
                symbol,
                default(Microsoft.CodeAnalysis.Rename.SymbolRenameOptions),
                newName);

            // Apply changes
            await _workspaceService.UpdateAndApplyChangesAsync(projectPath, newSolution);

            // Count modified files
            var changes = newSolution.GetChanges(solution);
            var filesModified = changes.GetProjectChanges()
                .SelectMany(pc => pc.GetChangedDocuments())
                .Distinct()
                .Count();

            var renameInfo = new RenameInfo
            {
                OldName = oldName,
                NewName = newName,
                SymbolKind = symbol.Kind.ToString(),
                FilesModified = filesModified,
                Message = $"Successfully renamed '{oldName}' to '{newName}' across the solution"
            };

            return ProviderResult<RenameInfo>.SuccessResult(renameInfo);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to rename symbol");
            return ProviderResult<RenameInfo>.FromException(ex);
        }
    }

    public async Task<ProviderResult<SymbolInfo>> GetSymbolInfoAsync(
        string projectPath,
        string filePath,
        int line,
        int column)
    {
        try
        {
            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(projectPath);
            var document = FindDocument(solution, filePath);

            if (document == null)
            {
                return ProviderResult<SymbolInfo>.ErrorResult("Document not found");
            }

            var semanticModel = await document.GetSemanticModelAsync();
            var syntaxRoot = await document.GetSyntaxRootAsync();

            if (semanticModel == null || syntaxRoot == null)
            {
                return ProviderResult<SymbolInfo>.ErrorResult("Failed to get semantic model");
            }

            var text = await document.GetTextAsync();
            var position = text.Lines[line - 1].Start + (column - 1);
            var node = syntaxRoot.FindNode(new TextSpan(position, 0));
            var symbol = semanticModel.GetSymbolInfo(node).Symbol ?? semanticModel.GetDeclaredSymbol(node);

            if (symbol == null)
            {
                return ProviderResult<SymbolInfo>.ErrorResult("No symbol found");
            }

            var symbolInfo = new SymbolInfo
            {
                Name = symbol.Name,
                Kind = symbol.Kind.ToString(),
                Type = (symbol as ILocalSymbol)?.Type?.ToString() ??
                       (symbol as IParameterSymbol)?.Type?.ToString() ??
                       (symbol as IPropertySymbol)?.Type?.ToString() ??
                       (symbol as IFieldSymbol)?.Type?.ToString() ?? "",
                ContainingType = symbol.ContainingType?.Name ?? "",
                ContainingNamespace = symbol.ContainingNamespace?.ToString() ?? "",
                IsStatic = symbol.IsStatic,
                IsAbstract = symbol.IsAbstract,
                IsVirtual = symbol.IsVirtual,
                Accessibility = symbol.DeclaredAccessibility.ToString(),
                Documentation = symbol.GetDocumentationCommentXml()
            };

            return ProviderResult<SymbolInfo>.SuccessResult(symbolInfo);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get symbol info");
            return ProviderResult<SymbolInfo>.FromException(ex);
        }
    }

    public Task<ProviderResult<RefactoringResult>> ExtractMethodAsync(
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
                "Extract method is not yet implemented for VB.NET. Use the advanced_extract_method tool instead."));
    }

    public Task<ProviderResult<RefactoringResult>> EncapsulateFieldAsync(
        string projectPath,
        string filePath,
        int line,
        int column)
    {
        return Task.FromResult(
            ProviderResult<RefactoringResult>.ErrorResult(
                "Encapsulate field is not yet implemented for VB.NET. Use the advanced_encapsulate_field tool instead."));
    }

    public ValueTask DisposeAsync()
    {
        // RoslynWorkspaceService is managed by DI container
        return ValueTask.CompletedTask;
    }

    private bool ShouldIncludeDiagnostic(Diagnostic diagnostic, string severityFilter)
    {
        return severityFilter.ToLower() switch
        {
            "error" => diagnostic.Severity == DiagnosticSeverity.Error,
            "warning" => diagnostic.Severity >= DiagnosticSeverity.Warning,
            "info" => diagnostic.Severity >= DiagnosticSeverity.Info,
            "all" => true,
            _ => diagnostic.Severity >= DiagnosticSeverity.Warning
        };
    }

    private Document? FindDocument(Solution solution, string filePath)
    {
        var normalizedPath = Path.GetFullPath(filePath);
        return solution.Projects
            .Where(p => p.Language == LanguageNames.VisualBasic)
            .SelectMany(p => p.Documents)
            .FirstOrDefault(d => Path.GetFullPath(d.FilePath ?? "") == normalizedPath);
    }
}
