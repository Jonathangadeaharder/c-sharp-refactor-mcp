using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.FindSymbols;
using Microsoft.CodeAnalysis.Rename;
using Microsoft.CodeAnalysis.Text;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;
using RoslynRefactorServer.Models;
using RoslynRefactorServer.Services;
using System.ComponentModel;
using System.Text.Json;

namespace RoslynRefactorServer.Tools;

/// <summary>
/// MCP tools for safe, semantically-aware C# refactoring.
/// This class exposes Roslyn's analytical and transformative power to AI agents.
/// </summary>
[McpTools]
public class RefactoringTools
{
    private readonly RoslynWorkspaceService _workspaceService;
    private readonly PathSecurityService _securityService;
    private readonly ILogger<RefactoringTools> _logger;

    public RefactoringTools(
        RoslynWorkspaceService workspaceService,
        PathSecurityService securityService,
        ILogger<RefactoringTools> logger)
    {
        _workspaceService = workspaceService;
        _securityService = securityService;
        _logger = logger;
    }

    /// <summary>
    /// Loads a C# solution into memory for analysis and refactoring.
    /// This tool must be called first before any other refactoring operations.
    /// </summary>
    [McpTool]
    [Description("Loads a C# solution (.sln file) into memory for analysis and refactoring. " +
                 "This tool must be called first to establish context before any other refactoring operations. " +
                 "Returns information about the loaded solution including project count.")]
    public async Task<string> load_solution(
        [Description("Absolute path to the .sln solution file to load")] string solutionPath)
    {
        try
        {
            _logger.LogInformation("Loading solution: {Path}", solutionPath);

            // Security validation
            _securityService.ValidateSolutionFile(solutionPath);

            // Load solution (this primes the cache)
            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(solutionPath);

            var projectCount = solution.Projects.Count();
            var documentCount = solution.Projects.SelectMany(p => p.Documents).Count();

            var result = new
            {
                success = true,
                message = $"Solution '{Path.GetFileName(solutionPath)}' loaded successfully.",
                projectCount = projectCount,
                documentCount = documentCount,
                projects = solution.Projects.Select(p => new
                {
                    name = p.Name,
                    documentCount = p.Documents.Count()
                }).ToList()
            };

            return JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load solution");
            return JsonSerializer.Serialize(new
            {
                success = false,
                error = ex.Message,
                type = ex.GetType().Name
            });
        }
    }

