# LSP Implementation Research: Missing Features

Research findings for implementing missing features in the Python MCP rewrite:
1. publishDiagnostics notification handling
2. Extract method refactoring
3. Project-level operations

## 1. Fix LSP Diagnostics (publishDiagnostics Listener)

### Current Issue
The LSP client currently returns empty diagnostics because it doesn't listen for `textDocument/publishDiagnostics` notifications from the server.

### LSP Protocol Specification

**Notification Direction:** Server → Client

**Notification Structure:**
```typescript
interface PublishDiagnosticsParams {
    uri: DocumentUri;
    version?: integer;
    diagnostics: Diagnostic[];
}

interface Diagnostic {
    range: Range;
    severity?: DiagnosticSeverity; // Error=1, Warning=2, Information=3, Hint=4
    code?: integer | string;
    source?: string;
    message: string;
    tags?: DiagnosticTag[]; // Unnecessary=1, Deprecated=2
    relatedInformation?: DiagnosticRelatedInformation[];
    data?: any;
}
```

### Solution: Async Notification Handler

**Problem:** Our current implementation only handles request/response, not notifications.

**Solution Architecture:**
```python
# Need to add notification queue for async processing
class LspClient:
    def __init__(self, ...):
        self._diagnostics_cache: Dict[str, List[DiagnosticInfo]] = {}
        self._notification_queue: asyncio.Queue = asyncio.Queue()

    async def _read_responses(self):
        """Read and process both responses and notifications."""
        # ... existing code ...

        # In message handling:
        if "method" in message:
            # This is a notification from server
            method = message["method"]
            if method == "textDocument/publishDiagnostics":
                await self._handle_diagnostics_notification(message["params"])

    async def _handle_diagnostics_notification(self, params):
        """Handle publishDiagnostics notification."""
        uri = params["uri"]
        diagnostics = params.get("diagnostics", [])

        # Convert to our DiagnosticInfo format
        parsed_diagnostics = []
        for diag in diagnostics:
            parsed_diagnostics.append(DiagnosticInfo(
                severity=self._parse_severity(diag.get("severity", 1)),
                message=diag["message"],
                file_path=self._uri_to_path(uri),
                line=diag["range"]["start"]["line"] + 1,
                column=diag["range"]["start"]["character"] + 1,
                diagnostic_id=str(diag.get("code", ""))
            ))

        # Cache diagnostics by file
        self._diagnostics_cache[uri] = parsed_diagnostics

    async def get_diagnostics(self, file_path: str | Path) -> DiagnosticsInfo:
        """Get cached diagnostics for a file."""
        file_uri = self._path_to_uri(file_path)

        # Open document if not already open
        await self._send_notification("textDocument/didOpen", {
            "textDocument": {
                "uri": file_uri,
                "languageId": self.language,
                "version": 1,
                "text": Path(file_path).read_text(),
            }
        })

        # Wait for diagnostics (with timeout)
        await asyncio.sleep(1.0)  # Give server time to analyze

        # Get from cache
        diagnostics = self._diagnostics_cache.get(file_uri, [])

        error_count = sum(1 for d in diagnostics if d.severity == DiagnosticSeverity.ERROR)
        warning_count = sum(1 for d in diagnostics if d.severity == DiagnosticSeverity.WARNING)
        info_count = sum(1 for d in diagnostics if d.severity == DiagnosticSeverity.INFO)

        return DiagnosticsInfo(
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            is_safe_to_refactor=error_count == 0,
            diagnostics=diagnostics
        )
```

### Implementation Estimate
- **Lines of code:** ~100 lines
- **Complexity:** Medium
- **Testing:** Need to test with real language servers
- **Files to modify:**
  - `python/src/refactor_mcp/clients/lsp.py` - Add notification handling

### Alternative: Use Existing LSP Client Library

Instead of implementing from scratch, consider using:

