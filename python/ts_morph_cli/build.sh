#!/bin/bash
set -e

echo "Building ts-morph CLI..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "Error: Node.js 18 or higher is required (found v$NODE_VERSION)"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Build TypeScript
echo "Compiling TypeScript..."
npm run build

# Make executable
chmod +x dist/index.js

echo "✓ Build complete!"
echo "Binary location: $(pwd)/dist/index.js"
echo ""
echo "Test with: echo '{\"command\":\"version\",\"parameters\":{}}' | node dist/index.js"
