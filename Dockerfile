# Simple single-stage Dockerfile for Django-Ollama
FROM python:3.11-slim

# Install uv for package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0
ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r django && useradd -r -g django -m -s /bin/bash django

# Set working directory
WORKDIR /app

# Copy project files
COPY --chown=django:django . /app

# Install Python packages to system using uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

# Create directories that need write access
RUN mkdir -p /app/demo_project/staticfiles \
    && mkdir -p /app/demo_project/media \
    && mkdir -p /app/demo_project/logs \
    && mkdir -p /app/demo_project/db \
    && chmod +x /app/demo_project/docker_entrypoint.py \
    && chmod -R 755 /app \
    && chown -R django:django /app \
    && chmod 775 /app/demo_project/db

# Switch to django user
USER django

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Production command
CMD ["python", "demo_project/docker_entrypoint.py"]