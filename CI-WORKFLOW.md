# CI Workflow: Build-Test-Log Pattern

## Quick Start

After pushing to your branch, the GitHub Action will:
1. Build and test your code
2. Generate `build-test.log` with full output
3. **Amend the log to your commit**
4. Force push back to your branch

To see the results:

```bash
git pull --force
cat build-test.log
```

## Why This Pattern?

Traditional CI/CD logs live in the CI platform (GitHub Actions UI). This workflow stores the log **in the commit itself**, giving you:

✅ **Permanent record** - Logs don't expire
✅ **Offline access** - Clone the repo, get the logs
✅ **Version controlled** - Logs tied to specific commits
✅ **No dashboard needed** - Just `cat build-test.log`
✅ **Git bisect friendly** - See build status for any historical commit

## How It Works

```
┌─────────────────────────────────────────────────────┐
│  1. You push commit ABC123                          │
└────────────┬────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────┐
│  2. GitHub Actions triggers                         │
│     - Checks out ABC123                             │
│     - Runs dotnet restore, build, test              │
│     - Captures all output → build-test.log          │
└────────────┬────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────┐
│  3. Workflow amends the commit                      │
│     git add build-test.log                          │
│     git commit --amend --no-edit                    │
│     git push --force-with-lease                     │
└────────────┬────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────┐
│  4. Commit ABC123 now includes build-test.log       │
│     SHA changes to DEF456                           │
└─────────────────────────────────────────────────────┘
```

## Example Log File

```
================================================================
Build and Test Execution Log
================================================================
Commit: abc123def456789...
Branch: claude/roslyn-mcp-server-architecture-011CV1um2aCttcQpVHJkDbqQ
Timestamp: 2025-01-15 14:30:45 UTC
Triggered by: push
Actor: github-username
================================================================

>>> Restoring dependencies...
  Determining projects to restore...
  Restored RoslynRefactorServer.csproj (in 1.2 sec).
  Restored RoslynRefactorServer.Tests.csproj (in 0.8 sec).

>>> Building project...
Microsoft (R) Build Engine version 17.8.0
  RoslynRefactorServer -> bin/Release/net8.0/RoslynRefactorServer.dll
  RoslynRefactorServer.Tests -> bin/Release/net8.0/RoslynRefactorServer.Tests.dll

Build exit code: 0
✅ BUILD SUCCEEDED

>>> Running tests...
Test run for RoslynRefactorServer.Tests.dll (.NET 8.0)
  Starting test execution, please wait...

  Passed PathSecurityServiceTests.ValidateAndNormalizePath_WithAllowedPath_ShouldSucceed
  Passed PathSecurityServiceTests.ValidateAndNormalizePath_WithDisallowedPath_ShouldThrowSecurityException
  Passed PathSecurityServiceTests.ValidateSolutionFile_WithValidSolutionFile_ShouldSucceed
  Passed ModelTests.ReferenceLocation_ShouldSetAndGetProperties
  Passed BasicIntegrationTests.Project_ShouldCompile
  ... (15 tests total)

Passed!  - Failed:     0, Passed:    15, Skipped:     0, Total:    15

Test exit code: 0
✅ TESTS PASSED

================================================================
End of Build and Test Log
Completed at: 2025-01-15 14:31:02 UTC
================================================================
```

## Important: Force Pull Required

After the workflow runs, your local commit SHA will be different from the remote (because the commit was amended). You MUST force pull:

```bash
# ❌ Regular pull will fail
git pull

# ✅ Force pull to get the amended commit
git pull --force
```

Or reset to remote:

```bash
git fetch origin
git reset --hard origin/your-branch-name
```

## When Amendment Happens

| Event | Log Amendment | Reason |
|-------|---------------|--------|
| Push to branch | ✅ Yes | Safe to amend feature branches |
| Pull request | ❌ No | Shouldn't modify PR commits |
| Push to main | ✅ Yes* | *Only if workflow is enabled for main |

The log is **always** uploaded as an artifact (30-day retention) even when not amended.

## Status Indicators

The log uses clear status indicators:

