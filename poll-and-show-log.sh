#!/bin/bash

echo "Workflow is still running. Polling for completion..."
echo "This typically takes 3-5 minutes. Checking every 10 seconds..."
echo ""

BRANCH="claude/roslyn-mcp-server-architecture-011CV1um2aCttcQpVHJkDbqQ"

for i in {1..30}; do
    echo "[$i/30] Checking..."
    git fetch origin --quiet 2>&1

    if git ls-tree -r origin/$BRANCH --name-only | grep -q "^build-test\.log$"; then
        echo ""
        echo "✅ WORKFLOW COMPLETED! Log file detected."
        echo ""
        echo "Pulling the amended commit..."
        git pull --force origin $BRANCH
        echo ""
        echo "======================================"
        echo "📄 build-test.log contents:"
        echo "======================================"
        cat build-test.log
        echo ""
        echo "======================================"
        echo "✅ Done!"
        exit 0
    fi

    sleep 10
done

echo ""
echo "⏰ Timeout after 5 minutes. Workflow may still be running."
echo "Check: https://github.com/Jonathangadeaharder/c-sharp-refactor-mcp/actions"
