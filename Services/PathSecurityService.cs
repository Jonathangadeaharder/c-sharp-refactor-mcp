using Microsoft.Extensions.Configuration;

namespace RoslynRefactorServer.Services;

/// <summary>
/// Service responsible for validating file and solution paths to prevent path traversal attacks.
/// Implements the security recommendations from Section 7.3 of the architecture document.
/// </summary>
public class PathSecurityService
{
    private readonly List<string> _allowedRootPaths;
    private readonly ILogger<PathSecurityService> _logger;

    public PathSecurityService(IConfiguration configuration, ILogger<PathSecurityService> logger)
    {
        _logger = logger;
        _allowedRootPaths = configuration.GetSection("Security:AllowedRootPaths")
            .Get<List<string>>() ?? new List<string>();

        if (!_allowedRootPaths.Any())
        {
            _logger.LogWarning("No allowed root paths configured. All path validations will fail.");
        }
        else
        {
            _logger.LogInformation("Configured {Count} allowed root paths", _allowedRootPaths.Count);
            foreach (var path in _allowedRootPaths)
            {
                _logger.LogInformation("  - {Path}", path);
            }
        }
    }

    /// <summary>
    /// Validates that a path is within one of the allowed root directories.
    /// Throws SecurityException if the path is not allowed.
    /// </summary>
    public string ValidateAndNormalizePath(string path, string parameterName = "path")
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            throw new ArgumentException("Path cannot be null or empty", parameterName);
        }

        try
        {
            // Canonicalize the path to prevent traversal attacks
            var normalizedPath = Path.GetFullPath(path);

            // Check if the path is within any allowed root
            bool isAllowed = _allowedRootPaths.Any(allowedRoot =>
            {
                var normalizedRoot = Path.GetFullPath(allowedRoot);
                return normalizedPath.StartsWith(normalizedRoot, StringComparison.OrdinalIgnoreCase);
            });

            if (!isAllowed)
            {
                _logger.LogWarning("Path validation failed for {Path}. Not within allowed roots.", normalizedPath);
                throw new SecurityException(
                    $"Access denied: Path '{normalizedPath}' is not within any allowed root directory. " +
                    $"Configured allowed roots: {string.Join(", ", _allowedRootPaths)}");
            }

            _logger.LogDebug("Path validated successfully: {Path}", normalizedPath);
            return normalizedPath;
        }
        catch (Exception ex) when (ex is not SecurityException)
        {
            _logger.LogError(ex, "Error validating path: {Path}", path);
            throw new ArgumentException($"Invalid path: {path}", parameterName, ex);
        }
    }

    /// <summary>
    /// Checks if a path exists and is a valid solution file
    /// </summary>
    public void ValidateSolutionFile(string path)
    {
        var normalizedPath = ValidateAndNormalizePath(path, "solutionPath");

        if (!File.Exists(normalizedPath))
        {
            throw new FileNotFoundException($"Solution file not found: {normalizedPath}");
        }

        if (!normalizedPath.EndsWith(".sln", StringComparison.OrdinalIgnoreCase))
        {
            throw new ArgumentException($"Path is not a solution file (.sln): {normalizedPath}");
        }
    }

    /// <summary>
    /// Validates that a document path exists
    /// </summary>
    public void ValidateDocumentFile(string path)
    {
        var normalizedPath = ValidateAndNormalizePath(path, "documentPath");

        if (!File.Exists(normalizedPath))
        {
            throw new FileNotFoundException($"Document file not found: {normalizedPath}");
        }
    }
}
