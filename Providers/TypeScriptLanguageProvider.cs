using Microsoft.Extensions.Logging;

namespace RoslynRefactorServer.Providers;

/// <summary>
/// Language provider for TypeScript using typescript-language-server
/// </summary>
public class TypeScriptLanguageProvider : BaseLspLanguageProvider
{
    public override string LanguageId => "typescript";
    public override string LanguageName => "TypeScript";
    public override IReadOnlyList<string> SupportedExtensions => new[] { ".ts", ".tsx" };
    public override IReadOnlyList<string> ProjectFileExtensions => new[] { "tsconfig.json", "package.json" };

    protected override string ServerCommand => "typescript-language-server";
    protected override string[] ServerArgs => new[] { "--stdio" };

    public TypeScriptLanguageProvider(ILogger<TypeScriptLanguageProvider> logger) : base(logger)
    {
    }
}