**pylspclient** (https://github.com/yeger00/pylspclient)
```python
from pylspclient import LspClient, LspEndpoint

# Example usage:
endpoint = LspEndpoint(server_cmd, server_args)
client = LspClient(endpoint)

# Register notification handler
def on_diagnostics(params):
    uri = params['uri']
    diagnostics = params['diagnostics']
    # Process diagnostics...

client.set_notification_callback("textDocument/publishDiagnostics", on_diagnostics)
```

**Pros:**
- Well-maintained library
- Handles JSON-RPC complexity
- Built-in notification handling

**Cons:**
- Additional dependency
- May not support async/await natively
- Need to adapt to our architecture

### Recommendation
**Option 1 (Recommended):** Enhance our existing async LspClient with notification queue
- More control over implementation
- No new dependencies
- Integrates cleanly with FastMCP async architecture

**Option 2:** Wrap pylspclient in async adapter
- Faster implementation
- More tested
- May have impedance mismatch with async patterns

---

## 2. Extract Method Refactoring

### Current Status
- **C#/VB.NET:** Placeholder only (returns "not implemented")
- **Other languages:** Not supported

### Solution 1: Roslyn Extract Method API

**Location:** `src/Features/CSharp/Portable/ExtractMethod/`

**Key Classes:**
- `ExtractMethodCodeRefactoringProvider` - Entry point
- `CSharpMethodExtractor` - Main extraction logic
- `AbstractExtractMethodService` - Base service

**Implementation Approach:**

```csharp
// In Roslyn CLI Program.cs
static async Task<object> ExtractMethodAsync(Dictionary<string, JsonElement> parameters)
{
    var projectPath = parameters["projectPath"].GetString()!;
    var filePath = parameters["filePath"].GetString()!;
    var startLine = parameters["startLine"].GetInt32() - 1;
    var startColumn = parameters["startColumn"].GetInt32() - 1;
    var endLine = parameters["endLine"].GetInt32() - 1;
    var endColumn = parameters["endColumn"].GetInt32() - 1;
    var methodName = parameters["methodName"].GetString()!;

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
        return new { success = false, error = "Document not found" };
    }

    // Get syntax tree and root
    var syntaxRoot = await document.GetSyntaxRootAsync();
    var text = await document.GetTextAsync();

    // Calculate positions
    var startPos = text.Lines[startLine].Start + startColumn;
    var endPos = text.Lines[endLine].Start + endColumn;
    var span = TextSpan.FromBounds(startPos, endPos);

    // Use ExtractMethodService (internal APIs)
    // Note: This requires accessing internal Roslyn APIs
    // Alternative: Use code generation approach

    try
    {
        // Simplified approach using SyntaxRewriter
        var selectedStatements = syntaxRoot.DescendantNodes()
            .Where(n => span.Contains(n.Span))
            .OfType<StatementSyntax>()
            .ToList();

        if (!selectedStatements.Any())
        {
            return new { success = false, error = "No valid statements selected" };
        }

        // Generate new method
        var parameters = DetermineParameters(selectedStatements, semanticModel);
        var returnType = DetermineReturnType(selectedStatements, semanticModel);

        var newMethod = SyntaxFactory.MethodDeclaration(
            returnType,
            methodName
        )
        .WithParameterList(parameters)
        .WithBody(SyntaxFactory.Block(selectedStatements));

        // Replace selected code with method call
        var methodCall = SyntaxFactory.ExpressionStatement(
            SyntaxFactory.InvocationExpression(
                SyntaxFactory.IdentifierName(methodName)
            )
        );

        // Apply transformation...
        // (Simplified - full implementation is complex)

        return new
        {
            success = true,
            methodName = methodName,
            filesModified = 1,
            parameters = parameters.Parameters.Select(p => p.Identifier.Text).ToArray(),
            returnType = returnType.ToString()
        };
    }
    catch (Exception ex)
    {
        return new
        {
            success = false,
            error = ex.Message
        };
    }
}
```

**Challenges:**
- ExtractMethod service uses internal APIs
- Complex dataflow analysis needed
- Parameter detection is non-trivial
- Return type inference is complex
- Need to handle all edge cases

**Complexity:** Very High (500-1000 lines)

### Solution 2: LSP Code Actions for Other Languages

**TypeScript/JavaScript:**
```python
async def extract_method_via_code_action(
    self,
    file_path: str | Path,
    start_line: int,
    start_column: int,
    end_line: int,
    end_column: int,
    method_name: str
) -> ExtractMethodResult:
    """Use LSP code actions to extract method."""

    file_uri = self._path_to_uri(file_path)

    # Request code actions for the selection
    result = await self._send_request(
        "textDocument/codeAction",
        {
            "textDocument": {"uri": file_uri},
            "range": {
                "start": {"line": start_line - 1, "character": start_column - 1},
                "end": {"line": end_line - 1, "character": end_column - 1}
            },
            "context": {
                "diagnostics": [],
                "only": ["refactor.extract.function"]  # Filter to extract actions
            }
        }
    )

    # Find extract function action
    extract_actions = [
        action for action in (result or [])
        if action.get("kind", "").startswith("refactor.extract")
    ]

    if not extract_actions:
        return ExtractMethodResult(
            success=False,
            error="Extract method not available for this selection"
        )

    # Apply the first extract action
    action = extract_actions[0]

    # Execute the code action
    if "command" in action:
        # Execute command
        await self._send_request("workspace/executeCommand", {
            "command": action["command"]["command"],
            "arguments": action["command"].get("arguments", [])
        })
    elif "edit" in action:
        # Apply workspace edit
        await self._apply_workspace_edit(action["edit"])

    return ExtractMethodResult(
        success=True,
        method_name=method_name,  # May differ from what server chose
        files_modified=1
    )
```

**Language Support:**
- **TypeScript/JavaScript:** ✅ Full support via TypeScript LSP
- **Python:** ✅ Via pylsp-rope plugin
- **Rust:** ✅ Via rust-analyzer
- **Go:** ⚠️ Limited (gopls may support)
- **Java:** ✅ Via Eclipse JDT LS
- **C++:** ❌ Not typically available

**Complexity:** Medium (200-300 lines)

### Recommendation
**Phase 1:** Implement LSP code actions for TypeScript, Python, Rust
- Easier to implement
- Works for most languages
- Uses standard LSP protocol

**Phase 2:** Implement Roslyn extract method for C#/VB.NET
- More complex
- Language-specific
- High value for .NET developers

---

## 3. Project-Level Operations

### Current Limitation
LSP clients work on individual files, not entire projects like Roslyn.

### LSP Solutions

#### 3.1 Workspace Symbols (`workspace/symbol`)

**Purpose:** Find symbols across entire workspace

```python
async def search_workspace_symbols(
    self,
    query: str,
    workspace_root: Path
) -> List[SymbolInformation]:
    """Search for symbols across entire workspace."""

    result = await self._send_request(
        "workspace/symbol",
        {"query": query}
    )

    symbols = []
    for symbol_info in (result or []):
        symbols.append(SymbolInformation(
            name=symbol_info["name"],
            kind=symbol_info["kind"],
            location={
                "uri": symbol_info["location"]["uri"],
                "range": symbol_info["location"]["range"]
            }
        ))

    return symbols
```

**Use Cases:**
- Find all classes/functions matching pattern
- Project-wide symbol search
- Dependency analysis

#### 3.2 Workspace-Wide Find References

**Already Implemented!** LSP `textDocument/references` works across files:

```python
# Current implementation already supports this
result = await self._send_request(
    "textDocument/references",
    {
        "textDocument": {"uri": file_uri},
        "position": {"line": line - 1, "character": column - 1},
        "context": {"includeDeclaration": True}
    }
)
# Returns references from ALL files in workspace
```

#### 3.3 Workspace-Wide Rename

**Already Implemented!** LSP `textDocument/rename` works across files:

```python
# Current implementation already supports this
result = await self._send_request(
    "textDocument/rename",
    {
        "textDocument": {"uri": file_uri},
        "position": {"line": line - 1, "character": column - 1},
        "newName": new_name
    }
)
# Returns workspace edit affecting multiple files
```

#### 3.4 Workspace Diagnostics (`workspace/diagnostic`)

**New in LSP 3.17:**

```python
async def get_workspace_diagnostics(
    self,
    workspace_root: Path
) -> Dict[str, List[DiagnosticInfo]]:
    """Get diagnostics for entire workspace."""

    # Request workspace diagnostics
    result = await self._send_request(
        "workspace/diagnostic",
        {
            "previousResultIds": []  # No previous results
        }
    )

    diagnostics_by_file = {}
    for item in result.get("items", []):
        uri = item["uri"]
        diagnostics = item.get("diagnostics", [])
        diagnostics_by_file[uri] = [
            self._parse_diagnostic(d) for d in diagnostics
        ]

    return diagnostics_by_file
```

**Note:** Requires LSP 3.17+ support from language server

### What LSP Already Provides

✅ **Project-wide find references** - Works out of box
✅ **Project-wide rename** - Works out of box
✅ **Workspace symbols** - Need to add (~50 lines)
✅ **Workspace diagnostics** - Need to add (~100 lines)

### What's Missing (LSP Limitations)

❌ **Project loading** - LSP doesn't have concept of "loading project"
❌ **Solution-wide compilation** - No equivalent to Roslyn's compilation
❌ **Cross-project refactoring** - Limited to workspace scope

### Recommendation

**For LSP languages:**
1. ✅ Keep using `textDocument/references` (already project-wide)
2. ✅ Keep using `textDocument/rename` (already project-wide)
3. ➕ Add `workspace/symbol` for symbol search
4. ➕ Add `workspace/diagnostic` for workspace-wide diagnostics

**For C#/VB.NET:**
- Continue using Roslyn for true project-level operations
- Solution loading, compilation, project-wide analysis

---

## Implementation Priority

### High Priority (Easy Wins)
1. **Fix LSP diagnostics** (~100 lines, Medium complexity)
   - Add notification queue and handler
   - Cache diagnostics by file
   - Update get_diagnostics to use cache

2. **Add workspace/symbol** (~50 lines, Low complexity)
   - Simple request/response
   - Useful for project-wide search

### Medium Priority
3. **Extract method via code actions** (~200 lines, Medium complexity)
   - Works for TypeScript, Python, Rust
   - Standard LSP protocol
   - High user value

4. **Workspace diagnostics** (~100 lines, Medium complexity)
   - Requires LSP 3.17+
   - Not all servers support it

### Low Priority (Complex)
5. **Roslyn extract method** (~500-1000 lines, Very high complexity)
   - Complex dataflow analysis
   - Internal APIs
   - Many edge cases

---

## Code Examples Repository

### pylsp-rope (Python Extract Method)
Installation: `pip install pylsp-rope`
Provides: Extract method, extract variable, inline variable

### rust-analyzer Code Actions
Supports: Extract function, extract variable, inline function

### TypeScript Language Server
Supports: Extract function, extract constant, extract type

---

## Testing Strategy

### Unit Tests
```python
# Test notification handling
async def test_diagnostics_notification():
    client = LspClient(...)
    await client.start()

    # Trigger diagnostics
    await client.get_diagnostics("test.py")

    # Wait for notification
    await asyncio.sleep(2)

    # Verify diagnostics were cached
    assert len(client._diagnostics_cache) > 0
```

### Integration Tests
```python
# Test with real language server
@pytest.mark.integration
async def test_typescript_extract_method():
    client = LspClient("typescript", "typescript-language-server", ["--stdio"])
    await client.start()

    result = await client.extract_method_via_code_action(
        file_path="test.ts",
        start_line=10,
        start_column=5,
        end_line=15,
        end_column=10,
        method_name="extractedMethod"
    )

    assert result.success is True
```

---

## Resources

### Documentation
- LSP Specification: https://microsoft.github.io/language-server-protocol/
- Roslyn Source: https://github.com/dotnet/roslyn
- pygls (Server): https://pygls.readthedocs.io/
- pylspclient: https://github.com/yeger00/pylspclient

### Examples
- rust-analyzer code actions: Extract function support
- pylsp-rope: Python refactoring plugin
- TypeScript LSP: Extract function via code actions

### Libraries
- **pylspclient** - Python LSP client (sync)
- **sansio-lsp-client** - Sans-IO LSP client
- **python-lsp-jsonrpc** - JSON-RPC for LSP
- **lsprotocol** - LSP types for Python

---

## Estimated Implementation Timeline

**Week 1: Diagnostics**
- Add notification queue to LspClient
- Implement publishDiagnostics handler
- Update get_diagnostics to use cache
- Test with TypeScript, Python, Rust

**Week 2: Workspace Features**
- Add workspace/symbol support
- Add workspace/diagnostic support
- Test project-wide operations

**Week 3: Extract Method (LSP)**
- Implement code action-based extract method
- Test with TypeScript, Python, Rust
- Document per-language support

**Week 4: Extract Method (Roslyn)**
- Research internal ExtractMethod APIs
- Implement basic extraction logic
- Handle parameter detection
- Test with C# projects

**Total: 4 weeks for complete implementation**

---

## Conclusion

All three missing features are achievable:

1. **Diagnostics** ✅ Straightforward, ~100 lines
2. **Extract method** ✅ Medium complexity for LSP, high for Roslyn
3. **Project-level ops** ✅ Mostly already working via LSP!

The Python rewrite can achieve feature parity with the C# version and exceed it for non-.NET languages.
