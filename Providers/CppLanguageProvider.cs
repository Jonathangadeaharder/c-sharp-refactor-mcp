using Microsoft.Extensions.Logging;

namespace RoslynRefactorServer.Providers;

/// <summary>
/// Language provider for C++ using clangd
/// </summary>
public class CppLanguageProvider : BaseLspLanguageProvider
{
    public override string LanguageId => "cpp";
    public override string LanguageName => "C++";
    public override IReadOnlyList<string> SupportedExtensions => new[] { ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx" };
    public override IReadOnlyList<string> ProjectFileExtensions => new[] { "CMakeLists.txt", "compile_commands.json", "Makefile" };

    protected override string ServerCommand => "clangd";
    protected override string[] ServerArgs => new[] { "--background-index" };

    public CppLanguageProvider(ILogger<CppLanguageProvider> logger) : base(logger)
    {
    }
}
