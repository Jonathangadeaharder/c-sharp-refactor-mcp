using Microsoft.Build.Locator;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using RoslynRefactorServer.Abstractions;
using RoslynRefactorServer.Providers;
using RoslynRefactorServer.Services;
using RoslynRefactorServer.Tools;

// CRITICAL: Register MSBuild before any Roslyn APIs are used
// This locates the .NET SDK's MSBuild instance
try
{
    if (!MSBuildLocator.IsRegistered)
    {
        var instances = MSBuildLocator.QueryVisualStudioInstances().ToList();
        if (instances.Any())
        {
            var instance = instances.OrderByDescending(i => i.Version).First();
            MSBuildLocator.RegisterInstance(instance);

            // Log to stderr (stdout is reserved for MCP protocol)
            Console.Error.WriteLine($"[INFO] Registered MSBuild instance: {instance.Name} {instance.Version}");
            Console.Error.WriteLine($"[INFO] MSBuild path: {instance.MSBuildPath}");
        }
        else
        {
            Console.Error.WriteLine("[WARNING] No MSBuild instances found. C# support will be limited.");
            Console.Error.WriteLine("[INFO] Other languages (TypeScript, Go, C++, Java, Rust) will still be available.");
        }
    }
}
catch (Exception ex)
{
    Console.Error.WriteLine($"[WARNING] Failed to register MSBuild: {ex.Message}");
    Console.Error.WriteLine("[INFO] C# support will be limited. Other languages will still be available.");
}

// Build and configure the host
var builder = Host.CreateApplicationBuilder(args);

// Configure logging to stderr only (stdout is reserved for MCP JSON-RPC)
builder.Logging.ClearProviders();
builder.Logging.AddConsole(options =>
{
    options.LogToStandardErrorThreshold = LogLevel.Trace;
});

// Add configuration from appsettings.json
builder.Configuration.AddJsonFile("appsettings.json", optional: true, reloadOnChange: true);

// Register core services
builder.Services.AddSingleton<RoslynWorkspaceService>();
builder.Services.AddSingleton<PathSecurityService>();

// Register all language providers
builder.Services.AddSingleton<ILanguageProvider, CSharpLanguageProvider>();
builder.Services.AddSingleton<ILanguageProvider, TypeScriptLanguageProvider>();
builder.Services.AddSingleton<ILanguageProvider, GoLanguageProvider>();
builder.Services.AddSingleton<ILanguageProvider, CppLanguageProvider>();
builder.Services.AddSingleton<ILanguageProvider, JavaLanguageProvider>();
builder.Services.AddSingleton<ILanguageProvider, RustLanguageProvider>();

// Register language detector service
builder.Services.AddSingleton<LanguageDetectorService>();

// Configure and register the MCP server
builder.Services.AddMcpServer(options =>
{
    options.ServerInfo = new ModelContextProtocol.Protocol.Implementation
    {
        Name = "multi-language-refactor-server",
        Version = "2.0.0"
    };
})
.WithToolsFromAssembly(); // Automatically discovers [McpServerToolType] classes

var app = builder.Build();

// Log startup information
var logger = app.Services.GetRequiredService<ILogger<Program>>();
logger.LogInformation("===========================================");
logger.LogInformation("Multi-Language Refactor MCP Server Starting");
logger.LogInformation("===========================================");
logger.LogInformation("Protocol: Model Context Protocol (MCP)");
logger.LogInformation("Transport: stdio (Standard I/O)");
logger.LogInformation("Semantic Engines: Roslyn + LSP");
logger.LogInformation("Supported Languages: C#, TypeScript, Go, C++, Java, Rust");
logger.LogInformation("===========================================");

try
{
    // Verify services are registered correctly
    var workspaceService = app.Services.GetRequiredService<RoslynWorkspaceService>();
    var securityService = app.Services.GetRequiredService<PathSecurityService>();
    var languageDetector = app.Services.GetRequiredService<LanguageDetectorService>();

    var providers = languageDetector.GetAllProviders().ToList();
    logger.LogInformation("Registered {Count} language providers: {Languages}",
        providers.Count,
        string.Join(", ", providers.Select(p => p.LanguageName)));

    logger.LogInformation("All services registered successfully");
    logger.LogInformation("Server is ready to accept MCP tool calls");

    // Run the server
    await app.RunAsync();

    return 0;
}
catch (Exception ex)
{
    logger.LogCritical(ex, "Fatal error during server execution");
    return 1;
}
