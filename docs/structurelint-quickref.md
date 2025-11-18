# Structurelint Quick Reference

## Running Locally

```bash
# Run from project root
structurelint .
```

Expected output when everything is correct:
```
✓ All checks passed
```

## Common Issues & Fixes

### ❌ Naming Convention Violation

**Problem:** File doesn't follow C# naming standards

**Example Error:**
```
Error: File 'myClass.cs' violates naming convention (expected PascalCase)
```

**Fix:**
```bash
# Rename file to PascalCase
mv myClass.cs MyClass.cs
```

### ❌ Too Many Files in Directory

**Problem:** Directory has more than 25 files (or 30 for tests)

**Example Error:**
```
Error: Directory 'Services/' has 30 files (max: 25)
```

**Fix:**
```bash
# Split into subdirectories by functionality
mkdir Services/Authentication
mv Services/Auth*.cs Services/Authentication/
```

### ❌ Build Artifacts Detected

**Problem:** bin/ or obj/ directories committed to git

**Example Error:**
```
Error: Disallowed pattern 'bin/**' found
```

**Fix:**
```bash
# Clean and remove from git
dotnet clean
git rm -r --cached bin/ obj/
git commit -m "Remove build artifacts from git"
```

### ❌ Directory Too Deep

**Problem:** Directory nesting exceeds 6 levels

**Example Error:**
```
Error: Directory depth 7 exceeds maximum 6
```

**Fix:** Flatten directory structure or reconsider organization

## File Naming Standards

| File Type | Convention | Examples |
|-----------|-----------|----------|
| C# Classes | PascalCase | `UserService.cs`, `DataProcessor.cs` |
| C# Tests | PascalCase + Tests | `UserServiceTests.cs`, `DataProcessorTest.cs` |
| Project Files | PascalCase | `RoslynRefactorServer.csproj` |
| Solution Files | PascalCase | `RoslynRefactorServer.sln` |
| Config Files | kebab-case | `appsettings.json`, `build-config.json` |
| Workflows | kebab-case | `build-and-test.yml` |
| Documentation | kebab-case / UPPERCASE | `README.md`, `CONTRIBUTING.md` |
| Shell Scripts | kebab-case | `check-workflow.sh` |

## CI Integration

Structurelint runs automatically on every push. The workflow order is:

1. ✅ Setup .NET and Go
2. ✅ **Run structurelint** ← Fails build if violations found
3. ✅ Restore dependencies
4. ✅ Build project
5. ✅ Run tests

## Configuration

Main config file: `.structurelint.yml`

### Current Limits

- Max directory depth: **6**
- Max files per directory: **25** (general), **30** (tests), **50** (test projects)
- Max subdirectories: **12**

### Excluded Directories

These are NOT linted:
- `.git/`
- `**/bin/`, `**/obj/`
- `**/.vs/`
- `**/node_modules/`
- `**/packages/`

### Blocked Patterns

These will FAIL the build:
- Build artifacts: `**/bin/**`, `**/obj/**`
- IDE files: `**/.vs/**`
- Temp files: `**/*.tmp`, `**/*.temp`
- Secrets: `**/*.key`, `**/*.pem`, `**/secrets.json`
- OS files: `**/Thumbs.db`, `**/.DS_Store`

## Pre-Commit Hook (Optional)

To run structurelint before every commit:

```bash
# Create .git/hooks/pre-commit
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
echo "Running structurelint..."
structurelint .
if [ $? -ne 0 ]; then
  echo "❌ Structurelint failed. Please fix violations before committing."
  exit 1
fi
echo "✅ Structurelint passed"
EOF

chmod +x .git/hooks/pre-commit
```

## Troubleshooting

### Structurelint not found

```bash
# Install from source
git clone https://github.com/Jonathangadeaharder/structurelint.git /tmp/structurelint
cd /tmp/structurelint
go build -o structurelint ./cmd/structurelint
sudo mv structurelint /usr/local/bin/
```

### False positive / Need exception

Edit `.structurelint.yml` to add exclusion:

```yaml
exclude:
  - "special-case/**"
```

Or add directory override:

```yaml
overrides:
  - path: "legacy/**"
    rules:
      naming-convention:
        "**/*.cs": "PascalCase|kebab-case"  # More flexible
```

## Help

- Full documentation: [STRUCTURELINT.md](STRUCTURELINT.md)
- Configuration file: [.structurelint.yml](.structurelint.yml)
- Structurelint repo: https://github.com/Jonathangadeaharder/structurelint
