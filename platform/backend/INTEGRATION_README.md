# Backend Integration Guide

## Overview

This document describes the integration of new backend modules into the existing iacgenie AI backend.

## Architecture

### Existing Backend (`iacgenie-ai/backend`)
- FastAPI application with Keycloak authentication
- Database: PostgreSQL (production), SQLite (development)
- Multiple service routers (auth, projects, deployments, etc.)
- Middleware: auth, rate limiting, logging, error handling

### New Backend Modules (`iacgenie-ai/backend_new_modules`)
- PostgreSQL-based persistence layer
- Agent executor for parallel task execution
- LLM proxy for multi-provider AI support
- Workflow engine for complex session management
- Artifact store with MinIO/PostgreSQL
- Secret store with HashiCorp Vault
- Sandbox manager for Docker SDK integration
- Git/CI/CD integration
- Observability with OpenTelemetry

## Integration Strategy

### Dual-Write Approach

During the migration period, both systems run in parallel:
1. Existing backend continues to use current database
2. New persistence layer is added as adapter
3. Data is written to both systems during transition

### Migration Phases

1. **Phase 1: Database & Persistence** (Current)
   - Create new persistence tables
   - Integrate persistence adapter
   - Add new API endpoints

2. **Phase 2: Services Integration**
   - Integrate LLM proxy
   - Add workflow engine
   - Configure observability

3. **Phase 3: Agent System**
   - Integrate agent executor
   - Add tool injection system

4. **Phase 4-12**: Continue with remaining phases from integration plan

## Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- MinIO (for artifact storage)
- HashiCorp Vault (for secrets)
- Redis (for caching and queues)

### Installation

1. **Clone the repository**
```bash
cd /Users/manjunathkanavi/workspace/git_workspace/iacgenie
```

2. **Install dependencies**
```bash
cd iacgenie-ai/backend
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run database migrations**
```bash
python -m db.migrations.create_tables
```

5. **Start the server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## New API Endpoints

### Persistence API (`/api/persistence`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions` | POST | Create session |
| `/sessions/{session_id}` | GET | Get session |
| `/sessions/{session_id}` | PUT | Update session |
| `/sessions` | GET | List sessions |
| `/sessions/{session_id}/iterations` | POST | Create iteration |
| `/sessions/{session_id}/iterations` | GET | List iterations |
| `/sessions/{session_id}/artifacts` | POST | Create artifact |
| `/sessions/{session_id}/artifacts` | GET | List artifacts |
| `/user-repo-configs` | POST | Create user repo config |
| `/user-repo-configs/{repo_url}` | GET | Get user repo config |
| `/user-repo-configs` | GET | List user repo configs |
| `/idempotency/check` | POST | Check idempotency |
| `/idempotency/record` | POST | Create idempotency record |
| `/health` | GET | Health check |

## Testing

### Run Unit Tests
```bash
cd iacgenie-ai/backend
pytest tests/test_persistence_adapter.py -v
```

### Run Integration Tests
```bash
pytest tests/ -v --integration
```

## Environment Variables

### Required for New Persistence Layer
```env
DATABASE_PROVIDER=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=iacgenie
POSTGRES_USER=iacgenie_user
POSTGRES_PASSWORD=your_password

# New Persistence Layer Configuration
DATABASE_URL=postgresql://iacgenie_user:password@localhost:5432/iacgenie
CONNECTION_POOL_SIZE=20

# MinIO Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# HashiCorp Vault Configuration
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=s.your_token

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
```

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL connection
psql -h localhost -U iacgenie_user -d iacgenie

# Check tables exist
psql -h localhost -U iacgenie_user -d iacgenie -c "\dt"
```

### Migration Issues
```bash
# Drop and recreate tables
python -m db.migrations.create_tables

# Check for errors in logs
tail -f logs/backend.log
```

### API Issues
```bash
# Check API health
curl http://localhost:8000/api/persistence/health

# Check OpenAPI docs
open http://localhost:8000/docs
```

## Next Steps

1. **Test the new endpoints**
   - Create a session
   - Add iterations
   - Upload artifacts

2. **Configure MinIO**
   - Set up MinIO server
   - Configure artifact storage

3. **Configure Vault**
   - Set up HashiCorp Vault
   - Configure secret management

4. **Migrate existing data**
   - Run migration scripts
   - Verify data integrity

5. **Update frontend**
   - Update API client
   - Add new UI components

## Support

For issues or questions:
1. Check the integration plan: `plans/backend_modules_integration_plan.md`
2. Review API documentation: `PERSISTENCE_API.md`
3. Check logs for errors
4. Run tests to verify functionality
