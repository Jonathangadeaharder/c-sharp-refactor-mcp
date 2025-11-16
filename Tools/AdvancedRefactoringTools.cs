using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Editing;
using Microsoft.CodeAnalysis.FindSymbols;
using Microsoft.CodeAnalysis.Text;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;
using RoslynRefactorServer.Services;
using System.ComponentModel;
using System.Text.Json;

namespace RoslynRefactorServer.Tools;

/// <summary>
/// Advanced MCP refactoring tools that require complex manual implementation
/// using low-level Roslyn APIs like data flow analysis and syntax rewriting.
/// </summary>
[McpTools]
public class AdvancedRefactoringTools
{
    private readonly RoslynWorkspaceService _workspaceService;
    private readonly PathSecurityService _securityService;
    private readonly ILogger<AdvancedRefactoringTools> _logger;

    public AdvancedRefactoringTools(
        RoslynWorkspaceService workspaceService,
        PathSecurityService securityService,
        ILogger<AdvancedRefactoringTools> logger)
    {
        _workspaceService = workspaceService;
        _securityService = securityService;
        _logger = logger;
    }

    /// <summary>
    /// Extracts a selected block of code into a new method with proper parameters and return values.
    /// </summary>
    [McpTool]
    [Description("Extracts a selected block of code into a new method. " +
                 "Uses data flow analysis to determine correct method signature (parameters and return type). " +
                 "This is a complex write operation. IMPORTANT: Ensure code has no compilation errors first.")]
    public async Task<string> extract_method(
        [Description("Absolute path to the .sln solution file")] string solutionPath,
        [Description("Absolute path to the .cs document")] string documentPath,
        [Description("Start line number (1-based) of code to extract")] int startLine,
        [Description("Start column number (1-based)")] int startColumn,
        [Description("End line number (1-based) of code to extract")] int endLine,
        [Description("End column number (1-based)")] int endColumn,
        [Description("Name for the new extracted method")] string newMethodName)
    {
        try
        {
            _logger.LogInformation("Extracting method from {Path}:{StartLine}-{EndLine}", documentPath, startLine, endLine);

            _securityService.ValidateSolutionFile(solutionPath);
            _securityService.ValidateDocumentFile(documentPath);

            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(solutionPath);
            var document = solution.Projects
                .SelectMany(p => p.Documents)
                .FirstOrDefault(d => Path.GetFullPath(d.FilePath ?? "") == Path.GetFullPath(documentPath));

            if (document == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Document not found" });
            }

            var semanticModel = await document.GetSemanticModelAsync();
            var syntaxRoot = await document.GetSyntaxRootAsync();
            var sourceText = await document.GetTextAsync();

            if (semanticModel == null || syntaxRoot == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Failed to get semantic model" });
            }

            // Calculate the text span to extract
            var startPos = sourceText.Lines[startLine - 1].Start + (startColumn - 1);
            var endPos = sourceText.Lines[endLine - 1].Start + (endColumn - 1);
            var span = TextSpan.FromBounds(startPos, endPos);

            // Find the statements to extract
            var nodesToExtract = syntaxRoot.DescendantNodes(span)
                .Where(n => span.Contains(n.Span) && n is StatementSyntax)
                .Cast<StatementSyntax>()
                .ToList();

            if (!nodesToExtract.Any())
            {
                return JsonSerializer.Serialize(new
                {
                    success = false,
                    error = "No valid statements found in the selected range. Make sure you're selecting complete statements."
                });
            }

            // Perform data flow analysis to determine method signature
            var dataFlowAnalysis = semanticModel.AnalyzeDataFlow(
                nodesToExtract.First(),
                nodesToExtract.Last());

            if (!dataFlowAnalysis.Succeeded)
            {
                return JsonSerializer.Serialize(new
                {
                    success = false,
                    error = "Data flow analysis failed. The selected code may have control flow issues."
                });
            }

            // Determine input parameters (variables read but not declared in selection)
            var inputVariables = dataFlowAnalysis.DataFlowsIn
                .Where(s => !s.IsStatic)
                .ToList();

            // Determine return values (variables written in selection and used after)
            var outputVariables = dataFlowAnalysis.DataFlowsOut.ToList();

            // Build the new method
            var parameters = inputVariables.Select(v =>
                SyntaxFactory.Parameter(SyntaxFactory.Identifier(v.Name))
                    .WithType(SyntaxFactory.ParseTypeName(v.GetTypeOrReturnType()?.ToString() ?? "object"))
            ).ToArray();

            var returnType = outputVariables.Count switch
            {
                0 => SyntaxFactory.ParseTypeName("void"),
                1 => SyntaxFactory.ParseTypeName(outputVariables[0].GetTypeOrReturnType()?.ToString() ?? "object"),
                _ => SyntaxFactory.ParseTypeName($"({string.Join(", ", outputVariables.Select(v => v.GetTypeOrReturnType()?.ToString() ?? "object"))})")
            };

            var extractedStatements = SyntaxFactory.List(nodesToExtract);

            // Add return statement if needed
            if (outputVariables.Count == 1)
            {
                var returnStatement = SyntaxFactory.ReturnStatement(
                    SyntaxFactory.IdentifierName(outputVariables[0].Name));
                extractedStatements = extractedStatements.Add(returnStatement);
            }
            else if (outputVariables.Count > 1)
            {
                var tupleElements = outputVariables.Select(v =>
                    SyntaxFactory.Argument(SyntaxFactory.IdentifierName(v.Name)));
                var returnStatement = SyntaxFactory.ReturnStatement(
                    SyntaxFactory.TupleExpression(SyntaxFactory.SeparatedList(tupleElements)));
                extractedStatements = extractedStatements.Add(returnStatement);
            }

            var newMethod = SyntaxFactory.MethodDeclaration(returnType, newMethodName)
                .WithParameterList(SyntaxFactory.ParameterList(SyntaxFactory.SeparatedList(parameters)))
                .WithModifiers(SyntaxFactory.TokenList(SyntaxFactory.Token(SyntaxKind.PrivateKeyword)))
                .WithBody(SyntaxFactory.Block(extractedStatements))
                .WithLeadingTrivia(SyntaxFactory.CarriageReturnLineFeed, SyntaxFactory.CarriageReturnLineFeed);

            // Create method invocation
            var invocationArguments = inputVariables.Select(v =>
                SyntaxFactory.Argument(SyntaxFactory.IdentifierName(v.Name)));
            var invocation = SyntaxFactory.InvocationExpression(
                SyntaxFactory.IdentifierName(newMethodName),
                SyntaxFactory.ArgumentList(SyntaxFactory.SeparatedList(invocationArguments)));

            StatementSyntax replacementStatement = outputVariables.Count switch
            {
                0 => SyntaxFactory.ExpressionStatement(invocation),
                1 => SyntaxFactory.ExpressionStatement(
                    SyntaxFactory.AssignmentExpression(
                        SyntaxKind.SimpleAssignmentExpression,
                        SyntaxFactory.IdentifierName(outputVariables[0].Name),
                        invocation)),
                _ => SyntaxFactory.ExpressionStatement(invocation) // Simplified for tuple case
            };

            // Find the containing method or property
            var containingMember = nodesToExtract.First().Ancestors()
                .OfType<MemberDeclarationSyntax>()
                .FirstOrDefault();

            if (containingMember == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Could not find containing member" });
            }

            // Replace the extracted code with the invocation
            var newRoot = syntaxRoot;
            foreach (var node in nodesToExtract.Skip(1))
            {
                newRoot = newRoot.RemoveNode(node, SyntaxRemoveOptions.KeepNoTrivia)!;
            }
            newRoot = newRoot.ReplaceNode(
                newRoot.FindNode(nodesToExtract.First().Span),
                replacementStatement);

            // Add the new method to the containing type
            var containingType = containingMember.Ancestors().OfType<TypeDeclarationSyntax>().FirstOrDefault();
            if (containingType != null)
            {
                var oldType = newRoot.FindNode(containingType.Span) as TypeDeclarationSyntax;
                if (oldType != null)
                {
                    var newType = oldType.AddMembers(newMethod);
                    newRoot = newRoot.ReplaceNode(oldType, newType);
                }
            }

            // Apply changes
            var newDocument = document.WithSyntaxRoot(newRoot);
            var newSolution = newDocument.Project.Solution;

            await _workspaceService.UpdateAndApplyChangesAsync(solutionPath, newSolution);

            return JsonSerializer.Serialize(new
            {
                success = true,
                message = $"Successfully extracted method '{newMethodName}'",
                methodName = newMethodName,
                parameterCount = inputVariables.Count,
                parameters = inputVariables.Select(v => new { name = v.Name, type = v.GetTypeOrReturnType()?.ToString() }).ToList()
            }, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to extract method");
            return JsonSerializer.Serialize(new { success = false, error = ex.Message, stack = ex.StackTrace });
        }
    }

    /// <summary>
    /// Encapsulates a field by creating a property and updating all references.
    /// </summary>
    [McpTool]
    [Description("Encapsulates a private field by creating a public property with get/set accessors. " +
                 "Updates all references to the field across the solution to use the new property. " +
                 "This is a write operation that modifies multiple files.")]
    public async Task<string> encapsulate_field(
        [Description("Absolute path to the .sln solution file")] string solutionPath,
        [Description("Absolute path to the .cs document containing the field")] string documentPath,
        [Description("Line number (1-based) of the field declaration")] int line,
        [Description("Column number (1-based) of the field")] int column)
    {
        try
        {
            _logger.LogInformation("Encapsulating field at {Path}:{Line}:{Column}", documentPath, line, column);

            _securityService.ValidateSolutionFile(solutionPath);
            _securityService.ValidateDocumentFile(documentPath);

            var solution = await _workspaceService.LoadOrRefreshSolutionAsync(solutionPath);
            var document = solution.Projects
                .SelectMany(p => p.Documents)
                .FirstOrDefault(d => Path.GetFullPath(d.FilePath ?? "") == Path.GetFullPath(documentPath));

            if (document == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Document not found" });
            }

            var semanticModel = await document.GetSemanticModelAsync();
            var syntaxRoot = await document.GetSyntaxRootAsync();

            if (semanticModel == null || syntaxRoot == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Failed to get semantic model" });
            }

            // Get the field symbol
            var sourceText = await document.GetTextAsync();
            var position = sourceText.Lines[line - 1].Start + (column - 1);
            var node = syntaxRoot.FindNode(new TextSpan(position, 0));
            var fieldSymbol = semanticModel.GetDeclaredSymbol(node) as IFieldSymbol;

            if (fieldSymbol == null)
            {
                return JsonSerializer.Serialize(new
                {
                    success = false,
                    error = "No field found at specified position. Make sure the cursor is on a field declaration."
                });
            }

            var fieldName = fieldSymbol.Name;
            var propertyName = char.ToUpper(fieldName[0]) + fieldName.Substring(1);
            if (fieldName.StartsWith("_"))
            {
                propertyName = char.ToUpper(fieldName[1]) + fieldName.Substring(2);
            }

            // Generate the property using SyntaxGenerator
            var generator = SyntaxGenerator.GetGenerator(document);
            var propertyDeclaration = generator.PropertyDeclaration(
                propertyName,
                generator.TypeExpression(fieldSymbol.Type),
                Accessibility.Public,
                DeclarationModifiers.None,
                getAccessorStatements: new[] { generator.ReturnStatement(generator.IdentifierName(fieldName)) },
                setAccessorStatements: new[] {
                    generator.AssignmentStatement(
                        generator.IdentifierName(fieldName),
                        generator.IdentifierName("value"))
                });

            // Find the field declaration node
            var fieldDeclaration = syntaxRoot.FindNode(fieldSymbol.Locations[0].SourceSpan)
                .AncestorsAndSelf()
                .OfType<FieldDeclarationSyntax>()
                .FirstOrDefault();

            if (fieldDeclaration == null)
            {
                return JsonSerializer.Serialize(new { success = false, error = "Could not find field declaration" });
            }

            // Make the field private if it isn't already
            var newFieldDeclaration = fieldDeclaration
                .WithModifiers(SyntaxFactory.TokenList(SyntaxFactory.Token(SyntaxKind.PrivateKeyword)));

            var newRoot = syntaxRoot.ReplaceNode(fieldDeclaration, newFieldDeclaration);

            // Add the property after the field
            var containingType = fieldDeclaration.Ancestors().OfType<TypeDeclarationSyntax>().FirstOrDefault();
            if (containingType != null)
            {
                var oldType = newRoot.FindNode(containingType.Span) as TypeDeclarationSyntax;
                if (oldType != null)
                {
                    var fieldIndex = oldType.Members.IndexOf(oldType.Members.OfType<FieldDeclarationSyntax>()
                        .First(f => f.Span == newFieldDeclaration.Span));
                    var newType = oldType.WithMembers(
                        oldType.Members.Insert(fieldIndex + 1, (MemberDeclarationSyntax)propertyDeclaration));
                    newRoot = newRoot.ReplaceNode(oldType, newType);
                }
            }

            // Update the document
            var updatedDocument = document.WithSyntaxRoot(newRoot);
            var currentSolution = updatedDocument.Project.Solution;

            // Find all references to the field and update them to use the property
            // (excluding the field declaration itself)
            var references = await SymbolFinder.FindReferencesAsync(fieldSymbol, solution);

            foreach (var reference in references)
            {
                foreach (var location in reference.Locations)
                {
                    // Skip if it's the declaration
                    if (location.Location.SourceSpan == fieldSymbol.Locations[0].SourceSpan)
                        continue;

                    var refDocument = location.Document;
                    var refRoot = await refDocument.GetSyntaxRootAsync();
                    var refNode = refRoot?.FindNode(location.Location.SourceSpan);

                    if (refNode is IdentifierNameSyntax identifierName)
                    {
                        var newIdentifier = identifierName.WithIdentifier(
                            SyntaxFactory.Identifier(propertyName));
                        var newRefRoot = refRoot!.ReplaceNode(identifierName, newIdentifier);
                        currentSolution = currentSolution.WithDocumentSyntaxRoot(refDocument.Id, newRefRoot);
                    }
                }
            }

            await _workspaceService.UpdateAndApplyChangesAsync(solutionPath, currentSolution);

            return JsonSerializer.Serialize(new
            {
                success = true,
                message = $"Successfully encapsulated field '{fieldName}' with property '{propertyName}'",
                fieldName = fieldName,
                propertyName = propertyName,
                referencesUpdated = references.Sum(r => r.Locations.Count()) - 1
            }, new JsonSerializerOptions { WriteIndented = true });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to encapsulate field");
            return JsonSerializer.Serialize(new { success = false, error = ex.Message });
        }
    }
}

// Extension helper
internal static class SymbolExtensions
{
    public static ITypeSymbol? GetTypeOrReturnType(this ISymbol symbol)
    {
        return symbol switch
        {
            ILocalSymbol local => local.Type,
            IParameterSymbol parameter => parameter.Type,
            IFieldSymbol field => field.Type,
            IPropertySymbol property => property.Type,
            IMethodSymbol method => method.ReturnType,
            _ => null
        };
    }
}
