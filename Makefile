# Makefile for django-ollama package development

.PHONY: help install install-dev test test-cov lint format check clean build publish docs

# Default target
help:
	@echo "Available commands:"
	@echo "  install       Install package in development mode"
	@echo "  install-dev   Install package with development dependencies"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage report"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black and isort"
	@echo "  check        Run all checks (lint, test, etc.)"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build package"
	@echo "  publish      Publish package to PyPI"
	@echo "  docs         Build documentation"
	@echo "  pre-commit   Install pre-commit hooks"

# Installation
install:
	uv pip install -e .

install-dev:
	uv pip install -e .[dev]
	uv pip install -r requirements-dev.txt

# Testing
test:
	pytest

test-cov:
	pytest --cov=src/django_ollama --cov-report=html --cov-report=term-missing

test-quick:
	pytest -x --tb=short

# Code quality
lint:
	flake8 src/ tests/
	mypy src/django_ollama
	bandit -r src/

format:
	black src/ tests/
	isort src/ tests/

check: lint test

# Pre-commit
pre-commit:
	pre-commit install
	pre-commit run --all-files

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Building and publishing
build: clean
	python -m build

publish-test: build
	twine upload --repository testpypi dist/*

publish: build
	twine upload dist/*

# Documentation
docs:
	cd docs && make html

docs-serve:
	cd docs && make serve

# Development utilities
shell:
	python -c "import django; django.setup()"
	python manage.py shell

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

# Docker development (if using Docker)
docker-build:
	docker build -t django-ollama-dev .

docker-test:
	docker run --rm django-ollama-dev pytest

# Ollama development helpers
ollama-pull-models:
	@echo "Pulling common Ollama models for development..."
	ollama pull llama3.2:1b
	ollama pull llama3.2:3b

ollama-start:
	@echo "Starting Ollama server..."
	ollama serve

# Version bumping (using setuptools-scm)
version:
	python -c "from setuptools_scm import get_version; print(get_version())"

# Security checks
security:
	bandit -r src/
	safety check

# Performance testing
perf-test:
	locust --host=http://localhost:8000