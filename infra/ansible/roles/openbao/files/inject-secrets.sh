#!/bin/bash
# OpenBao Secret Injector — Docker entrypoint wrapper
# Usage: inject-secrets.sh <service-name> -- <command> [args...]
#
# This script:
#   1. Creates /var/run/approle/ directory
#   2. Runs the Python injector to fetch and inject secrets
#   3. Exec's the main command

set -e

SERVICE_NAME="${1:?Usage: inject-secrets.sh <service-name> -- <command>}"
shift

mkdir -p /var/run/approle

# Find the -- separator
CMD_START=""
for i in "$@"; do
  if [ "$i" = "--" ]; then
    shift
    break
  fi
done

exec python3 /usr/local/bin/openbao_injector.py "$SERVICE_NAME" -- "$@"
