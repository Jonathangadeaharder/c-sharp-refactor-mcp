#!/bin/bash
# Test script for Roslyn CLI tool

set -e

echo "Testing Roslyn CLI tool..."
echo ""

# Find the executable
if [ -f "bin/roslyn-cli" ]; then
    CLI="./bin/roslyn-cli"
elif [ -f "bin/Release/net8.0/roslyn-cli" ]; then
    CLI="dotnet bin/Release/net8.0/RoslynCLI.dll"
else
    CLI="dotnet run --"
fi

echo "Using CLI: ${CLI}"
echo ""

# Test 1: Version command
echo "Test 1: Version command"
echo '{"command":"version","parameters":{}}' | ${CLI}
echo "✓ Version command passed"
echo ""

# Test 2: Load project (if test project exists)
TEST_PROJECT="../../test-project/SampleProject/SampleProject.csproj"
if [ -f "${TEST_PROJECT}" ]; then
    echo "Test 2: Load project"
    echo "{\"command\":\"load_project\",\"parameters\":{\"projectPath\":\"${TEST_PROJECT}\"}}" | ${CLI}
    echo "✓ Load project passed"
    echo ""
else
    echo "Test 2: Skipped (test project not found)"
    echo ""
fi

# Test 3: Invalid command (should error gracefully)
echo "Test 3: Invalid command (should error)"
echo '{"command":"invalid_command","parameters":{}}' | ${CLI} || echo "✓ Error handling works"
echo ""

echo "All tests passed!"
