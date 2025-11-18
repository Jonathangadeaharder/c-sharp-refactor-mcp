using RoslynRefactorServer.Models;

namespace RoslynRefactorServer.Abstractions;

/// <summary>
/// Core abstraction for language-specific refactoring operations.
/// Each language provider (C#, TypeScript, Go, etc.) implements this interface.
/// </summary>
public interface ILanguageProvider
{
    /// <summary>
    /// Language identifier (e.g., "csharp", "typescript", "go", "cpp", "java", "rust")
    /// </summary>
    string LanguageId { get; }

    /// <summary>
    /// Human-readable language name
    /// </summary>
    string LanguageName { get; }

    /// <summary>
    /// File extensions supported by this provider (e.g., [".cs"], [".ts", ".tsx"])
    /// </summary>
    IReadOnlyList<string> SupportedExtensions { get; }

    /// <summary>
    /// Project/solution file extensions (e.g., [".sln", ".csproj"], [".go.mod"], etc.)
    /// </summary>
    IReadOnlyList<string> ProjectFileExtensions { get; }

    /// <summary>
    /// Initializes the language provider (e.g., starts LSP server, loads workspace)
    /// </summary>
    Task InitializeAsync(CancellationToken cancellationToken = default);

    /// <summary>
    /// Loads a project or solution into memory for analysis
    /// </summary>
    /// <param name="projectPath">Path to project/solution file</param>
    /// <returns>Result with project information</returns>
    Task<ProviderResult<ProjectInfo>> LoadProjectAsync(string projectPath);

    /// <summary>
    /// Gets compilation diagnostics (errors, warnings) for a project
    /// </summary>
    /// <param name="projectPath">Path to project/solution file</param>
    /// <param name="severityFilter">Minimum severity: "Error", "Warning", "Info", "All"</param>
    /// <returns>Result with diagnostics</returns>
    Task<ProviderResult<DiagnosticsInfo>> GetDiagnosticsAsync(string projectPath, string severityFilter = "Warning");

    /// <summary>
    /// Finds all references to a symbol across the project
    /// </summary>
    /// <param name="projectPath">Path to project/solution file</param>
    /// <param name="filePath">Path to source file</param>
    /// <param name="line">Line number (1-based)</param>
    /// <param name="column">Column number (1-based)</param>
    /// <returns>Result with reference locations</returns>
    Task<ProviderResult<ReferencesInfo>> FindReferencesAsync(
        string projectPath,
        string filePath,
        int line,
        int column);

    /// <summary>
    /// Renames a symbol across the entire project
    /// </summary>
    /// <param name="projectPath">Path to project/solution file</param>
    /// <param name="filePath">Path to source file</param>
    /// <param name="line">Line number (1-based)</param>
    /// <param name="column">Column number (1-based)</param>
    /// <param name="newName">New name for the symbol</param>
    /// <returns>Result with rename information</returns>
    Task<ProviderResult<RenameInfo>> RenameSymbolAsync(
        string projectPath,
        string filePath,
        int line,
        int column,
        string newName);

    /// <summary>
    /// Gets detailed information about a symbol
    /// </summary>
    /// <param name="projectPath">Path to project/solution file</param>
    /// <param name="filePath">Path to source file</param>
    /// <param name="line">Line number (1-based)</param>
    /// <param name="column">Column number (1-based)</param>
    /// <returns>Result with symbol information</returns>
    Task<ProviderResult<SymbolInfo>> GetSymbolInfoAsync(
        string projectPath,
        string filePath,
        int line,
        int column);

    /// <summary>
    /// Extracts selected code into a new method/function
    /// </summary>
    /// <param name="projectPath">Path to project/solution file</param>
    /// <param name="filePath">Path to source file</param>
    /// <param name="startLine">Start line (1-based)</param>
    /// <param name="startColumn">Start column (1-based)</param>
    /// <param name="endLine">End line (1-based)</param>
    /// <param name="endColumn">End column (1-based)</param>
    /// <param name="newMethodName">Name for the extracted method</param>
    /// <returns>Result with extraction information</returns>
    Task<ProviderResult<RefactoringResult>> ExtractMethodAsync(
        string projectPath,
        string filePath,
        int startLine,
        int startColumn,
        int endLine,
        int endColumn,
        string newMethodName);

    /// <summary>
    /// Encapsulates a field by creating a property/getter-setter
    /// </summary>
    /// <param name="projectPath">Path to project/solution file</param>
    /// <param name="filePath">Path to source file</param>
    /// <param name="line">Line number (1-based)</param>
    /// <param name="column">Column number (1-based)</param>
    /// <returns>Result with encapsulation information</returns>
    Task<ProviderResult<RefactoringResult>> EncapsulateFieldAsync(
        string projectPath,
        string filePath,
        int line,
        int column);

    /// <summary>
    /// Disposes resources (e.g., LSP connection, workspace)
    /// </summary>
    ValueTask DisposeAsync();
}
