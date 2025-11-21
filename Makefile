.PHONY: help install install-dev test test-cov lint format clean build publish docs

help:
	@echo "Available commands:"
	@echo "  make install       - Install package"
	@echo "  make install-dev   - Install package with dev dependencies"
	@echo "  make test          - Run tests"
	@echo "  make test-cov      - Run tests with coverage"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make build         - Build package"
	@echo "  make publish       - Publish to PyPI"
	@echo "  make docs          - Generate documentation"
	@echo "  make security      - Run security checks"
	@echo "  make all           - Run format, lint, and test"

install:
	uv sync

install-dev:
	uv sync --dev --all-extras

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ -v --cov=anime_downloader --cov-report=html --cov-report=term

lint:
	@echo "Running ruff..."
	uv run ruff check anime_downloader tests
	@echo "Running mypy..."
	uv run mypy anime_downloader --ignore-missing-imports || true
	@echo "Checking import order..."
	uv run isort --check-only anime_downloader tests
	@echo "Checking code format..."
	uv run black --check anime_downloader tests

format:
	@echo "Formatting with black..."
	uv run black anime_downloader tests
	@echo "Sorting imports..."
	uv run isort anime_downloader tests
	@echo "Done!"

security:
	@echo "Running bandit security scan..."
	uv run bandit -r anime_downloader -f json -o bandit-report.json || true
	@echo "Running safety check..."
	uv run safety check || true

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Done!"

build: clean
	@echo "Building package..."
	uv build
	@echo "Done!"

publish: build
	@echo "Publishing to PyPI..."
	uv publish
	@echo "Done!"

docs:
	@echo "Documentation is in docs/ directory"
	@echo "API docs: docs/API.md"

all: format lint test
	@echo "All checks passed!"

# Development helpers
run-cli:
	uv run python -m anime_downloader.main

run-gui:
	uv run python -m anime_downloader.main --gui

watch-tests:
	uv run pytest-watch tests/ -v

profile:
	uv run python -m cProfile -o profile.stats -m anime_downloader.main
	uv run python -m pstats profile.stats

# Docker commands (if needed in future)
docker-build:
	docker build -t animepahe-dl .

docker-run:
	docker run -it --rm animepahe-dl

# Git helpers
git-clean:
	git clean -fdx

pre-commit: format lint test
	@echo "Pre-commit checks passed!"
