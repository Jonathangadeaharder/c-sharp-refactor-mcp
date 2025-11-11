# Test Project for Roslyn-MCP Server

This is a simple C# console application used to test the Roslyn-MCP server's refactoring capabilities.

## Project Structure

```
TestSolution.sln
└── SampleProject/
    ├── SampleProject.csproj
    ├── Program.cs
    ├── Calculator.cs
    └── DataProcessor.cs
```

## Test Scenarios

### 1. Rename Symbol
**Target:** `AddNumbers` method in `Calculator.cs` (line 10)
**Test:** Rename to `Add`
**Expected:** All references updated, including call in `Program.cs`

### 2. Find All References
**Target:** `_lastResult` field in `Calculator.cs` (line 8)
**Expected:** Find 4 references (declaration + 3 usages)

### 3. Encapsulate Field
**Target:** `_lastResult` field in `Calculator.cs` (line 8)
**Expected:**
- Field remains private
- New public property `LastResult` created
- All usages updated to use property

### 4. Extract Method
**Target:** Lines 37-40 in `DataProcessor.cs` (the console output block)
**Expected:**
- New method `DisplayProcessingResults` created
- Parameters: `data`, `upperData`, `length`, `reversed`
- Original code replaced with method call

### 5. Get Diagnostics
**Test:** Should return 0 errors (project compiles cleanly)

## Using with the MCP Server

### Step 1: Load the solution
```json
{
  "name": "load_solution",
  "arguments": {
    "solutionPath": "/absolute/path/to/test-project/TestSolution.sln"
  }
}
```

### Step 2: Check for errors
```json
{
  "name": "get_diagnostics",
  "arguments": {
    "solutionPath": "/absolute/path/to/test-project/TestSolution.sln",
    "severityFilter": "Error"
  }
}
```

### Step 3: Find references to _lastResult
```json
{
  "name": "find_all_references",
  "arguments": {
    "solutionPath": "/absolute/path/to/test-project/TestSolution.sln",
    "documentPath": "/absolute/path/to/test-project/SampleProject/Calculator.cs",
    "line": 8,
    "column": 17
  }
}
```

### Step 4: Rename AddNumbers to Add
```json
{
  "name": "rename_symbol",
  "arguments": {
    "solutionPath": "/absolute/path/to/test-project/TestSolution.sln",
    "documentPath": "/absolute/path/to/test-project/SampleProject/Calculator.cs",
    "line": 10,
    "column": 16,
    "newName": "Add"
  }
}
```

### Step 5: Encapsulate the _lastResult field
```json
{
  "name": "encapsulate_field",
  "arguments": {
    "solutionPath": "/absolute/path/to/test-project/TestSolution.sln",
    "documentPath": "/absolute/path/to/test-project/SampleProject/Calculator.cs",
    "line": 8,
    "column": 17
  }
}
```

## Expected Results

After running all refactorings:

1. ✅ `AddNumbers` → `Add`
2. ✅ `_lastResult` → encapsulated with `LastResult` property
3. ✅ All references updated across files
4. ✅ Project still compiles with 0 errors
5. ✅ All changes written to disk

## Verification

Build the project after refactoring:
```bash
cd test-project/SampleProject
dotnet build
```

Should output:
```
Build succeeded.
    0 Warning(s)
    0 Error(s)
```
