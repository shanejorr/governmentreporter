# Multi-stage Dockerfile for GovernmentReporter MCP Server
# Optimized for production deployment with security best practices

# Stage 1: Build stage with full development tools
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager (faster than pip)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy dependency files and source code
COPY pyproject.toml uv.lock* ./
COPY src/ ./src/

# Install dependencies using uv sync
RUN uv sync --frozen

# Stage 2: Runtime stage with minimal footprint
FROM python:3.11-slim

# Set metadata labels
LABEL maintainer="GovernmentReporter"
LABEL description="MCP Server for semantic search of US government documents"
LABEL version="0.1.0"

# Create non-root user for security
RUN groupadd -r mcpserver && useradd -r -g mcpserver -u 1000 mcpserver

# Set working directory
WORKDIR /app

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /build/.venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"

# Copy application code
COPY src/ /app/src/
COPY logging.yaml /app/logging.yaml
COPY pyproject.toml /app/pyproject.toml

# Create necessary directories with proper permissions
RUN mkdir -p /app/data/qdrant /app/data/progress /app/logs && \
    chown -R mcpserver:mcpserver /app

# Switch to non-root user
USER mcpserver

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV QDRANT_DB_PATH=/app/data/qdrant/qdrant_db

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; from governmentreporter.server.config import ServerConfig; sys.exit(0)"

# Expose MCP server port (if applicable)
# EXPOSE 8080

# Volume for persistent data
VOLUME ["/app/data", "/app/logs"]

# Default command: start MCP server
CMD ["python", "-m", "governmentreporter.server"]

# Alternative commands (uncomment as needed):
# For ingestion:
# CMD ["python", "-m", "governmentreporter.cli.main", "ingest", "scotus", "--start-date", "2024-01-01", "--end-date", "2024-12-31"]
# For query testing:
# CMD ["python", "-m", "governmentreporter.cli.main", "query", "constitutional law"]
