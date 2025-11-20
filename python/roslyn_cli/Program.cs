using Microsoft.Build.Locator;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.FindSymbols;
using Microsoft.CodeAnalysis.MSBuild;
using Microsoft.CodeAnalysis.Rename;
using System.Text.Json;
using System.Text.Json.Serialization;

// Register MSBuild
MSBuildLocator.RegisterDefaults();

// Read JSON request from stdin
var input = Console.In.ReadToEnd();
var request = JsonSerializer.Deserialize<Request>(input);

if (request == null)
{
    WriteError("Invalid request: could not parse JSON");
    return 1;
}

try
{
    var result = await ProcessCommandAsync(request);
    WriteSuccess(result);
    return 0;
}
catch (Exception ex)
{
    WriteError(ex.Message);
    return 1;
}

static async Task<object> ProcessCommandAsync(Request request)
{
    return request.Command switch
    {
        "version" => new { version = "1.0.0", roslyn = typeof(MSBuildWorkspace).Assembly.GetName().Version?.ToString() },
        "load_project" => await LoadProjectAsync(request.Parameters),
        "get_diagnostics" => await GetDiagnosticsAsync(request.Parameters),
        "find_references" => await FindReferencesAsync(request.Parameters),
        "rename_symbol" => await RenameSymbolAsync(request.Parameters),
        "get_symbol_info" => await GetSymbolInfoAsync(request.Parameters),
        "extract_method" => await ExtractMethodAsync(request.Parameters),
        _ => throw new ArgumentException($"Unknown command: {request.Command}")
    };
}

static async Task<object> LoadProjectAsync(Dictionary<string, JsonElement> parameters)
{
    var projectPath = parameters["projectPath"].GetString()!;

    using var workspace = MSBuildWorkspace.Create();

    // Suppress workspace diagnostics
    workspace.WorkspaceFailed += (sender, args) => { };

    Solution solution;
    if (projectPath.EndsWith(".sln", StringComparison.OrdinalIgnoreCase))
    {
        solution = await workspace.OpenSolutionAsync(projectPath);
    }
    else
    {
        var project = await workspace.OpenProjectAsync(projectPath);
        solution = project.Solution;
    }

    var documentCount = solution.Projects.Sum(p => p.Documents.Count());
    var projectCount = solution.Projects.Count();
    var language = solution.Projects.FirstOrDefault()?.Language ?? "unknown";

    return new
    {
        documentCount,
        projectCount,
        language = language.ToLowerInvariant()
    };
}

static async Task<object> GetDiagnosticsAsync(Dictionary<string, JsonElement> parameters)
{
    var projectPath = parameters["projectPath"].GetString()!;
    var severityFilter = parameters.TryGetValue("severityFilter", out var filter)
        ? filter.GetString()
        : "Warning";

    using var workspace = MSBuildWorkspace.Create();
    workspace.WorkspaceFailed += (sender, args) => { };

    Solution solution;
    if (projectPath.EndsWith(".sln", StringComparison.OrdinalIgnoreCase))
    {
        solution = await workspace.OpenSolutionAsync(projectPath);
    }
    else
    {
        var project = await workspace.OpenProjectAsync(projectPath);
        solution = project.Solution;
    }

    var diagnostics = new List<object>();
    var errorCount = 0;
    var warningCount = 0;
    var infoCount = 0;

    foreach (var project in solution.Projects)
    {
        var compilation = await project.GetCompilationAsync();
        if (compilation == null) continue;

        foreach (var diagnostic in compilation.GetDiagnostics())
        {
            // Filter by severity
            var include = severityFilter switch
            {
                "Error" => diagnostic.Severity == DiagnosticSeverity.Error,
                "Warning" => diagnostic.Severity >= DiagnosticSeverity.Warning,
                "Info" => diagnostic.Severity >= DiagnosticSeverity.Info,
                "All" => true,
                _ => diagnostic.Severity >= DiagnosticSeverity.Warning
            };

            if (!include) continue;

            // Count by severity
            switch (diagnostic.Severity)
            {
                case DiagnosticSeverity.Error:
                    errorCount++;
                    break;
                case DiagnosticSeverity.Warning:
                    warningCount++;
                    break;
                case DiagnosticSeverity.Info:
                    infoCount++;
                    break;
            }

            var lineSpan = diagnostic.Location.GetLineSpan();
            diagnostics.Add(new
            {
                severity = diagnostic.Severity.ToString(),
                message = diagnostic.GetMessage(),
                filePath = lineSpan.Path,
                line = lineSpan.StartLinePosition.Line + 1,  // Convert to 1-based
                column = lineSpan.StartLinePosition.Character + 1,
                diagnosticId = diagnostic.Id
            });
        }
    }

    return new
    {
        errorCount,
        warningCount,
        infoCount,
        isSafeToRefactor = errorCount == 0,
        diagnostics
    };
}

