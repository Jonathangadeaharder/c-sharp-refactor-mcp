// @structurelint:no-test - Integration component requiring LSP server
using Microsoft.Extensions.Logging;

namespace RoslynRefactorServer.Providers;

/// <summary>
/// Language provider for Python using Pyright (Python type checker and language server)
/// Based on the python-refactor-mcp architecture
/// </summary>
public class PythonLanguageProvider : BaseLspLanguageProvider
{
    public override string LanguageId => "python";
    public override string LanguageName => "Python";
    public override IReadOnlyList<string> SupportedExtensions => new[] { ".py", ".pyi" };
    public override IReadOnlyList<string> ProjectFileExtensions => new[] { "pyproject.toml", "setup.py", "requirements.txt", "Pipfile" };

    // Pyright is the recommended language server for Python
    // It provides type checking and semantic analysis
    protected override string ServerCommand => "pyright-langserver";
    protected override string[] ServerArgs => new[] { "--stdio" };

    public PythonLanguageProvider(ILogger<PythonLanguageProvider> logger) : base(logger)
    {
        _logger.LogInformation("Python language provider initialized (using Pyright)");
    }
}
