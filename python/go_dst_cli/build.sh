#!/bin/bash
set -e

echo "Building Go dst CLI..."

# Check if Go is installed
if ! command -v go &> /dev/null; then
    echo "Error: Go is not installed"
    echo "Please install Go 1.21+ from https://go.dev/dl/"
    exit 1
fi

# Check Go version
GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')
REQUIRED_VERSION="1.21"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$GO_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Go $REQUIRED_VERSION or higher is required (found $GO_VERSION)"
    exit 1
fi

# Download dependencies
echo "Downloading dependencies..."
go mod download

# Build binary
echo "Building binary..."
go build -o bin/go-dst-cli main.go

# Make executable
chmod +x bin/go-dst-cli

echo "✓ Build complete!"
echo "Binary location: $(pwd)/bin/go-dst-cli"
echo ""
echo "Test with: echo '{\"command\":\"version\",\"parameters\":{}}' | ./bin/go-dst-cli"
