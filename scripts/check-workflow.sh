#!/bin/bash

# Script to check if GitHub Actions workflow has completed and amended the commit

echo "🔍 Checking GitHub Actions Workflow Status..."
echo "================================================"
echo ""

BRANCH="claude/roslyn-mcp-server-architecture-011CV1um2aCttcQpVHJkDbqQ"
MAX_ATTEMPTS=20
WAIT_SECONDS=15

for i in $(seq 1 $MAX_ATTEMPTS); do
    echo "[$i/$MAX_ATTEMPTS] Fetching from remote..."
    git fetch origin --quiet

    # Check if build-test.log exists on remote
    if git ls-tree -r origin/$BRANCH --name-only | grep -q "^build-test.log$"; then
        echo ""
        echo "✅ SUCCESS! Workflow has completed and amended the commit!"
        echo ""
        echo "📥 Pulling the amended commit..."
        git pull --force origin $BRANCH
        echo ""

        if [ -f "build-test.log" ]; then
            echo "📄 Build and Test Log:"
            echo "================================================"
            cat build-test.log
            echo ""
            echo "================================================"
            echo "✅ All done! Log file is now in your repository."
        else
            echo "⚠️  Log file exists on remote but not pulled yet. Try: git pull --force"
        fi

        exit 0
    else
        echo "   ⏳ Workflow still running or queued..."

        if [ $i -lt $MAX_ATTEMPTS ]; then
            echo "   Waiting ${WAIT_SECONDS}s before next check..."
            sleep $WAIT_SECONDS
        fi
    fi
done

echo ""
echo "⏰ Timeout reached after $(($MAX_ATTEMPTS * $WAIT_SECONDS)) seconds."
echo ""
echo "The workflow may still be queued or running. You can:"
echo "  1. View it on GitHub: https://github.com/Jonathangadeaharder/c-sharp-refactor-mcp/actions"
echo "  2. Run this script again: ./check-workflow.sh"
echo "  3. Manually check: git fetch origin && git ls-tree -r origin/$BRANCH --name-only | grep log"
