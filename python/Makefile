.PHONY: help install install-dev test lint format clean run build

help:
	@echo "Available commands:"
	@echo "  make install       - Install package"
	@echo "  make install-dev   - Install with dev dependencies"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linters (ruff, mypy)"
	@echo "  make format        - Format code (black, ruff)"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make run           - Run MCP server"
	@echo "  make build         - Build distribution packages"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest

test-verbose:
	pytest -v -s

test-coverage:
	pytest --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

lint:
	ruff check src tests
	mypy src

format:
	black src tests
	ruff check --fix src tests

clean:
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:
	python -m refactor_mcp.cli

run-debug:
	python -m refactor_mcp.cli --log-level DEBUG

run-sse:
	python -m refactor_mcp.cli --transport sse --port 8000

build:
	pip install build
	python -m build

# Development helpers
check: format lint test
	@echo "✓ All checks passed!"

watch-test:
	pytest-watch

# Docker commands (optional)
docker-build:
	docker build -t refactor-mcp:latest .

docker-run:
	docker run -it --rm refactor-mcp:latest