static async Task<object> FindReferencesAsync(Dictionary<string, JsonElement> parameters)
{
    var projectPath = parameters["projectPath"].GetString()!;
    var filePath = parameters["filePath"].GetString()!;
    var line = parameters["line"].GetInt32() - 1;  // Convert to 0-based
    var column = parameters["column"].GetInt32() - 1;

    using var workspace = MSBuildWorkspace.Create();
    workspace.WorkspaceFailed += (sender, args) => { };

    Solution solution;
    if (projectPath.EndsWith(".sln", StringComparison.OrdinalIgnoreCase))
    {
        solution = await workspace.OpenSolutionAsync(projectPath);
    }
    else
    {
        var project = await workspace.OpenProjectAsync(projectPath);
        solution = project.Solution;
    }

    // Find the document
    var document = solution.Projects
        .SelectMany(p => p.Documents)
        .FirstOrDefault(d => Path.GetFullPath(d.FilePath!) == Path.GetFullPath(filePath));

    if (document == null)
    {
        throw new ArgumentException($"Document not found: {filePath}");
    }

    // Get semantic model and find symbol
    var semanticModel = await document.GetSemanticModelAsync();
    var syntaxRoot = await document.GetSyntaxRootAsync();
    var position = syntaxRoot!.GetLocation().SourceTree!.GetText().Lines[line].Start + column;
    var node = syntaxRoot.FindToken(position).Parent;
    var symbol = semanticModel!.GetSymbolInfo(node!).Symbol;

    if (symbol == null)
    {
        return new
        {
            symbolName = "",
            referenceCount = 0,
            references = Array.Empty<object>()
        };
    }

    // Find all references
    var references = await SymbolFinder.FindReferencesAsync(symbol, solution);
    var locations = new List<object>();

    foreach (var reference in references)
    {
        foreach (var location in reference.Locations)
        {
            var lineSpan = location.Location.GetLineSpan();
            var sourceTree = location.Location.SourceTree;

            // Get preview text
            var preview = "";
            if (sourceTree != null)
            {
                var text = sourceTree.GetText();
                var lineText = text.Lines[lineSpan.StartLinePosition.Line].ToString().Trim();
                preview = lineText.Length > 100 ? lineText.Substring(0, 100) + "..." : lineText;
            }

            locations.Add(new
            {
                filePath = lineSpan.Path,
                line = lineSpan.StartLinePosition.Line + 1,
                column = lineSpan.StartLinePosition.Character + 1,
                preview
            });
        }
    }

    return new
    {
        symbolName = symbol.Name,
        referenceCount = locations.Count,
        references = locations
    };
}

static async Task<object> RenameSymbolAsync(Dictionary<string, JsonElement> parameters)
{
    var projectPath = parameters["projectPath"].GetString()!;
    var filePath = parameters["filePath"].GetString()!;
    var line = parameters["line"].GetInt32() - 1;
    var column = parameters["column"].GetInt32() - 1;
    var newName = parameters["newName"].GetString()!;

    using var workspace = MSBuildWorkspace.Create();
    workspace.WorkspaceFailed += (sender, args) => { };

    Solution solution;
    if (projectPath.EndsWith(".sln", StringComparison.OrdinalIgnoreCase))
    {
        solution = await workspace.OpenSolutionAsync(projectPath);
    }
    else
    {
        var project = await workspace.OpenProjectAsync(projectPath);
        solution = project.Solution;
    }

    // Find the document
    var document = solution.Projects
        .SelectMany(p => p.Documents)
        .FirstOrDefault(d => Path.GetFullPath(d.FilePath!) == Path.GetFullPath(filePath));

    if (document == null)
    {
        throw new ArgumentException($"Document not found: {filePath}");
    }

    // Get semantic model and find symbol
    var semanticModel = await document.GetSemanticModelAsync();
    var syntaxRoot = await document.GetSyntaxRootAsync();
    var position = syntaxRoot!.GetLocation().SourceTree!.GetText().Lines[line].Start + column;
    var node = syntaxRoot.FindToken(position).Parent;
    var symbol = semanticModel!.GetSymbolInfo(node!).Symbol;

    if (symbol == null)
    {
        return new
        {
            success = false,
            error = "No symbol found at position",
            symbolName = "",
            filesModified = 0,
            locationsModified = 0
        };
    }

    try
    {
        // Perform rename
        var newSolution = await Renamer.RenameSymbolAsync(solution, symbol, newName, null);

        // Apply changes to files
        var changedDocuments = newSolution.GetChanges(solution).GetProjectChanges()
            .SelectMany(pc => pc.GetChangedDocuments())
            .Distinct()
            .ToList();

        var filesModified = 0;
        var locationsModified = 0;

        foreach (var docId in changedDocuments)
        {
            var oldDoc = solution.GetDocument(docId);
            var newDoc = newSolution.GetDocument(docId);

            if (oldDoc != null && newDoc != null && oldDoc.FilePath != null)
            {
                var newText = await newDoc.GetTextAsync();
                File.WriteAllText(oldDoc.FilePath, newText.ToString());
                filesModified++;

                // Count changes (approximate)
                var oldText = await oldDoc.GetTextAsync();
                var changes = newText.GetChangeRanges(oldText);
                locationsModified += changes.Count;
            }
        }

        return new
        {
            success = true,
            symbolName = symbol.Name,
            filesModified,
            locationsModified
        };
    }
    catch (Exception ex)
    {
        return new
        {
            success = false,
            error = ex.Message,
            symbolName = symbol.Name,
            filesModified = 0,
            locationsModified = 0
        };
    }
}

