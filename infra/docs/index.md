# IacGenie Platform — Documentation Index

> **Last Updated**: 2026-08-08

## Documentation Structure

```
infra/
├── DOCS-README.md          ← You are here (master doc index)
├── INFRA-ANSIBLE-DESIGN.md  ← Architecture & design
├── README.md               ← Quick start & reference
├── deploy.sh               ← Deployment script
├── health-check.sh         ← Health checks
├── drift-detect.sh         ← Drift detection
├── backup-restore.sh       ← Backup & restore
├── ansible/
│   └── VARIABLES-REFERENCE.md  ← Ansible variables reference
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

| Topic | Document |
|-------|----------|
| Architecture | [INFRA-ANSIBLE-DESIGN.md](../INFRA-ANSIBLE-DESIGN.md) |
| Quick Start | [README.md](../README.md) |
| Deployment | [deploy.sh](../deploy.sh) |
| Health Checks | [health-check.sh](../health-check.sh) |
| Drift Detection | [drift-detect.sh](../drift-detect.sh) |
| Backup/Restore | [backup-restore.sh](../backup-restore.sh) |
| Ansible Variables | [ansible/VARIABLES-REFERENCE.md](../ansible/VARIABLES-REFERENCE.md) |

## Running Services

All 20+ services documented in [INFRA-ANSIBLE-DESIGN.md](../INFRA-ANSIBLE-DESIGN.md#running-services).

## Emergency Procedures

See [DOCS-README.md](../DOCS-README.md#emergency-procedures) for:
- Service down recovery
- Data loss restoration
- Full VM redeploy
- OpenBao unseal
- Keycloak lockout
