# IacGenie Platform — Documentation Index

> **Last Updated**: 2026-08-08

## Documentation Structure

```
infra/
├── DOCS-README.md          ← Master doc index (admin/devops/engineer guides)
├── INFRA-SERVICES.md       ← Service inventory & network topology
├── DEPLOYMENT-RUNBOOK.md   ← Step-by-step deployment guide
├── HEALTH-CHECKS.md        ← Health check endpoints for all services
├── OPENBAO-SECRETS.md      ← OpenBao secrets structure & KV engines
├── DISASTER-RECOVERY.md    ← DR procedures & backup/restore
├── ARCHITECTURE.md         ← C4 architecture diagrams
├── ANSIBLE-ROLES.md        ← Ansible role documentation
├── MONITORING.md           ← Grafana/Prometheus/Loki docs
├── INFRA-ANSIBLE-DESIGN.md ← Architecture & design
├── README.md               ← Quick start & reference
├── deploy.sh               ← Deployment script
├── health-check.sh         ← Health checks
├── drift-detect.sh         ← Drift detection
├── backup-restore.sh       ← Backup & restore
└── docs/                   ← Detailed operational docs
    └── index.md           ← This file (navigation hub)
```

## Quick Links by Role

| Role | Primary Docs |
|------|-------------|
| **End Users** | [DOCS-README.md](../DOCS-README.md#admin-guide) |
| **Admins** | [DOCS-README.md](../DOCS-README.md#admin-guide) |
| **DevOps Engineers** | [DOCS-README.md](../DOCS-README.md#devops-engineer-guide) |
| **Engineers/AI Agents** | [DOCS-README.md](../DOCS-README.md#engineerai-agent-guide) |

## Quick Links by Topic

|| Topic | Document ||
|-------|----------||
| Architecture | [ARCHITECTURE.md](../ARCHITECTURE.md) ||
| Service Inventory | [INFRA-SERVICES.md](../INFRA-SERVICES.md) ||
| Deployment | [DEPLOYMENT-RUNBOOK.md](../DEPLOYMENT-RUNBOOK.md) ||
| Health Checks | [HEALTH-CHECKS.md](../HEALTH-CHECKS.md) ||
| OpenBao Secrets | [OPENBAO-SECRETS.md](../OPENBAO-SECRETS.md) ||
| Disaster Recovery | [DISASTER-RECOVERY.md](../DISASTER-RECOVERY.md) ||
| Ansible Roles | [ANSIBLE-ROLES.md](../ANSIBLE-ROLES.md) ||
| Monitoring | [MONITORING.md](../MONITORING.md) ||
| Quick Start | [README.md](../README.md) ||
| Admin/DevOps Guide | [DOCS-README.md](../DOCS-README.md) ||

## Running Services

All 20+ services documented in [INFRA-ANSIBLE-DESIGN.md](../INFRA-ANSIBLE-DESIGN.md#running-services).

## Emergency Procedures

See [DOCS-README.md](../DOCS-README.md#emergency-procedures) for:
- Service down recovery
- Data loss restoration
- Full VM redeploy
- OpenBao unseal
- Keycloak lockout
