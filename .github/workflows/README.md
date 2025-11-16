# GitHub Actions Workflows

## Overview

This repository includes two automated workflows:

1. **Build and Test Workflow** (`build-and-test.yml`) - Builds and tests the project
2. **Repomix Bundle Workflow** (`repomix.yml`) - Generates a bundled codebase artifact

---

## Build and Test Workflow

This workflow (`build-and-test.yml`) automatically builds and tests the Roslyn-MCP Server on every push and pull request.

### What It Does

1. **Checks out the code** with full history
2. **Sets up .NET 8.0** SDK
3. **Restores dependencies** (`dotnet restore`)
4. **Builds the project** (`dotnet build`)
5. **Runs all tests** (`dotnet test`)
6. **Captures all output** to `build-test.log`
7. **Amends the log to the commit** (on push events)
8. **Force pushes** the amended commit back to the branch

### Key Features

#### 📝 Automatic Log Generation

All build and test output is captured in `build-test.log` which includes:
- Commit hash and branch name
- Timestamp (UTC)
- Full restore/build/test output
- Exit codes and status indicators
- Final summary

#### 🔄 Commit Amendment

On push events, the workflow:
1. Amends `build-test.log` to the commit that triggered the workflow
2. Force pushes the amended commit back
3. This means the log is stored **in the commit itself**

#### 📦 Artifact Upload (Fallback)

