// @structurelint:no-test - Integration component requiring LSP server
using Microsoft.Extensions.Logging;

namespace RoslynRefactorServer.Providers;

/// <summary>
/// Language provider for Go using gopls
/// </summary>
public class GoLanguageProvider : BaseLspLanguageProvider
{
    public override string LanguageId => "go";
    public override string LanguageName => "Go";
    public override IReadOnlyList<string> SupportedExtensions => new[] { ".go" };
    public override IReadOnlyList<string> ProjectFileExtensions => new[] { "go.mod", "go.sum" };

    protected override string ServerCommand => "gopls";
    protected override string[] ServerArgs => Array.Empty<string>();

    public GoLanguageProvider(ILogger<GoLanguageProvider> logger) : base(logger)
    {
    }
}
