# CI Workflow Guide

This guide explains how the automated test and logging workflow works.

## Overview

The Multi-Language Refactor MCP Server uses GitHub Actions to automatically:
1. ✅ Build the project
2. ✅ Run all tests
3. ✅ Validate project structure (structurelint)
4. ✅ Capture complete execution log
5. ✅ **Amend the log to your commit** (auto-commits on push)

## How It Works

### Workflow Trigger

The workflow runs automatically on:
- **Push** to `claude/**` branches, `main`, or `develop`
- **Pull Requests** to `main`

### Workflow Steps

```
1. Checkout code
   ↓
2. Setup .NET 8.0
   ↓
3. Restore dependencies
   ↓
4. Build project (Release configuration)
   ↓
5. Run tests (with detailed verbosity)
   ↓
6. Run structurelint validation (if available)
   ↓
7. Generate consolidated test-execution.log
   ↓
8. Amend commit with the log file
   ↓
9. Force push the amended commit
```

### The Test Log

The `test-execution.log` file contains:
- **Workflow metadata**: Run number, branch, commit, author, timestamp
- **Build output**: Complete dotnet build output
- **Test results**: Detailed test execution with pass/fail status
- **Structurelint validation**: Project structure validation results
- **Summary**: Quick overview of all checks (✅/❌)

Example structure:
```
===========================================
Multi-Language Refactor MCP Server
Test Execution Log
===========================================

Workflow Run: 42
Branch: claude/my-feature
Commit: abc123...
Timestamp: 2024-01-15 10:30:00 UTC

===========================================
BUILD RESULTS
===========================================
[dotnet build output...]

===========================================
TEST RESULTS
===========================================
[dotnet test output...]

===========================================
STRUCTURELINT VALIDATION
===========================================
[structurelint output...]

===========================================
SUMMARY
===========================================
✅ Build: PASSED
✅ Tests: PASSED
✅ Structurelint: PASSED
```

## Using the Workflow

### After Pushing Your Code

1. **Push your changes:**
   ```bash
   git push origin claude/my-feature
   ```

2. **Wait for workflow to complete** (~1-3 minutes)
   - Watch progress at: `https://github.com/Jonathangadeaharder/c-sharp-refactor-mcp/actions`

3. **Pull the amended commit:**
   ```bash
   git pull --force
   ```

4. **View the test log:**
   ```bash
   cat test-execution.log
   ```

### The Commit Amendment Process

The workflow uses a smart amendment strategy:

```bash
# After tests run, the workflow:
git add test-execution.log
git commit --amend --no-edit -m "[skip ci] CI: Update test log"
git push --force-with-lease origin <branch>
```

**Important notes:**
- Uses `--force-with-lease` for safety (won't overwrite if someone else pushed)
- Adds `[skip ci]` to prevent infinite loop
- Only amends on **push** events (not on PRs)
- Preserves original commit message

### For Pull Requests

On pull requests, the workflow:
- ✅ Runs all checks
- 📝 Posts results as a comment
- 📎 Uploads log as downloadable artifact
- ❌ **Does NOT amend commit** (to avoid conflicts)

You can download the artifact from the workflow run page.

## Why This Pattern?

Traditional CI logs expire and live only in the GitHub Actions UI. This workflow stores the log **in the repository itself**:

### Advantages

| Traditional CI | Commit-Amended Logs |
|----------------|---------------------|
| ❌ Logs expire after 90 days | ✅ Permanent record in Git history |
| ❌ Requires GitHub Actions UI access | ✅ Available offline (`git clone` includes logs) |
| ❌ Not tied to specific code state | ✅ Version controlled with the code |
| ❌ Hard to compare test results over time | ✅ Easy diff with `git diff HEAD~1 test-execution.log` |

### Example: Comparing Test Results

```bash
# See what changed in tests between commits
git diff HEAD~1 test-execution.log

# View test log from 5 commits ago
git show HEAD~5:test-execution.log

# Search test history
git log -p test-execution.log | grep "FAILED"
```

## Troubleshooting

### "Already up to date" after git pull

This means the workflow didn't amend (likely because tests already passed and log didn't change).

