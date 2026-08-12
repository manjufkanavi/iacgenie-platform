FROM node:22-slim AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci 2>/dev/null || npm install

COPY . .
RUN npm run build

FROM node:22-slim

WORKDIR /app

# Install curl and download LightPanda binary
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Download platform-appropriate LightPanda binary
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
      TARGET="x86_64-linux"; \
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
      TARGET="aarch64-linux"; \
    else \
      TARGET="x86_64-linux"; \
    fi && \
    curl -L -o /usr/local/bin/lightpanda \
      "https://github.com/lightpanda-io/browser/releases/download/nightly/lightpanda-$TARGET" && \
    chmod +x /usr/local/bin/lightpanda

COPY --from=builder /app/package.json /app/package-lock.json* ./
RUN npm ci --omit=dev 2>/dev/null || npm install --omit=dev

COPY --from=builder /app/dist ./dist

# Create non-root user for running the application
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 3071

CMD ["node", "dist/server.js"]
