using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.MSBuild;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using System.Collections.Concurrent;

namespace RoslynRefactorServer.Services;

/// <summary>
/// Singleton service managing Roslyn workspace state, caching, and concurrency.
/// This is the core "Semantic Oracle" that maintains solution state across tool calls.
///
/// Optimizations implemented:
/// 1. LRU cache eviction with memory management
/// 2. Compilation caching for faster diagnostics
/// 3. FileSystemWatcher with debouncing for reactive cache invalidation
/// </summary>
public class RoslynWorkspaceService : IDisposable
{
    private readonly MSBuildWorkspace _workspace;
    private readonly ILogger<RoslynWorkspaceService> _logger;

    // OPTIMIZATION 1: LRU Cache with Memory Management
    // Caches solution metadata including memory estimates and access times
    private readonly ConcurrentDictionary<string, SolutionCacheEntry> _solutionCache;
    private readonly long _maxCacheMemoryBytes;
    private readonly SemaphoreSlim _evictionLock = new(1, 1);

    // OPTIMIZATION 2: Compilation Caching
    // Caches compiled assemblies per project for faster diagnostics
    private readonly ConcurrentDictionary<ProjectId, CompilationCacheEntry> _compilationCache;

    // OPTIMIZATION 3: FileSystemWatcher with Debouncing
    // Reactive cache invalidation instead of O(N) staleness checks
    private readonly ConcurrentDictionary<string, FileSystemWatcher> _fileWatchers;
    private readonly ConcurrentDictionary<string, CancellationTokenSource> _debouncers;
    private readonly int _debounceDelayMs;
    private readonly bool _enableFileWatcher;

    // Manages per-solution write locks to prevent race conditions.
    // Key: absolute solution file path. Value: a semaphore for that solution.
    private readonly ConcurrentDictionary<string, SemaphoreSlim> _solutionLocks;

    // Tracks file modification times (fallback for when FileSystemWatcher is disabled)
    private readonly ConcurrentDictionary<string, ConcurrentDictionary<string, DateTime>> _fileTimestamps;

    /// <summary>
    /// Cache entry with memory tracking and LRU metadata
    /// </summary>
    private class SolutionCacheEntry
    {
        public Solution Solution { get; set; } = null!;
        public DateTime LastAccessed { get; set; }
        public long EstimatedMemoryBytes { get; set; }
        public int DocumentCount { get; set; }
    }

    /// <summary>
    /// Compilation cache entry with staleness detection
    /// </summary>
    private class CompilationCacheEntry
    {
        public Compilation Compilation { get; set; } = null!;
        public DateTime CachedAt { get; set; }
        public DateTime LastProjectModification { get; set; }
    }

    public RoslynWorkspaceService(ILogger<RoslynWorkspaceService> logger, IConfiguration? configuration = null)
    {
        _logger = logger;
        _workspace = MSBuildWorkspace.Create();

        // Initialize caches
        _solutionCache = new ConcurrentDictionary<string, SolutionCacheEntry>();
        _compilationCache = new ConcurrentDictionary<ProjectId, CompilationCacheEntry>();
        _solutionLocks = new ConcurrentDictionary<string, SemaphoreSlim>();
        _fileTimestamps = new ConcurrentDictionary<string, ConcurrentDictionary<string, DateTime>>();
        _fileWatchers = new ConcurrentDictionary<string, FileSystemWatcher>();
        _debouncers = new ConcurrentDictionary<string, CancellationTokenSource>();

        // Load configuration (defaults if not provided)
        _maxCacheMemoryBytes = configuration?.GetValue<long>("Workspace:MaxCacheMemoryMB", 4096) * 1024 * 1024 ?? 4L * 1024 * 1024 * 1024; // Default: 4GB
        _debounceDelayMs = configuration?.GetValue<int>("Workspace:DebounceDelayMs", 500) ?? 500; // Default: 500ms
        _enableFileWatcher = configuration?.GetValue<bool>("Workspace:EnableFileWatcher", true) ?? true; // Default: enabled

        _logger.LogInformation("RoslynWorkspaceService initialized with MaxCacheMemory={MaxMemoryMB}MB, DebounceDelay={DebounceMs}ms, FileWatcher={EnabledFileWatcher}",
            _maxCacheMemoryBytes / (1024 * 1024), _debounceDelayMs, _enableFileWatcher);

        // Log workspace diagnostics (helpful for debugging)
        _workspace.WorkspaceFailed += (sender, args) =>
        {
            _logger.LogWarning("Workspace diagnostic: {Diagnostic}", args.Diagnostic.Message);
        };
    }

