#!/bin/bash

# Check SearXNG health
echo "Checking SearXNG..."
if ! curl -s -f "http://localhost:8080/healthz" > /dev/null; then
  echo "❌ SearXNG health check failed"
  exit 1
fi
echo "✅ SearXNG is healthy"

# Check MCP Server
echo "Checking MCP Server..."
if ! curl -s -f "http://localhost:7805/health" > /dev/null; then
  echo "❌ MCP Server health check failed"
  exit 1
fi
echo "✅ MCP Server is healthy"

# Check Kono Gateway
echo "Checking Kono Gateway..."
if ! curl -s -f "http://localhost:8085/healthz" > /dev/null; then
  echo "❌ Kono Gateway health check failed"
  exit 1
fi
echo "✅ Kono Gateway is healthy"

echo "🎉 All services are healthy!"