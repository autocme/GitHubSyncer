# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml uv.lock ./

# Install dependencies using uv for faster builds
RUN pip install uv && uv pip install --system --no-cache .

# Copy application code
COPY . .

# Create non-root user and setup directories
RUN useradd -m -u 1000 appuser && \
    mkdir -p /repos && \
    chown -R appuser:appuser /app /repos && \
    chmod -R 755 /repos

# Add entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONPATH=/app
ENV MAIN_PATH=/repos

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/v1/health || exit 1

# Use entrypoint script for automatic setup
ENTRYPOINT ["/entrypoint.sh"]