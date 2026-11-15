# ==========================================
# NOVEXA Discord Bot - Production Dockerfile
# Optimized for Render Cloud Deployment
# ==========================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies:
# - ffmpeg: required for music streaming, audio encoding, and filters
# - libopus0: required by discord.py for Discord voice channel streaming
# - libsodium23 & build-essential: required for PyNaCl voice encryption
# - ca-certificates & curl: required for SSL verification and health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libopus0 \
    libsodium23 \
    ca-certificates \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for Docker layer caching
COPY requirements.txt .

# Upgrade pip and install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code (excluding items specified in .dockerignore)
COPY . .

# Ensure essential runtime directories exist
RUN mkdir -p /app/database /app/logs /app/assets /app/cache

# Expose web dashboard port (overridden automatically by Render via $PORT)
EXPOSE 8080

# Healthcheck for container runtimes
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Start NOVEXA Bot & Integrated Web Dashboard
CMD ["python", "main.py"]

