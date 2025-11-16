using Microsoft.Build.Locator;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
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
            Console.Error.WriteLine("[ERROR] No MSBuild instances found. Please install the .NET SDK.");
            return 1;
        }
    }
}
catch (Exception ex)
{
    Console.Error.WriteLine($"[ERROR] Failed to register MSBuild: {ex.Message}");
    return 1;
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

// Configure and register the MCP server
builder.Services.AddMcpServer(options =>
{
    options.ServerInfo = new ModelContextProtocol.Protocol.Implementation
    {
        Name = "roslyn-refactor-server",
        Version = "1.0.0"
    };
})
.WithToolsFromAssembly(); // Automatically discovers [McpServerToolType] classes

var app = builder.Build();

// Log startup information
var logger = app.Services.GetRequiredService<ILogger<Program>>();
logger.LogInformation("===========================================");
logger.LogInformation("Roslyn Refactor MCP Server Starting");
logger.LogInformation("===========================================");
logger.LogInformation("Protocol: Model Context Protocol (MCP)");
logger.LogInformation("Transport: stdio (Standard I/O)");
logger.LogInformation("Semantic Engine: Roslyn (.NET Compiler Platform)");
logger.LogInformation("===========================================");

try
{
    // Verify services are registered correctly
    var workspaceService = app.Services.GetRequiredService<RoslynWorkspaceService>();
    var securityService = app.Services.GetRequiredService<PathSecurityService>();

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
