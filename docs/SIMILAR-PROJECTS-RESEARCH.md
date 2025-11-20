# Similar Projects Research Report

## Overview

This document catalogs GitHub projects that are highly relevant to **c-sharp-refactor-mcp** and provides comprehensive learning opportunities. These projects are organized by category and relevance to help inform improvements, identify best practices, and understand the broader ecosystem.

**Report Date:** November 20, 2025
**Project Context:** Multi-Language Refactoring MCP Server with Roslyn & LSP integration

---

## Executive Summary

The c-sharp-refactor-mcp project occupies a unique position in the MCP ecosystem by combining:
- Comprehensive multi-language support (8 languages)
- Hybrid architecture (Roslyn for .NET, LSP for others)
- Safe, semantic refactoring operations
- AI agent integration via MCP protocol

**Key Findings:**
- **2 direct competitors** exist (SharpToolsMCP, RefactorMCP) - both C#-only
- **No multi-language MCP refactoring servers** identified
- **Opportunity for differentiation** through broader language support
- **Mature ecosystems** exist for learning (Roslyn analyzers, LSP implementations)

---

## Category 1: Directly Related MCP Refactoring Projects

### 1. SharpToolsMCP ⭐⭐⭐⭐⭐
**Repository:** https://github.com/kooshi/SharpToolsMCP
**Stars:** 32
**Primary Language:** C#
**Status:** Active

#### Description
A comprehensive Roslyn-powered MCP server designed specifically to empower AI agents with C# code analysis and modification capabilities. This is arguably the **most similar project** to c-sharp-refactor-mcp.

#### Key Features
- **Dual Protocol Support:** SSE (HTTP) and Stdio communication
- **Advanced Roslyn Integration:** Semantic models, symbol resolution, code modification
- **Token Efficiency:** Minimizes context sent to AI agents (removes indentation, FQN navigation)
- **Git Integration:** Automated branch creation, commit management, undo functionality
- **Complexity Analysis:** Cyclomatic and cognitive complexity detection
- **Source Resolution:** Local files, SourceLink, embedded PDBs, decompilation fallbacks

#### Architecture Highlights
```
MCP Client (Claude/Copilot)
        ↓
SharpToolsMCP Server
        ↓
    ┌───┴──────────────┐
    ↓                  ↓
Roslyn Engine     Git Operations
```

#### What to Learn
1. **Token Optimization Strategies:**
   - Removing indentation from code context
   - FQN-based fuzzy matching for imprecise symbol references
   - Dynamic complexity-adjusted resolution depth

2. **Git Workflow Integration:**
   - Automated branch creation per refactoring session
   - Commit management with automatic rollback
   - Undo functionality for failed operations

3. **Error Handling:**
   - Compilation error reporting post-modification
   - Validation layers before applying changes

4. **Code Quality Features:**
   - Semantic similarity detection
   - Complexity metrics exposure

#### Comparison to c-sharp-refactor-mcp

| Feature | SharpToolsMCP | c-sharp-refactor-mcp |
|---------|---------------|----------------------|
| **Languages** | C# only | 8 languages (C#, VB.NET, TS, Python, Go, C++, Java, Rust) |
| **Protocol** | SSE + Stdio | Stdio only |
| **Git Integration** | ✅ Built-in | ❌ Not implemented |
| **Token Optimization** | ✅ Advanced | ⚠️ Basic |
| **Complexity Analysis** | ✅ Built-in | ❌ Not implemented |
| **Source Resolution** | ✅ Multiple sources | ⚠️ Local files only |
| **Multi-Language** | ❌ C# only | ✅ 8 languages |

#### Recommendations
- **Adopt:** Token optimization techniques (indentation removal, FQN fuzzy matching)
- **Consider:** Git integration for automated commit/rollback workflows
- **Evaluate:** Complexity analysis as additional MCP tool
- **Study:** Source resolution patterns (SourceLink, decompilation)

---

### 2. RefactorMCP ⭐⭐⭐⭐
**Repository:** https://github.com/dave-hillier/refactor-mcp
**Stars:** 34
**Primary Language:** C#
**Status:** Active

#### Description
A focused MCP server concentrating on a curated, high-quality set of Roslyn-based refactoring operations. Takes a **quality over quantity** approach with well-tested refactorings.

#### Key Features
- **Curated Refactoring Set:**
  - Extract method
  - Introduce field/parameter/variable
  - Convert to static
  - Move methods between classes
  - Extract class
  - Inline method

- **Design Pattern Support:**
  - Decorator pattern code generation
  - Adapter pattern code generation

- **Safety Features:**
  - Dependency checking before deletion
  - Compilation verification post-refactoring

- **Metrics & Discovery:**
  - Exposes metrics via custom resource schemes
  - "List Tools" discovery mechanism

#### Architecture Highlights
```
MCP Client
    ↓
RefactorMCP Server
    ↓
Roslyn Refactoring API
    ↓
Test Suite (Comprehensive)
```

#### What to Learn
1. **Focused Approach:**
   - Limited, well-tested refactoring set
   - Clear separation of concerns
   - Emphasis on correctness over breadth

2. **Pattern-Based Code Generation:**
   - Decorator and adapter pattern templates
   - How to generate boilerplate safely

3. **Testing Patterns:**
   - Comprehensive test coverage for refactorings
   - Verification strategies for semantic correctness

4. **Resource Schemes:**
   - Custom MCP resource URIs for metrics
   - Discovery mechanisms for tool exploration

#### Comparison to c-sharp-refactor-mcp

| Feature | RefactorMCP | c-sharp-refactor-mcp |
|---------|-------------|----------------------|
| **Refactoring Operations** | 6 core + patterns | 7 core operations |
| **Pattern Generation** | ✅ Decorator, Adapter | ❌ Not implemented |
| **Safe Deletion** | ✅ Dependency checking | ❌ Not implemented |
| **Test Coverage** | ✅ Comprehensive | ⚠️ Basic |
| **Metrics Exposure** | ✅ Custom resources | ❌ Not implemented |
| **Multi-Language** | ❌ C# only | ✅ 8 languages |
| **Extract Class** | ✅ Implemented | ❌ Not implemented |
| **Inline Method** | ✅ Implemented | ❌ Not implemented |

#### Recommendations
- **Adopt:** Pattern-based code generation (decorator, adapter)
- **Improve:** Test coverage using their test patterns
- **Add:** Extract class refactoring
- **Add:** Inline method refactoring (reverse of extract)
- **Consider:** Metrics exposure via MCP resources