static async Task<object> GetSymbolInfoAsync(Dictionary<string, JsonElement> parameters)
{
    var projectPath = parameters["projectPath"].GetString()!;
    var filePath = parameters["filePath"].GetString()!;
    var line = parameters["line"].GetInt32() - 1;
    var column = parameters["column"].GetInt32() - 1;

    using var workspace = MSBuildWorkspace.Create();
    workspace.WorkspaceFailed += (sender, args) => { };

    Solution solution;
    if (projectPath.EndsWith(".sln", StringComparison.OrdinalIgnoreCase))
    {
        solution = await workspace.OpenSolutionAsync(projectPath);
    }
    else
    {
        var project = await workspace.OpenProjectAsync(projectPath);
        solution = project.Solution;
    }

    // Find the document
    var document = solution.Projects
        .SelectMany(p => p.Documents)
        .FirstOrDefault(d => Path.GetFullPath(d.FilePath!) == Path.GetFullPath(filePath));

    if (document == null)
    {
        throw new ArgumentException($"Document not found: {filePath}");
    }

    // Get semantic model and find symbol
    var semanticModel = await document.GetSemanticModelAsync();
    var syntaxRoot = await document.GetSyntaxRootAsync();
    var position = syntaxRoot!.GetLocation().SourceTree!.GetText().Lines[line].Start + column;
    var node = syntaxRoot.FindToken(position).Parent;
    var symbol = semanticModel!.GetSymbolInfo(node!).Symbol;

    if (symbol == null)
    {
        return new
        {
            name = "",
            kind = "unknown",
            type = ""
        };
    }

    return new
    {
        name = symbol.Name,
        kind = symbol.Kind.ToString(),
        type = symbol is IMethodSymbol method ? method.ReturnType.ToString() : symbol.ToString(),
        containingType = symbol.ContainingType?.Name,
        containingNamespace = symbol.ContainingNamespace?.ToString(),
        isStatic = symbol.IsStatic,
        isAbstract = symbol.IsAbstract,
        isVirtual = symbol.IsVirtual,
        accessibility = symbol.DeclaredAccessibility.ToString(),
        documentation = symbol.GetDocumentationCommentXml()
    };
}

static async Task<object> ExtractMethodAsync(Dictionary<string, JsonElement> parameters)
{
    // Extract method is complex and requires code generation
    // For MVP, return not implemented
    return new
    {
        success = false,
        error = "Extract method not yet implemented in CLI",
        methodName = parameters.TryGetValue("methodName", out var name) ? name.GetString() : "",
        filesModified = 0
    };
}

static void WriteSuccess(object result)
{
    var response = new
    {
        success = true,
        result
    };
    Console.WriteLine(JsonSerializer.Serialize(response, new JsonSerializerOptions
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false
    }));
}

static void WriteError(string message)
{
    var response = new
    {
        success = false,
        error = message
    };
    Console.WriteLine(JsonSerializer.Serialize(response, new JsonSerializerOptions
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false
    }));
}

// Request/Response models
record Request(
    [property: JsonPropertyName("command")] string Command,
    [property: JsonPropertyName("parameters")] Dictionary<string, JsonElement> Parameters
);
