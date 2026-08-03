# Operations Cheatsheet

## Quick Commands

```bash
# Deploy full stack
cd ~/iacgenie-platform
docker compose -f infra/docker-compose/docker-compose-unified.yml up -d

# Deploy just IaCGenie services
docker compose -f infra/docker-compose/docker-compose-iacgenie.yml up -d

# Deploy just LightSerp services
docker compose -f infra/docker-compose/docker-compose-lightsrp.yml up -d

# Check all service status
docker compose -f infra/docker-compose/docker-compose-unified.yml ps

# View recent logs for a service
docker compose -f infra/docker-compose/docker-compose-unified.yml logs -f <service-name>

# Backup all data
ansible-playbook infra/ansible/playbooks/backup.yml

# Validate deployment
ansible-playbook infra/ansible/playbooks/validate.yml

# Rollback to previous compose version
cd ~/iacgenie-platform/infra/docker-compose/
mv docker-compose-unified.yml docker-compose-unified.yml.current
mv docker-compose-unified.yml.bak.pre-deploy docker-compose-unified.yml
docker compose -f docker-compose-unified.yml up -d
```

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| IaCGenie API | 8080 | http://127.0.0.1:8080 |
| Keycloak | 8083 | http://127.0.0.1:8083 |
| SearXNG | 8082 | http://127.0.0.1:8082 |
| LightSerp API | 8000 | http://127.0.0.1:8000 |
| Gitea | 3002 | http://127.0.0.1:3002 |
| OpenBao | 8200 | http://127.0.0.1:8200 |
| MinIO | 9000 | http://127.0.0.1:9000 |
| PostgreSQL | 5432 | 127.0.0.1:5432 |
| Redis | 6379 | 127.0.0.1:6379 |

## Health Checks

```bash
# Quick health check script
curl -s http://127.0.0.1:8080/health && echo " IaCGenie OK"
curl -s http://127.0.0.1:8083/realms/master && echo " Keycloak OK"
curl -s http://127.0.0.1:8082/ && echo " SearXNG OK"
curl -s http://127.0.0.1:9000/minio/health/live && echo " MinIO OK"
curl -s http://127.0.0.1:8200/v1/sys/health && echo " OpenBao OK"
```

## Troubleshooting

1. **Service not starting**: Check logs with `docker compose logs <service>`
2. **Port conflict**: Check with `sudo lsof -i :<port>`
3. **Database issues**: Check PostgreSQL logs in docker compose
4. **Keycloak issues**: Verify realm-export.json is valid
5. **Nginx issues**: Check `nginx -t` and `/var/log/nginx/`