---

## Category 2: MCP Server Infrastructure & Patterns

### 3. Awesome DotNET-MCP ⭐⭐⭐
**Repository:** https://github.com/SciSharp/Awesome-DotNET-MCP
**Stars:** 82
**Primary Language:** Markdown
**Status:** Active

#### Description
A curated collection of MCP resources specifically for .NET developers. Provides comprehensive overview of the MCP ecosystem in the .NET world.

#### What's Included
- **MCP Servers:** Directory of existing .NET MCP implementations
- **SDKs:** .NET MCP SDK recommendations and comparisons
- **Tooling:** Build tools, testing frameworks, debugging aids
- **Reference Implementations:** Example servers and clients
- **Best Practices:** Community-contributed patterns

#### Value for c-sharp-refactor-mcp
1. **Ecosystem Positioning:** Understand where your project fits
2. **Alternative Approaches:** Learn from other .NET MCP servers
3. **SDK Recommendations:** Ensure using best-in-class libraries
4. **Community Patterns:** Adopt proven patterns

#### Action Items
- [ ] Review list and identify similar servers to study
- [ ] Compare SDK choices with recommendations
- [ ] Identify integration opportunities (testing tools, etc.)
- [ ] Consider contributing c-sharp-refactor-mcp to this list

---

### 4. MCP Example Servers (Anthropic Official) ⭐⭐⭐⭐⭐
**Repository:** https://modelcontextprotocol.io/examples
**Primary Language:** TypeScript
**Status:** Official Reference

#### Description
Official reference implementations from Anthropic demonstrating core MCP features. These are the **canonical examples** for protocol implementation.

#### Example Servers
1. **Fetch:** HTTP request capabilities
2. **Filesystem:** Safe file system access with path validation
3. **Git:** Repository operations and history querying
4. **Memory:** Persistent state management across sessions
5. **Sequential Thinking:** Multi-step reasoning support
6. **Time:** Date/time utilities

#### Architecture Patterns to Study

**1. Path Security (Filesystem Server):**
```typescript
// Validates all paths against allowed directories
function isPathAllowed(requestedPath: string): boolean {
    const normalized = path.resolve(requestedPath);
    return allowedDirs.some(dir => normalized.startsWith(dir));
}
```

**2. State Management (Memory Server):**
```typescript
// Persistent key-value store across sessions
class MemoryStore {
    private data: Map<string, any>;

    async persist() { /* Save to disk */ }
    async restore() { /* Load from disk */ }
}
```

**3. Resource Schemes (Git Server):**
```typescript
// Custom URI scheme for repository resources
// git://repo-path/history
// git://repo-path/status
```

#### What to Learn
1. **Security Best Practices:**
   - Path validation patterns
   - Input sanitization
   - Error handling

2. **State Management:**
   - Caching strategies
   - Persistence patterns
   - Session handling

3. **Protocol Implementation:**
   - Proper JSON-RPC 2.0 usage
   - Tool registration patterns
   - Resource exposure

4. **Error Handling:**
   - Structured error responses
   - Graceful degradation
   - User-friendly messages

#### Recommendations for c-sharp-refactor-mcp
- **Verify:** Path security implementation matches Filesystem server patterns
- **Consider:** Memory server patterns for caching compiled solutions
- **Adopt:** Resource schemes for exposing project metrics
- **Review:** Error handling patterns for consistency

---

## Category 3: Roslyn & Semantic Analysis Projects

### 5. SonarAnalyzer for .NET ⭐⭐⭐⭐⭐
**Repository:** https://github.com/SonarSource/sonar-dotnet
**Primary Language:** C#
**Status:** Production (SonarQube)

#### Description
A **production-grade Roslyn analyzer** with 470+ C# rules and 210+ VB.NET rules. Powers SonarQube's .NET analysis and represents the largest open-source Roslyn analyzer implementation.

#### Scale & Complexity
- **680+ Total Rules:** Comprehensive coverage of code quality issues
- **Enterprise Usage:** Handles solutions with 1000+ projects
- **Multi-Language:** C# and VB.NET with shared infrastructure
- **Integration:** Works with MSBuild, EditorConfig, third-party analyzers

#### Architecture Highlights
```
SonarAnalyzer
    ├── C# Analyzers (470+)
    ├── VB.NET Analyzers (210+)
    ├── Shared Infrastructure
    │   ├── Symbol Resolution
    │   ├── Control Flow Analysis
    │   ├── Data Flow Analysis
    │   └── Pattern Matching
    └── Integration Layer
        ├── MSBuild
        ├── EditorConfig
        └── SonarQube API
```

#### What to Learn

**1. Large-Scale Rule Implementation:**
```csharp
// Pattern: Analyzer registration
[DiagnosticAnalyzer(LanguageNames.CSharp)]
public class MyAnalyzer : SonarDiagnosticAnalyzer
{
    public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics { get; }

    protected override void Initialize(SonarAnalysisContext context)
    {
        context.RegisterCompilationStartAction(OnCompilationStart);
    }
}
```

**2. Symbol Resolution Patterns:**
```csharp
// Efficient symbol queries
var methodSymbol = semanticModel.GetDeclaredSymbol(methodDeclaration);
var typeSymbol = compilation.GetTypeByMetadataName("System.String");
var references = methodSymbol.DeclaringSyntaxReferences;
```

**3. Performance Optimization:**
- Incremental analysis (only changed files)
- Symbol caching across analyzers
- Compilation-wide state sharing
- Parallel analysis execution

**4. EditorConfig Integration:**
```ini
# Respecting project-specific settings
[*.cs]
dotnet_diagnostic.S1234.severity = error
```

**5. Control Flow Analysis:**
```csharp
// Complex flow analysis for null checks, unreachable code, etc.
var cfg = ControlFlowGraph.Create(methodBody);
foreach (var block in cfg.Blocks)
{
    // Analyze reachability, null state, etc.
}
```

#### Comparison to c-sharp-refactor-mcp

| Feature | SonarAnalyzer | c-sharp-refactor-mcp |
|---------|---------------|----------------------|
| **Scale** | 680+ rules | 7 refactorings |
| **Performance** | Optimized for large solutions | Some optimization (LRU cache) |
| **Symbol Resolution** | Highly optimized patterns | Basic usage |
| **EditorConfig** | ✅ Full integration | ❌ Not implemented |
| **Control Flow** | ✅ Advanced CFG analysis | ❌ Not used |
| **Third-Party Integration** | ✅ Imports other analyzers | ❌ Not applicable |

