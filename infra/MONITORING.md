# IacGenie Platform — Monitoring Dashboard Documentation

> **Last Updated**: 2026-08-16  
> **Grafana URL**: https://grafana.iacgenie.com  
> **Prometheus URL**: https://prometheus.iacgenie.com  
> **Loki URL**: https://loki.iacgenie.com

---

## Monitoring Stack Overview

| Component | Port | Purpose | Retention |
|-----------|------|---------|-----------|
| Prometheus | 9090 | Metrics collection & storage | 30 days |
| Grafana | 3001 | Dashboards & visualization | — |
| Loki | 3100 | Log aggregation | 30 days |
| Promtail | — | Log shipper | — |
| Node Exporter | 9100 | System metrics | 30 days |

---

## Dashboards

### 1. Service Health Dashboard

**Purpose**: Real-time service status  
**Key Panels**:
- Service uptime (up metric)
- Container health status
- Restart count
- Memory usage per container

**PromQL Examples**:
```promql
# Service availability
up{job="iacgenie"}

# Memory usage
container_memory_usage_bytes{container=~"iacgenie_.*"}

# CPU usage
rate(container_cpu_usage_seconds_total{container=~"iacgenie_.*"}[5m])
```

### 2. Infrastructure Dashboard

**Purpose**: VM-level metrics  
**Key Panels**:
- CPU usage (per core)
- Memory usage
- Disk usage
- Network I/O
- Load average

**PromQL Examples**:
```promql
# CPU usage
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disk usage
(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100
```

### 3. Application Dashboard

**Purpose**: Application-level metrics  
**Key Panels**:
- HTTP request rate
- Error rate (5xx)
- Response time (p50, p95, p99)
- Active connections

**PromQL Examples**:
```promql
# Request rate
rate(http_requests_total{job="iacgenie"}[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### 4. Database Dashboard

**Purpose**: PostgreSQL & Redis metrics  
**Key Panels**:
- Connection count
- Query rate
- Cache hit ratio (Redis)
- Replication lag

**PromQL Examples**:
```promql
# PostgreSQL connections
pg_stat_activity_count{datname="iacgenie"}

# Redis hit rate
redis_hits_total / (redis_hits_total + redis_misses_total)
```

### 5. Security Dashboard

**Purpose**: Security metrics  
**Key Panels**:
- Failed login attempts
- Rate limit violations
- WAF blocks (CrowdSec)
- Falco alerts

---

## Alert Rules

### Critical Alerts

| Alert | Condition | Severity | Notification |
|-------|-----------|----------|-------------|
| ServiceDown | `up == 0` for 2m | Critical | PagerDuty + Email |
| HighErrorRate | `rate(http_requests_total{status=~"5.."}[5m]) > 0.1` | Critical | PagerDuty |
| DiskFull | `node_filesystem_avail_bytes{mountpoint="/"} < 5GB` | Critical | Email |
| OpenBaoSealed | `bao_operator_unsealed == 0` | Critical | Email |

### Warning Alerts

| Alert | Condition | Severity | Notification |
|-------|-----------|----------|-------------|
| HighMemory | `container_memory_usage > 80%` | Warning | Email |
| HighCPU | `container_cpu_usage > 80%` | Warning | Email |
| SlowResponse | `histogram_quantile(0.95, ...) > 2s` | Warning | Email |
| DiskSpaceLow | `node_filesystem_avail < 10GB` | Warning | Email |

### Info Alerts

| Alert | Condition | Severity | Notification |
|-------|-----------|----------|-------------|
| ServiceRestarted | `container_restarts > 0` | Info | Email |
| BackupCompleted | `backup_completed == 1` | Info | Email |

---

## Log Queries (Loki)

### Application Logs

```lucene
# All error logs
{job="iacgenie"} |= "ERROR"

# Specific service
{container="iacgenie_backend"} |= "error"

# Last 1 hour
{container=~"iacgenie_.*"} |~ "warn|error"
```

### Nginx Logs

```lucene
# 5xx errors
{job="nginx"} |= "500" or |= "502" or |= "503" or |= "504"

# Slow requests
{job="nginx"} | json | status >= "500"
```

---

## Grafana Configuration

### Data Sources

| Name | Type | URL |
|------|------|-----|
| Prometheus | Prometheus | http://127.0.0.1:9090 |
| Loki | Loki | http://127.0.0.1:3100 |

### Admin Credentials

```bash
# Get from OpenBao
bao kv get iacgenie/kv/monitoring/grafana_admin_password
```

---

## Alertmanager Configuration

**Location**: `infra/configs/alertmanager/alertmanager.yml`

**Notification Channels**:
- Email (admin)
- Slack (optional)
- PagerDuty (optional)

---

## Troubleshooting

### Prometheus Not Scraping

```bash
# Check Prometheus status
curl -s http://127.0.0.1:9090/-/healthy

# Check targets
curl -s http://127.0.0.1:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health != "up")'

# Check Prometheus logs
docker logs iacgenie_prometheus
```

### Grafana Dashboard Empty

```bash
# Check data source connectivity
curl -s http://127.0.0.1:3002/api/datasources | jq '.[] | select(.type=="prometheus")'

# Check Grafana logs
docker logs iacgenie_grafana
```

### Loki Not Receiving Logs

```bash
# Check Promtail status
curl -s http://127.0.0.1:9080/ready

# Check Loki status
curl -s http://127.0.0.1:3100/ready

# Check Promtail logs
docker logs iacgenie_promtail
```
