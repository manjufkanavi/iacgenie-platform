# =============================================================================
# SAST Toolchain Image
# Bundles static-analysis tools for Python + TypeScript/Node.js monorepos.
# Used by Gitea Actions CI to run linting/security scans with JSON output.
#
# Tools:
#   Python : ruff, bandit, semgrep, mypy
#   Node/TS: eslint + typescript-eslint, gitleaks (secrets)
#   Utils  : jq, git, curl
# =============================================================================

# ---- Stage 1: Build gitleaks (Go binary) -----------------------------------
FROM golang:1.22-alpine AS gitleaks-builder
ARG GITLEAKS_VERSION=v8.18.2
RUN go install github.com/zricethezav/gitleaks/v8@${GITLEAKS_VERSION}

# ---- Stage 2: Final image ---------------------------------------------------
FROM python:3.12-slim

ENV NODE_MAJOR=20 \
    NPM_CONFIG_PREFIX=/root/.npm-global \
    PATH="/root/.npm-global/bin:${PATH}"

# System deps + Node.js 20 LTS via nodesource
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        git \
        jq \
        gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" \
        | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Gitleaks binary from builder stage
COPY --from=gitleaks-builder /go/bin/gitleaks /usr/local/bin/gitleaks

# Python SAST tools (pinned)
RUN pip install --no-cache-dir \
        ruff==0.4.8 \
        bandit==1.7.9 \
        semgrep==1.78.0 \
        mypy==1.10.0 \
        flake8==7.1.1 \
        checkov==3.2.529

# Node/TS SAST tools (pinned)
RUN npm install -g \
        eslint@8.57.0 \
        typescript@5.4.5 \
        typescript-eslint@7.13.1 \
        @typescript-eslint/parser@7.13.1 \
        @typescript-eslint/eslint-plugin@7.13.1 \
    && npm cache clean --force

# Version-print helper for CI verification
COPY sast-version /usr/local/bin/sast-version
RUN chmod +x /usr/local/bin/sast-version

WORKDIR /workspace
CMD ["/bin/bash"]
