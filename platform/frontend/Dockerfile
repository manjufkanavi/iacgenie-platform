# =============================================================================
# IacGenie Frontend — Multi-Stage Docker Build
# =============================================================================
# Build context: platform/ directory
# Platform-level shared files (App.tsx, types.ts, constants.ts) are copied
# to the build root so sibling imports resolve correctly.
#
# Usage: docker build --platform linux/amd64 -t iacgenie-frontend:latest \
#   -f platform/frontend/Dockerfile platform/
# =============================================================================

# ---- Builder ----
FROM node:22-alpine AS builder

WORKDIR /app

# Copy package.json from frontend subdirectory
COPY frontend/package.json ./package.json

# Install dependencies
RUN npm ci 2>/dev/null || npm install

# Copy frontend source code (creates /app with all frontend subdirs)
COPY frontend/ .

# Copy platform-level shared files to root so ../imports resolve correctly
COPY App.tsx ./App.tsx
COPY types.ts ./types.ts
COPY types.ts ./store/types.ts
COPY constants.ts ./constants.ts

# Build the app
RUN npm run build

# ---- Production ----
FROM nginx:1.25-alpine AS production

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/iacgenie.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
