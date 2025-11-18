using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.MSBuild;
using Microsoft.Extensions.Logging;
using System.Collections.Concurrent;

namespace RoslynRefactorServer.Services;

/// <summary>
/// Singleton service managing Roslyn workspace state, caching, and concurrency.
/// This is the core "Semantic Oracle" that maintains solution state across tool calls.
/// </summary>
public class RoslynWorkspaceService : IDisposable
{
    private readonly MSBuildWorkspace _workspace;
    private readonly ILogger<RoslynWorkspaceService> _logger;

    // Caches the "head state" of loaded solutions.
    // Key: absolute solution file path. Value: the Solution object.
    private readonly ConcurrentDictionary<string, Solution> _solutionCache;

    // Manages per-solution write locks to prevent race conditions.
    // Key: absolute solution file path. Value: a semaphore for that solution.
    private readonly ConcurrentDictionary<string, SemaphoreSlim> _solutionLocks;

    // Tracks file modification times to detect stale cache
    private readonly ConcurrentDictionary<string, ConcurrentDictionary<string, DateTime>> _fileTimestamps;

    public RoslynWorkspaceService(ILogger<RoslynWorkspaceService> logger)
    {
        _logger = logger;
        _workspace = MSBuildWorkspace.Create();
        _solutionCache = new ConcurrentDictionary<string, Solution>();
        _solutionLocks = new ConcurrentDictionary<string, SemaphoreSlim>();
        _fileTimestamps = new ConcurrentDictionary<string, ConcurrentDictionary<string, DateTime>>();

        // Log workspace diagnostics (helpful for debugging)
        _workspace.WorkspaceFailed += (sender, args) =>
        {
            _logger.LogWarning("Workspace diagnostic: {Diagnostic}", args.Diagnostic.Message);
        };
    }

    /// <summary>
    /// Loads a solution into cache, or refreshes if stale.
    /// This implements the "on-demand cache refresh" pattern to prevent data loss.
    /// </summary>
    public async Task<Solution> LoadOrRefreshSolutionAsync(string solutionPath)
    {
        var normalizedPath = Path.GetFullPath(solutionPath);

        if (_solutionCache.TryGetValue(normalizedPath, out Solution? cachedSolution))
        {
            _logger.LogInformation("Found cached solution for {Path}", normalizedPath);

            // Check if cache is stale by comparing file timestamps
            if (await IsCacheStaleAsync(normalizedPath, cachedSolution))
            {
                _logger.LogInformation("Cache is stale, reloading solution {Path}", normalizedPath);
                return await ReloadSolutionAsync(normalizedPath);
            }

            _logger.LogInformation("Cache is fresh, returning cached solution");
            return cachedSolution;
        }

        // Cache is empty, load from disk
        _logger.LogInformation("Loading solution for the first time: {Path}", normalizedPath);
        return await ReloadSolutionAsync(normalizedPath);
    }

    /// <summary>
    /// Checks if the cached solution is stale by comparing file modification times
    /// </summary>
    private async Task<bool> IsCacheStaleAsync(string solutionPath, Solution solution)
    {
        try
        {
            var timestamps = _fileTimestamps.GetOrAdd(solutionPath, _ => new ConcurrentDictionary<string, DateTime>());

            foreach (var project in solution.Projects)
            {
                foreach (var document in project.Documents)
                {
                    if (document.FilePath == null) continue;

                    var fileInfo = new FileInfo(document.FilePath);
                    if (!fileInfo.Exists) continue;

                    var lastWriteTime = fileInfo.LastWriteTimeUtc;

                    if (timestamps.TryGetValue(document.FilePath, out var cachedTime))
                    {
                        if (lastWriteTime > cachedTime)
                        {
                            _logger.LogInformation("File {FilePath} has been modified externally", document.FilePath);
                            return true;
                        }
                    }
                }
            }

            return false;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Error checking cache staleness, forcing reload");
            return true;
        }
    }

    /// <summary>
    /// Reloads a solution from disk and updates the cache
    /// </summary>
    private async Task<Solution> ReloadSolutionAsync(string solutionPath)
    {
        var normalizedPath = Path.GetFullPath(solutionPath);

        try
        {
            _logger.LogInformation("Opening solution: {Path}", normalizedPath);
            var solution = await _workspace.OpenSolutionAsync(normalizedPath);

            // Update cache
            _solutionCache[normalizedPath] = solution;

            // Update timestamps
            UpdateTimestamps(normalizedPath, solution);

            _logger.LogInformation("Solution loaded successfully: {ProjectCount} projects", solution.Projects.Count());
            return solution;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load solution: {Path}", normalizedPath);
            throw;
        }
    }

    /// <summary>
    /// Updates the timestamp cache for all files in the solution
    /// </summary>
    private void UpdateTimestamps(string solutionPath, Solution solution)
    {
        var timestamps = _fileTimestamps.GetOrAdd(solutionPath, _ => new ConcurrentDictionary<string, DateTime>());
        timestamps.Clear();

        foreach (var project in solution.Projects)
        {
            foreach (var document in project.Documents)
            {
                if (document.FilePath == null) continue;

                try
                {
                    var fileInfo = new FileInfo(document.FilePath);
                    if (fileInfo.Exists)
                    {
                        timestamps[document.FilePath] = fileInfo.LastWriteTimeUtc;
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, "Failed to get timestamp for {FilePath}", document.FilePath);
                }
            }
        }
    }

    /// <summary>
    /// Applies changes to the workspace and updates the cache atomically.
    /// This method MUST be used for all write operations to ensure thread safety.
    /// </summary>
    public async Task UpdateAndApplyChangesAsync(string solutionPath, Solution newSolution)
    {
        var normalizedPath = Path.GetFullPath(solutionPath);

        // Get or create a lock specific to this solution path
        var solutionLock = _solutionLocks.GetOrAdd(normalizedPath, _ => new SemaphoreSlim(1, 1));

        // Asynchronously wait to enter the critical section
        await solutionLock.WaitAsync();
        try
        {
            _logger.LogInformation("Applying changes to solution: {Path}", normalizedPath);

            // CRITICAL SECTION: Only one thread at a time per solution can be in here.

            // Apply changes to the workspace, which writes to disk
            if (!_workspace.TryApplyChanges(newSolution))
            {
                throw new InvalidOperationException($"Failed to apply changes to workspace for solution: {normalizedPath}");
            }

            // Only if successful, update the cache to the new head state.
            _solutionCache[normalizedPath] = newSolution;

            // Update timestamps
            UpdateTimestamps(normalizedPath, newSolution);

            _logger.LogInformation("Changes applied successfully");
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to apply changes");

            // Invalidate cache to force reload on next operation
            _solutionCache.TryRemove(normalizedPath, out _);
            _fileTimestamps.TryRemove(normalizedPath, out _);

            throw;
        }
        finally
        {
            // Release the lock
            solutionLock.Release();
        }
    }

    /// <summary>
    /// Invalidates the cache for a solution, forcing a reload on next access
    /// </summary>
    public void InvalidateCache(string solutionPath)
    {
        var normalizedPath = Path.GetFullPath(solutionPath);
        _solutionCache.TryRemove(normalizedPath, out _);
        _fileTimestamps.TryRemove(normalizedPath, out _);
        _logger.LogInformation("Cache invalidated for {Path}", normalizedPath);
    }

    public void Dispose()
    {
        _workspace?.Dispose();

        foreach (var semaphore in _solutionLocks.Values)
        {
            semaphore?.Dispose();
        }

        _solutionLocks.Clear();
        _solutionCache.Clear();
        _fileTimestamps.Clear();
    }
}
