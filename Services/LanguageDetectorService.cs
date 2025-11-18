using Microsoft.Extensions.Logging;
using RoslynRefactorServer.Abstractions;

namespace RoslynRefactorServer.Services;

/// <summary>
/// Service for detecting the language of a project and returning the appropriate language provider
/// </summary>
public class LanguageDetectorService
{
    private readonly ILogger<LanguageDetectorService> _logger;
    private readonly Dictionary<string, ILanguageProvider> _providers;

    public LanguageDetectorService(
        IEnumerable<ILanguageProvider> providers,
        ILogger<LanguageDetectorService> logger)
    {
        _logger = logger;
        _providers = providers.ToDictionary(p => p.LanguageId, p => p);

        _logger.LogInformation("Registered {Count} language providers: {Languages}",
            _providers.Count,
            string.Join(", ", _providers.Keys));
    }

    /// <summary>
    /// Detects the language from a project file path
    /// </summary>
    public ILanguageProvider? DetectFromProjectFile(string projectPath)
    {
        var extension = Path.GetExtension(projectPath).ToLowerInvariant();

        foreach (var provider in _providers.Values)
        {
            if (provider.ProjectFileExtensions.Any(ext =>
                ext.Equals(extension, StringComparison.OrdinalIgnoreCase)))
            {
                _logger.LogInformation("Detected language {Language} from project file extension {Extension}",
                    provider.LanguageName, extension);
                return provider;
            }
        }

        // Try to detect from directory structure
        var directory = Path.GetDirectoryName(projectPath);
        if (directory != null)
        {
            return DetectFromDirectory(directory);
        }

        _logger.LogWarning("Could not detect language from project file: {Path}", projectPath);
        return null;
    }

    /// <summary>
    /// Detects the language from a source file path
    /// </summary>
    public ILanguageProvider? DetectFromSourceFile(string filePath)
    {
        var extension = Path.GetExtension(filePath).ToLowerInvariant();

        foreach (var provider in _providers.Values)
        {
            if (provider.SupportedExtensions.Any(ext =>
                ext.Equals(extension, StringComparison.OrdinalIgnoreCase)))
            {
                _logger.LogInformation("Detected language {Language} from file extension {Extension}",
                    provider.LanguageName, extension);
                return provider;
            }
        }

        _logger.LogWarning("Could not detect language from source file: {Path}", filePath);
        return null;
    }

    /// <summary>
    /// Detects language from directory structure by looking for characteristic files
    /// </summary>
    public ILanguageProvider? DetectFromDirectory(string directoryPath)
    {
        if (!Directory.Exists(directoryPath))
        {
            return null;
        }

        // Check for characteristic project files
        var files = Directory.GetFiles(directoryPath, "*", SearchOption.TopDirectoryOnly);

        foreach (var provider in _providers.Values)
        {
            foreach (var projectExt in provider.ProjectFileExtensions)
            {
                if (files.Any(f => f.EndsWith(projectExt, StringComparison.OrdinalIgnoreCase)))
                {
                    _logger.LogInformation("Detected language {Language} from directory contents",
                        provider.LanguageName);
                    return provider;
                }
            }
        }

        // Check for language-specific marker files
        var markerFiles = new Dictionary<string, string>
        {
            { "go.mod", "go" },
            { "Cargo.toml", "rust" },
            { "pyproject.toml", "python" },
            { "requirements.txt", "python" },
            { "setup.py", "python" },
            { "package.json", "typescript" }, // Could be JavaScript, but TypeScript is a superset
            { "pom.xml", "java" },
            { "build.gradle", "java" },
            { "CMakeLists.txt", "cpp" }
        };

        foreach (var (markerFile, languageId) in markerFiles)
        {
            if (files.Any(f => Path.GetFileName(f).Equals(markerFile, StringComparison.OrdinalIgnoreCase)))
            {
                if (_providers.TryGetValue(languageId, out var provider))
                {
                    _logger.LogInformation("Detected language {Language} from marker file {Marker}",
                        provider.LanguageName, markerFile);
                    return provider;
                }
            }
        }

        _logger.LogWarning("Could not detect language from directory: {Path}", directoryPath);
        return null;
    }

    /// <summary>
    /// Gets a language provider by its language ID
    /// </summary>
    public ILanguageProvider? GetProvider(string languageId)
    {
        _providers.TryGetValue(languageId.ToLowerInvariant(), out var provider);
        return provider;
    }

    /// <summary>
    /// Gets all registered language providers
    /// </summary>
    public IEnumerable<ILanguageProvider> GetAllProviders()
    {
        return _providers.Values;
    }
}
