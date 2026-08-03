#!/usr/bin/env bash
#
# Pre-push hook: sync to both GitHub (origin) and Gitea simultaneously
#
# Usage: Place in .git/hooks/pre-push
# Checks if gitea.iacgenie.com is reachable; if yes, pushes to both remotes.
# If Gitea is down, pushes only to GitHub with a warning.
#
# IMPORTANT: Uses GIT_DUAL_SYNC env var to prevent recursive hook execution.
#

set -euo pipefail

GITEA_REMOTE="${GITEA_REMOTE:-gitea}"
GITEA_BASE_URL="${GITEA_BASE_URL:-https://gitea.iacgenie.com}"
GITEA_TIMEOUT="${GITEA_TIMEOUT:-5}"

# Prevent recursive hook execution
if [ -n "${GIT_DUAL_SYNC:-}" ]; then
    exit 0
fi

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# The trigger_remote is the first argument passed by git
TRIGGER_REMOTE="${1:-}"
CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo "")"

# If no branch, skip (likely a tag push or detached HEAD)
if [ -z "$CURRENT_BRANCH" ]; then
    exit 0
fi

echo ""
echo "--- Gitea Dual-Remote Sync ---"

# Function to check if Gitea is reachable
check_gitea() {
    local status_code
    status_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$GITEA_TIMEOUT" --max-time "$((GITEA_TIMEOUT * 2))" "$GITEA_BASE_URL" 2>/dev/null || echo "000")

    if [[ "$status_code" -ge 200 && "$status_code" -lt 500 ]]; then
        return 0  # Up
    else
        return 1  # Down
    fi
}

# Internal push function: sets env var to prevent recursion
push_internal() {
    local remote="$1"
    GIT_DUAL_SYNC=1 git push "$remote" "$CURRENT_BRANCH"
}

# If Gitea is reachable, push to both remotes
if check_gitea; then
    echo -e "${GREEN}✓${NC} Gitea ($GITEA_BASE_URL) is UP"

    # Determine trigger remote
    if [ -z "$TRIGGER_REMOTE" ]; then
        TRIGGER_REMOTE="origin"
    fi

    # Push to the trigger remote first (using env var to prevent recursion)
    echo "Pushing to $TRIGGER_REMOTE..."
    if push_internal "$TRIGGER_REMOTE" 2>&1; then
        echo -e "${GREEN}✓${NC} Pushed to $TRIGGER_REMOTE"
    else
        echo -e "${RED}✗${NC} Failed to push to $TRIGGER_REMOTE"
        exit 1
    fi

    # Push to the OTHER remote using --no-verify + env var to prevent recursion
    if [ "$TRIGGER_REMOTE" != "$GITEA_REMOTE" ]; then
        echo "Pushing to $GITEA_REMOTE..."
        if push_internal "$GITEA_REMOTE" --no-verify 2>&1; then
            echo -e "${GREEN}✓${NC} Pushed to $GITEA_REMOTE"
        else
            echo -e "${RED}✗${NC} Failed to push to $GITEA_REMOTE (non-blocking)"
        fi
    else
        # Trigger was gitea, push to origin
        echo "Pushing to origin..."
        if push_internal "origin" --no-verify 2>&1; then
            echo -e "${GREEN}✓${NC} Pushed to origin"
        else
            echo -e "${RED}✗${NC} Failed to push to origin (non-blocking)"
        fi
    fi
else
    echo -e "${YELLOW}⚠${NC} Gitea ($GITEA_BASE_URL) is DOWN — pushing to GitHub only"
    echo -e "${YELLOW}⚠${NC} Gitea will sync on next cron job (every 6 hours)"
    echo ""

    # When Gitea is down, always push to origin
    TARGET="$TRIGGER_REMOTE"
    if [ "$TARGET" = "$GITEA_REMOTE" ]; then
        TARGET="origin"
    fi
    if [ -z "$TARGET" ]; then
        TARGET="origin"
    fi

    echo "Pushing to $TARGET..."
    if push_internal "$TARGET" 2>&1; then
        echo -e "${GREEN}✓${NC} Pushed to $TARGET ($CURRENT_BRANCH)"
    else
        echo -e "${RED}✗${NC} Failed to push to $TARGET"
        exit 1
    fi
fi

echo "--- Sync Complete ---"
echo ""

exit 0