    /// <summary>
    /// Gets all compilation diagnostics (errors, warnings) for a solution.
    /// This is a critical safety check that must be performed before refactoring.
    /// </summary>
    [McpTool]
    [Description("Gets all compilation diagnostics (errors, warnings, info) for a solution. " +
                 "This is a CRITICAL safety check that should be performed before any refactoring operation. " +
                 "Refactoring on code with compilation errors is unsafe and may produce incorrect results. " +
                 "Returns a list of diagnostics with severity, message, file path, and line number.")]
    public async Task<string> get_diagnostics(
        [Description("Absolute path to the .sln solution file")] string solutionPath,
        [Description("Minimum severity level to report: Error, Warning, Info, or All. Default is Warning.")] string severityFilter = "Warning")
    {
        try
        {
            _logger.LogInformation("Getting diagnostics for solution: {Path}", solutionPath);

            _securityService.ValidateSolutionFile(solutionPath);
            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(solutionPath);

            var allDiagnostics = new List<DiagnosticInfo>();

            foreach (var project in solution.Projects)
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

            var result = new
            {
                success = true,
                errorCount = errorCount,
                warningCount = warningCount,
                totalCount = allDiagnostics.Count,
                isSafeToRefactor = errorCount == 0,
                message = errorCount > 0
                    ? $"UNSAFE: Found {errorCount} compilation errors. Refactoring is NOT recommended."
                    : "SAFE: No compilation errors found. Safe to proceed with refactoring.",
                diagnostics = allDiagnostics.Take(100).ToList() // Limit to first 100 for performance
            };

            return JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get diagnostics");
            return JsonSerializer.Serialize(new { success = false, error = ex.Message });
        }
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

    /// <summary>
    /// Finds all references to a symbol across the entire solution.
    /// </summary>
    [McpTool]
    [Description("Finds all references to a symbol (class, method, variable, etc.) across the entire solution. " +
                 "Uses semantic analysis to find only true references, not text matches. " +
                 "Returns a list of locations with file path, line number, and code snippet.")]
    public async Task<string> find_all_references(
        [Description("Absolute path to the .sln solution file")] string solutionPath,
        [Description("Absolute path to the .cs document containing the symbol")] string documentPath,
        [Description("Line number (1-based) of the symbol")] int line,
        [Description("Column number (1-based) of the symbol")] int column)
    {
        try
        {
            _logger.LogInformation("Finding references at {Path}:{Line}:{Column}", documentPath, line, column);

            _securityService.ValidateSolutionFile(solutionPath);
            _securityService.ValidateDocumentFile(documentPath);

            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(solutionPath);
            var document = solution.Projects
                .SelectMany(p => p.Documents)
                .FirstOrDefault(d => Path.GetFullPath(d.FilePath ?? "") == Path.GetFullPath(documentPath));

            if (document == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Document not found in solution" });
            }

            var semanticModel = await document.GetSemanticModelAsync();
            var syntaxRoot = await document.GetSyntaxRootAsync();
            if (semanticModel == null || syntaxRoot == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Failed to get semantic model" });
            }

            // Convert line/column to position
            var text = await document.GetTextAsync();
            var position = text.Lines[line - 1].Start + (column - 1);
            var node = syntaxRoot.FindNode(new TextSpan(position, 0));

            // Get the symbol at this position
            var symbol = semanticModel.GetSymbolInfo(node).Symbol ?? semanticModel.GetDeclaredSymbol(node);
            if (symbol == null)
            {
                return JsonSerializer.Serialize(new
                {
                    success = false,
                    error = $"No symbol found at {line}:{column}. Make sure the cursor is on a valid symbol (class, method, variable, etc.)."
                });
            }

            // Find all references
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

            var result = new
            {
                success = true,
                symbolName = symbol.Name,
                symbolKind = symbol.Kind.ToString(),
                referenceCount = locations.Count,
                references = locations
            };

            return JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to find references");
            return JsonSerializer.Serialize(new { success = false, error = ex.Message });
        }
    }

    /// <summary>
    /// Safely renames a symbol across the entire solution using Roslyn's semantic rename API.
    /// </summary>
    [McpTool]
    [Description("Safely renames a symbol (class, method, variable, property, etc.) across the entire solution. " +
                 "Uses Roslyn's semantic rename API which handles scope, overloads, and naming conflicts correctly. " +
                 "This is a write operation that modifies files on disk. " +
                 "IMPORTANT: Run get_diagnostics first to ensure the code has no compilation errors.")]
    public async Task<string> rename_symbol(
        [Description("Absolute path to the .sln solution file")] string solutionPath,
        [Description("Absolute path to the .cs document containing the symbol")] string documentPath,
        [Description("Line number (1-based) of the symbol to rename")] int line,
        [Description("Column number (1-based) of the symbol to rename")] int column,
        [Description("New name for the symbol")] string newName)
    {
        try
        {
            _logger.LogInformation("Renaming symbol at {Path}:{Line}:{Column} to {NewName}", documentPath, line, column, newName);

            _securityService.ValidateSolutionFile(solutionPath);
            _securityService.ValidateDocumentFile(documentPath);

            if (string.IsNullOrWhiteSpace(newName))
            {
                return JsonSerializer.Serialize(new { success = false, error = "New name cannot be empty" });
            }

            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(solutionPath);
            var document = solution.Projects
                .SelectMany(p => p.Documents)
                .FirstOrDefault(d => Path.GetFullPath(d.FilePath ?? "") == Path.GetFullPath(documentPath));

            if (document == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Document not found in solution" });
            }

            var semanticModel = await document.GetSemanticModelAsync();
            var syntaxRoot = await document.GetSyntaxRootAsync();
            if (semanticModel == null || syntaxRoot == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Failed to get semantic model" });
            }

            // Get the symbol
            var text = await document.GetTextAsync();
            var position = text.Lines[line - 1].Start + (column - 1);
            var node = syntaxRoot.FindNode(new TextSpan(position, 0));
            var symbol = semanticModel.GetSymbolInfo(node).Symbol ?? semanticModel.GetDeclaredSymbol(node);

            if (symbol == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "No symbol found at specified position" });
            }

            var oldName = symbol.Name;

            // Perform the rename using Roslyn's high-level API
            var newSolution = await Renamer.RenameSymbolAsync(
                solution,
                symbol,
                new Microsoft.CodeAnalysis.Options.OptionSet(),
                newName);

            // Apply changes atomically
            await _workspaceService.UpdateAndApplyChangesAsync(solutionPath, newSolution);

            var result = new
            {
                success = true,
                message = $"Successfully renamed '{oldName}' to '{newName}' across the solution",
                oldName = oldName,
                newName = newName,
                symbolKind = symbol.Kind.ToString()
            };

            return JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to rename symbol");
            return JsonSerializer.Serialize(new { success = false, error = ex.Message });
        }
    }

    /// <summary>
    /// Gets detailed information about a symbol at a specific location.
    /// </summary>
    [McpTool]
    [Description("Gets detailed information about a symbol (class, method, variable, etc.) at a specific location. " +
                 "Returns symbol name, kind, type, containing type, namespace, and other metadata. " +
                 "Useful for understanding code structure before refactoring.")]
    public async Task<string> get_symbol_info(
        [Description("Absolute path to the .sln solution file")] string solutionPath,
        [Description("Absolute path to the .cs document containing the symbol")] string documentPath,
        [Description("Line number (1-based) of the symbol")] int line,
        [Description("Column number (1-based) of the symbol")] int column)
    {
        try
        {
            _securityService.ValidateSolutionFile(solutionPath);
            _securityService.ValidateDocumentFile(documentPath);

            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(solutionPath);
            var document = solution.Projects
                .SelectMany(p => p.Documents)
                .FirstOrDefault(d => Path.GetFullPath(d.FilePath ?? "") == Path.GetFullPath(documentPath));

            if (document == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Document not found" });
            }

            var semanticModel = await document.GetSemanticModelAsync();
            var syntaxRoot = await document.GetSyntaxRootAsync();
            if (semanticModel == null || syntaxRoot == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Failed to get semantic model" });
            }

            var text = await document.GetTextAsync();
            var position = text.Lines[line - 1].Start + (column - 1);
            var node = syntaxRoot.FindNode(new TextSpan(position, 0));
            var symbol = semanticModel.GetSymbolInfo(node).Symbol ?? semanticModel.GetDeclaredSymbol(node);

            if (symbol == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "No symbol found" });
            }

            var result = new
            {
                success = true,
                name = symbol.Name,
                kind = symbol.Kind.ToString(),
                type = (symbol as ILocalSymbol)?.Type?.ToString() ??
                       (symbol as IParameterSymbol)?.Type?.ToString() ??
                       (symbol as IPropertySymbol)?.Type?.ToString() ??
                       (symbol as IFieldSymbol)?.Type?.ToString() ?? "",
                containingType = symbol.ContainingType?.Name ?? "",
                containingNamespace = symbol.ContainingNamespace?.ToString() ?? "",
                isStatic = symbol.IsStatic,
                isAbstract = symbol.IsAbstract,
                isVirtual = symbol.IsVirtual,
                accessibility = symbol.DeclaredAccessibility.ToString(),
                documentation = symbol.GetDocumentationCommentXml()
            };

            return JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get symbol info");
            return JsonSerializer.Serialize(new { success = false, error = ex.Message });
        }
    }
}
