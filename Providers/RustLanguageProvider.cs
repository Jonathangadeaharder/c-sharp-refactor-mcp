using Microsoft.Extensions.Logging;

namespace RoslynRefactorServer.Providers;

/// <summary>
/// Language provider for Rust using rust-analyzer
/// </summary>
public class RustLanguageProvider : BaseLspLanguageProvider
{
    public override string LanguageId => "rust";
    public override string LanguageName => "Rust";
    public override IReadOnlyList<string> SupportedExtensions => new[] { ".rs" };
    public override IReadOnlyList<string> ProjectFileExtensions => new[] { "Cargo.toml", "Cargo.lock" };

    protected override string ServerCommand => "rust-analyzer";
    protected override string[] ServerArgs => Array.Empty<string>();

    public RustLanguageProvider(ILogger<RustLanguageProvider> logger) : base(logger)
    {
    }
}
