# Improvement Recommendations for c-sharp-refactor-mcp

## Overview

This document provides **actionable implementation recommendations** for enhancing the c-sharp-refactor-mcp project based on analysis of 17 similar projects in the ecosystem. Each recommendation includes:

- **Rationale:** Why this improvement matters
- **Implementation Approach:** How to build it
- **Effort Estimate:** Development complexity
- **Priority:** Critical, High, Medium, or Long-Term
- **Code Examples:** Concrete implementation guidance

**Document Date:** November 20, 2025
**Based on:** SIMILAR-PROJECTS-RESEARCH.md analysis

---

## Table of Contents

1. [Critical Priority](#critical-priority)
   - Token Optimization
   - Git Integration
   - Pattern-Based Code Generation
   - Test Coverage Improvements
   - Additional Core Refactorings

2. [High Priority](#high-priority)
   - EditorConfig Integration
   - Performance Optimization
   - Rename Options
   - Impact Analysis
   - Recipe System

3. [Medium Priority](#medium-priority)
   - Architecture Validation
   - Security Analysis
   - Template System
   - Resource Schemes

4. [Long-Term Research](#long-term-research)
   - Grammar-Based Language Support
   - Cross-Repository Operations
   - Query-Based Analysis

---

## Critical Priority

### 1. Token Optimization (SharpToolsMCP Pattern)

#### Rationale
AI agents have token limits (typically 200K context window). Sending full source files with indentation wastes precious tokens. SharpToolsMCP demonstrates **3-5x token reduction** techniques that directly improve AI agent effectiveness.

#### Current State
- ✅ Sends symbol information (metadata)
- ⚠️ Sends full source code with formatting
- ❌ No token usage tracking
- ❌ No context minimization

#### Implementation Approach

**1.1 Remove Indentation from Code Context**

```csharp
// New service: Services/TokenOptimizationService.cs
public class TokenOptimizationService
{
    public string MinimizeCodeContext(string sourceCode)
    {
        var lines = sourceCode.Split('\n');
        var minimized = new StringBuilder();

        foreach (var line in lines)
        {
            // Remove leading whitespace but preserve structure with markers
            var trimmed = line.TrimStart();
            if (!string.IsNullOrWhiteSpace(trimmed))
            {
                // Count original indentation
                int indent = line.Length - trimmed.Length;
                minimized.AppendLine($"[I{indent}]{trimmed}");
            }
        }

        return minimized.ToString();
    }

    public string RestoreIndentation(string minimizedCode)
    {
        var lines = minimizedCode.Split('\n');
        var restored = new StringBuilder();

        foreach (var line in lines)
        {
            var match = Regex.Match(line, @"^\[I(\d+)\](.*)$");
            if (match.Success)
            {
                int indent = int.Parse(match.Groups[1].Value);
                string content = match.Groups[2].Value;
                restored.AppendLine(new string(' ', indent) + content);
            }
            else
            {
                restored.AppendLine(line);
            }
        }

        return restored.ToString();
    }
}
```

**1.2 FQN-Based Fuzzy Matching**

```csharp
// Add to Services/RoslynWorkspaceService.cs
public async Task<(ISymbol? symbol, Document? document, int line, int column)>
    FindSymbolByFuzzyFQN(string solutionPath, string fuzzyFQN, double threshold = 0.8)
{
    var solution = await GetOrLoadSolutionAsync(solutionPath);

    // Build FQN index if not exists
    var index = await GetOrBuildFQNIndexAsync(solution);

    // Fuzzy match using Levenshtein distance
    var bestMatch = index
        .Select(kvp => new
        {
            Symbol = kvp.Key,
            Location = kvp.Value,
            Similarity = CalculateSimilarity(fuzzyFQN, kvp.Value.FQN)
        })
        .Where(m => m.Similarity >= threshold)
        .OrderByDescending(m => m.Similarity)
        .FirstOrDefault();

    if (bestMatch != null)
    {
        return (bestMatch.Symbol, bestMatch.Location.Document,
                bestMatch.Location.Line, bestMatch.Location.Column);
    }

    return (null, null, 0, 0);
}

private double CalculateSimilarity(string s1, string s2)
{
    int distance = LevenshteinDistance(s1, s2);
    int maxLen = Math.Max(s1.Length, s2.Length);
    return 1.0 - (double)distance / maxLen;
}
```

**1.3 Complexity-Adjusted Resolution**

```csharp
// Add to Models/ResolutionOptions.cs
public enum ResolutionDepth
{
    Minimal,      // Just the symbol definition
    Standard,     // Symbol + immediate members
    Deep,         // Symbol + members + dependencies
    Comprehensive // Full type hierarchy
}

// Add to Services/SymbolResolutionService.cs
public async Task<string> ResolveSymbolContext(
    ISymbol symbol,
    ResolutionDepth depth,
    TokenOptimizationService optimizer)
{
    var context = new StringBuilder();

    // Always include symbol definition
    context.AppendLine(optimizer.MinimizeCodeContext(
        await GetSymbolDefinitionAsync(symbol)));

    if (depth >= ResolutionDepth.Standard)
    {
        // Include immediate members
        foreach (var member in GetImmediateMembers(symbol))
        {
            context.AppendLine(optimizer.MinimizeCodeContext(
                await GetSymbolSignatureAsync(member)));
        }
    }

    if (depth >= ResolutionDepth.Deep)
    {
        // Include dependencies (types used in signatures)
        foreach (var dependency in GetDependencies(symbol))
        {
            context.AppendLine(optimizer.MinimizeCodeContext(
                await GetSymbolSignatureAsync(dependency)));
        }
    }

    if (depth == ResolutionDepth.Comprehensive)
    {
        // Include full type hierarchy
        var hierarchy = GetTypeHierarchy(symbol);
        foreach (var type in hierarchy)
        {
            context.AppendLine(optimizer.MinimizeCodeContext(
                await GetSymbolDefinitionAsync(type)));
        }
    }

    return context.ToString();
}
```

**1.4 New MCP Tool: `get_symbol_context`**

```csharp
// Add to Tools/RefactoringTools.cs
[McpServerTool]
[Description("Gets optimized symbol context with token usage tracking")]
public async Task<string> get_symbol_context(
    [Description("Path to solution file")] string solutionPath,
    [Description("Fully qualified name or fuzzy FQN")] string symbolFQN,
    [Description("Resolution depth: minimal, standard, deep, comprehensive")] string depth = "standard",
    [Description("Whether to minimize tokens (remove indentation)")] bool optimizeTokens = true)
{
    _pathSecurity.ValidateSolutionFile(solutionPath);

    var resolutionDepth = Enum.Parse<ResolutionDepth>(depth, ignoreCase: true);

    // Try exact FQN match first
    var (symbol, _, _, _) = await _workspace.FindSymbolByFQN(solutionPath, symbolFQN);

    // Fallback to fuzzy matching
    if (symbol == null)
    {
        (symbol, _, _, _) = await _workspace.FindSymbolByFuzzyFQN(solutionPath, symbolFQN);
    }

    if (symbol == null)
    {
        return JsonSerializer.Serialize(new { error = "Symbol not found" });
    }

    var context = await _symbolResolution.ResolveSymbolContext(
        symbol, resolutionDepth, _tokenOptimization);

    // Track token usage
    int tokenCount = EstimateTokenCount(context);

    return JsonSerializer.Serialize(new
    {
        success = true,
        symbolFQN = symbol.ToDisplayString(),
        context = optimizeTokens ? context : await GetOriginalContext(symbol),
        tokenCount,
        optimizationSavings = optimizeTokens ? CalculateSavings(symbol) : 0
    });
}
```

#### Effort Estimate
- **Development:** 2-3 weeks
- **Testing:** 1 week
- **Documentation:** 2 days

#### Success Metrics
- [ ] 3-5x reduction in token usage for symbol context
- [ ] Fuzzy FQN matching with 90%+ accuracy
- [ ] Token usage tracking in all MCP tool responses

---

### 2. Git Integration (SharpToolsMCP Pattern)

#### Rationale
Refactoring can break code. Git integration provides **automatic rollback** capabilities and **commit history** for AI-driven changes. This builds user trust and enables experimentation.

#### Current State
- ❌ No git integration
- ❌ No commit/rollback functionality
- ❌ No branch management
- ⚠️ Changes are immediate and irreversible

#### Implementation Approach

**2.1 Git Service Abstraction**

```csharp
// New service: Services/GitService.cs
public class GitService
{
    private readonly ILogger<GitService> _logger;
    private readonly PathSecurityService _pathSecurity;

    public async Task<string> CreateRefactoringBranchAsync(
        string repositoryPath,
        string refactoringType)
    {
        _pathSecurity.ValidateAndNormalizePath(repositoryPath);

        var branchName = $"refactor/{refactoringType}-{DateTime.UtcNow:yyyyMMddHHmmss}";

        await RunGitCommandAsync(repositoryPath, $"checkout -b {branchName}");

        _logger.LogInformation("Created refactoring branch: {Branch}", branchName);

        return branchName;
    }

    public async Task<string> CommitChangesAsync(
        string repositoryPath,
        string message,
        string[] changedFiles)
    {
        foreach (var file in changedFiles)
        {
            await RunGitCommandAsync(repositoryPath, $"add {file}");
        }

        var commitHash = await RunGitCommandAsync(
            repositoryPath,
            $"commit -m \"{message}\"");

        _logger.LogInformation("Committed changes: {Hash}", commitHash);

        return commitHash.Trim();
    }

    public async Task RollbackToCommitAsync(
        string repositoryPath,
        string commitHash)
    {
        await RunGitCommandAsync(repositoryPath, $"reset --hard {commitHash}");
        _logger.LogInformation("Rolled back to commit: {Hash}", commitHash);
    }

    public async Task<bool> HasUncommittedChangesAsync(string repositoryPath)
    {
        var status = await RunGitCommandAsync(repositoryPath, "status --porcelain");
        return !string.IsNullOrWhiteSpace(status);
    }

    private async Task<string> RunGitCommandAsync(string repoPath, string arguments)
    {
        var processInfo = new ProcessStartInfo
        {
            FileName = "git",
            Arguments = arguments,
            WorkingDirectory = repoPath,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };

        using var process = Process.Start(processInfo);
        if (process == null)
            throw new InvalidOperationException("Failed to start git process");

        var output = await process.StandardOutput.ReadToEndAsync();
        var error = await process.StandardError.ReadToEndAsync();

        await process.WaitForExitAsync();

        if (process.ExitCode != 0)
            throw new GitException($"Git command failed: {error}");

        return output;
    }
}

public class GitException : Exception
{
    public GitException(string message) : base(message) { }
}
```

**2.2 Refactoring Transaction Pattern**

```csharp
// New abstraction: Abstractions/IRefactoringTransaction.cs
public interface IRefactoringTransaction : IAsyncDisposable
{
    string TransactionId { get; }
    string BranchName { get; }
    Task<bool> CommitAsync(string message);
    Task RollbackAsync();
    Task<RefactoringTransactionStatus> GetStatusAsync();
}

// Implementation: Services/RefactoringTransaction.cs
public class RefactoringTransaction : IRefactoringTransaction
{
    private readonly GitService _git;
    private readonly string _repositoryPath;
    private readonly string _originalBranch;
    private readonly string _originalCommit;
    private bool _committed;
    private bool _rolledBack;

    public string TransactionId { get; }
    public string BranchName { get; }

    private RefactoringTransaction(
        GitService git,
        string repositoryPath,
        string branchName,
        string originalBranch,
        string originalCommit)
    {
        _git = git;
        _repositoryPath = repositoryPath;
        BranchName = branchName;
        _originalBranch = originalBranch;
        _originalCommit = originalCommit;
        TransactionId = Guid.NewGuid().ToString("N");
    }

    public static async Task<RefactoringTransaction> BeginAsync(
        GitService git,
        string repositoryPath,
        string refactoringType)
    {
        // Check for uncommitted changes
        if (await git.HasUncommittedChangesAsync(repositoryPath))
        {
            throw new InvalidOperationException(
                "Repository has uncommitted changes. Commit or stash them first.");
        }

        // Get current state
        var originalBranch = await git.GetCurrentBranchAsync(repositoryPath);
        var originalCommit = await git.GetCurrentCommitAsync(repositoryPath);

        // Create refactoring branch
        var branchName = await git.CreateRefactoringBranchAsync(
            repositoryPath, refactoringType);

        return new RefactoringTransaction(
            git, repositoryPath, branchName, originalBranch, originalCommit);
    }

    public async Task<bool> CommitAsync(string message)
    {
        if (_committed)
            throw new InvalidOperationException("Transaction already committed");
        if (_rolledBack)
            throw new InvalidOperationException("Transaction already rolled back");

        var changedFiles = await _git.GetChangedFilesAsync(_repositoryPath);

        if (changedFiles.Length == 0)
        {
            return false; // No changes to commit
        }

        await _git.CommitChangesAsync(
            _repositoryPath,
            $"[Refactoring] {message}",
            changedFiles);

        _committed = true;
        return true;
    }

    public async Task RollbackAsync()
    {
        if (_rolledBack)
            return; // Already rolled back

        // Switch back to original branch
        await _git.CheckoutBranchAsync(_repositoryPath, _originalBranch);

        // Delete refactoring branch
        await _git.DeleteBranchAsync(_repositoryPath, BranchName, force: true);

        // Reset to original commit
        await _git.RollbackToCommitAsync(_repositoryPath, _originalCommit);

        _rolledBack = true;
    }

    public async ValueTask DisposeAsync()
    {
        if (!_committed && !_rolledBack)
        {
            // Auto-rollback on disposal if not explicitly committed
            await RollbackAsync();
        }
    }
}
```

**2.3 Update Refactoring Tools with Git Support**

```csharp
// Update Tools/AdvancedRefactoringTools.cs
[McpServerTool]
[Description("Extracts code into a new method with git transaction support")]
public async Task<string> extract_method(
    [Description("Path to solution file")] string solutionPath,
    [Description("Path to source file")] string documentPath,
    [Description("Start line (1-based)")] int startLine,
    [Description("Start column (1-based)")] int startColumn,
    [Description("End line (1-based)")] int endLine,
    [Description("End column (1-based)")] int endColumn,
    [Description("New method name")] string newMethodName,
    [Description("Enable git transaction (auto-commit/rollback)")] bool useGit = true,
    [Description("Git commit message (if useGit=true)")] string? commitMessage = null)
{
    _pathSecurity.ValidateSolutionFile(solutionPath);
    _pathSecurity.ValidateDocumentFile(documentPath);

    IRefactoringTransaction? transaction = null;

    try
    {
        // Begin git transaction if enabled
        if (useGit)
        {
            var repoPath = Path.GetDirectoryName(solutionPath)!;
            transaction = await RefactoringTransaction.BeginAsync(
                _git, repoPath, "extract-method");
        }

        // Perform refactoring (existing logic)
        var result = await PerformExtractMethodAsync(
            solutionPath, documentPath, startLine, startColumn,
            endLine, endColumn, newMethodName);

        if (!result.Success)
        {
            if (transaction != null)
                await transaction.RollbackAsync();

            return JsonSerializer.Serialize(new
            {
                success = false,
                error = result.Error,
                gitTransactionId = transaction?.TransactionId,
                gitStatus = "rolled_back"
            });
        }

        // Commit if git enabled
        string? gitCommitHash = null;
        if (transaction != null)
        {
            var message = commitMessage ??
                $"Extract method '{newMethodName}' in {Path.GetFileName(documentPath)}";

            bool committed = await transaction.CommitAsync(message);

            gitCommitHash = committed
                ? await _git.GetCurrentCommitAsync(Path.GetDirectoryName(solutionPath)!)
                : null;
        }

        return JsonSerializer.Serialize(new
        {
            success = true,
            newMethodName,
            filesModified = result.FilesModified,
            gitTransactionId = transaction?.TransactionId,
            gitBranch = transaction?.BranchName,
            gitCommitHash,
            gitStatus = gitCommitHash != null ? "committed" : "no_changes"
        });
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Extract method failed");

        if (transaction != null)
            await transaction.RollbackAsync();

        return JsonSerializer.Serialize(new
        {
            success = false,
            error = ex.Message,
            gitTransactionId = transaction?.TransactionId,
            gitStatus = "rolled_back"
        });
    }
    finally
    {
        if (transaction != null)
            await transaction.DisposeAsync();
    }
}
```

**2.4 New MCP Tool: `git_rollback`**

```csharp
// Add to Tools/RefactoringTools.cs
[McpServerTool]
[Description("Rolls back a refactoring transaction by transaction ID")]
public async Task<string> git_rollback(
    [Description("Transaction ID from previous refactoring")] string transactionId)
{
    // Look up transaction in transaction log
    var transaction = await _transactionLog.GetAsync(transactionId);

    if (transaction == null)
    {
        return JsonSerializer.Serialize(new
        {
            success = false,
            error = "Transaction not found"
        });
    }

    // Perform rollback
    await _git.CheckoutBranchAsync(transaction.RepositoryPath, transaction.OriginalBranch);
    await _git.RollbackToCommitAsync(transaction.RepositoryPath, transaction.OriginalCommit);
    await _git.DeleteBranchAsync(transaction.RepositoryPath, transaction.BranchName, force: true);

    return JsonSerializer.Serialize(new
    {
        success = true,
        transactionId,
        rolledBackBranch = transaction.BranchName,
        restoredCommit = transaction.OriginalCommit
    });
}
```

#### Effort Estimate
- **Development:** 3-4 weeks
- **Testing:** 2 weeks (critical for reliability)
- **Documentation:** 3 days

#### Success Metrics
- [ ] 100% rollback success rate in tests
- [ ] Auto-commit on successful refactorings
- [ ] Transaction log for debugging
- [ ] Git support configurable (can be disabled)

---

### 3. Pattern-Based Code Generation (RefactorMCP Pattern)

#### Rationale
Design patterns (Decorator, Adapter, Factory, etc.) involve **boilerplate code** that's tedious to write manually. Automated pattern generation is a high-value refactoring that AI agents can leverage.

#### Current State
- ❌ No pattern generation
- ❌ No boilerplate code generation
- ⚠️ Users must manually implement patterns

#### Implementation Approach

**3.1 Pattern Template System**

```csharp
// New abstraction: Abstractions/ICodePattern.cs
public interface ICodePattern
{
    string PatternName { get; }
    string Description { get; }
    Task<ProviderResult<GeneratedCode>> GenerateAsync(
        ISymbol targetSymbol,
        PatternOptions options);
}

// Base implementation: Services/Patterns/CodePatternBase.cs
public abstract class CodePatternBase : ICodePattern
{
    protected readonly RoslynWorkspaceService Workspace;
    protected readonly SyntaxGenerator Generator;

    public abstract string PatternName { get; }
    public abstract string Description { get; }

    public abstract Task<ProviderResult<GeneratedCode>> GenerateAsync(
        ISymbol targetSymbol,
        PatternOptions options);

    protected async Task<Document> AddGeneratedCodeToDocumentAsync(
        Document document,
        SyntaxNode generatedNode,
        InsertionLocation location)
    {
        var root = await document.GetSyntaxRootAsync();
        var newRoot = location switch
        {
            InsertionLocation.AfterTarget => root.InsertNodesAfter(
                location.TargetNode, new[] { generatedNode }),
            InsertionLocation.BeforeTarget => root.InsertNodesBefore(
                location.TargetNode, new[] { generatedNode }),
            InsertionLocation.AsNestedType => InsertAsNestedType(
                root, location.TargetNode, generatedNode),
            _ => throw new ArgumentException("Invalid insertion location")
        };

        return document.WithSyntaxRoot(newRoot);
    }
}
```

**3.2 Decorator Pattern Implementation**

```csharp
// Services/Patterns/DecoratorPattern.cs
public class DecoratorPattern : CodePatternBase
{
    public override string PatternName => "Decorator";
    public override string Description =>
        "Generates a decorator class that wraps an interface implementation";

    public override async Task<ProviderResult<GeneratedCode>> GenerateAsync(
        ISymbol targetSymbol,
        PatternOptions options)
    {
        // Validate target is an interface
        if (targetSymbol is not INamedTypeSymbol { TypeKind: TypeKind.Interface } interfaceSymbol)
        {
            return ProviderResult<GeneratedCode>.ErrorResult(
                "Decorator pattern requires an interface");
        }

        var decoratorName = options.GetOption<string>("decoratorName") ??
            $"{interfaceSymbol.Name}Decorator";

        // Generate decorator class
        var decoratorClass = Generator.ClassDeclaration(
            decoratorName,
            accessibility: Accessibility.Public,
            baseType: Generator.IdentifierName(interfaceSymbol.Name));

        // Add private field for wrapped instance
        var wrappedField = Generator.FieldDeclaration(
            "_wrapped",
            Generator.TypeExpression(interfaceSymbol),
            Accessibility.Private,
            DeclarationModifiers.ReadOnly);

        decoratorClass = Generator.AddMembers(decoratorClass, wrappedField);

        // Add constructor
        var constructorParam = Generator.ParameterDeclaration(
            "wrapped",
            Generator.TypeExpression(interfaceSymbol));

        var constructor = Generator.ConstructorDeclaration(
            decoratorName,
            new[] { constructorParam },
            Accessibility.Public,
            statements: new[]
            {
                Generator.AssignmentStatement(
                    Generator.MemberAccessExpression(
                        Generator.ThisExpression(), "_wrapped"),
                    Generator.IdentifierName("wrapped"))
            });

        decoratorClass = Generator.AddMembers(decoratorClass, constructor);

        // Implement all interface methods (delegating to wrapped instance)
        foreach (var member in interfaceSymbol.GetMembers())
        {
            if (member is IMethodSymbol method)
            {
                var decoratorMethod = GenerateDecoratorMethod(method);
                decoratorClass = Generator.AddMembers(decoratorClass, decoratorMethod);
            }
            else if (member is IPropertySymbol property)
            {
                var decoratorProperty = GenerateDecoratorProperty(property);
                decoratorClass = Generator.AddMembers(decoratorClass, decoratorProperty);
            }
        }

        return ProviderResult<GeneratedCode>.SuccessResult(new GeneratedCode
        {
            Syntax = decoratorClass,
            FileName = $"{decoratorName}.cs",
            Namespace = interfaceSymbol.ContainingNamespace?.ToDisplayString()
        });
    }

    private SyntaxNode GenerateDecoratorMethod(IMethodSymbol method)
    {
        // Generate method that delegates to _wrapped.MethodName(...)
        var parameters = method.Parameters.Select(p =>
            Generator.ParameterDeclaration(p.Name, Generator.TypeExpression(p.Type)));

        var methodCall = Generator.InvocationExpression(
            Generator.MemberAccessExpression(
                Generator.IdentifierName("_wrapped"),
                method.Name),
            method.Parameters.Select(p => Generator.IdentifierName(p.Name)));

        SyntaxNode statement = method.ReturnsVoid
            ? Generator.ExpressionStatement(methodCall)
            : Generator.ReturnStatement(methodCall);

        return Generator.MethodDeclaration(
            method.Name,
            parameters,
            returnType: Generator.TypeExpression(method.ReturnType),
            accessibility: Accessibility.Public,
            modifiers: DeclarationModifiers.Virtual, // Allow overriding in subclasses
            statements: new[] { statement });
    }

    private SyntaxNode GenerateDecoratorProperty(IPropertySymbol property)
    {
        var getAccessor = Generator.GetAccessorDeclaration(
            statements: new[]
            {
                Generator.ReturnStatement(
                    Generator.MemberAccessExpression(
                        Generator.IdentifierName("_wrapped"),
                        property.Name))
            });

        var accessors = new List<SyntaxNode> { getAccessor };

        if (!property.IsReadOnly)
        {
            var setAccessor = Generator.SetAccessorDeclaration(
                statements: new[]
                {
                    Generator.AssignmentStatement(
                        Generator.MemberAccessExpression(
                            Generator.IdentifierName("_wrapped"),
                            property.Name),
                        Generator.IdentifierName("value"))
                });

            accessors.Add(setAccessor);
        }

        return Generator.PropertyDeclaration(
            property.Name,
            Generator.TypeExpression(property.Type),
            accessibility: Accessibility.Public,
            modifiers: DeclarationModifiers.Virtual,
            getAccessorStatements: new[] { accessors[0] },
            setAccessorStatements: accessors.Count > 1 ? new[] { accessors[1] } : null);
    }
}
```

**3.3 Adapter Pattern Implementation**

```csharp
// Services/Patterns/AdapterPattern.cs
public class AdapterPattern : CodePatternBase
{
    public override string PatternName => "Adapter";
    public override string Description =>
        "Generates an adapter class that adapts one interface to another";

    public override async Task<ProviderResult<GeneratedCode>> GenerateAsync(
        ISymbol targetSymbol,
        PatternOptions options)
    {
        // Validate target is a class
        if (targetSymbol is not INamedTypeSymbol { TypeKind: TypeKind.Class } targetClass)
        {
            return ProviderResult<GeneratedCode>.ErrorResult(
                "Adapter pattern requires a class to adapt");
        }

        // Get target interface from options
        var targetInterfaceName = options.GetOption<string>("targetInterface");
        if (string.IsNullOrEmpty(targetInterfaceName))
        {
            return ProviderResult<GeneratedCode>.ErrorResult(
                "Target interface name required");
        }

        var adapterName = options.GetOption<string>("adapterName") ??
            $"{targetClass.Name}Adapter";

        // Generate adapter class
        var adapterClass = Generator.ClassDeclaration(
            adapterName,
            accessibility: Accessibility.Public,
            baseType: Generator.IdentifierName(targetInterfaceName));

        // Add private field for adaptee
        var adapteeField = Generator.FieldDeclaration(
            "_adaptee",
            Generator.TypeExpression(targetClass),
            Accessibility.Private,
            DeclarationModifiers.ReadOnly);

        adapterClass = Generator.AddMembers(adapterClass, adapteeField);

        // Add constructor
        var constructorParam = Generator.ParameterDeclaration(
            "adaptee",
            Generator.TypeExpression(targetClass));

        var constructor = Generator.ConstructorDeclaration(
            adapterName,
            new[] { constructorParam },
            Accessibility.Public,
            statements: new[]
            {
                Generator.AssignmentStatement(
                    Generator.MemberAccessExpression(
                        Generator.ThisExpression(), "_adaptee"),
                    Generator.IdentifierName("adaptee"))
            });

        adapterClass = Generator.AddMembers(adapterClass, constructor);

        // Generate method stubs for interface implementation
        // (AI agent will need to fill in the adaptation logic)
        var targetInterface = await FindInterfaceSymbolAsync(targetInterfaceName);

        if (targetInterface != null)
        {
            foreach (var member in targetInterface.GetMembers())
            {
                if (member is IMethodSymbol method)
                {
                    var stubMethod = GenerateAdapterMethodStub(method);
                    adapterClass = Generator.AddMembers(adapterClass, stubMethod);
                }
            }
        }

        return ProviderResult<GeneratedCode>.SuccessResult(new GeneratedCode
        {
            Syntax = adapterClass,
            FileName = $"{adapterName}.cs",
            Namespace = targetClass.ContainingNamespace?.ToDisplayString(),
            RequiresManualCompletion = true,
            ManualCompletionInstructions =
                "TODO: Implement adapter methods by calling appropriate _adaptee methods"
        });
    }

    private SyntaxNode GenerateAdapterMethodStub(IMethodSymbol method)
    {
        var parameters = method.Parameters.Select(p =>
            Generator.ParameterDeclaration(p.Name, Generator.TypeExpression(p.Type)));

        // Generate stub that throws NotImplementedException
        var throwStatement = Generator.ThrowStatement(
            Generator.ObjectCreationExpression(
                Generator.IdentifierName("NotImplementedException"),
                Generator.LiteralExpression(
                    $"TODO: Adapt this method to call _adaptee methods")));

        return Generator.MethodDeclaration(
            method.Name,
            parameters,
            returnType: Generator.TypeExpression(method.ReturnType),
            accessibility: Accessibility.Public,
            statements: new[] { throwStatement });
    }
}
```

**3.4 New MCP Tool: `generate_pattern`**

```csharp
// Add to Tools/AdvancedRefactoringTools.cs
[McpServerTool]
[Description("Generates a design pattern implementation (Decorator, Adapter, etc.)")]
public async Task<string> generate_pattern(
    [Description("Path to solution file")] string solutionPath,
    [Description("Pattern name: decorator, adapter, factory, singleton, etc.")]
        string patternName,
    [Description("Target symbol FQN (interface for decorator, class for adapter)")]
        string targetSymbolFQN,
    [Description("Pattern options (JSON)")] string optionsJson = "{}")
{
    _pathSecurity.ValidateSolutionFile(solutionPath);

    // Get pattern implementation
    var pattern = _patternFactory.GetPattern(patternName);
    if (pattern == null)
    {
        return JsonSerializer.Serialize(new
        {
            success = false,
            error = $"Unknown pattern: {patternName}",
            availablePatterns = _patternFactory.GetAvailablePatterns()
        });
    }

    // Find target symbol
    var (symbol, document, _, _) = await _workspace.FindSymbolByFQN(
        solutionPath, targetSymbolFQN);

    if (symbol == null)
    {
        return JsonSerializer.Serialize(new
        {
            success = false,
            error = "Target symbol not found"
        });
    }

    // Parse options
    var options = PatternOptions.FromJson(optionsJson);

    // Generate pattern code
    var result = await pattern.GenerateAsync(symbol, options);

    if (!result.Success)
    {
        return JsonSerializer.Serialize(new
        {
            success = false,
            error = result.Error
        });
    }

    // Add generated code to project
    var generatedFile = result.Data!;
    var targetProject = document.Project;

    var newDocument = targetProject.AddDocument(
        generatedFile.FileName,
        generatedFile.Syntax,
        folders: generatedFile.Namespace?.Split('.'));

    await _workspace.UpdateAndApplyChangesAsync(solutionPath, newDocument.Project.Solution);

    return JsonSerializer.Serialize(new
    {
        success = true,
        patternName,
        generatedFile = generatedFile.FileName,
        requiresManualCompletion = generatedFile.RequiresManualCompletion,
        instructions = generatedFile.ManualCompletionInstructions
    });
}
```

#### Effort Estimate
- **Development:** 3-4 weeks (patterns are complex)
- **Testing:** 2 weeks
- **Documentation:** 3 days

#### Additional Patterns to Implement
1. ✅ Decorator Pattern
2. ✅ Adapter Pattern
3. ⚠️ Factory Pattern (Phase 2)
4. ⚠️ Singleton Pattern (Phase 2)
5. ⚠️ Observer Pattern (Phase 2)
6. ⚠️ Strategy Pattern (Phase 2)

#### Success Metrics
- [ ] 6+ design patterns supported
- [ ] Generated code compiles without errors
- [ ] Patterns follow C# naming conventions
- [ ] AI agents can successfully use pattern generation

---

### 4. Test Coverage Improvements (RefactorMCP Pattern)

#### Rationale
Refactoring operations are **high-risk**. Comprehensive tests ensure:
- Refactorings don't break semantics
- Edge cases are handled
- Regressions are caught early

RefactorMCP demonstrates excellent test patterns to adopt.

#### Current State
- ⚠️ Basic test coverage
- ❌ Limited edge case testing
- ❌ No refactoring correctness verification tests
- ❌ No performance benchmarks

#### Implementation Approach

**4.1 Refactoring Test Base Class**

```csharp
// RoslynRefactorServer.Tests/RefactoringTestBase.cs
public abstract class RefactoringTestBase
{
    protected async Task<Document> CreateTestDocumentAsync(string sourceCode)
    {
        var workspace = new AdhocWorkspace();
        var projectInfo = ProjectInfo.Create(
            ProjectId.CreateNewId(),
            VersionStamp.Create(),
            "TestProject",
            "TestProject",
            LanguageNames.CSharp);

        var project = workspace.AddProject(projectInfo);
        return workspace.AddDocument(
            project.Id,
            "TestDocument.cs",
            SourceText.From(sourceCode));
    }

    protected async Task VerifyRefactoringAsync(
        string sourceCode,
        string expectedCode,
        Func<Document, Task<Document>> refactoringAction)
    {
        // Normalize whitespace for comparison
        var normalizedSource = NormalizeWhitespace(sourceCode);
        var normalizedExpected = NormalizeWhitespace(expectedCode);

        // Create test document
        var document = await CreateTestDocumentAsync(normalizedSource);

        // Apply refactoring
        var refactoredDocument = await refactoringAction(document);

        // Get refactored source
        var refactoredSource = await refactoredDocument.GetTextAsync();
        var normalizedRefactored = NormalizeWhitespace(refactoredSource.ToString());

        // Assert
        Assert.Equal(normalizedExpected, normalizedRefactored);

        // Verify compilation (no errors introduced)
        await VerifyCompilationAsync(refactoredDocument);
    }

    protected async Task VerifyCompilationAsync(Document document)
    {
        var compilation = await document.Project.GetCompilationAsync();
        var diagnostics = compilation.GetDiagnostics()
            .Where(d => d.Severity == DiagnosticSeverity.Error);

        if (diagnostics.Any())
        {
            var errorMessages = string.Join("\n",
                diagnostics.Select(d => $"{d.Id}: {d.GetMessage()}"));
            Assert.Fail($"Compilation errors after refactoring:\n{errorMessages}");
        }
    }

    protected string NormalizeWhitespace(string code)
    {
        var tree = CSharpSyntaxTree.ParseText(code);
        return tree.GetRoot().NormalizeWhitespace().ToFullString();
    }

    protected async Task<(int line, int column)> FindSymbolLocationAsync(
        Document document,
        string symbolName)
    {
        var tree = await document.GetSyntaxTreeAsync();
        var root = await tree.GetRootAsync();

        var node = root.DescendantNodes()
            .FirstOrDefault(n => n.ToString().Contains(symbolName));

        if (node == null)
            throw new ArgumentException($"Symbol '{symbolName}' not found");

        var lineSpan = tree.GetLineSpan(node.Span);
        return (lineSpan.StartLinePosition.Line + 1,
                lineSpan.StartLinePosition.Character + 1);
    }
}
```

**4.2 Extract Method Test Examples**

```csharp
// RoslynRefactorServer.Tests/ExtractMethodTests.cs
public class ExtractMethodTests : RefactoringTestBase
{
    [Fact]
    public async Task ExtractMethod_SimpleStatements_GeneratesCorrectSignature()
    {
        var source = @"
class C
{
    void M()
    {
        int x = 1;
        int y = 2;
        int z = x + y;
        Console.WriteLine(z);
    }
}";

        var expected = @"
class C
{
    void M()
    {
        NewMethod();
    }

    void NewMethod()
    {
        int x = 1;
        int y = 2;
        int z = x + y;
        Console.WriteLine(z);
    }
}";

        await VerifyRefactoringAsync(source, expected,
            async doc => await ExtractMethodAsync(doc, startLine: 5, endLine: 8, "NewMethod"));
    }

    [Fact]
    public async Task ExtractMethod_WithInputVariables_GeneratesParameters()
    {
        var source = @"
class C
{
    void M()
    {
        int x = 1;
        int y = 2;
        int z = x + y; // Extract this line
        Console.WriteLine(z);
    }
}";

        var expected = @"
class C
{
    void M()
    {
        int x = 1;
        int y = 2;
        int z = Calculate(x, y);
        Console.WriteLine(z);
    }

    int Calculate(int x, int y)
    {
        return x + y;
    }
}";

        await VerifyRefactoringAsync(source, expected,
            async doc => await ExtractMethodAsync(doc, startLine: 7, endLine: 7, "Calculate"));
    }

    [Fact]
    public async Task ExtractMethod_WithMultipleOutputs_GeneratesTuple()
    {
        var source = @"
class C
{
    void M()
    {
        int a = 1;
        int b = 2;
        a = a + 1;
        b = b + 1;
        Console.WriteLine(a + b);
    }
}";

        var expected = @"
class C
{
    void M()
    {
        int a = 1;
        int b = 2;
        (a, b) = Increment(a, b);
        Console.WriteLine(a + b);
    }

    (int, int) Increment(int a, int b)
    {
        a = a + 1;
        b = b + 1;
        return (a, b);
    }
}";

        await VerifyRefactoringAsync(source, expected,
            async doc => await ExtractMethodAsync(doc, startLine: 6, endLine: 7, "Increment"));
    }

    [Fact]
    public async Task ExtractMethod_NestedScopes_HandlesCorrectly()
    {
        var source = @"
class C
{
    void M()
    {
        int x = 1;
        if (x > 0)
        {
            int y = x * 2;
            Console.WriteLine(y);
        }
    }
}";

        var expected = @"
class C
{
    void M()
    {
        int x = 1;
        if (x > 0)
        {
            PrintDouble(x);
        }
    }

    void PrintDouble(int x)
    {
        int y = x * 2;
        Console.WriteLine(y);
    }
}";

        await VerifyRefactoringAsync(source, expected,
            async doc => await ExtractMethodAsync(doc, startLine: 7, endLine: 8, "PrintDouble"));
    }

    [Fact]
    public async Task ExtractMethod_InvalidSelection_ReturnsError()
    {
        var source = @"
class C
{
    void M()
    {
        int x = 1; // Can't extract partial statement
    }
}";

        var document = await CreateTestDocumentAsync(source);

        // Extract partial statement (should fail)
        await Assert.ThrowsAsync<InvalidOperationException>(
            async () => await ExtractMethodAsync(document, startLine: 5, startColumn: 1,
                endLine: 5, endColumn: 10, "NewMethod"));
    }
}
```

**4.3 Rename Symbol Test Examples**

```csharp
// RoslynRefactorServer.Tests/RenameSymbolTests.cs
public class RenameSymbolTests : RefactoringTestBase
{
    [Fact]
    public async Task RenameSymbol_Method_UpdatesAllReferences()
    {
        var source = @"
class C
{
    void OldMethod() { }

    void Caller()
    {
        OldMethod();
        this.OldMethod();
    }
}";

        var expected = @"
class C
{
    void NewMethod() { }

    void Caller()
    {
        NewMethod();
        this.NewMethod();
    }
}";

        await VerifyRefactoringAsync(source, expected,
            async doc =>
            {
                var (line, col) = await FindSymbolLocationAsync(doc, "OldMethod");
                return await RenameSymbolAsync(doc, line, col, "NewMethod");
            });
    }

    [Fact]
    public async Task RenameSymbol_PrivateField_UpdatesGettersSetters()
    {
        var source = @"
class C
{
    private int _oldField;

    public int OldField
    {
        get => _oldField;
        set => _oldField = value;
    }
}";

        var expected = @"
class C
{
    private int _newField;

    public int OldField
    {
        get => _newField;
        set => _newField = value;
    }
}";

        await VerifyRefactoringAsync(source, expected,
            async doc =>
            {
                var (line, col) = await FindSymbolLocationAsync(doc, "_oldField");
                return await RenameSymbolAsync(doc, line, col, "_newField");
            });
    }

    [Fact]
    public async Task RenameSymbol_DoesNotRenameUnrelatedSymbols()
    {
        var source = @"
class C
{
    void Method() { }
}

class D
{
    void Method() { } // Should NOT be renamed
}";

        var expected = @"
class C
{
    void RenamedMethod() { }
}

class D
{
    void Method() { } // Should NOT be renamed
}";

        await VerifyRefactoringAsync(source, expected,
            async doc =>
            {
                // Rename C.Method, not D.Method
                var (line, col) = await FindSymbolLocationAsync(doc, "class C");
                var cMethod = await FindSymbolInClassAsync(doc, "C", "Method");
                return await RenameSymbolAsync(doc, cMethod.line, cMethod.col, "RenamedMethod");
            });
    }
}
```

**4.4 Integration Tests with Multiple Projects**

```csharp
// RoslynRefactorServer.Tests/IntegrationTests.cs
public class IntegrationTests
{
    [Fact]
    public async Task RenameSymbol_AcrossProjects_UpdatesAllReferences()
    {
        // Create solution with 2 projects
        var solution = CreateTestSolution();

        // Project A defines a class
        var projectA = solution.Projects.First(p => p.Name == "ProjectA");
        projectA = projectA.AddDocument("ClassA.cs", @"
public class ClassA
{
    public void MethodA() { }
}").Project;

        // Project B references Project A
        var projectB = solution.Projects.First(p => p.Name == "ProjectB");
        projectB = projectB.AddProjectReference(
            new ProjectReference(projectA.Id));

        projectB = projectB.AddDocument("ClassB.cs", @"
class ClassB
{
    void M()
    {
        var a = new ClassA();
        a.MethodA(); // Reference to Project A
    }
}").Project;

        solution = projectB.Solution;

        // Rename MethodA to MethodRenamed
        var classADoc = projectA.Documents.First(d => d.Name == "ClassA.cs");
        var (line, col) = await FindSymbolLocationAsync(classADoc, "MethodA");

        var workspace = new RoslynWorkspaceService(/* ... */);
        var result = await workspace.RenameSymbolAsync(
            solution, classADoc.FilePath, line, col, "MethodRenamed");

        // Verify both projects were updated
        var updatedProjectA = result.Solution.GetProject(projectA.Id);
        var updatedClassA = await updatedProjectA.Documents
            .First(d => d.Name == "ClassA.cs")
            .GetTextAsync();

        Assert.Contains("MethodRenamed", updatedClassA.ToString());

        var updatedProjectB = result.Solution.GetProject(projectB.Id);
        var updatedClassB = await updatedProjectB.Documents
            .First(d => d.Name == "ClassB.cs")
            .GetTextAsync();

        Assert.Contains("MethodRenamed", updatedClassB.ToString());
        Assert.DoesNotContain("MethodA", updatedClassB.ToString());
    }
}
```

**4.5 Performance Benchmarks**

```csharp
// RoslynRefactorServer.Tests/PerformanceBenchmarks.cs
[MemoryDiagnoser]
public class PerformanceBenchmarks
{
    private Solution _largeSolution;

    [GlobalSetup]
    public async Task Setup()
    {
        // Create a large test solution (100 projects, 1000 files)
        _largeSolution = await CreateLargeSolutionAsync(
            projectCount: 100,
            filesPerProject: 10);
    }

    [Benchmark]
    public async Task LoadSolution_Large()
    {
        var workspace = new RoslynWorkspaceService(/* ... */);
        await workspace.LoadSolutionAsync(_largeSolution.FilePath);
    }

    [Benchmark]
    public async Task FindAllReferences_AcrossSolution()
    {
        var workspace = new RoslynWorkspaceService(/* ... */);
        var doc = _largeSolution.Projects.First().Documents.First();
        await workspace.FindAllReferencesAsync(
            _largeSolution.FilePath, doc.FilePath, line: 1, column: 1);
    }

    [Benchmark]
    public async Task RenameSymbol_AcrossSolution()
    {
        var workspace = new RoslynWorkspaceService(/* ... */);
        var doc = _largeSolution.Projects.First().Documents.First();
        await workspace.RenameSymbolAsync(
            _largeSolution, doc.FilePath, line: 1, column: 1, "NewName");
    }

    [Benchmark]
    public async Task GetDiagnostics_EntireSolution()
    {
        var workspace = new RoslynWorkspaceService(/* ... */);
        await workspace.GetDiagnosticsAsync(_largeSolution.FilePath, "Error");
    }
}
```

#### Effort Estimate
- **Development:** 2-3 weeks
- **Test Writing:** Ongoing (add tests with each feature)
- **Benchmark Setup:** 3 days

#### Success Metrics
- [ ] 80%+ code coverage
- [ ] 100+ refactoring correctness tests
- [ ] Edge case coverage (nested scopes, multiple outputs, etc.)
- [ ] Performance benchmarks for large solutions
- [ ] CI/CD integration with test reporting

---

### 5. Additional Core Refactorings (Roslynator Pattern)

#### Rationale
The project currently has **7 core refactorings**. Roslynator demonstrates 200+. Adding **10-15 high-value refactorings** would significantly increase utility.

#### Current State
- ✅ Extract Method
- ✅ Encapsulate Field
- ✅ Rename Symbol
- ✅ Find References
- ✅ Get Symbol Info
- ❌ Inline Method (reverse of extract)
- ❌ Extract Class
- ❌ Move Method
- ❌ Convert Patterns (foreach → LINQ, etc.)

#### Top 10 Missing Refactorings

**Priority 1: Inverse Operations**
1. **Inline Method** - Reverse of extract method
2. **Inline Variable** - Replace variable with its value

**Priority 2: Type-Level Refactorings**
3. **Extract Class** - Split large class into smaller ones
4. **Extract Interface** - Create interface from class
5. **Move Method to Class** - Move method to different class

**Priority 3: Code Modernization**
6. **Convert foreach to LINQ** - `foreach` → `.Select()`, `.Where()`, etc.
7. **Convert LINQ to foreach** - Reverse
8. **Use Pattern Matching** - Convert `is` + cast to pattern matching
9. **Use Expression Body** - Convert `{ return x; }` to `=> x`

**Priority 4: Code Quality**
10. **Introduce Null Check** - Add null guard to method
11. **Remove Unused Usings** - Clean up imports
12. **Sort Usings** - Alphabetize imports

#### Implementation Example: Inline Method

```csharp
// Add to Tools/AdvancedRefactoringTools.cs
[McpServerTool]
[Description("Inlines a method by replacing all calls with the method body")]
public async Task<string> inline_method(
    [Description("Path to solution file")] string solutionPath,
    [Description("Path to source file")] string documentPath,
    [Description("Line number of method to inline")] int line,
    [Description("Column number of method to inline")] int column,
    [Description("Whether to remove method after inlining")] bool removeMethod = true)
{
    _pathSecurity.ValidateSolutionFile(solutionPath);
    _pathSecurity.ValidateDocumentFile(documentPath);

    try
    {
        var solution = await _workspace.GetOrLoadSolutionAsync(solutionPath);
        var document = solution.Projects
            .SelectMany(p => p.Documents)
            .FirstOrDefault(d => d.FilePath == documentPath);

        if (document == null)
            return JsonError("Document not found");

        var semanticModel = await document.GetSemanticModelAsync();
        var syntaxRoot = await document.GetSyntaxRootAsync();

        // Get method at position
        var position = GetPosition(syntaxRoot, line, column);
        var methodNode = syntaxRoot.FindToken(position)
            .Parent
            .AncestorsAndSelf()
            .OfType<MethodDeclarationSyntax>()
            .FirstOrDefault();

        if (methodNode == null)
            return JsonError("No method found at specified location");

        var methodSymbol = semanticModel.GetDeclaredSymbol(methodNode);
        if (methodSymbol == null)
            return JsonError("Could not resolve method symbol");

        // Validation: Can only inline simple methods
        if (methodNode.Body == null)
            return JsonError("Cannot inline expression-bodied method");

        if (methodNode.Body.Statements.Count > 10)
            return JsonError("Method too complex to inline (>10 statements)");

        // Find all references to this method
        var references = await SymbolFinder.FindReferencesAsync(
            methodSymbol, solution);

        var documentEditor = await DocumentEditor.CreateAsync(document);

        foreach (var reference in references)
        {
            foreach (var location in reference.Locations)
            {
                var refDocument = solution.GetDocument(location.Document.Id);
                var refRoot = await refDocument.GetSyntaxRootAsync();
                var refNode = refRoot.FindNode(location.Location.SourceSpan);

                // Get invocation expression
                var invocation = refNode.AncestorsAndSelf()
                    .OfType<InvocationExpressionSyntax>()
                    .FirstOrDefault();

                if (invocation == null)
                    continue;

                // Clone method body
                var inlinedStatements = methodNode.Body.Statements.Select(s =>
                    (StatementSyntax)s.WithoutTrivia());

                // Replace parameters with arguments
                var parameterMap = BuildParameterMap(
                    methodSymbol.Parameters, invocation.ArgumentList.Arguments);

                var rewriter = new ParameterRewriter(parameterMap);
                inlinedStatements = inlinedStatements.Select(s =>
                    (StatementSyntax)rewriter.Visit(s));

                // Replace invocation with inlined code
                var inlinedBlock = SyntaxFactory.Block(inlinedStatements);

                // If invocation is a statement, replace with block
                var invocationStatement = invocation.AncestorsAndSelf()
                    .OfType<ExpressionStatementSyntax>()
                    .FirstOrDefault();

                if (invocationStatement != null)
                {
                    var newRoot = refRoot.ReplaceNode(
                        invocationStatement,
                        inlinedBlock.Statements);

                    refDocument = refDocument.WithSyntaxRoot(newRoot);
                }
            }
        }

        // Remove original method if requested
        if (removeMethod)
        {
            var newRoot = syntaxRoot.RemoveNode(methodNode, SyntaxRemoveOptions.KeepNoTrivia);
            document = document.WithSyntaxRoot(newRoot);
        }

        await _workspace.UpdateAndApplyChangesAsync(solutionPath, document.Project.Solution);

        return JsonSerializer.Serialize(new
        {
            success = true,
            methodName = methodSymbol.Name,
            inlinedCallCount = references.Sum(r => r.Locations.Count()),
            methodRemoved = removeMethod
        });
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Inline method failed");
        return JsonError(ex.Message);
    }
}

// Helper class for parameter substitution
private class ParameterRewriter : CSharpSyntaxRewriter
{
    private readonly Dictionary<string, ExpressionSyntax> _parameterMap;

    public ParameterRewriter(Dictionary<string, ExpressionSyntax> parameterMap)
    {
        _parameterMap = parameterMap;
    }

    public override SyntaxNode VisitIdentifierName(IdentifierNameSyntax node)
    {
        if (_parameterMap.TryGetValue(node.Identifier.Text, out var replacement))
        {
            return replacement;
        }

        return base.VisitIdentifierName(node);
    }
}
```

#### Implementation Example: Extract Interface

```csharp
[McpServerTool]
[Description("Extracts an interface from a class's public members")]
public async Task<string> extract_interface(
    [Description("Path to solution file")] string solutionPath,
    [Description("Path to source file")] string documentPath,
    [Description("Line number of class")] int line,
    [Description("Column number of class")] int column,
    [Description("Interface name")] string interfaceName,
    [Description("Whether to implement interface in class")] bool implementInterface = true)
{
    _pathSecurity.ValidateSolutionFile(solutionPath);
    _pathSecurity.ValidateDocumentFile(documentPath);

    try
    {
        var solution = await _workspace.GetOrLoadSolutionAsync(solutionPath);
        var document = solution.Projects
            .SelectMany(p => p.Documents)
            .FirstOrDefault(d => d.FilePath == documentPath);

        if (document == null)
            return JsonError("Document not found");

        var semanticModel = await document.GetSemanticModelAsync();
        var syntaxRoot = await document.GetSyntaxRootAsync();

        // Get class at position
        var position = GetPosition(syntaxRoot, line, column);
        var classNode = syntaxRoot.FindToken(position)
            .Parent
            .AncestorsAndSelf()
            .OfType<ClassDeclarationSyntax>()
            .FirstOrDefault();

        if (classNode == null)
            return JsonError("No class found at specified location");

        var classSymbol = semanticModel.GetDeclaredSymbol(classNode);
        if (classSymbol == null)
            return JsonError("Could not resolve class symbol");

        // Generate interface from public members
        var generator = SyntaxGenerator.GetGenerator(document);

        var interfaceMembers = new List<SyntaxNode>();

        foreach (var member in classSymbol.GetMembers())
        {
            if (member.DeclaredAccessibility != Accessibility.Public)
                continue;

            if (member is IMethodSymbol method && !method.IsStatic)
            {
                var interfaceMethod = generator.MethodDeclaration(method);
                interfaceMembers.Add(interfaceMethod);
            }
            else if (member is IPropertySymbol property && !property.IsStatic)
            {
                var interfaceProperty = generator.PropertyDeclaration(property);
                interfaceMembers.Add(interfaceProperty);
            }
        }

        var interfaceDeclaration = generator.InterfaceDeclaration(
            interfaceName,
            accessibility: Accessibility.Public,
            members: interfaceMembers);

        // Add interface to same file or new file
        var newDocument = document.WithSyntaxRoot(
            syntaxRoot.InsertNodesBefore(classNode, new[] { interfaceDeclaration }));

        // Update class to implement interface
        if (implementInterface)
        {
            var updatedClassNode = classNode.AddBaseListTypes(
                SyntaxFactory.SimpleBaseType(
                    SyntaxFactory.IdentifierName(interfaceName)));

            var newRoot = await newDocument.GetSyntaxRootAsync();
            newRoot = newRoot.ReplaceNode(classNode, updatedClassNode);
            newDocument = newDocument.WithSyntaxRoot(newRoot);
        }

        await _workspace.UpdateAndApplyChangesAsync(solutionPath, newDocument.Project.Solution);

        return JsonSerializer.Serialize(new
        {
            success = true,
            interfaceName,
            memberCount = interfaceMembers.Count,
            implementedInClass = implementInterface
        });
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Extract interface failed");
        return JsonError(ex.Message);
    }
}
```

#### Effort Estimate
- **Per Refactoring:** 1-2 weeks each
- **10 Refactorings:** 3-4 months
- **Testing:** 1 week per refactoring
- **Documentation:** 1 day per refactoring

#### Success Metrics
- [ ] 15+ total refactorings (current 7 + 8 new)
- [ ] All refactorings pass semantic correctness tests
- [ ] Documentation for each refactoring with examples
- [ ] AI agents can successfully use all refactorings

---

## High Priority

### 6. EditorConfig Integration (SonarAnalyzer Pattern)

#### Rationale
Different projects have different coding standards. EditorConfig is the industry standard for project-specific settings. Refactorings should **respect project conventions** (naming, indentation, etc.).

#### Current State
- ❌ No EditorConfig support
- ⚠️ Uses hardcoded conventions (PascalCase for properties, etc.)
- ❌ Can introduce style inconsistencies

#### Implementation Approach

```csharp
// New service: Services/EditorConfigService.cs
public class EditorConfigService
{
    private readonly Dictionary<string, EditorConfigSettings> _cache = new();

    public async Task<EditorConfigSettings> LoadForDocumentAsync(string documentPath)
    {
        // Find .editorconfig by walking up directory tree
        var directory = Path.GetDirectoryName(documentPath);

        while (directory != null)
        {
            var configPath = Path.Combine(directory, ".editorconfig");

            if (File.Exists(configPath))
            {
                if (!_cache.TryGetValue(configPath, out var settings))
                {
                    settings = await ParseEditorConfigAsync(configPath);
                    _cache[configPath] = settings;
                }

                return settings;
            }

            directory = Path.GetDirectoryName(directory);
        }

        return EditorConfigSettings.Default;
    }

    private async Task<EditorConfigSettings> ParseEditorConfigAsync(string path)
    {
        var settings = new EditorConfigSettings();
        var lines = await File.ReadAllLinesAsync(path);

        string currentSection = "*";

        foreach (var line in lines)
        {
            if (line.StartsWith("[") && line.EndsWith("]"))
            {
                currentSection = line.Trim('[', ']');
                continue;
            }

            if (line.Contains('='))
            {
                var parts = line.Split('=', 2);
                var key = parts[0].Trim();
                var value = parts[1].Trim();

                // Parse relevant settings
                if (key.StartsWith("dotnet_naming_rule"))
                {
                    ParseNamingRule(settings, key, value);
                }
                else if (key == "indent_size")
                {
                    settings.IndentSize = int.Parse(value);
                }
                else if (key == "indent_style")
                {
                    settings.IndentStyle = value;
                }
            }
        }

        return settings;
    }

    private void ParseNamingRule(EditorConfigSettings settings, string key, string value)
    {
        // Parse dotnet_naming_rule.* settings
        // Example: dotnet_naming_rule.private_fields_should_be_camelcase.severity = warning

        var match = Regex.Match(key, @"dotnet_naming_rule\.(.+?)\.(.+)");
        if (match.Success)
        {
            var ruleName = match.Groups[1].Value;
            var property = match.Groups[2].Value;

            if (!settings.NamingRules.ContainsKey(ruleName))
            {
                settings.NamingRules[ruleName] = new NamingRule();
            }

            var rule = settings.NamingRules[ruleName];

            switch (property)
            {
                case "severity":
                    rule.Severity = value;
                    break;
                case "symbols":
                    rule.Symbols = value;
                    break;
                case "style":
                    rule.Style = value;
                    break;
            }
        }
    }
}

public class EditorConfigSettings
{
    public int IndentSize { get; set; } = 4;
    public string IndentStyle { get; set; } = "space";
    public Dictionary<string, NamingRule> NamingRules { get; set; } = new();

    public string GetNamingConvention(SymbolKind kind, Accessibility accessibility)
    {
        // Return appropriate naming convention based on EditorConfig rules
        // Examples: camel_case, pascal_case, all_upper, etc.

        var applicableRules = NamingRules.Values
            .Where(r => MatchesSymbol(r, kind, accessibility))
            .OrderByDescending(r => r.Specificity)
            .ToList();

        return applicableRules.FirstOrDefault()?.Style ?? "pascal_case";
    }

    private bool MatchesSymbol(NamingRule rule, SymbolKind kind, Accessibility accessibility)
    {
        // Check if rule applies to this symbol
        // This requires parsing rule.Symbols which references another setting
        return true; // Simplified
    }

    public static EditorConfigSettings Default => new();
}

public class NamingRule
{
    public string Severity { get; set; } = "warning";
    public string Symbols { get; set; } = "";
    public string Style { get; set; } = "pascal_case";
    public int Specificity { get; set; } = 0;
}
```

**Usage in Refactorings:**

```csharp
// Update AdvancedRefactoringTools.cs - encapsulate_field
public async Task<string> encapsulate_field(...)
{
    // ... existing code ...

    // Load EditorConfig settings
    var editorConfig = await _editorConfigService.LoadForDocumentAsync(documentPath);

    // Get naming convention for properties
    var namingConvention = editorConfig.GetNamingConvention(
        SymbolKind.Property, Accessibility.Public);

    // Apply convention to property name
    var propertyName = ApplyNamingConvention(
        fieldSymbol.Name, namingConvention);

    // Generate property with correct naming
    var property = _generator.PropertyDeclaration(
        propertyName,
        _generator.TypeExpression(fieldSymbol.Type),
        Accessibility.Public,
        getAccessorStatements: new[] { /* ... */ });

    // ... rest of refactoring ...
}

private string ApplyNamingConvention(string name, string convention)
{
    return convention switch
    {
        "pascal_case" => ToPascalCase(name),
        "camel_case" => ToCamelCase(name),
        "all_upper" => name.ToUpperInvariant(),
        "all_lower" => name.ToLowerInvariant(),
        _ => name
    };
}
```

#### Effort Estimate
- **Development:** 2 weeks
- **Testing:** 1 week
- **Documentation:** 2 days

#### Success Metrics
- [ ] Reads .editorconfig files
- [ ] Applies naming conventions from EditorConfig
- [ ] Respects indentation settings
- [ ] Falls back to defaults if no EditorConfig

---

### 7. Performance Optimization (OmniSharp/SonarAnalyzer Patterns)

#### Rationale
Current project uses LRU cache, but **lacks incremental analysis**. For large solutions (1000+ projects), full re-analysis is expensive. OmniSharp demonstrates incremental patterns.

#### Current State
- ✅ LRU cache for solutions
- ✅ Compilation caching
- ✅ FileSystemWatcher for invalidation
- ❌ No incremental analysis (re-analyzes all files)
- ❌ No parallel analysis
- ⚠️ Slow for large solutions (30s+ load time)

#### Implementation Approach

**7.1 Incremental Analysis**

```csharp
// Update Services/RoslynWorkspaceService.cs
private readonly ConcurrentDictionary<DocumentId, DocumentAnalysisCache> _documentCache = new();

private class DocumentAnalysisCache
{
    public DateTime LastModified { get; set; }
    public SemanticModel? SemanticModel { get; set; }
    public ImmutableArray<Diagnostic> Diagnostics { get; set; }
    public SyntaxTree? SyntaxTree { get; set; }
}

public async Task<ImmutableArray<Diagnostic>> GetDiagnosticsIncrementalAsync(
    string solutionPath,
    string[] changedFiles)
{
    var solution = await GetOrLoadSolutionAsync(solutionPath);

    var allDiagnostics = ImmutableArray.CreateBuilder<Diagnostic>();

    // Only analyze changed files + their dependents
    var documentsToAnalyze = GetAffectedDocuments(solution, changedFiles);

    await Parallel.ForEachAsync(documentsToAnalyze,
        async (document, ct) =>
        {
            var diagnostics = await GetDocumentDiagnosticsAsync(document);
            lock (allDiagnostics)
            {
                allDiagnostics.AddRange(diagnostics);
            }
        });

    return allDiagnostics.ToImmutable();
}

private IEnumerable<Document> GetAffectedDocuments(
    Solution solution,
    string[] changedFiles)
{
    var changedDocuments = solution.Projects
        .SelectMany(p => p.Documents)
        .Where(d => changedFiles.Contains(d.FilePath))
        .ToList();

    // Find documents that depend on changed documents
    var affectedDocuments = new HashSet<Document>(changedDocuments);

    foreach (var changedDoc in changedDocuments)
    {
        var dependents = FindDependentDocuments(solution, changedDoc);
        affectedDocuments.UnionWith(dependents);
    }

    return affectedDocuments;
}

private IEnumerable<Document> FindDependentDocuments(
    Solution solution,
    Document changedDocument)
{
    // Find documents that reference symbols from changedDocument
    var semanticModel = await changedDocument.GetSemanticModelAsync();
    var publicSymbols = semanticModel.GetDeclaredSymbols()
        .Where(s => s.DeclaredAccessibility == Accessibility.Public);

    var dependents = new List<Document>();

    foreach (var symbol in publicSymbols)
    {
        var references = await SymbolFinder.FindReferencesAsync(symbol, solution);

        foreach (var reference in references)
        {
            foreach (var location in reference.Locations)
            {
                dependents.Add(location.Document);
            }
        }
    }

    return dependents.Distinct();
}

private async Task<ImmutableArray<Diagnostic>> GetDocumentDiagnosticsAsync(
    Document document)
{
    // Check cache first
    if (_documentCache.TryGetValue(document.Id, out var cache))
    {
        var fileInfo = new FileInfo(document.FilePath);

        if (fileInfo.LastWriteTimeUtc <= cache.LastModified)
        {
            // Cache hit
            return cache.Diagnostics;
        }
    }

    // Cache miss - recompute
    var semanticModel = await document.GetSemanticModelAsync();
    var diagnostics = semanticModel.GetDiagnostics();

    _documentCache[document.Id] = new DocumentAnalysisCache
    {
        LastModified = DateTime.UtcNow,
        SemanticModel = semanticModel,
        Diagnostics = diagnostics,
        SyntaxTree = await document.GetSyntaxTreeAsync()
    };

    return diagnostics;
}
```

**7.2 Lazy Project Loading**

```csharp
// Update Services/RoslynWorkspaceService.cs
public async Task<Solution> LoadSolutionLazyAsync(string solutionPath)
{
    var workspace = MSBuildWorkspace.Create();

    // Configure workspace to skip unreferenced projects
    workspace.LoadMetadataForReferencedProjects = false;
    workspace.SkipUnrecognizedProjects = true;

    // Open solution (only loads project metadata, not documents)
    var solution = await workspace.OpenSolutionAsync(solutionPath);

    // Store in cache
    _solutionCache[solutionPath] = new SolutionCacheEntry
    {
        Solution = solution,
        LastAccessed = DateTime.UtcNow,
        EstimatedMemoryBytes = EstimateMemoryUsage(solution),
        IsLazyLoaded = true
    };

    return solution;
}

public async Task<Project> LoadProjectFullyAsync(ProjectId projectId)
{
    // Load all documents for a specific project on-demand
    var solution = _solutionCache.Values
        .Select(entry => entry.Solution)
        .FirstOrDefault(s => s.Projects.Any(p => p.Id == projectId));

    if (solution == null)
        throw new InvalidOperationException("Project not found in cached solutions");

    var project = solution.GetProject(projectId);

    // Force load all documents
    foreach (var document in project.Documents)
    {
        await document.GetSemanticModelAsync();
    }

    return project;
}
```

**7.3 Parallel Analysis**

```csharp
// Update Services/RoslynWorkspaceService.cs
public async Task<DiagnosticsInfo> GetDiagnosticsParallelAsync(
    string solutionPath,
    string severityFilter = "Warning")
{
    var solution = await GetOrLoadSolutionAsync(solutionPath);

    var diagnosticsList = new ConcurrentBag<DiagnosticInfo>();
    var errorCount = 0;
    var warningCount = 0;

    // Analyze all projects in parallel
    await Parallel.ForEachAsync(solution.Projects,
        new ParallelOptions { MaxDegreeOfParallelism = Environment.ProcessorCount },
        async (project, ct) =>
        {
            var compilation = await GetOrCacheCompilationAsync(project);
            if (compilation == null)
                return;

            var projectDiagnostics = compilation.GetDiagnostics()
                .Where(d => ShouldIncludeDiagnostic(d, severityFilter));

            foreach (var diagnostic in projectDiagnostics)
            {
                diagnosticsList.Add(new DiagnosticInfo
                {
                    Severity = diagnostic.Severity.ToString(),
                    Message = diagnostic.GetMessage(),
                    FilePath = diagnostic.Location.SourceTree?.FilePath ?? "",
                    Line = diagnostic.Location.GetLineSpan().StartLinePosition.Line + 1,
                    Column = diagnostic.Location.GetLineSpan().StartLinePosition.Character + 1,
                    DiagnosticId = diagnostic.Id
                });

                if (diagnostic.Severity == DiagnosticSeverity.Error)
                    Interlocked.Increment(ref errorCount);
                else if (diagnostic.Severity == DiagnosticSeverity.Warning)
                    Interlocked.Increment(ref warningCount);
            }
        });

    return new DiagnosticsInfo
    {
        ErrorCount = errorCount,
        WarningCount = warningCount,
        IsSafeToRefactor = errorCount == 0,
        Diagnostics = diagnosticsList.ToList()
    };
}
```

#### Effort Estimate
- **Development:** 3 weeks
- **Testing:** 2 weeks (performance regression tests)
- **Documentation:** 2 days

#### Success Metrics
- [ ] 10x faster incremental analysis vs. full analysis
- [ ] Lazy loading reduces initial load time by 5x
- [ ] Parallel analysis utilizes all CPU cores
- [ ] No performance regressions on small solutions

---

## Conclusion

This document provides **actionable, detailed implementation guidance** for 15+ critical improvements to the c-sharp-refactor-mcp project. Each recommendation is prioritized, estimated, and includes concrete code examples.

**Next Steps:**
1. Review and prioritize recommendations with stakeholders
2. Create GitHub issues for each recommendation
3. Implement critical priority items first (Phases 1-2)
4. Iterate based on user feedback and ecosystem evolution

**Implementation Phases:**
- **Phase 1 (Critical):** 3-4 months - Token optimization, Git integration, patterns, tests, core refactorings
- **Phase 2 (High):** 2-3 months - EditorConfig, performance, rename options, impact analysis
- **Phase 3 (Medium):** 3-4 months - Architecture validation, security, templates
- **Phase 4 (Long-Term):** Ongoing research - Grammar-based support, cross-repo, query-based

By systematically implementing these improvements, **c-sharp-refactor-mcp** will evolve into a **comprehensive, production-ready AI-driven refactoring platform** that sets the standard for multi-language MCP servers.
