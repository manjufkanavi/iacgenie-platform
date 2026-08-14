#!/bin/bash
# OpenBao health check cron job
# Runs every 5 minutes to restart OpenBao if container has stopped

STATUS=$(docker inspect --format="{{ .State.Status }}" iacgenie_openbao 2>/dev/null || echo "stopped")
if [ "$STATUS" != "running" ]; then
  echo "$(date) OpenBao is $STATUS, restarting..." >> /var/log/openbao-health.log
  docker compose -f /home/mkanavi/docker/iacgenie/docker-compose.yml restart openbao
fi
