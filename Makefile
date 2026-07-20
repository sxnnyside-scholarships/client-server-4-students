.PHONY: help install install-dev test clean

help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development/testing dependencies"
	@echo "  make test         - Run all automated tests"
	@echo "  make clean        - Remove Python cache files"

install:
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=term-missing

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