### Force push conflicts

If you push while the workflow is running:
```bash
# Fetch the amended commit
git fetch origin

# Reset to the remote version
git reset --hard origin/<branch-name>
```

### Workflow not running

Check:
1. Branch name matches trigger pattern (e.g., `claude/**`)
2. Commit message doesn't contain `[skip ci]`
3. GitHub Actions are enabled for the repository

### Test log not updating

The workflow only amends if there are changes to the log. If tests produce identical output, no amendment occurs.

## Local Testing

To generate the same log locally:

```bash
#!/bin/bash
# local-test.sh

cat > test-execution.log <<'EOF'
===========================================
Multi-Language Refactor MCP Server
Test Execution Log (Local Run)
===========================================

Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')

===========================================
BUILD RESULTS
===========================================
EOF

dotnet build --configuration Release 2>&1 | tee -a test-execution.log

cat >> test-execution.log <<'EOF'

===========================================
TEST RESULTS
===========================================
EOF

dotnet test --no-build --configuration Release --verbosity detailed 2>&1 | tee -a test-execution.log

echo ""
echo "✅ Test log generated: test-execution.log"
cat test-execution.log
```

Make it executable and run:
```bash
chmod +x local-test.sh
./local-test.sh
```

## Workflow Configuration

The workflow is defined in `.github/workflows/test-and-log.yml`.

### Key Configuration Options

```yaml
# Branches that trigger the workflow
on:
  push:
    branches:
      - 'claude/**'
      - 'main'
      - 'develop'
```

### Customizing the Workflow

To modify the workflow:

1. Edit `.github/workflows/test-and-log.yml`
2. Test locally with `act` (GitHub Actions local runner):
   ```bash
   # Install act: https://github.com/nektos/act
   act push -j test-and-amend
   ```
3. Push and verify

## Best Practices

### DO:
- ✅ Pull with `--force` after workflow completes
- ✅ Review the test log before continuing development
- ✅ Use `git show HEAD:test-execution.log` to view latest log
- ✅ Keep workflow fast (currently ~1-3 minutes)

### DON'T:
- ❌ Push while workflow is running (causes conflicts)
- ❌ Manually edit test-execution.log (workflow overwrites it)
- ❌ Delete the log file (workflow recreates it)
- ❌ Amend commits manually after workflow runs (causes divergence)

## Advanced Usage

### Skipping the Workflow

To skip the workflow on a specific commit:
```bash
git commit -m "WIP: experiments [skip ci]"
git push
```

### Running Only Specific Checks

The workflow always runs all checks, but you can run them individually locally:

```bash
# Build only
dotnet build --configuration Release

# Tests only
dotnet test --configuration Release

# Structurelint only
structurelint .
```

### Accessing Historical Logs

```bash
# View log from specific commit
git show <commit-sha>:test-execution.log

# View all changes to test logs
git log -p --follow test-execution.log

# Find when a test started failing
git log --all -p -S "FAILED" test-execution.log
```

## Artifact Storage

In addition to commit amendment, the workflow uploads the log as an artifact:

- **Retention**: 30 days
- **Access**: GitHub Actions run page → "Artifacts" section
- **Download**: Click "test-execution-log" to download

This provides a backup if you need the log before pulling.

## Security Considerations

### Token Permissions

The workflow uses `GITHUB_TOKEN` with:
- ✅ `contents: write` - To amend commits
- ✅ `pull-requests: write` - To comment on PRs

### Force Push Safety

The workflow uses `--force-with-lease` instead of `--force`:
- Prevents overwriting if remote changed
- Fails safely if concurrent pushes occurred
- Logs warning instead of corrupting history

## Integration with Development Workflow

### Typical Development Cycle

```bash
# 1. Make changes
vim Program.cs

# 2. Commit and push
git add .
git commit -m "Add new language provider"
git push origin claude/new-feature

# 3. Wait for workflow (1-3 min)
# Watch: https://github.com/.../actions

# 4. Pull the amended commit
git pull --force

# 5. Review test results
cat test-execution.log

# 6. If tests passed, continue developing
# If tests failed, fix and repeat
```

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Artifacts](https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts)
