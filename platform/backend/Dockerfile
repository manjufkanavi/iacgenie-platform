FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    curl \
    libxmlsec1-dev \
    pkg-config \
    unzip \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install OpenTofu Standalone CLI
RUN curl --proto '=https' --tlsv1.2 -fsSL https://get.opentofu.org/install-opentofu.sh -o install-opentofu.sh && \
    chmod +x install-opentofu.sh && \
    ./install-opentofu.sh --install-method standalone && \
    rm install-opentofu.sh


# Copy requirements file
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

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

# Health check - wait 10 seconds before starting health checks to allow app startup
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Create non-root user for running the application
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser
RUN chown -R appuser:appgroup /app
USER appuser

# Start the application
CMD ["python", "start.py"]