#### Recommendations
- **Study:** Symbol resolution optimization patterns
- **Adopt:** EditorConfig integration for project-specific settings
- **Consider:** Control flow analysis for more complex refactorings
- **Learn:** Performance optimization techniques for large solutions
- **Evaluate:** Incremental analysis for changed files only

---

### 6. Roslynator ⭐⭐⭐⭐⭐
**Repository:** https://josefpihrt.github.io/docs/roslynator/
**Primary Language:** C#
**Status:** Active (200+ refactorings)

#### Description
The most **comprehensive Roslyn-based refactoring library** available. Provides 200+ refactorings, 500+ analyzers, and extensive code fixes for C#.

#### Scale & Features
- **200+ Refactorings:** Extract, inline, move, rename, convert patterns
- **500+ Analyzers:** Code quality, performance, style
- **100+ Code Fixes:** Automatic corrections
- **IDE Integration:** Visual Studio, VS Code, Rider

#### Architecture Highlights
```
Roslynator
    ├── Refactorings (200+)
    │   ├── Metadata (XML)
    │   └── Implementation (C#)
    ├── Analyzers (500+)
    │   ├── Code Quality
    │   ├── Performance
    │   └── Style
    ├── Code Fixes (100+)
    └── Code Generation
        └── Metadata → Code Generator
```

#### What to Learn

**1. Metadata-Driven Architecture:**
```xml
<!-- Refactoring metadata -->
<Refactoring Id="RR0001"
             Title="Extract Method"
             Category="Method"
             Scope="Selection">
    <Description>Extracts selected code into a new method.</Description>
    <Syntax>
        <Node Kind="Block" />
    </Syntax>
</Refactoring>
```

**2. Code Generation from Metadata:**
```csharp
// Automatically generates:
// - Documentation
// - Test scaffolding
// - Tool registration
// - IDE integration code
```

**3. Comprehensive Refactoring Patterns:**

| Category | Examples |
|----------|----------|
| **Extract** | Method, Property, Field, Local, Interface |
| **Inline** | Method, Property, Local, Constant |
| **Move** | Method to class, Type to file, Member |
| **Convert** | Pattern matching, LINQ, Loops, Conditionals |
| **Simplify** | Boolean expressions, Null checks, LINQ queries |
| **Add** | Parameter, Exception filter, Using directive |

**4. Testing Patterns:**
```csharp
// Pattern for testing refactorings
[Fact]
public async Task ExtractMethod_BasicScenario()
{
    var source = @"
class C
{
    void M()
    {
        [|int x = 1;
        Console.WriteLine(x);|]
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
        Console.WriteLine(x);
    }
}";

    await VerifyRefactoringAsync(source, expected);
}
```

#### Comparison to c-sharp-refactor-mcp

| Feature | Roslynator | c-sharp-refactor-mcp |
|---------|------------|----------------------|
| **Refactorings** | 200+ | 7 core |
| **Metadata-Driven** | ✅ XML metadata | ❌ Hard-coded |
| **Code Generation** | ✅ Automatic | ❌ Manual |
| **Testing** | ✅ Comprehensive | ⚠️ Basic |
| **IDE Integration** | ✅ VS, VS Code, Rider | ✅ MCP protocol (indirect) |
| **Inline Method** | ✅ Implemented | ❌ Not implemented |
| **Convert Patterns** | ✅ 50+ conversions | ❌ Not implemented |
| **Multi-Language** | ❌ C# only | ✅ 8 languages |

#### Recommendations
- **Consider:** Metadata-driven refactoring architecture for scalability
- **Add:** Inline method refactoring (reverse of extract)
- **Study:** Convert pattern refactorings (foreach → LINQ, etc.)
- **Adopt:** Comprehensive testing patterns
- **Evaluate:** Code generation for reducing boilerplate

---

### 7. Metalama (PostSharp Technologies) ⭐⭐⭐⭐
**Repository:** https://metalama.net
**Primary Language:** C#
**Status:** Commercial (with free tier)

#### Description
A modern **meta-programming framework** for C# that provides aspect-oriented programming (AOP), compile-time code generation, and architecture verification. Represents the **most advanced** code transformation tooling for C#.

#### Key Capabilities
1. **Aspect-Oriented Programming:** Cross-cutting concerns (logging, caching, etc.)
2. **Compile-Time Code Generation:** Using C# templates
3. **Architecture Validation:** Enforcing architectural rules at compile-time
4. **IDE Integration:** CodeLens hints, diff visualization
5. **Compile-Time LINQ:** Querying code models with LINQ-style APIs

#### Architecture Highlights
```
Metalama Framework
    ├── Aspect System
    │   ├── Method Aspects (logging, caching)
    │   ├── Property Aspects (validation, notification)
    │   └── Type Aspects (serialization)
    ├── Code Generation
    │   ├── T# Templates (C# with metaprogramming)
    │   └── Roslyn SyntaxFactory wrapping
    ├── Architecture Validation
    │   ├── Naming conventions
    │   ├── Dependency rules
    │   └── Pattern enforcement
    └── IDE Integration
        ├── CodeLens (shows applied aspects)
        └── Diff View (original vs. generated)
```

#### What to Learn

**1. Aspect-Oriented Programming:**
```csharp
// Apply logging to all public methods
[Log]
public class UserService
{
    public void CreateUser(string name) { ... }  // Automatically logged
}

// Aspect implementation
public class LogAttribute : MethodAspect
{
    public override void OnEntry(MethodExecutionArgs args)
    {
        Console.WriteLine($"Entering {args.Method.Name}");
    }
}
```

**2. Compile-Time Code Generation:**
```csharp
// Template for property generation
[Template]
public dynamic ImplementProperty(FieldInfo field)
{
    return meta.Proceed(); // Accesses meta-model
}
```

**3. Architecture Validation:**
```csharp
// Enforce layering rules
[assembly: VerifyArchitecture]
[assembly: LayerRule("UI", CanReference = "Business")]
[assembly: LayerRule("Business", CanReference = "Data")]
```

**4. Compile-Time LINQ:**
```csharp
// Query code model
var publicMethods = compilation
    .AllTypes
    .SelectMany(t => t.Methods)
    .Where(m => m.Accessibility == Accessibility.Public);
```

**5. IDE Integration:**
- CodeLens hints show which aspects are applied
- Diff view shows original code vs. generated code
- Real-time validation errors

