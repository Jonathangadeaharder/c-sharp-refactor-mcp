#!/bin/bash
set -e

echo "Testing ts-morph CLI..."

# Check if built
if [ ! -f "dist/index.js" ]; then
    echo "Error: dist/index.js not found. Run ./build.sh first"
    exit 1
fi

# Test version command
echo "Testing version command..."
echo '{"command":"version","parameters":{}}' | node dist/index.js

echo ""
echo "✓ All tests passed!"
