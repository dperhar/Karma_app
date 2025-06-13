# Multi-stage build for better optimization
FROM python:3.11-slim as builder

# Install system dependencies in a single layer
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Create non-privileged user
RUN useradd -m appuser

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Setup minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Setup Selectel certificate
RUN mkdir -p /usr/local/share/ca-certificates/selectel && \
    curl -k https://s3.ru-1.storage.selcloud.ru -o /usr/local/share/ca-certificates/selectel/storage.crt && \
    update-ca-certificates

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Create logs directory and set permissions
RUN mkdir -p /app/logs && \
    chmod +x start.sh && \
    chown -R appuser:appuser /app

# Switch to non-privileged user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    AWS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
