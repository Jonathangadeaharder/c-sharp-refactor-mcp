#!/bin/bash
# Build script for Roslyn CLI tool

set -e

echo "Building Roslyn CLI tool..."

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     RUNTIME=linux-x64;;
    Darwin*)    RUNTIME=osx-x64;;
    MINGW*|MSYS*|CYGWIN*)   RUNTIME=win-x64;;
    *)          RUNTIME=linux-x64;;
esac

echo "Detected runtime: ${RUNTIME}"

# Build for current platform
echo "Building release configuration..."
dotnet build -c Release

echo "Publishing self-contained executable..."
dotnet publish -c Release -r ${RUNTIME} --self-contained -o bin

# Make executable (Unix only)
if [ "${RUNTIME}" != "win-x64" ]; then
    chmod +x bin/roslyn-cli
fi

echo ""
echo "✓ Build complete!"
echo "Executable: $(pwd)/bin/roslyn-cli"
echo ""
echo "Test with:"
echo "  echo '{\"command\":\"version\",\"parameters\":{}}' | ./bin/roslyn-cli"