- ✅ `BUILD SUCCEEDED` - Build completed without errors
- ❌ `BUILD FAILED` - Build encountered errors
- ✅ `TESTS PASSED` - All tests passed
- ❌ `TESTS FAILED` - One or more tests failed

## Checking Status Without Pulling

You can view the log on GitHub:

1. Navigate to your commit on github.com
2. Open `build-test.log` in the file tree
3. View the full build output

Or check the Actions tab for the workflow run.

## Collaboration Tips

When working in a team:

1. **Communicate**: Let teammates know about this pattern
2. **Document**: Point them to this file
3. **Branch Naming**: Use clear feature branch names
4. **Before Merge**: Always `git pull --force` before merging

## Disabling Amendment

To disable commit amendment (and only use artifact upload):

Edit `.github/workflows/build-and-test.yml`:

```yaml
# Find these steps and change their conditions:
- name: Amend commit with log file
  if: false  # Changed from: if: always() && github.event_name == 'push'

- name: Force push amended commit
  if: false  # Changed from: if: always() && github.event_name == 'push'
```

## Troubleshooting

### Error: "refusing to allow a GitHub App to create or update workflow"

**Solution**: The GITHUB_TOKEN doesn't have permission to modify workflows. This happens if you're trying to amend a commit that modifies `.github/workflows/*.yml`.

**Workaround**: Either:
1. Don't modify workflows and code in the same commit
2. Use a Personal Access Token instead of GITHUB_TOKEN

### Error: "failed to push some refs"

**Cause**: Branch protection rules prevent force push.

**Solution**: Either:
1. Exempt GitHub Actions bot from force push restrictions
2. Disable amendment (see above)
3. Use a branch without protection rules

### Log is empty or incomplete

**Cause**: Build/test commands failed early.

**Solution**: Check the Actions tab for the full workflow log. The `build-test.log` is only updated if the commands execute.

### Merge conflicts after force pull

**Cause**: You have uncommitted local changes.

**Solution**:
```bash
# Stash your changes
git stash

# Force pull
git pull --force

# Reapply your changes
git stash pop
```

## Technical Details

### Why --force-with-lease?

The workflow uses `--force-with-lease` instead of `--force`:

```bash
git push --force-with-lease origin ${{ github.ref_name }}
```

This is safer than `--force` because it:
- Checks the remote hasn't changed since we fetched
- Prevents accidental overwrites
- Fails if someone else pushed in the meantime

### Workflow Permissions

The workflow requires `contents: write`:

```yaml
permissions:
  contents: write  # Required to push commits
```

This is configured in the workflow file and uses the automatic `GITHUB_TOKEN`.

### Artifact Upload as Fallback

Even with amendment, logs are uploaded as artifacts:

```yaml
- name: Upload log as artifact (fallback)
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: build-test-log
    path: build-test.log
    retention-days: 30
```

This provides a fallback if:
- Amendment fails
- You're working with a pull request
- You need to compare logs across runs

## Best Practices

1. ✅ **Use descriptive commit messages** - The log is attached to your commit
2. ✅ **Review the log before merging** - Ensure tests passed
3. ✅ **Force pull immediately** - Don't let your local branch diverge
4. ✅ **Keep commits atomic** - One logical change per commit
5. ❌ **Don't amend public branches** - Use this pattern for feature branches
6. ❌ **Don't modify workflows and code together** - Can cause permission issues

## Alternatives Considered

### Traditional CI (No Amendment)

**Pros**: Standard pattern, no force pushes
**Cons**: Logs expire, requires CI dashboard access, not version controlled

### Separate Log Branch

**Pros**: No force push to feature branches
**Cons**: Disconnected from code, complex to navigate

### Commit Status API

**Pros**: Native GitHub feature
**Cons**: Doesn't store full logs, UI only

### Pull Request Comments

**Pros**: Visible in PR discussion
**Cons**: Only works for PRs, verbose, not tied to commits

## Further Reading

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Git Amend Documentation](https://git-scm.com/docs/git-commit#Documentation/git-commit.txt---amend)
- [Force Push Best Practices](https://git-scm.com/docs/git-push#Documentation/git-push.txt---force-with-leaseltrefnamegt)

## Questions?

If you encounter issues or have suggestions, please open an issue in the repository.
