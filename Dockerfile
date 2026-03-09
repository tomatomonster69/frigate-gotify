# Use Python 3.12 slim image for smaller size
FROM python:3.12-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Create config directory with proper ownership for appuser
RUN mkdir -p /app/config && chown appuser:appuser /app/config

USER appuser

# Set Python path
ENV PYTHONPATH=/app

# Expose Web UI port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:80/')" || exit 1

# Run the service
CMD ["python", "-m", "src.main"]