#### Advanced Concepts

**Aspect Composition:**
```csharp
[Log]
[Cache]
[Retry(MaxAttempts = 3)]
public async Task<User> GetUserAsync(int id) { ... }
// Aspects are composed in order: Retry → Cache → Log → Method
```

**Compile-Time Validation:**
```csharp
// Ensures all async methods end with "Async"
public class AsyncNamingRule : CompilationRule
{
    public override void Validate(IDeclaration declaration)
    {
        if (declaration is IMethod method &&
            method.ReturnType.Is(typeof(Task)) &&
            !method.Name.EndsWith("Async"))
        {
            ReportError($"{method.Name} should end with 'Async'");
        }
    }
}
```

#### Comparison to c-sharp-refactor-mcp

| Feature | Metalama | c-sharp-refactor-mcp |
|---------|----------|----------------------|
| **Code Transformation** | ✅ Advanced (AOP) | ✅ Basic (refactoring) |
| **Compile-Time** | ✅ Compile-time generation | ⚠️ Runtime refactoring |
| **Templates** | ✅ T# template language | ❌ Hard-coded |
| **Architecture Rules** | ✅ Validation framework | ❌ Not implemented |
| **IDE Integration** | ✅ CodeLens, diff view | ✅ MCP protocol |
| **LINQ-style Queries** | ✅ Compile-time LINQ | ❌ Not implemented |
| **Multi-Language** | ❌ C# only | ✅ 8 languages |

#### Recommendations
- **Study:** AOP patterns for potential "apply pattern" refactorings
- **Consider:** Template-based code generation approach
- **Evaluate:** Architecture validation as additional MCP tools
- **Learn:** Compile-time LINQ patterns for code querying
- **Adopt:** IDE integration patterns (though MCP provides alternative)

---

## Category 4: Code Analysis & Quality Tools

### 8. OpenRewrite ⭐⭐⭐⭐
**Repository:** https://github.com/openrewrite/rewrite
**Primary Language:** Java
**Status:** Active (Netflix, Uber, others use it)

#### Description
An **automated refactoring ecosystem** designed for mass code transformations across repositories. Focuses on framework migrations, security fixes, and standardization at scale.

#### Key Features
- **Recipe-Based Refactoring:** Composable refactoring recipes
- **Large-Scale Transformations:** Handles 1000+ project migrations
- **Framework Migrations:** Common patterns (Spring Boot upgrades, Java version updates)
- **Cross-Repository:** Operates across monorepos and multi-repo setups
- **Semantic Analysis:** Type-aware transformations

#### Architecture Highlights
```
OpenRewrite
    ├── Recipe System
    │   ├── Atomic Recipes (single transformation)
    │   └── Composite Recipes (multiple steps)
    ├── Visitors
    │   ├── Java Visitor
    │   ├── XML Visitor (pom.xml, etc.)
    │   └── YAML Visitor (configs)
    ├── Search & Analyze
    │   ├── Find patterns
    │   └── Generate reports
    └── Apply & Test
        ├── Apply transformations
        └── Verify with tests
```

#### What to Learn

**1. Recipe-Based Architecture:**
```java
// Atomic recipe
public class ChangeMethodName extends Recipe {
    @Override
    public TreeVisitor<?, ExecutionContext> getVisitor() {
        return new JavaIsoVisitor<>() {
            @Override
            public J.MethodInvocation visitMethodInvocation(
                J.MethodInvocation method,
                ExecutionContext ctx
            ) {
                if (method.getSimpleName().equals("oldMethod")) {
                    return method.withName(
                        method.getName().withSimpleName("newMethod")
                    );
                }
                return method;
            }
        };
    }
}
```

**2. Composite Recipes:**
```yaml
# Recipe composition
name: com.example.MigrateToNewFramework
displayName: Migrate to New Framework
recipeList:
  - com.example.UpdateDependencies
  - com.example.RenamePackages
  - com.example.RefactorAPIs
  - com.example.UpdateConfigs
```

**3. Large-Scale Transformation Patterns:**
- **Search First:** Identify all affected locations
- **Generate Report:** Show impact analysis
- **Apply Atomically:** All-or-nothing transformation
- **Verify:** Run tests to confirm success

**4. Framework Migration Recipes:**
```yaml
# Spring Boot 2.x → 3.x migration
name: org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0
recipeList:
  - org.openrewrite.java.migrate.UpgradeToJava17
  - org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0_buildFile
  - org.openrewrite.java.spring.boot3.SpringBootProperties_3_0
```

#### Comparison to c-sharp-refactor-mcp

| Feature | OpenRewrite | c-sharp-refactor-mcp |
|---------|-------------|----------------------|
| **Recipe System** | ✅ Composable recipes | ❌ Single operations |
| **Large-Scale** | ✅ 1000+ projects | ⚠️ Single solution focus |
| **Framework Migration** | ✅ Pre-built recipes | ❌ Not implemented |
| **Cross-Repository** | ✅ Supported | ❌ Not implemented |
| **Impact Analysis** | ✅ Pre-transformation reports | ⚠️ Basic (find references) |
| **Multi-Language** | ⚠️ Java, XML, YAML | ✅ 8 languages |

#### Recommendations
- **Consider:** Recipe-based architecture for composable refactorings
- **Add:** Impact analysis tools (show all changes before applying)
- **Evaluate:** Framework migration recipes (e.g., .NET Framework → .NET 8)
- **Study:** Cross-repository refactoring patterns
- **Adopt:** Search-first, apply-second workflow

---

### 9. CodeQL (GitHub) ⭐⭐⭐⭐⭐
**Repository:** https://codeql.github.com
**Primary Language:** QL (query language)
**Status:** Production (GitHub Advanced Security)

#### Description
GitHub's **semantic code analysis engine** used for security vulnerability detection. Treats code as data and allows querying with a declarative language (QL).

