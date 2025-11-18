using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;
using RoslynRefactorServer.Abstractions;
using RoslynRefactorServer.Services;
using System.ComponentModel;
using System.Text.Json;

namespace RoslynRefactorServer.Tools;

/// <summary>
/// Unified MCP tools for multi-language refactoring.
/// Automatically detects the language and delegates to the appropriate provider.
/// </summary>
[McpServerToolType]
public class UnifiedRefactoringTools
{
    private readonly LanguageDetectorService _languageDetector;
    private readonly PathSecurityService _securityService;
    private readonly ILogger<UnifiedRefactoringTools> _logger;

    public UnifiedRefactoringTools(
        LanguageDetectorService languageDetector,
        PathSecurityService securityService,
        ILogger<UnifiedRefactoringTools> logger)
    {
        _languageDetector = languageDetector;
        _securityService = securityService;
        _logger = logger;
    }

    /// <summary>
    /// Loads a project or solution into memory for analysis and refactoring.
    /// Supports C#, TypeScript, Go, C++, Java, and Rust.
    /// </summary>
    [McpServerTool]
    [Description("Loads a project or solution into memory for analysis and refactoring. " +
                 "Automatically detects the language from the project file. " +
                 "Supported languages: C# (.sln, .csproj), TypeScript (tsconfig.json), Go (go.mod), " +
                 "C++ (CMakeLists.txt), Java (pom.xml, build.gradle), Rust (Cargo.toml). " +
                 "This tool must be called first before any other refactoring operations.")]
    public async Task<string> load_project(
        [Description("Absolute path to the project file (e.g., .sln, tsconfig.json, go.mod, Cargo.toml, etc.)")] string projectPath)
    {
        try
        {
            _logger.LogInformation("Loading project: {Path}", projectPath);

            // Security validation
            _securityService.ValidateSolutionFile(projectPath);

            // Detect language
            var provider = _languageDetector.DetectFromProjectFile(projectPath);
            if (provider == null)
            {
                return JsonSerializer.Serialize(new
                {
                    success = false,
                    error = "Could not detect language from project file. Supported: .sln, .csproj, tsconfig.json, go.mod, CMakeLists.txt, pom.xml, build.gradle, Cargo.toml"
                });
            }

            // Initialize provider if needed
            await provider.InitializeAsync();

            // Load project
            var result = await provider.LoadProjectAsync(projectPath);

            if (!result.Success)
            {
                return JsonSerializer.Serialize(new
                {
                    success = false,
                    error = result.Error,
                    errorType = result.ErrorType
                });
            }

            var response = new
            {
                success = true,
                message = $"{provider.LanguageName} project '{result.Data!.ProjectName}' loaded successfully.",
                language = provider.LanguageName,
                languageId = provider.LanguageId,
                projectPath = result.Data.ProjectPath,
                projectName = result.Data.ProjectName,
                fileCount = result.Data.FileCount,
                subProjects = result.Data.SubProjects
            };

            return JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load project");
            return JsonSerializer.Serialize(new
            {
                success = false,
                error = ex.Message,
                type = ex.GetType().Name
            });
        }
    }

    /// <summary>
    /// Gets all compilation diagnostics (errors, warnings) for a project.
    /// </summary>
    [McpServerTool]
    [Description("Gets all compilation diagnostics (errors, warnings, info) for a project. " +
                 "This is a CRITICAL safety check that should be performed before any refactoring operation. " +
                 "Automatically detects the language from the project file. " +
                 "Returns a list of diagnostics with severity, message, file path, and line number.")]
    public async Task<string> get_diagnostics(
        [Description("Absolute path to the project file")] string projectPath,
        [Description("Minimum severity level to report: Error, Warning, Info, or All. Default is Warning.")] string severityFilter = "Warning")
    {
        try
        {
            _securityService.ValidateSolutionFile(projectPath);

            var provider = _languageDetector.DetectFromProjectFile(projectPath);
            if (provider == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Could not detect language" });
            }

            await provider.InitializeAsync();
            var result = await provider.GetDiagnosticsAsync(projectPath, severityFilter);

            if (!result.Success)
            {
                return JsonSerializer.Serialize(new { success = false, error = result.Error });
            }

            var response = new
            {
                success = true,
                language = provider.LanguageName,
                errorCount = result.Data!.ErrorCount,
                warningCount = result.Data.WarningCount,
                totalCount = result.Data.TotalCount,
                isSafeToRefactor = result.Data.IsSafeToRefactor,
                message = result.Data.Message,
                diagnostics = result.Data.Diagnostics
            };

            return JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get diagnostics");
            return JsonSerializer.Serialize(new { success = false, error = ex.Message });
        }
    }

