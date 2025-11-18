// @structurelint:no-test - Integration component requiring LSP server
using Microsoft.Extensions.Logging;

namespace RoslynRefactorServer.Providers;

/// <summary>
/// Language provider for Java using jdtls (Eclipse JDT Language Server)
/// </summary>
public class JavaLanguageProvider : BaseLspLanguageProvider
{
    public override string LanguageId => "java";
    public override string LanguageName => "Java";
    public override IReadOnlyList<string> SupportedExtensions => new[] { ".java" };
    public override IReadOnlyList<string> ProjectFileExtensions => new[] { "pom.xml", "build.gradle", "build.gradle.kts" };

    protected override string ServerCommand => "jdtls";
    protected override string[] ServerArgs => Array.Empty<string>();

    public JavaLanguageProvider(ILogger<JavaLanguageProvider> logger) : base(logger)
    {
    }
}