The log is also uploaded as a GitHub Actions artifact:
- Available for 30 days
- Useful for pull requests (where commit amendment doesn't happen)
- Accessible via the Actions UI

### Viewing the Log

#### After a Push

```bash
# Pull the amended commit
git pull --force

# View the log
cat build-test.log
```

Or simply view the file on GitHub in the commit.

#### For Pull Requests

The log is available as an artifact in the Actions tab:
1. Go to the workflow run
2. Scroll to "Artifacts"
3. Download `build-test-log`

### How It Works: The Amendment Process

```yaml
1. Workflow triggers on push
2. Build and test run, output → build-test.log
3. git add build-test.log
4. git commit --amend --no-edit
5. git push --force-with-lease
6. Your commit now includes the log!
```

### Security & Permissions

The workflow requires `contents: write` permission to push commits. This is configured in the workflow file.

### Workflow Triggers

- **Push**: Any branch
- **Pull Request**: Targeting `main` branch

### Status Indicators

The log uses emoji status indicators:

- ✅ `BUILD SUCCEEDED` - Build completed successfully
- ❌ `BUILD FAILED` - Build failed
- ✅ `TESTS PASSED` - All tests passed
- ❌ `TESTS FAILED` - One or more tests failed

### Example Log File

```
================================================================
Build and Test Execution Log
================================================================
Commit: abc123def456...
Branch: feature/my-feature
Timestamp: 2025-01-15 14:30:45 UTC
Triggered by: push
Actor: octocat
================================================================

>>> Restoring dependencies...
  Determining projects to restore...
  Restored /workspace/RoslynRefactorServer.csproj (in 1.2 sec).

>>> Building project...
  RoslynRefactorServer -> /workspace/bin/Release/net8.0/RoslynRefactorServer.dll

Build exit code: 0
✅ BUILD SUCCEEDED

>>> Running tests...
  Starting test execution, please wait...
  Passed!  - Failed:     0, Passed:    15, Skipped:     0, Total:    15

Test exit code: 0
✅ TESTS PASSED

================================================================
End of Build and Test Log
Completed at: 2025-01-15 14:31:02 UTC
================================================================
```

### Advantages of This Approach

1. **No CI Dashboard Required**: Just check the commit for the log
2. **Version Controlled**: Logs are tied to specific commits
3. **Permanent Record**: Logs don't expire (unlike artifacts)
4. **Offline Access**: Pull the repo, get the logs
5. **Bisect Friendly**: See build status for any commit in history

### Disadvantages

1. **Force Push**: Uses force push (with lease for safety)
2. **Commit History**: Amends commits (changes SHA)
3. **Collaboration**: May confuse teammates unfamiliar with this pattern

### Best Practices

- **Don't amend public commits**: Only use on feature branches
- **Communicate**: Let your team know about this pattern
- **Pull with --force**: Always use `git pull --force` after workflow runs
- **Check the log**: Review `build-test.log` before merging

### Disabling Commit Amendment

To disable commit amendment and only use artifact upload, modify the workflow:

```yaml
# Change this condition:
if: always() && github.event_name == 'push'

# To this:
if: false
```

Or simply remove the "Amend commit" and "Force push" steps.

### Troubleshooting

#### Workflow fails at "Force push" step

**Cause**: Branch protection rules may prevent force pushes.

**Solution**: Either:
1. Exempt the GitHub Actions bot from branch protection
2. Disable commit amendment (see above)

#### Log file is empty or missing

**Cause**: Build/test commands failed before output could be captured.

**Solution**: Check the workflow logs in GitHub Actions UI.

#### Merge conflicts after pull

**Cause**: Local changes conflict with the amended commit.

**Solution**:
```bash
git fetch origin
git reset --hard origin/your-branch
```

### Future Enhancements

Potential improvements:
- Parse test results and add to commit message
- Generate code coverage reports
- Benchmark performance metrics
- Compare against previous runs

---

## Repomix Bundle Workflow

This workflow (`repomix.yml`) automatically generates a bundled version of the entire codebase using [Repomix](https://github.com/yamadashy/repomix) and publishes it as a GitHub Actions artifact.

### What It Does

1. **Checks out the code** with full history
2. **Sets up Node.js** (required for repomix)
3. **Runs Repomix** to bundle the codebase into a single file
4. **Generates metadata** about the bundle (commit, branch, timestamp)
5. **Uploads artifacts** with both commit-specific and latest versions

### Key Features

#### 📦 Codebase Bundling

Repomix combines your entire codebase into a single, well-formatted plain text file that includes:
- All source code files
- Project structure and hierarchy
- File metadata and statistics
- Clear file separation markers
- Configurable inclusion/exclusion patterns

#### 🎯 Multiple Artifact Versions

Two artifacts are uploaded for each run:
1. **`repomix-bundle-{commit-sha}`** - Commit-specific bundle (90-day retention)
2. **`repomix-bundle-latest`** - Always the latest bundle (30-day retention)

#### 📊 Bundle Statistics

Each workflow run provides:
- Total line count
- Bundle file size
- Generation timestamp
- Git commit and branch info

### Configuration

#### `.repomixignore`

Specifies files and directories to exclude from the bundle:
- Build outputs (`bin/`, `obj/`)
- Dependencies (`node_modules/`, `packages/`)
- IDE files (`.vs/`, `.vscode/`)
- Test results and logs
- Binary files

#### `repomix.config.json`

Configures repomix behavior:
```json
{
  "output": {
    "style": "plain",
    "showLineNumbers": true,
    "removeComments": false
  },
  "include": ["**/*.cs", "**/*.csproj", "**/*.md"],
  "ignore": {
    "useGitignore": true,
    "customPatterns": ["bin/**", "obj/**"]
  }
}
```

### Workflow Triggers

- **Push**: `main`, `develop`, and `claude/**` branches
- **Pull Request**: Targeting `main` branch
- **Manual**: Via `workflow_dispatch` (Actions tab → Run workflow)

### Downloading the Bundle

#### From GitHub Actions UI

1. Go to the [Actions tab](https://github.com/your-repo/actions)
2. Click on a "Repomix Codebase Bundle" workflow run
3. Scroll to "Artifacts" section
4. Download either:
   - `repomix-bundle-{commit-sha}` - Specific commit version
   - `repomix-bundle-latest` - Most recent version

#### Using GitHub CLI

```bash
# List artifacts for a specific run
gh run view {run-id}

# Download the latest bundle
gh run download --name repomix-bundle-latest

# Download a specific commit's bundle
gh run download --name repomix-bundle-{commit-sha}
```

### Use Cases

The repomix bundle is useful for:

1. **AI/LLM Context**: Provide entire codebase to AI tools like Claude or GPT
2. **Code Review**: Share complete codebase snapshot with reviewers
3. **Documentation**: Generate comprehensive codebase documentation
4. **Archival**: Create point-in-time snapshots of the codebase
5. **Analysis**: Feed to static analysis tools that prefer single-file input
6. **Onboarding**: Help new developers understand the complete codebase structure

### Bundle Contents

The generated `repomix-output.txt` includes:
- Plain text formatted codebase structure
- All source files with line numbers
- File paths and metadata
- Project hierarchy
- Statistics and summary

The `repomix-metadata.json` includes:
```json
{
  "commit": "abc123...",
  "branch": "feature/my-feature",
  "timestamp": "2025-01-15 14:30:45 UTC",
  "triggered_by": "push",
  "actor": "username",
  "repository": "owner/repo"
}
```

### Security

- The workflow uses `contents: read` permission (minimal access)
- Security scanning is enabled via `enableSecurityCheck: true`
- Sensitive files can be excluded via `.repomixignore`
- No credentials or secrets are included in the bundle

### Performance

Typical workflow execution:
- Checkout: ~5-10 seconds
- Node.js setup: ~10-15 seconds (cached after first run)
- Repomix execution: ~5-30 seconds (depends on codebase size)
- Artifact upload: ~5-10 seconds
- **Total**: Usually under 1 minute

**Note**: The workflow uses Node.js v22 (current LTS) and repomix v1.0.0 (pinned for reproducibility).

### Customization

#### Change Output Format

Edit `repomix.config.json`:
```json
{
  "output": {
    "style": "xml"  // or "markdown", "plain" (default)
  }
}
```

#### Exclude Additional Files

Add to `.repomixignore`:
```gitignore
# Custom exclusions
*.secret
private/
```

#### Change Retention Period

Edit `repomix.yml`:
```yaml
- name: Upload Repomix bundle as artifact
  uses: actions/upload-artifact@v4
  with:
    retention-days: 180  # Change from 90 (default is 90-day retention)
```

### Troubleshooting

#### Bundle is too large

**Cause**: Too many files included or large binary files

**Solution**:
1. Add more patterns to `.repomixignore`
2. Use `include` patterns in `repomix.config.json` to be more selective
3. Check for accidentally committed large files

#### Missing files in bundle

**Cause**: Files excluded by ignore patterns

**Solution**:
1. Check `.repomixignore` and `.gitignore`
2. Review `customPatterns` in `repomix.config.json`
3. Ensure files are committed to git

#### Workflow fails at repomix step

**Cause**: Invalid configuration or repomix error

**Solution**:
1. Check workflow logs for specific error
2. Validate `repomix.config.json` syntax
3. Try running repomix locally: `npx repomix`

### Local Testing

Test the bundle generation locally:

```bash
# Install repomix
npm install -g repomix

# Generate bundle
repomix

# View output
cat repomix-output.txt

# Check stats
wc -l repomix-output.txt
du -h repomix-output.txt
```

### Integration with Other Workflows

The repomix bundle can be used by other workflows:

```yaml
- name: Download latest bundle
  uses: actions/download-artifact@v4
  with:
    name: repomix-bundle-latest

- name: Process bundle
  run: |
    # Your processing logic here
    cat repomix-output.txt | your-tool
```
