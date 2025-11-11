namespace RoslynRefactorServer.Models;

/// <summary>
/// Represents a reference location in the codebase
/// </summary>
public class ReferenceLocation
{
    public string FilePath { get; set; } = string.Empty;
    public int StartLine { get; set; }
    public int StartColumn { get; set; }
    public int EndLine { get; set; }
    public int EndColumn { get; set; }
    public string CodeSnippet { get; set; } = string.Empty;
}
