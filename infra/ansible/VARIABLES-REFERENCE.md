# Ansible Infrastructure — Variables Reference

> **IMPORTANT**: `group_vars/all.yml` is ANSIBLE_VAULT encrypted.
> This file documents all variables, their purpose, and their OpenBao paths.

## Variable Categories

### Infrastructure
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `vm_hostname` | iacgenie | — | VM hostname |
| `vm_ip` | 192.168.0.118 | — | VM IP address |
| `ansible_user` | mkanavi | — | SSH user |

### Docker
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `docker_version` | latest | — | Docker version |
| `docker_compose_version` | latest | — | Docker Compose version |
| `data_dir` | /home/mkanavi/docker/iacgenie | — | Base data directory |

### PostgreSQL
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `postgres_version` | 15 | — | PostgreSQL version |
| `postgres_user` | lightsrp | — | Database user |
| `postgres_db` | lightsrp | — | Database name |
| `postgres_password` | — | `iacgenie/kv/postgres/password` | Database password (from OpenBao) |
| `postgres_port` | 5432 | — | PostgreSQL port |

### Redis
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `redis_version` | 7 | — | Redis version |
| `redis_password` | — | `iacgenie/kv/redis/password` | Redis password (from OpenBao) |
| `redis_port` | 6379 | — | Redis port |

### MinIO
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `minio_root_user` | iacgenie | `iacgenie/kv/minio/root_user` | MinIO admin user |
| `minio_root_password` | — | `iacgenie/kv/minio/root_password` | MinIO admin password (from OpenBao) |
| `minio_port` | 9000 | — | MinIO API port |
| `minio_console_port` | 9001 | — | MinIO Console port |

### OpenBao
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `openbao_version` | 2.6.0 | — | OpenBao version |
| `openbao_port` | 8200 | — | OpenBao HTTP port |
| `openbao_root_token` | — | `iacgenie/kv/openbao/root_token` | OpenBao root token (from OpenBao) |
| `openbao_unseal_keys` | — | `iacgenie/kv/openbao/unseal_keys` | Shamir unseal keys (from OpenBao) |
| `openbao_data_dir` | /home/mkanavi/docker/iacgenie/data/openbao | — | OpenBao config directory |
| `openbao_raft_dir` | /home/mkanavi/docker/iacgenie/data/openbao_raft | — | OpenBao Raft DB directory |

### Keycloak
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `keycloak_version` | 26.0 | — | Keycloak version |
| `keycloak_port` | 8083 | — | Keycloak host port (maps to 8080 container) |
| `keycloak_admin_user` | admin | `iacgenie/kv/keycloak/admin_user` | Keycloak admin user |
| `keycloak_admin_password` | — | `iacgenie/kv/keycloak/admin_password` | Keycloak admin password (from OpenBao) |
| `keycloak_db_password` | — | `iacgenie/kv/keycloak/db_password` | Keycloak DB password (from OpenBao) |
| `keycloak_realm` | iacgenie | — | Default realm name |
| `keycloak_host` | auth.iacgenie.com | — | Keycloak hostname |

### Gitea
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `gitea_version` | 1.23.4 | — | Gitea version |
| `gitea_data_dir` | /home/mkanavi/docker/iacgenie/data/gitea | — | Gitea data directory |
| `gitea_web_port` | 3000 | — | Gitea web port |
| `gitea_ssh_port` | 2222 | — | Gitea SSH port |
| `gitea_db_password` | — | `iacgenie/kv/gitea/db_password` | Gitea DB password (from OpenBao) |
| `gitea_admin_password` | — | `iacgenie/kv/gitea/admin_password` | Gitea admin password (from OpenBao) |

### LightSerp
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `lightserp_api_port` | 8000 | — | LightSerp API host port |
| `lightserp_webui_port` | 3001 | — | LightSerp WebUI host port |
| `lightserp_api_secret` | — | `iacgenie/kv/lightserp/api_secret` | API secret (from OpenBao) |
| `lightserp_kc_client_secret` | — | `iacgenie/kv/lightserp/kc_client_secret` | Keycloak client secret (from OpenBao) |

### SearXNG
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `searxng_port` | 8082 | — | SearXNG host port |
| `searxng_secret` | — | `iacgenie/kv/searxng/secret` | SearXNG secret key (from OpenBao) |

### NSQD
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `nsqd_port` | 4150 | — | NSQD TCP port |
| `nsqd_http_port` | 4151 | — | NSQD HTTP port |

### Nginx
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `nginx_config_path` | /etc/nginx/conf.d/iacgenie-unified.conf | — | Nginx config path |
| `nginx_rate_limit` | 10r/s | — | General rate limit |

### Cloudflare
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `cloudflared_version` | 2025.6.0 | — | Cloudflared version |
| `cloudflared_tunnel_name` | iacgenie-tunnel | — | Tunnel name |
| `cloudflared_api_token` | — | `iacgenie/kv/cloudflare/api_token` | Cloudflare API token |
| `cloudflared_account_tag` | — | `iacgenie/kv/cloudflare/account_tag` | Cloudflare account tag |

### Backup
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `backup_dir` | /home/mkanavi/backups/encrypted | — | Backup destination |
| `backup_cron_schedule` | 0 2 * * * | — | Daily at 2 AM |
| `backup_encryption_key` | — | `iacgenie/kv/backup/encryption_key` | GPG encryption key |
| `backup_retention_days` | 30 | — | Days to keep backups |

### Monitoring (Prometheus/Grafana/Loki)
| Variable | Default | Vault Path | Description |
|----------|---------|------------|-------------|
| `prometheus_port` | 9090 | — | Prometheus web port |
| `grafana_port` | 3001 | — | Grafana web port |
| `grafana_admin_password` | — | `iacgenie/kv/grafana/admin_password` | Grafana admin password |
| `loki_retention` | 720h | — | Log retention (30 days) |
