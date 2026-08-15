# =============================================================================
# LightSerp API — Multi-Stage Docker Build
# =============================================================================
# Stage 1: Install system deps + download LightPanda binary
# Stage 2: Install Node.js deps + copy source
# Stage 3: Production — minimal runtime
# =============================================================================

# ---- Stage 1: Download LightPanda binary ----
FROM node:22-alpine AS lightpanda

# Download platform-appropriate LightPanda binary
RUN apk add --no-cache curl ca-certificates && \
    ARCH=$(uname -m) && \
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

# ---- Stage 2: Install deps ----
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci 2>/dev/null || npm install

COPY . .
RUN npm run build

# ---- Stage 3: Production ----
FROM node:22-alpine AS production

WORKDIR /app

# Copy LightPanda from stage 1
COPY --from=lightpanda /usr/local/bin/lightpanda /usr/local/bin/lightpanda

# Copy Node.js deps
COPY --from=builder /app/package.json /app/package-lock.json* ./
RUN npm ci --omit=dev 2>/dev/null || npm install --omit=dev

# Copy built output
COPY --from=builder /app/dist ./dist

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup -h /app -s /sbin/nologin && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 3071

CMD ["node", "dist/server.js"]
