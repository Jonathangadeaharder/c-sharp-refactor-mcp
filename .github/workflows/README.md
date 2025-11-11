# GitHub Actions Workflows

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
