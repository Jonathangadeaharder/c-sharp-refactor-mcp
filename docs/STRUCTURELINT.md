# Structurelint Integration

This project uses [structurelint](https://github.com/Jonathangadeaharder/structurelint) to enforce project structure, organization, and architectural integrity.

## What is Structurelint?

Structurelint is a next-generation linter designed to enforce filesystem topology, ensuring the project remains clean, maintainable, and aligned with best practices. Unlike traditional linters that focus on code quality, structurelint validates:

- Directory depth limits
- File count restrictions per directory
- Naming conventions (PascalCase, camelCase, kebab-case, etc.)
- File existence requirements
- Architectural boundaries
- Prohibited patterns (compiled artifacts, secrets, etc.)

## Installation

### Using Go (Recommended for Local Development)

```bash
# Clone and build from source
git clone https://github.com/Jonathangadeaharder/structurelint.git /tmp/structurelint
cd /tmp/structurelint
go build -o /usr/local/bin/structurelint ./cmd/structurelint

# Verify installation
structurelint --version
```

### Pre-built Binaries

Download pre-built binaries from the [releases page](https://github.com/Jonathangadeaharder/structurelint/releases) for:
- Linux (amd64)
- macOS (Apple Silicon)

## Running Locally

```bash
# Run from project root
structurelint .

# All checks should pass
# ✓ All checks passed
```

## Configuration

The project's structurelint rules are defined in `.structurelint.yml` at the root of the repository.

### Current Rules

**Metric Rules:**
- `max-depth: 6` - Prevents excessive directory nesting
- `max-files-in-dir: 25` - Keeps directories focused (30 for tests, 50 for test projects)
- `max-subdirs: 12` - Controls complexity per directory level

**Naming Conventions:**
- C# files (`.cs`): PascalCase
- Project files (`.csproj`): PascalCase
- Solution files (`.sln`): PascalCase
- Configuration files (`.json`, `.yml`): kebab-case or lowercase
- Markdown files (`.md`): kebab-case, UPPERCASE, or PascalCase
- Shell scripts (`.sh`): kebab-case or snake_case

**File Existence Requirements:**
- README.md (exactly 1)
- LICENSE (exactly 1)
- .gitignore (exactly 1)
- appsettings.json (exactly 1)
- At least one .sln and .csproj file
- At least one workflow file in .github/workflows/

**Disallowed Patterns:**
- Compiled artifacts: `**/bin/**`, `**/obj/**`
- IDE files: `**/.vs/**`, `**/.vscode/*.log`
- Temporary files: `**/*.tmp`, `**/*.temp`
- OS files: `**/Thumbs.db`, `**/.DS_Store`
- Secrets: `**/*.key`, `**/*.pem`, `**/secrets.json`

### Directory Overrides

Special rules apply to:
- `test-project/`: Allows up to 50 files per directory
- `RoslynRefactorServer.Tests/`: Allows up to 30 files, enforces `*Tests.cs` naming
- `.github/`: Strictly enforces kebab-case for workflows
- `examples/`: More flexible naming (PascalCase or kebab-case)

### Global Exclusions

The following directories are excluded from linting:
- `.git/`
- `**/bin/`, `**/obj/`
- `**/.vs/`
- `**/node_modules/`, `**/packages/`

## CI/CD Integration

Structurelint runs automatically in the GitHub Actions workflow on every push and pull request.

The workflow:
1. Sets up Go environment
2. Builds structurelint from source
3. Runs linting before building the project
4. Logs results to `build-test.log`
5. Fails the build if structure rules are violated

**Workflow Steps:**
```yaml
- Setup Go (for structurelint)
- Install structurelint
- Run structurelint
- Restore dependencies
- Build project
- Run tests
```

### Current Limits

- Max directory depth: **4**
- Max files per directory: **15** (general), **20** (tests), **25** (test projects)
- Max subdirectories: **8**

If structurelint fails, the build will not proceed. This ensures structural integrity is maintained before compilation.

## Customizing Rules

To modify structurelint rules:

1. Edit `.structurelint.yml`
2. Run `structurelint .` locally to test
3. Commit changes
4. Push to trigger CI validation

### Adding New Rules

See the [structurelint documentation](https://github.com/Jonathangadeaharder/structurelint) for available rule types:

- Cognitive complexity metrics
- Halstead complexity metrics
- Import graph analysis
- Dead code detection
- Test adjacency requirements
- File content templates

## Troubleshooting

### "max-files-in-dir" Violation

If a directory has too many files:
- Consider splitting into subdirectories by functionality
- Check if the limit is appropriate for that directory
- Add a directory-specific override in `.structurelint.yml`

### "naming-convention" Violation

Ensure files follow C# naming standards:
- Classes, interfaces, structs: `MyClass.cs` (PascalCase)
- Test files: `MyClassTests.cs` or `MyClassTest.cs`
- Configuration: `my-config.json` (kebab-case)

### "disallowed-patterns" Violation

Remove prohibited files:
```bash
# Clean build artifacts
dotnet clean

# Remove IDE files from git
git rm -r --cached .vs/
echo ".vs/" >> .gitignore
```

### False Positives

If structurelint incorrectly flags a valid pattern:
1. Add an exclusion to `.structurelint.yml`:
   ```yaml
   exclude:
     - "path/to/exception/**"
   ```
2. Or add a directory override:
   ```yaml
   overrides:
     - path: "specific-dir/**"
       rules:
         disallowed-patterns:
           severity: warning  # Downgrade to warning
   ```

## Benefits

Structurelint helps maintain:

- **Consistency**: All C# files follow PascalCase convention
- **Cleanliness**: No build artifacts or secrets in source control
- **Scalability**: Prevents "god directories" with hundreds of files
- **Maintainability**: Clear, predictable project structure
- **Security**: Blocks accidental commits of sensitive files

## Resources

- [Structurelint GitHub Repository](https://github.com/Jonathangadeaharder/structurelint)
- [Project Configuration](.structurelint.yml)
- [CI Workflow](.github/workflows/build-and-test.yml)

---

**Note**: Structurelint runs as part of the CI pipeline and will fail builds if violations are detected. Always run `structurelint .` locally before pushing changes.
