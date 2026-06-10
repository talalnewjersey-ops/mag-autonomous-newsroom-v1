# ================================================================
# NEXUS-14: MoneyAbroadGuide Autonomous Newsroom V1
# Docker Container Configuration
# ================================================================

FROM python:3.11-slim

# Metadata
LABEL maintainer="MoneyAbroadGuide.com"
LABEL description="NEXUS-14 Autonomous Newsroom - 14-Agent AI System"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libffi-dev \
    libssl-dev \
    chromium \
    chromium-driver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p \
    /app/output/topics \
    /app/output/articles \
    /app/output/images \
    /app/output/reports \
    /app/logs/agents \
    /app/logs/errors \
    /app/config

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN groupadd -r nexus14 && \
    useradd -r -g nexus14 -d /app -s /sbin/nologin nexus14 && \
    chown -R nexus14:nexus14 /app

USER nexus14

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "from monitoring.health_check import HealthChecker; import asyncio; asyncio.run(HealthChecker({}).quick_check())" || exit 1

# Default command
CMD ["python", "main.py", "--mode", "scheduled"]

# ================================================================
# Build: docker build -t nexus14:latest .
# Run:   docker run -d --env-file .env --name nexus14 nexus14:latest
# ================================================================
