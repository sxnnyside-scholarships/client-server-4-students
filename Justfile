# CS4S Developer Task Runner
# Requires: https://github.com/casey/just

# Default command
default:
    @just --list

# Install all dependencies and setup git hooks
install:
    uv sync --all-groups
    uv run pre-commit install

# Run the application locally
dev:
    uv run python main.py

# Build a portable distribution package via PyInstaller
build:
    uv run python scripts/build_dist.py

# Run all automated tests
test:
    uv run pytest tests/ -v

# Run static type checking
typecheck:
    uv run mypy src/ tests/

# Run the code linter
lint:
    uv run ruff check .

# Format the codebase
format:
    uv run ruff format .

# Run the complete quality gate
check: format lint typecheck test
    @echo "All engineering gates passed!"

# Remove all temporary build caches and artifacts
clean:
    find . -type d -name "__pycache__" -not -path "*/.venv/*" -exec rm -rf {} +
    find . -type f -name "*.pyc" -not -path "*/.venv/*" -delete
    find . -type d -name ".pytest_cache" -not -path "*/.venv/*" -exec rm -rf {} +
    find . -type d -name ".mypy_cache" -not -path "*/.venv/*" -exec rm -rf {} +
    find . -type d -name ".ruff_cache" -not -path "*/.venv/*" -exec rm -rf {} +
    find . -type d -name "build" -not -path "*/.venv/*" -exec rm -rf {} +
    find . -type d -name "dist" -not -path "*/.venv/*" -exec rm -rf {} +
    find . -type d -name "*.egg-info" -not -path "*/.venv/*" -exec rm -rf {} +
