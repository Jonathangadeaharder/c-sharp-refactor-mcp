namespace RoslynRefactorServer.Models;

/// <summary>
/// Information about a loaded project
/// </summary>
public class ProjectInfo
{
    public string ProjectPath { get; init; } = string.Empty;
    public string ProjectName { get; init; } = string.Empty;
    public int FileCount { get; init; }
    public string Language { get; init; } = string.Empty;
    public List<string>? SubProjects { get; init; }
}

/// <summary>
/// Compilation diagnostics information
/// </summary>
public class DiagnosticsInfo
{
    public int ErrorCount { get; init; }
    public int WarningCount { get; init; }
    public int TotalCount { get; init; }
    public bool IsSafeToRefactor { get; init; }
    public string Message { get; init; } = string.Empty;
    public List<DiagnosticInfo> Diagnostics { get; init; } = new();
}

/// <summary>
/// Information about symbol references
/// </summary>
public class ReferencesInfo
{
    public string SymbolName { get; init; } = string.Empty;
    public string SymbolKind { get; init; } = string.Empty;
    public int ReferenceCount { get; init; }
    public List<ReferenceLocation> References { get; init; } = new();
}

/// <summary>
/// Information about a renamed symbol
/// </summary>
public class RenameInfo
{
    public string OldName { get; init; } = string.Empty;
    public string NewName { get; init; } = string.Empty;
    public string SymbolKind { get; init; } = string.Empty;
    public int FilesModified { get; init; }
    public string Message { get; init; } = string.Empty;
}

/// <summary>
/// Detailed symbol information
/// </summary>
public class SymbolInfo
{
    public string Name { get; init; } = string.Empty;
    public string Kind { get; init; } = string.Empty;
    public string Type { get; init; } = string.Empty;
    public string ContainingType { get; init; } = string.Empty;
    public string ContainingNamespace { get; init; } = string.Empty;
    public bool IsStatic { get; init; }
    public bool IsAbstract { get; init; }
    public bool IsVirtual { get; init; }
    public string Accessibility { get; init; } = string.Empty;
    public string? Documentation { get; init; }
}

/// <summary>
/// Result of a refactoring operation
/// </summary>
public class RefactoringResult
{
    public string Message { get; init; } = string.Empty;
    public int FilesModified { get; init; }
    public List<string> ModifiedFiles { get; init; } = new();
}
