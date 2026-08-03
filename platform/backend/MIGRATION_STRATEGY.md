# Database Migration Strategy

## Overview

This document outlines the migration strategy for integrating the new persistence layer into the existing iacgenie AI backend.

## Current State

### Existing Database (PostgreSQL/SQLite)
- **Tables**: `users`, `projects`, `ai_generations`, `deployments`
- **ORM**: Direct SQLAlchemy Table definitions
- **Provider**: PostgreSQL (production), SQLite (development)
- **Session Management**: In-memory `jobs` dict in `main.py`

### New Persistence Layer
- **Tables**: `session_states`, `iterations`, `artifacts`, `user_repo_configs`, `processed_events`
- **ORM**: SQLAlchemy declarative Base with relationships
- **Provider**: PostgreSQL (primary)
- **Session Management**: Database-backed with lifecycle states

## Migration Strategy: Dual-Write Approach

### Phase 1: Coexistence (Current)
Both systems run in parallel:
- Existing backend continues to use current database
- New persistence layer is added as adapter
- Data is written to both systems during transition

### Phase 2: Migration (Future)
Gradual migration of data:
1. Migrate existing sessions to new schema
2. Update frontend to use new endpoints
3. Deprecate old endpoints

### Phase 3: Decommission (Future)
Remove legacy code:
- Remove in-memory session management
- Remove old database adapter
- Use only new persistence layer

## Database Schema Comparison

### Existing Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | User accounts | id, email, name, role |
| `projects` | Project metadata | id, user_id, name, description |
| `ai_generations` | AI generation records | id, user_id, project_id, model, prompt |
| `deployments` | Deployment records | id, user_id, project_id, platform |

### New Persistence Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `session_states` | Session lifecycle management | id, build_id, user_id, status, current_iteration |
| `iterations` | Iteration tracking | id, session_id, iteration_num, error, artifacts |
| `artifacts` | Generated files tracking | id, session_id, iteration_num, type, storage_path |
| `user_repo_configs` | Repository configurations | id, user_id, repo_url, git_provider |
| `processed_events` | Idempotency keys | idempotency_key, result, expires_at |

## Integration Points

### 1. Session Management
- **Old**: In-memory `jobs` dict in `main.py`
- **New**: Database-backed `session_states` table
- **Migration**: Create sessions in both systems during transition

### 2. Artifact Storage
- **Old**: File system in `STORAGE_PATH`
- **New**: MinIO with PostgreSQL metadata
- **Migration**: Store artifacts in both systems during transition

### 3. User Authentication
- **Old**: Firebase Admin SDK
- **New**: HashiCorp Vault (for secrets only)
- **Migration**: Keep Firebase auth, use Vault for sensitive data

## Migration Steps

### Step 1: Create New Tables
```bash
# Run migrations to create new tables
python -m db.migrations.create_tables
```

### Step 2: Update Database Provider
```python
# db/db_provider.py
from db.adapters.persistence_adapter import persistence_adapter

# Initialize both adapters
db_provider.initialize()
persistence_adapter.initialize()
```

### Step 3: Update Session Creation
```python
# main.py
def create_session(build_id, user_id, prompt):
    # Create in new persistence layer
    session = persistence_adapter.create_session(
        build_id=build_id,
        user_id=user_id,
        prompt=prompt
    )
    
    # Also create in old system for backward compatibility
    jobs[build_id] = {
        "user_id": user_id,
        "prompt": prompt,
        "status": "CREATED"
    }
    
    return session
```

### Step 4: Update Session Queries
```python
# main.py
def get_session(build_id):
    # Query new persistence layer first
    session = persistence_adapter.get_session_by_build_id(build_id)
    
    if not session:
        # Fallback to old system
        return jobs.get(build_id)
    
    return session
```

## Environment Variables

### Required for New Persistence Layer
```env
# Database Configuration
DATABASE_PROVIDER=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=iacgenie
POSTGRES_USER=iacgenie_user
POSTGRES_PASSWORD=your_password

# New Persistence Layer Configuration
DATABASE_URL=postgresql://iacgenie_user:password@localhost:5432/iacgenie
CONNECTION_POOL_SIZE=20
DB_MAX_RETRIES=3
DB_RETRY_DELAY_MS=1000

# MinIO Configuration (for artifact storage)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# HashiCorp Vault Configuration (for secrets)
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=s.your_token
```

## Testing Strategy

### Unit Tests
```python
# tests/test_persistence_adapter.py
def test_create_session():
    session = persistence_adapter.create_session(
        build_id="test-build-123",
        user_id="user-123",
        prompt="Test prompt"
    )
    assert session is not None
    assert session['build_id'] == "test-build-123"

def test_get_session():
    session = persistence_adapter.get_session(session_id)
    assert session is not None
```

### Integration Tests
```python
# tests/test_migration.py
def test_session_migration():
    # Create session in old system
    old_session = create_old_session()
    
    # Verify it's accessible from new system
    new_session = persistence_adapter.get_session_by_build_id(old_session['build_id'])
    assert new_session is not None
```

## Rollback Plan

If issues occur during migration:
1. Stop the application
2. Revert to old database adapter
3. Clear new persistence layer tables
4. Resume operation with old system

## Success Criteria

Migration is successful when:
- [ ] All existing features continue working
- [ ] New persistence layer is fully functional
- [ ] Data integrity maintained across systems
- [ ] No breaking changes to existing functionality
- [ ] Performance impact is acceptable (< 10% degradation)
- [ ] All tests pass

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Coexistence (Dual-Write) | 2 weeks | In Progress |
| Migration | 1 week | Pending |
| Decommission | 3 days | Pending |

## Notes

- Keep both systems running during transition period
- Monitor for data inconsistencies
- Update frontend gradually to use new endpoints
- Deprecate old endpoints after migration complete