#### Key Features
- **Code as Data:** Query code like a database
- **Multi-Language:** 9+ languages (C#, Java, JavaScript, Python, Go, C++, Ruby, etc.)
- **Security Focus:** Pre-built queries for OWASP Top 10
- **Semantic Analysis:** Full type awareness, control flow, data flow
- **IDE Integration:** VS Code extension

#### Architecture Highlights
```
CodeQL
    ├── Extractors (per language)
    │   ├── Parse source code
    │   └── Build database (facts)
    ├── Query Language (QL)
    │   ├── Declarative (SQL-like)
    │   └── Logic programming
    ├── Standard Library
    │   ├── AST queries
    │   ├── Data flow
    │   └── Taint tracking
    └── Query Packs
        ├── Security queries
        └── Code quality queries
```

#### What to Learn

**1. Code as Data Philosophy:**
```ql
// Find all methods that don't handle exceptions
import csharp

from Method m
where not exists(TryStmt try | try.getEnclosingCallable() = m)
  and m.getNumberOfLinesOfCode() > 20
select m, "Method " + m.getName() + " doesn't handle exceptions"
```

**2. Data Flow Analysis:**
```ql
// Find SQL injection vulnerabilities
import csharp
import semmle.code.csharp.security.dataflow.SqlInjection

from SqlInjectionSink sink, SqlInjectionSource source
where source.flowsTo(sink)
select sink, "SQL injection from $@.", source, "user input"
```

**3. Taint Tracking:**
```ql
// Track untrusted data flow
class UntrustedDataFlow extends TaintTracking::Configuration {
    override predicate isSource(DataFlow::Node source) {
        source instanceof RemoteFlowSource
    }

    override predicate isSink(DataFlow::Node sink) {
        sink instanceof SqlSink
    }
}
```

**4. Multi-Language Support Strategy:**
- **Per-Language Extractors:** Parse and create database
- **Shared Query Infrastructure:** Common patterns across languages
- **Language-Specific Libraries:** AST abstractions per language

#### Comparison to c-sharp-refactor-mcp

| Feature | CodeQL | c-sharp-refactor-mcp |
|---------|--------|----------------------|
| **Query Language** | ✅ Declarative QL | ❌ Imperative API calls |
| **Code as Data** | ✅ Database approach | ⚠️ Workspace approach |
| **Security Focus** | ✅ Vulnerability detection | ❌ Not implemented |
| **Data Flow** | ✅ Advanced taint tracking | ⚠️ Basic (extract method only) |
| **Multi-Language** | ✅ 9+ languages | ✅ 8 languages |
| **Pre-Built Queries** | ✅ 1000+ queries | ❌ 7 operations |

#### Recommendations
- **Study:** Multi-language architecture (extractors + shared infrastructure)
- **Consider:** Query-based approach for code analysis tools
- **Add:** Security-focused analysis tools (SQL injection detection, XSS, etc.)
- **Learn:** Data flow analysis patterns for complex refactorings
- **Evaluate:** Taint tracking for security refactorings

---

## Category 5: LSP & Multi-Language Server Implementations

### 10. OmniSharp/omnisharp-roslyn ⭐⭐⭐⭐⭐
**Repository:** https://github.com/OmniSharp/omnisharp-roslyn
**Primary Language:** C#
**Status:** Production (powers VS Code C#)

#### Description
A **production LSP server** for C# that powers IntelliSense across multiple editors (VS Code, Vim, Emacs, etc.). Represents the most mature C# LSP implementation.

#### Key Features
- **Multi-Editor Support:** VS Code, Vim, Emacs, Sublime, Atom
- **Full Roslyn Integration:** Semantic analysis, completion, refactoring
- **MSBuild Workspace:** Handles .NET projects at scale
- **Performance Optimizations:** Caching, incremental analysis
- **Rich Refactoring:** Rename, extract method, organize imports

#### Architecture Highlights
```
OmniSharp-Roslyn
    ├── LSP Server (HTTP + Stdio)
    ├── Roslyn Workspace
    │   ├── MSBuild integration
    │   └── Project system
    ├── Handlers
    │   ├── Completion
    │   ├── Hover
    │   ├── Rename
    │   ├── Find References
    │   └── Code Actions
    └── Performance
        ├── Incremental compilation
        └── Background analysis
```

#### What to Learn

**1. Multi-Editor Support Strategy:**
- Abstract protocol layer (LSP)
- Editor-specific quirks handled in thin adapters
- Core logic shared across all editors

**2. MSBuild Workspace Integration:**
```csharp
// Efficient project loading
var workspace = MSBuildWorkspace.Create();
var solution = await workspace.OpenSolutionAsync(solutionPath);

// Incremental updates
workspace.WorkspaceChanged += OnWorkspaceChanged;
```

**3. Performance Challenges & Solutions:**
- **Problem:** Large solutions (1000+ projects) slow to load
- **Solution 1:** Lazy project loading (only load referenced projects)
- **Solution 2:** Background compilation
- **Solution 3:** Incremental analysis (only changed files)

**4. Rename Options:**
```csharp
// Sophisticated rename with options
var options = new RenameOptions
{
    RenameOverloads = true,
    RenameInComments = false,
    RenameInStrings = false
};
```

**5. Code Actions (Quick Fixes):**
```csharp
// Expose Roslyn code fixes via LSP
var codeActions = await GetCodeActionsAsync(document, range);
// Maps Roslyn CodeAction → LSP CodeAction
```

#### Comparison to c-sharp-refactor-mcp

| Feature | OmniSharp | c-sharp-refactor-mcp |
|---------|-----------|----------------------|
| **Protocol** | LSP (HTTP + Stdio) | MCP (Stdio) |
| **Editor Support** | VS Code, Vim, Emacs | MCP clients (Claude, Copilot) |
| **Performance** | ✅ Highly optimized | ⚠️ Some optimization |
| **Incremental Analysis** | ✅ Yes | ❌ Full re-analysis |
| **Code Actions** | ✅ All Roslyn fixes | ⚠️ Limited |
| **Rename Options** | ✅ Advanced options | ⚠️ Basic rename |
| **Multi-Language** | ❌ C# only | ✅ 8 languages |

#### Recommendations
- **Study:** Incremental analysis patterns (only changed files)
- **Adopt:** Rename options (comments, strings, overloads)
- **Learn:** Performance optimization for large solutions
- **Consider:** Code actions as MCP tools (quick fixes)
- **Evaluate:** Lazy project loading strategy

---

### 11. Pascal Language Server ⭐⭐⭐
**Repository:** https://github.com/genericptr/pascal-language-server
**Primary Language:** Pascal
**Status:** Active

#### Description
A clean example of **LSP implementation** for a less-common language. Demonstrates wrapping existing code analysis tools (Lazarus CodeTools) with LSP.

#### What to Learn

**1. LSP Server Architecture:**
```pascal
// Clean separation of concerns
TLSPServer = class
    FTransport: TJSONRPCTransport;
    FCodeTools: TCodeToolManager;

    procedure HandleInitialize(params: TInitializeParams);
    procedure HandleTextDocumentDidOpen(params: TDidOpenParams);
    procedure HandleTextDocumentCompletion(params: TCompletionParams);
end;
```

**2. Backend Integration Pattern:**
```
LSP Server (thin layer)
    ↓
Lazarus CodeTools (thick logic)
    ↓
Pascal Parser & Semantic Analyzer
```

**3. Method Implementation Examples:**
- `textDocument/completion` → Code completion
- `textDocument/hover` → Symbol information
- `textDocument/definition` → Go to definition
- `textDocument/references` → Find all references

#### Comparison to c-sharp-refactor-mcp

| Feature | Pascal LSP | c-sharp-refactor-mcp |
|---------|------------|----------------------|
| **Protocol** | LSP | MCP |
| **Backend** | Lazarus CodeTools | Roslyn + LSP servers |
| **Architecture** | Thin wrapper | Direct integration |
| **Language Support** | Pascal only | 8 languages |

#### Recommendations
- **Study:** Clean LSP implementation patterns
- **Learn:** Backend integration strategy (thin wrapper vs. direct)
- **Reference:** For adding new language providers

---

## Category 6: AST Manipulation & Code Generation

### 12. NSwag ⭐⭐⭐⭐
**Repository:** https://github.com/RicoSuter/NSwag
**Primary Language:** C#
**Status:** Active (enterprise usage)

#### Description
A comprehensive toolchain for generating code from OpenAPI/Swagger specifications. Demonstrates **large-scale code generation** patterns in C#.

#### Key Features
- **Multi-Target Generation:** C#, TypeScript, Angular, React
- **Template System:** Liquid templates for code generation
- **Full-Stack Support:** Client generation + server stubs
- **Customization:** Extensible template system

#### Architecture Highlights
```
NSwag
    ├── OpenAPI Parser
    │   └── Swagger/OpenAPI spec → Model
    ├── Code Generators
    │   ├── CSharp Client
    │   ├── TypeScript Client
    │   ├── Angular Client
    │   └── ASP.NET Server
    ├── Template Engine (Liquid)
    │   └── Templates with placeholders
    └── Customization
        └── Template overrides
```

#### What to Learn

**1. Code Generation Pipeline:**
```
OpenAPI Spec → Parse → Internal Model → Apply Template → Generated Code
```

**2. Template System:**
```liquid
// Liquid template example
{% for operation in operations %}
public async Task<{{operation.ResponseType}}> {{operation.MethodName}}Async(
    {% for param in operation.Parameters %}
    {{param.Type}} {{param.Name}}{% if not forloop.last %}, {% endif %}
    {% endfor %}
)
{
    // Generated implementation
}
{% endfor %}
```

**3. Large-Scale Code Generation:**
- Generates complete client libraries (1000+ lines)
- Handles complex type hierarchies
- Manages dependencies and imports

**4. Multi-Target Strategy:**
- Shared internal model
- Per-language code generators
- Template-based customization

#### Comparison to c-sharp-refactor-mcp

| Feature | NSwag | c-sharp-refactor-mcp |
|---------|-------|----------------------|
| **Code Generation** | ✅ From specs | ⚠️ From refactoring |
| **Templates** | ✅ Liquid templates | ❌ Hard-coded |
| **Multi-Target** | ✅ C#, TS, Angular | ✅ 8 languages (different context) |
| **Large-Scale** | ✅ Complete libraries | ⚠️ Single operations |
| **Customization** | ✅ Template overrides | ❌ Not implemented |

#### Recommendations
- **Study:** Template-based code generation approach
- **Consider:** Template system for pattern generation (decorators, adapters)
- **Learn:** Large-scale code generation patterns
- **Evaluate:** Customization mechanisms for user-specific needs

---

### 13. MrKWatkins/Ast ⭐⭐⭐
**Repository:** https://github.com/MrKWatkins/Ast
**Primary Language:** C#
**Status:** Active

#### Description
A **generic AST library** for building and manipulating abstract syntax trees in C#. Provides visitor patterns, tree walking utilities, and error tracking.

#### Key Features
- **Generic Node Hierarchy:** Type-safe tree structures
- **Visitor Pattern:** Built-in support for tree traversal
- **Source Position Tracking:** Maps nodes to source locations
- **Error Reporting:** Hierarchical error and warning system
- **Immutable Trees:** Safe concurrent access

#### Architecture Highlights
```csharp
// Generic AST node
public abstract class Node<TNode> where TNode : Node<TNode>
{
    public TNode? Parent { get; }
    public IEnumerable<TNode> Children { get; }
    public SourcePosition Position { get; set; }

    public IEnumerable<TNode> DescendantsAndSelf();
    public IEnumerable<TNode> Ancestors();
}

// Visitor pattern
public abstract class Visitor<TNode> where TNode : Node<TNode>
{
    public virtual void Visit(TNode node) { ... }
    protected virtual void DefaultVisit(TNode node) { ... }
}
```

#### What to Learn

**1. AST Data Structure Design:**
```csharp
// Strongly-typed tree
public class ExpressionNode : Node<ExpressionNode>
{
    public ExpressionType Type { get; init; }
}

public class BinaryExpression : ExpressionNode
{
    public ExpressionNode Left => Children[0];
    public ExpressionNode Right => Children[1];
    public BinaryOperator Operator { get; init; }
}
```

**2. Tree Walking Utilities:**
```csharp
// Convenient LINQ-style queries
var allMethodCalls = root
    .DescendantsAndSelf()
    .OfType<MethodCallNode>();

var firstError = root
    .DescendantsAndSelf()
    .FirstOrDefault(n => n.HasErrors);
```

**3. Source Position Tracking:**
```csharp
public class SourcePosition
{
    public int Line { get; init; }
    public int Column { get; init; }
    public int Length { get; init; }
    public string? FilePath { get; init; }
}
```

**4. Error Reporting:**
```csharp
// Hierarchical errors
public class ErrorInfo
{
    public ErrorLevel Level { get; init; } // Error, Warning, Info
    public string Message { get; init; }
    public SourcePosition Position { get; init; }
}

node.AddError("Invalid syntax", ErrorLevel.Error);
var allErrors = root.DescendantsAndSelf().SelectMany(n => n.Errors);
```

#### Comparison to c-sharp-refactor-mcp

| Feature | MrKWatkins/Ast | c-sharp-refactor-mcp |
|---------|----------------|----------------------|
| **AST Abstraction** | ✅ Generic library | ⚠️ Roslyn-specific |
| **Visitor Pattern** | ✅ Built-in | ⚠️ Custom traversal |
| **Source Tracking** | ✅ Built-in | ✅ Roslyn provides |
| **Error Hierarchy** | ✅ Custom system | ✅ Roslyn diagnostics |
| **Immutability** | ✅ Yes | ✅ Roslyn is immutable |

#### Recommendations
- **Study:** Generic AST patterns (applicable beyond Roslyn)
- **Learn:** Visitor pattern best practices
- **Reference:** For building custom AST transformations
- **Consider:** Error tracking patterns for refactoring operations

---

## Category 7: Multi-Language Analysis

### 14. ANTLR-NG (Next Generation ANTLR) ⭐⭐⭐⭐
**Repository:** https://github.com/mike-lischke/antlr-ng
**Primary Language:** TypeScript
**Status:** Active (ANTLR4 successor)

#### Description
A **parser generator** that creates parsers from grammar files across multiple target languages. Demonstrates grammar-based approach to multi-language support.

#### Key Features
- **Multi-Language Targets:** C++, C#, Java, JavaScript, Python, Go, Swift
- **Grammar-Driven:** Define syntax once, generate parsers for all targets
- **Parse Tree Generation:** Automatic AST creation
- **Visitor & Listener:** Dual patterns for tree traversal
- **Error Recovery:** Sophisticated error handling

#### Architecture Highlights
```
ANTLR-NG
    ├── Grammar Definition (.g4 files)
    │   ├── Lexer rules (tokens)
    │   └── Parser rules (syntax)
    ├── Code Generator
    │   ├── C++ generator
    │   ├── C# generator
    │   ├── Java generator
    │   └── [others...]
    ├── Runtime Libraries (per target)
    │   ├── Lexer base class
    │   ├── Parser base class
    │   └── Parse tree classes
    └── Tree Walkers
        ├── Visitor pattern
        └── Listener pattern
```

#### What to Learn

**1. Grammar Definition:**
```antlr
// C# grammar example
grammar CSharp;

compilationUnit
    : usingDirective* namespaceMemberDeclaration* EOF
    ;

usingDirective
    : 'using' identifier ('.' identifier)* ';'
    ;

classDeclaration
    : 'class' identifier '{' classMemberDeclaration* '}'
    ;
```

**2. Multi-Language Support Strategy:**
- **Grammar is language-agnostic**
- **Target-specific code generation**
- **Shared runtime concepts** (Lexer, Parser, Parse Tree)
- **Per-language idioms** in generated code

**3. Visitor Pattern:**
```csharp
// Auto-generated visitor
public class CSharpBaseVisitor<T> : AbstractParseTreeVisitor<T>
{
    public virtual T VisitCompilationUnit(CompilationUnitContext context) { ... }
    public virtual T VisitClassDeclaration(ClassDeclarationContext context) { ... }
}

// Custom visitor
public class MyAnalyzer : CSharpBaseVisitor<int>
{
    public override int VisitClassDeclaration(ClassDeclarationContext context)
    {
        Console.WriteLine($"Found class: {context.identifier().GetText()}");
        return base.VisitClassDeclaration(context);
    }
}
```

**4. Error Recovery:**
```antlr
// Error handling rules
@parser::members {
    @Override
    public void recover(RecognitionException e) {
        // Custom error recovery
    }
}
```

#### Comparison to c-sharp-refactor-mcp

| Feature | ANTLR-NG | c-sharp-refactor-mcp |
|---------|----------|----------------------|
| **Multi-Language** | ✅ Grammar-based | ✅ Provider-based |
| **Approach** | Parse trees | Semantic models |
| **Grammar Definition** | ✅ Declarative | ❌ Per-provider |
| **Code Generation** | ✅ Multi-target | ❌ Not applicable |
| **Semantic Analysis** | ⚠️ Parse trees only | ✅ Full semantics |
| **Refactoring** | ❌ Not built-in | ✅ Core feature |

#### Recommendations
- **Consider:** Grammar-based approach for simpler language support
- **Study:** Multi-language architecture (shared grammar + target-specific generation)
- **Evaluate:** For languages without good LSP servers
- **Note:** Parse trees lack semantic information (types, symbols) needed for safe refactoring

---

### 15. Semantic-Analyzer-RS ⭐⭐
**Repository:** https://github.com/mrLSD/semantic-analyzer-rs
**Primary Language:** Rust
**Status:** Educational

#### Description
A Rust library demonstrating **semantic analysis concepts** including scope checking, type checking, and symbol tables. Good educational resource for understanding semantic analysis fundamentals.

#### Key Concepts

**1. Name Binding & Scope Checking:**
```rust
pub struct ScopeChecker {
    scopes: Vec<SymbolTable>,
}

impl ScopeChecker {
    pub fn enter_scope(&mut self) {
        self.scopes.push(SymbolTable::new());
    }

    pub fn exit_scope(&mut self) {
        self.scopes.pop();
    }

    pub fn declare(&mut self, name: String, symbol: Symbol) -> Result<(), Error> {
        // Check for redeclaration in current scope
        if self.current_scope().contains(&name) {
            return Err(Error::Redeclaration);
        }
        self.current_scope_mut().insert(name, symbol);
        Ok(())
    }

    pub fn lookup(&self, name: &str) -> Option<&Symbol> {
        // Search from innermost to outermost scope
        self.scopes.iter().rev().find_map(|scope| scope.get(name))
    }
}
```

**2. Symbol Table Implementation:**
```rust
pub struct SymbolTable {
    symbols: HashMap<String, Symbol>,
}

pub struct Symbol {
    name: String,
    symbol_type: SymbolType,
    scope_level: usize,
}
```

**3. Type Checking:**
```rust
pub fn check_binary_op(op: BinaryOp, left: Type, right: Type) -> Result<Type, Error> {
    match (op, left, right) {
        (BinaryOp::Add, Type::Int, Type::Int) => Ok(Type::Int),
        (BinaryOp::Add, Type::String, Type::String) => Ok(Type::String),
        _ => Err(Error::TypeMismatch),
    }
}
```

**4. Flow Control Analysis:**
```rust
pub fn check_return_paths(function: &FunctionNode) -> Result<(), Error> {
    if !function.return_type.is_void() {
        if !all_paths_return(function) {
            return Err(Error::MissingReturn);
        }
    }
    Ok(())
}
```

#### What to Learn

**1. Language-Agnostic Semantic Analysis Patterns:**
- Scope management (enter/exit scope)
- Symbol table (hierarchical lookup)
- Type checking (operand compatibility)
- Flow control validation

**2. Symbol Resolution:**
- Name binding in nested scopes
- Shadowing rules
- Forward references

**3. Error Reporting:**
- Type mismatches
- Undefined symbols
- Redeclarations
- Control flow issues

#### Comparison to c-sharp-refactor-mcp

| Feature | Semantic-Analyzer-RS | c-sharp-refactor-mcp |
|---------|---------------------|----------------------|
| **Semantic Analysis** | ✅ Educational | ✅ Production (Roslyn/LSP) |
| **Scope Checking** | ✅ Manual | ✅ Roslyn/LSP provide |
| **Type Checking** | ✅ Manual | ✅ Roslyn/LSP provide |
| **Symbol Tables** | ✅ Custom | ✅ Roslyn/LSP provide |
| **Practical Use** | ❌ Educational | ✅ Production |

#### Recommendations
- **Study:** For understanding semantic analysis fundamentals
- **Reference:** When implementing custom language support
- **Learn:** Scope checking patterns (useful for validating refactorings)
- **Note:** Roslyn/LSP already provide these capabilities for supported languages

---

## Strategic Analysis & Recommendations

### Positioning in the Ecosystem

**c-sharp-refactor-mcp Unique Value Proposition:**
1. **Only multi-language MCP refactoring server** (8 languages)
2. **Hybrid architecture** (Roslyn + LSP) leveraging best tools per language
3. **Unified API** across all languages via MCP protocol

**Direct Competitors:**
- SharpToolsMCP (C# only, more features)
- RefactorMCP (C# only, focused approach)

**Competitive Advantages:**
- ✅ Multi-language support (8 vs. 1)
- ✅ Unified API across languages
- ✅ LSP integration for non-.NET languages

**Competitive Disadvantages:**
- ❌ Fewer refactoring operations than RefactorMCP
- ❌ Fewer advanced features than SharpToolsMCP (git, complexity, token optimization)
- ❌ LSP providers have limited capabilities vs. Roslyn providers

---

## Priority Recommendations by Category

### 🔥 Critical (Implement First)

**From SharpToolsMCP:**
1. **Token Optimization:** Reduce context sent to AI agents
   - Remove indentation from code snippets
   - FQN-based symbol navigation
   - Complexity-adjusted resolution depth

2. **Git Integration:** Automated commit/rollback workflow
   - Branch creation per refactoring session
   - Automatic commits with descriptive messages
   - Undo functionality for failed operations

**From RefactorMCP:**
3. **Pattern-Based Code Generation:**
   - Decorator pattern generation
   - Adapter pattern generation
   - Other GoF patterns

4. **Improved Test Coverage:**
   - Comprehensive refactoring tests
   - Follow RefactorMCP test patterns

**From Roslynator:**
5. **Additional Refactorings:**
   - Inline method (reverse of extract)
   - Extract class
   - Move method to class
   - Convert patterns (foreach → LINQ, etc.)

---

### ⚡ High Priority (Next Phase)

**From SonarAnalyzer:**
6. **EditorConfig Integration:**
   - Respect project-specific settings
   - Configurable refactoring behavior

7. **Performance Optimization:**
   - Incremental analysis (only changed files)
   - Symbol caching across operations
   - Parallel analysis execution

**From OmniSharp:**
8. **Rename Options:**
   - Rename in comments (optional)
   - Rename in strings (optional)
   - Rename overloads (optional)

**From OpenRewrite:**
9. **Impact Analysis:**
   - Pre-transformation reports
   - Show all changes before applying
   - Risk assessment

10. **Recipe System:**
    - Composable refactoring recipes
    - Multi-step transformations
    - Framework migration support

---

### 📊 Medium Priority (Future Enhancement)

**From Metalama:**
11. **Architecture Validation:**
    - Naming convention enforcement
    - Dependency rules
    - Pattern enforcement

**From CodeQL:**
12. **Security Analysis:**
    - SQL injection detection
    - XSS detection
    - Security-focused refactorings

**From NSwag:**
13. **Template System:**
    - User-customizable templates
    - Pattern generation templates
    - Code generation framework

**From MCP Examples:**
14. **Resource Schemes:**
    - Expose project metrics
    - Custom resource URIs
    - Improved discovery

---

### 🔮 Long-Term (Research)

**From ANTLR-NG:**
15. **Grammar-Based Language Support:**
    - Alternative to LSP for simpler languages
    - Faster integration for new languages

**From OpenRewrite:**
16. **Cross-Repository Operations:**
    - Multi-solution refactoring
    - Monorepo support

**From Metalama:**
17. **Query-Based Analysis:**
    - LINQ-style code queries
    - More flexible analysis tools

---

## Implementation Roadmap

### Phase 1: Core Improvements (Months 1-2)
- Token optimization (SharpToolsMCP patterns)
- Git integration
- Pattern generation (decorator, adapter)
- Improved test coverage

### Phase 2: Advanced Features (Months 3-4)
- Additional refactorings (inline, extract class, move method)
- Rename options
- Impact analysis
- EditorConfig integration

### Phase 3: Scale & Performance (Months 5-6)
- Incremental analysis
- Recipe system for composable refactorings
- Performance optimization for large solutions

### Phase 4: Enterprise Features (Months 7+)
- Architecture validation
- Security analysis
- Template system
- Cross-repository operations

---

## Conclusion

The **c-sharp-refactor-mcp** project has a strong foundation with its unique multi-language support and hybrid architecture. By learning from the 17 projects analyzed in this report, the project can evolve from a solid multi-language refactoring server into a **comprehensive AI-driven development platform**.

**Key Takeaways:**
1. **Differentiate on multi-language support** (already unique)
2. **Match competitors on C# features** (git, token optimization, complexity)
3. **Improve LSP provider capabilities** (diagnostics, more refactorings)
4. **Scale to enterprise** (performance, security, validation)

The recommendations are prioritized based on:
- Competitive necessity (matching SharpToolsMCP, RefactorMCP)
- User value (git integration, impact analysis)
- Technical complexity vs. benefit
- Ecosystem trends (security, architecture validation)

By systematically implementing these recommendations, **c-sharp-refactor-mcp** can become the **go-to MCP server for multi-language refactoring** in the AI-driven development ecosystem.