    /// <summary>
    /// Finds all references to a symbol across the project.
    /// </summary>
    [McpServerTool]
    [Description("Finds all references to a symbol (class, method, variable, function, etc.) across the entire project. " +
                 "Uses semantic analysis to find only true references, not text matches. " +
                 "Automatically detects the language from the project file. " +
                 "Returns a list of locations with file path, line number, and code snippet.")]
    public async Task<string> find_all_references(
        [Description("Absolute path to the project file")] string projectPath,
        [Description("Absolute path to the source file containing the symbol")] string filePath,
        [Description("Line number (1-based) of the symbol")] int line,
        [Description("Column number (1-based) of the symbol")] int column)
    {
        try
        {
            _securityService.ValidateSolutionFile(projectPath);
            _securityService.ValidateDocumentFile(filePath);

            var provider = _languageDetector.DetectFromProjectFile(projectPath);
            if (provider == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Could not detect language" });
            }

            await provider.InitializeAsync();
            var result = await provider.FindReferencesAsync(projectPath, filePath, line, column);

            if (!result.Success)
            {
                return JsonSerializer.Serialize(new { success = false, error = result.Error });
            }

            var response = new
            {
                success = true,
                language = provider.LanguageName,
                symbolName = result.Data!.SymbolName,
                symbolKind = result.Data.SymbolKind,
                referenceCount = result.Data.ReferenceCount,
                references = result.Data.References
            };

            return JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to find references");
            return JsonSerializer.Serialize(new { success = false, error = ex.Message });
        }
    }

    /// <summary>
    /// Safely renames a symbol across the entire project.
    /// </summary>
    [McpServerTool]
    [Description("Safely renames a symbol (class, method, variable, property, function, etc.) across the entire project. " +
                 "Uses semantic analysis which handles scope, overloads, and naming conflicts correctly. " +
                 "This is a write operation that modifies files on disk. " +
                 "Automatically detects the language from the project file. " +
                 "IMPORTANT: Run get_diagnostics first to ensure the code has no compilation errors.")]
    public async Task<string> rename_symbol(
        [Description("Absolute path to the project file")] string projectPath,
        [Description("Absolute path to the source file containing the symbol")] string filePath,
        [Description("Line number (1-based) of the symbol to rename")] int line,
        [Description("Column number (1-based) of the symbol to rename")] int column,
        [Description("New name for the symbol")] string newName)
    {
        try
        {
            _securityService.ValidateSolutionFile(projectPath);
            _securityService.ValidateDocumentFile(filePath);

            var provider = _languageDetector.DetectFromProjectFile(projectPath);
            if (provider == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Could not detect language" });
            }

            await provider.InitializeAsync();
            var result = await provider.RenameSymbolAsync(projectPath, filePath, line, column, newName);

            if (!result.Success)
            {
                return JsonSerializer.Serialize(new { success = false, error = result.Error });
            }

            var response = new
            {
                success = true,
                language = provider.LanguageName,
                message = result.Data!.Message,
                oldName = result.Data.OldName,
                newName = result.Data.NewName,
                symbolKind = result.Data.SymbolKind,
                filesModified = result.Data.FilesModified
            };

            return JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = true });
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
    [McpServerTool]
    [Description("Gets detailed information about a symbol (class, method, variable, function, etc.) at a specific location. " +
                 "Returns symbol name, kind, type, containing type, namespace, and other metadata. " +
                 "Automatically detects the language from the project file. " +
                 "Useful for understanding code structure before refactoring.")]
    public async Task<string> get_symbol_info(
        [Description("Absolute path to the project file")] string projectPath,
        [Description("Absolute path to the source file containing the symbol")] string filePath,
        [Description("Line number (1-based) of the symbol")] int line,
        [Description("Column number (1-based) of the symbol")] int column)
    {
        try
        {
            _securityService.ValidateSolutionFile(projectPath);
            _securityService.ValidateDocumentFile(filePath);

            var provider = _languageDetector.DetectFromProjectFile(projectPath);
            if (provider == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Could not detect language" });
            }

            await provider.InitializeAsync();
            var result = await provider.GetSymbolInfoAsync(projectPath, filePath, line, column);

            if (!result.Success)
            {
                return JsonSerializer.Serialize(new { success = false, error = result.Error });
            }

            var response = new
            {
                success = true,
                language = provider.LanguageName,
                name = result.Data!.Name,
                kind = result.Data.Kind,
                type = result.Data.Type,
                containingType = result.Data.ContainingType,
                containingNamespace = result.Data.ContainingNamespace,
                isStatic = result.Data.IsStatic,
                isAbstract = result.Data.IsAbstract,
                isVirtual = result.Data.IsVirtual,
                accessibility = result.Data.Accessibility,
                documentation = result.Data.Documentation
            };

            return JsonSerializer.Serialize(response, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to get symbol info");
            return JsonSerializer.Serialize(new { success = false, error = ex.Message });
        }
    }
}
