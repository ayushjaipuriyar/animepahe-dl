# Multi-stage build for smaller final image
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock .python-version ./
COPY anime_downloader ./anime_downloader

# Install dependencies and build
RUN uv sync --frozen --no-dev && \
    uv build --wheel

# Final stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fzf \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash animeuser

# Set working directory
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy application code
COPY --chown=animeuser:animeuser . .

# Copy built wheel from builder
COPY --from=builder /app/dist/*.whl /tmp/

# Install application using uv
RUN uv pip install --system /tmp/*.whl && \
    rm -rf /tmp/*.whl

# Create directories for downloads and config
RUN mkdir -p /downloads /config && \
    chown -R animeuser:animeuser /downloads /config

# Switch to non-root user
USER animeuser

# Set volumes
VOLUME ["/downloads", "/config"]

# Set environment variables for config location
ENV XDG_CONFIG_HOME=/config \
    DOWNLOAD_DIR=/downloads

# Default command
ENTRYPOINT ["animepahe-dl"]
CMD ["--help"]