    /// <summary>
    /// Loads a solution into cache, or refreshes if stale.
    /// This implements the "on-demand cache refresh" pattern to prevent data loss.
    /// OPTIMIZATION: Updates LRU last accessed time and triggers eviction if needed.
    /// </summary>
    public async Task<Solution> LoadOrRefreshSolutionAsync(string solutionPath)
    {
        var normalizedPath = Path.GetFullPath(solutionPath);

        if (_solutionCache.TryGetValue(normalizedPath, out SolutionCacheEntry? cacheEntry))
        {
            _logger.LogInformation("Found cached solution for {Path}", normalizedPath);

            // OPTIMIZATION: Update last accessed time for LRU
            cacheEntry.LastAccessed = DateTime.UtcNow;

            // Check if cache is stale (only if FileSystemWatcher is disabled)
            if (!_enableFileWatcher && await IsCacheStaleAsync(normalizedPath, cacheEntry.Solution))
            {
                _logger.LogInformation("Cache is stale, reloading solution {Path}", normalizedPath);
                return await ReloadSolutionAsync(normalizedPath);
            }

            _logger.LogInformation("Cache is fresh, returning cached solution");
            return cacheEntry.Solution;
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
    /// OPTIMIZATION: Creates cache entry with memory estimates and sets up FileSystemWatcher
    /// </summary>
    private async Task<Solution> ReloadSolutionAsync(string solutionPath)
    {
        var normalizedPath = Path.GetFullPath(solutionPath);

        try
        {
            _logger.LogInformation("Opening solution: {Path}", normalizedPath);
            var solution = await _workspace.OpenSolutionAsync(normalizedPath);

            // OPTIMIZATION 1: Estimate memory usage for LRU eviction
            var documentCount = solution.Projects.SelectMany(p => p.Documents).Count();
            var estimatedMemoryBytes = EstimateMemoryUsage(solution);

            // Create cache entry
            var cacheEntry = new SolutionCacheEntry
            {
                Solution = solution,
                LastAccessed = DateTime.UtcNow,
                EstimatedMemoryBytes = estimatedMemoryBytes,
                DocumentCount = documentCount
            };

            // OPTIMIZATION 1: Check if we need to evict before adding
            await EvictLRUIfNeededAsync(estimatedMemoryBytes);

            // Update cache
            _solutionCache[normalizedPath] = cacheEntry;

            // Update timestamps (fallback for when FileSystemWatcher is disabled)
            UpdateTimestamps(normalizedPath, solution);

            // OPTIMIZATION 3: Setup FileSystemWatcher for this solution
            if (_enableFileWatcher)
            {
                SetupFileWatcher(normalizedPath);
            }

            _logger.LogInformation("Solution loaded successfully: {ProjectCount} projects, {DocumentCount} documents, ~{MemoryMB}MB",
                solution.Projects.Count(), documentCount, estimatedMemoryBytes / (1024 * 1024));

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
    /// OPTIMIZATION: Invalidates related compilation cache entries.
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

            // OPTIMIZATION 2: Invalidate compilation cache for modified projects
            if (_solutionCache.TryGetValue(normalizedPath, out var oldEntry))
            {
                var changedProjects = newSolution.GetChanges(oldEntry.Solution).GetProjectChanges();
                foreach (var projectChange in changedProjects)
                {
                    _compilationCache.TryRemove(projectChange.ProjectId, out _);
                    _logger.LogDebug("Invalidated compilation cache for project {ProjectId}", projectChange.ProjectId);
                }
            }

            // Update cache entry (reuse existing or create new)
            if (_solutionCache.TryGetValue(normalizedPath, out var cacheEntry))
            {
                cacheEntry.Solution = newSolution;
                cacheEntry.LastAccessed = DateTime.UtcNow;
            }
            else
            {
                var documentCount = newSolution.Projects.SelectMany(p => p.Documents).Count();
                _solutionCache[normalizedPath] = new SolutionCacheEntry
                {
                    Solution = newSolution,
                    LastAccessed = DateTime.UtcNow,
                    EstimatedMemoryBytes = EstimateMemoryUsage(newSolution),
                    DocumentCount = documentCount
                };
            }

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
    /// OPTIMIZATION: Also cleans up FileSystemWatcher and compilation cache
    /// </summary>
    public void InvalidateCache(string solutionPath)
    {
        var normalizedPath = Path.GetFullPath(solutionPath);

        // Remove solution cache entry
        if (_solutionCache.TryRemove(normalizedPath, out var cacheEntry))
        {
            // OPTIMIZATION 2: Remove compilation cache for all projects in the solution
            foreach (var project in cacheEntry.Solution.Projects)
            {
                _compilationCache.TryRemove(project.Id, out _);
            }
        }

        _fileTimestamps.TryRemove(normalizedPath, out _);

        // OPTIMIZATION 3: Cleanup FileSystemWatcher
        if (_fileWatchers.TryRemove(normalizedPath, out var watcher))
        {
            watcher.Dispose();
        }

        // Cancel any pending debounce operations
        if (_debouncers.TryRemove(normalizedPath, out var cts))
        {
            cts.Cancel();
            cts.Dispose();
        }

        _logger.LogInformation("Cache invalidated for {Path}", normalizedPath);
    }

    // =============================================================================================
    // OPTIMIZATION 1: LRU Cache Eviction with Memory Management
    // =============================================================================================

    /// <summary>
    /// Estimates memory usage of a solution based on document count and project count
    /// </summary>
    private long EstimateMemoryUsage(Solution solution)
    {
        // Heuristic: ~50KB per document + ~10MB per project (for metadata and references)
        var documentCount = solution.Projects.SelectMany(p => p.Documents).Count();
        var projectCount = solution.Projects.Count();

        var estimatedBytes = (documentCount * 50L * 1024) + (projectCount * 10L * 1024 * 1024);

        return estimatedBytes;
    }

    /// <summary>
    /// Evicts least recently used solutions if adding the new solution would exceed memory limit
    /// </summary>
    private async Task EvictLRUIfNeededAsync(long newSolutionBytes)
    {
        await _evictionLock.WaitAsync();
        try
        {
            var totalMemory = _solutionCache.Values.Sum(e => e.EstimatedMemoryBytes);

            // Check if we need to evict
            if (totalMemory + newSolutionBytes <= _maxCacheMemoryBytes)
            {
                return; // No eviction needed
            }

            _logger.LogWarning("Cache memory limit approaching: {CurrentMB}MB + {NewMB}MB > {MaxMB}MB. Starting LRU eviction.",
                totalMemory / (1024 * 1024),
                newSolutionBytes / (1024 * 1024),
                _maxCacheMemoryBytes / (1024 * 1024));

            // Evict solutions in LRU order until we have enough space
            var sortedByLRU = _solutionCache
                .OrderBy(kvp => kvp.Value.LastAccessed)
                .ToList();

            foreach (var (path, entry) in sortedByLRU)
            {
                if (totalMemory + newSolutionBytes <= _maxCacheMemoryBytes)
                {
                    break; // Enough space freed
                }

                _logger.LogInformation("Evicting solution {Path} (LastAccessed: {LastAccessed}, ~{MemoryMB}MB)",
                    path, entry.LastAccessed, entry.EstimatedMemoryBytes / (1024 * 1024));

                InvalidateCache(path);
                totalMemory -= entry.EstimatedMemoryBytes;
            }

            _logger.LogInformation("LRU eviction complete. New memory estimate: {MemoryMB}MB",
                totalMemory / (1024 * 1024));
        }
        finally
        {
            _evictionLock.Release();
        }
    }

    /// <summary>
    /// Gets cache statistics for monitoring
    /// </summary>
    public (int SolutionCount, long TotalMemoryBytes, int OldestAccessAgeSeconds) GetCacheStatistics()
    {
        var entries = _solutionCache.Values.ToList();
        if (entries.Count == 0)
        {
            return (0, 0, 0);
        }

        var totalMemory = entries.Sum(e => e.EstimatedMemoryBytes);
        var oldestAccess = entries.Min(e => e.LastAccessed);
        var ageSeconds = (int)(DateTime.UtcNow - oldestAccess).TotalSeconds;

        return (entries.Count, totalMemory, ageSeconds);
    }

    // =============================================================================================
    // OPTIMIZATION 2: Compilation Caching for Faster Diagnostics
    // =============================================================================================

    /// <summary>
    /// Gets a cached compilation for a project, or compiles and caches if not available
    /// </summary>
    public async Task<Compilation?> GetOrCacheCompilationAsync(Project project)
    {
        // Check if we have a cached compilation
        if (_compilationCache.TryGetValue(project.Id, out var cached))
        {
            // Validate that the cached compilation is still valid
            var projectLastModified = await GetProjectLastModificationTimeAsync(project);

            if (cached.LastProjectModification >= projectLastModified)
            {
                _logger.LogDebug("Using cached compilation for project {ProjectName}", project.Name);
                return cached.Compilation;
            }

            _logger.LogDebug("Cached compilation is stale for project {ProjectName}", project.Name);
        }

        // Compile and cache
        _logger.LogInformation("Compiling project {ProjectName}...", project.Name);
        var compilation = await project.GetCompilationAsync();

        if (compilation != null)
        {
            var lastModified = await GetProjectLastModificationTimeAsync(project);

            _compilationCache[project.Id] = new CompilationCacheEntry
            {
                Compilation = compilation,
                CachedAt = DateTime.UtcNow,
                LastProjectModification = lastModified
            };

            _logger.LogDebug("Cached compilation for project {ProjectName}", project.Name);
        }

        return compilation;
    }

    /// <summary>
    /// Gets the last modification time of any file in the project
    /// </summary>
    private async Task<DateTime> GetProjectLastModificationTimeAsync(Project project)
    {
        var maxTime = DateTime.MinValue;

        foreach (var document in project.Documents)
        {
            if (document.FilePath == null || !File.Exists(document.FilePath))
                continue;

            try
            {
                var fileTime = File.GetLastWriteTimeUtc(document.FilePath);
                if (fileTime > maxTime)
                {
                    maxTime = fileTime;
                }
            }
            catch
            {
                // Ignore errors
            }
        }

        return maxTime;
    }

    // =============================================================================================
    // OPTIMIZATION 3: FileSystemWatcher with Debouncing
    // =============================================================================================

    /// <summary>
    /// Sets up a FileSystemWatcher for a solution to detect external changes
    /// </summary>
    private void SetupFileWatcher(string solutionPath)
    {
        var normalizedPath = Path.GetFullPath(solutionPath);

        // Check if watcher already exists
        if (_fileWatchers.ContainsKey(normalizedPath))
        {
            return;
        }

        try
        {
            var directory = Path.GetDirectoryName(normalizedPath);
            if (directory == null || !Directory.Exists(directory))
            {
                _logger.LogWarning("Cannot setup FileSystemWatcher: directory not found for {Path}", solutionPath);
                return;
            }

            var watcher = new FileSystemWatcher(directory)
            {
                IncludeSubdirectories = true,
                NotifyFilter = NotifyFilters.LastWrite | NotifyFilters.FileName | NotifyFilters.DirectoryName,
                Filter = "*.*" // Watch all files
            };

            // Wire up events
            watcher.Changed += (s, e) => OnFileSystemChange(normalizedPath, e);
            watcher.Created += (s, e) => OnFileSystemChange(normalizedPath, e);
            watcher.Deleted += (s, e) => OnFileSystemChange(normalizedPath, e);
            watcher.Renamed += (s, e) => OnFileSystemChange(normalizedPath, e);

            watcher.Error += (s, e) =>
            {
                _logger.LogError(e.GetException(), "FileSystemWatcher error for {Path}", normalizedPath);
            };

            watcher.EnableRaisingEvents = true;
            _fileWatchers[normalizedPath] = watcher;

            _logger.LogInformation("FileSystemWatcher enabled for {Path}", normalizedPath);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to setup FileSystemWatcher for {Path}. Falling back to timestamp checks.", solutionPath);
        }
    }

    /// <summary>
    /// Handles file system change events with debouncing
    /// </summary>
    private void OnFileSystemChange(string solutionPath, FileSystemEventArgs e)
    {
        // Filter out non-code files (bin, obj, etc.)
        var filePath = e.FullPath;
        if (filePath.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}") ||
            filePath.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}") ||
            filePath.Contains($"{Path.DirectorySeparatorChar}.vs{Path.DirectorySeparatorChar}") ||
            filePath.Contains($"{Path.DirectorySeparatorChar}.git{Path.DirectorySeparatorChar}"))
        {
            return; // Ignore build artifacts and VCS files
        }

        // Only watch relevant file extensions
        var extension = Path.GetExtension(filePath).ToLowerInvariant();
        if (extension != ".cs" && extension != ".csproj" && extension != ".sln" && extension != ".vb")
        {
            return;
        }

        _logger.LogDebug("File system change detected: {ChangeType} {Path}", e.ChangeType, e.Name);

        // Debounce the invalidation
        DebounceInvalidation(solutionPath);
    }

    /// <summary>
    /// Debounces cache invalidation to avoid invalidating on every keystroke
    /// </summary>
    private void DebounceInvalidation(string solutionPath)
    {
        // Cancel existing debounce timer
        if (_debouncers.TryGetValue(solutionPath, out var existingCts))
        {
            existingCts.Cancel();
            existingCts.Dispose();
        }

        // Start new debounce timer
        var cts = new CancellationTokenSource();
        _debouncers[solutionPath] = cts;

        _ = Task.Run(async () =>
        {
            try
            {
                await Task.Delay(_debounceDelayMs, cts.Token);

                // If we get here, the delay completed without cancellation
                if (!cts.Token.IsCancellationRequested)
                {
                    _logger.LogInformation("Debounce period completed, invalidating cache for {Path}", solutionPath);
                    InvalidateCache(solutionPath);
                    _debouncers.TryRemove(solutionPath, out _);
                }
            }
            catch (TaskCanceledException)
            {
                // Expected when a new change arrives before debounce completes
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error during debounce for {Path}", solutionPath);
            }
        }, cts.Token);
    }

    // =============================================================================================
    // Disposal
    // =============================================================================================

    public void Dispose()
    {
        _logger.LogInformation("Disposing RoslynWorkspaceService...");

        // Dispose workspace
        _workspace?.Dispose();

        // Dispose semaphores
        foreach (var semaphore in _solutionLocks.Values)
        {
            semaphore?.Dispose();
        }

        // Dispose eviction lock
        _evictionLock?.Dispose();

        // Dispose file watchers
        foreach (var watcher in _fileWatchers.Values)
        {
            watcher?.Dispose();
        }

        // Cancel and dispose debounce tokens
        foreach (var cts in _debouncers.Values)
        {
            cts?.Cancel();
            cts?.Dispose();
        }

        // Clear collections
        _solutionLocks.Clear();
        _solutionCache.Clear();
        _compilationCache.Clear();
        _fileTimestamps.Clear();
        _fileWatchers.Clear();
        _debouncers.Clear();

        _logger.LogInformation("RoslynWorkspaceService disposed");
    }
}
