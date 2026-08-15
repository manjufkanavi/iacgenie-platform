# =============================================================================
# IacGenie Backend — Multi-Stage Docker Build
# =============================================================================
# Stage 1: Install OpenTofu binary
# Stage 2: Install Python deps (with build cache)
# Stage 3: Production — minimal runtime image
# =============================================================================

# ---- Stage 1: OpenTofu binary ----
FROM debian:bookworm-slim AS tofu-builder

RUN ARCH=$(uname -m) && \
    case "$ARCH" in \
        x86_64) TOFU_ARCH="amd64";; \
        aarch64) TOFU_ARCH="arm64";; \
        *) TOFU_ARCH="amd64";; \
    esac && \
    curl --proto '=https' --tlsv1.2 -fsSL \
        "https://github.com/opentofu/opentofu/releases/latest/download/tofu_1.12.5_linux_${TOFU_ARCH}.zip" \
        -o /tmp/tofu.zip && \
    unzip -o /tmp/tofu.zip -d /tmp/ && \
    mv /tmp/tofu /usr/local/bin/tofu && \
    rm -f /tmp/tofu.zip

# ---- Stage 2: Install Python deps ----
FROM python:3.11-slim AS deps

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install only runtime system deps (build tools not needed at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# ---- Stage 3: Production ----
FROM python:3.11-slim AS production

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/usr/local/bin:$PATH"

# Copy OpenTofu from builder
COPY --from=tofu-builder /usr/local/bin/tofu /usr/local/bin/tofu

# Copy Python deps from deps stage
COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY . /app

# Expose port
EXPOSE 8000

# Set environment variables for PostgreSQL (defaults that can be overridden)
ENV DATABASE_PROVIDER=postgres
ENV POSTGRES_HOST=localhost
ENV POSTGRES_PORT=5432
ENV POSTGRES_DATABASE=iacgenie
ENV POSTGRES_USER=iacgenie_user
# ENV POSTGRES_PASSWORD=iacgenie_dev_password
ENV HOST=0.0.0.0
ENV PORT=8000

# Create non-root user for running the application
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser
RUN chown -R appuser:appgroup /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start the application
CMD ["python", "start.py"]
