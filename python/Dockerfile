# Multi-stage Dockerfile for refactor-mcp Python rewrite
# Stage 1: Build Roslyn CLI
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS roslyn-builder

WORKDIR /build/roslyn_cli

# Copy Roslyn CLI source
COPY roslyn_cli/RoslynCLI.csproj .
COPY roslyn_cli/Program.cs .

# Restore dependencies
RUN dotnet restore

# Build and publish self-contained Roslyn CLI
RUN dotnet publish -c Release -r linux-x64 --self-contained -o /app/roslyn_cli/bin

# Stage 2: Build Python environment
FROM python:3.11-slim AS python-base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements
COPY pyproject.toml .
COPY README.md .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Stage 3: Final runtime image
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 mcp && \
    mkdir -p /app /workspace && \
    chown -R mcp:mcp /app /workspace

WORKDIR /app

# Copy Python environment from python-base
COPY --from=python-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-base /usr/local/bin /usr/local/bin

# Copy Roslyn CLI from roslyn-builder
COPY --from=roslyn-builder /app/roslyn_cli/bin /app/roslyn_cli/bin
RUN chmod +x /app/roslyn_cli/bin/roslyn-cli

# Copy application source
COPY --chown=mcp:mcp src ./src
COPY --chown=mcp:mcp pyproject.toml .
COPY --chown=mcp:mcp README.md .

# Install application in editable mode
RUN pip install --no-cache-dir -e .

# Switch to non-root user
USER mcp

# Set environment variables
ENV REFACTOR_MCP_ALLOWED_ROOT_PATHS="/workspace" \
    REFACTOR_MCP_LOG_LEVEL="INFO" \
    REFACTOR_MCP_ROSLYN_CLI_PATH="/app/roslyn_cli/bin/roslyn-cli" \
    PYTHONUNBUFFERED=1

# Expose port for SSE transport (optional)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; from refactor_mcp.config import Config; Config.load(); sys.exit(0)"

# Default command: run with stdio transport
CMD ["python", "-m", "refactor_mcp.cli"]

# Alternative commands:
# SSE transport: CMD ["python", "-m", "refactor_mcp.cli", "--transport", "sse", "--port", "8000"]
# Debug mode: CMD ["python", "-m", "refactor_mcp.cli", "--log-level", "DEBUG"]
