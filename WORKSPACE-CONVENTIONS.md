# Workspace Conventions

## Repository Structure

```
iacgenie-platform/
├── platform/          # IaCGenie application code
│   ├── backend/       # Python FastAPI
│   ├── frontend/      # React/Next.js dashboard
│   ├── infra/         # Terraform modules
│   └── docs/          # Platform docs
│
├── lightserv/         # LightSerp service
│   ├── src/           # TypeScript API
│   ├── webui/         # Next.js WebUI
│   ├── scripts/       # Utility scripts
│   ├── infra/         # Service-specific infra
│   └── docs/          # Service docs
│
├── infra/             # Shared infrastructure (Docker, Ansible, Nginx)
│   ├── docker-compose/    # Docker Compose files
│   ├── ansible/           # Ansible roles and playbooks
│   ├── nginx/             # Nginx vHost configs
│   ├── certs/             # TLS certificates
│   ├── keycloak/          # Keycloak realm config
│   ├── configs/           # Prometheus, Loki, cloudflared
│   ├── systemd/           # Systemd units
│   ├── scripts/           # Deploy/backup/management scripts
│   ├── docs/              # Infrastructure docs
│   └── tests/             # Infrastructure integration tests
│
├── shared/            # Cross-cutting concerns
│   └── docs/              # Architecture, ops cheatsheet
│
└── scripts/           # Root-level scripts (deploy.sh)
```

## Conventions

### Code
- Python: ruff for formatting, mypy for type checking
- TypeScript: ESLint + Prettier (via webui/ and platform/frontend/)
- Go: Standard gofmt + golint

### Ansible
- Roles go in `infra/ansible/roles/<role-name>/`
- Playbooks go in `infra/ansible/playbooks/`
- Inventory in `infra/ansible/inventory/`
- Group vars in `infra/ansible/vars/`

### Docker
- Docker Compose files in `infra/docker-compose/`
- Per-service compose files: `docker-compose-<service>.yml`
- Unified compose: `docker-compose-unified.yml`

### Git
- Main branch: `main`
- Feature branches: `feat/<description>`
- Bug fixes: `fix/<description>`
- Commits: Conventional commits format

### Secrets
- Never commit secrets
- Use OpenBao for production secrets management
- `.env.example` files document required env vars
- Actual `.env` files are gitignored
