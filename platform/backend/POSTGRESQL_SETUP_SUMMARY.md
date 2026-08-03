# PostgreSQL Setup for iacgenie AI - Development Environment

## Overview

This document provides a comprehensive summary of the PostgreSQL setup for the iacgenie AI backend service. PostgreSQL is the primary database, MinIO handles object storage, and Redis provides caching and message queuing. Authentication is handled by Keycloak.

> **Note**: This document was originally written during the Firebase-to-PostgreSQL migration. Firebase authentication has since been replaced with Keycloak.

## Architecture

### Current System Architecture

```
┌─────────────────┐         ┌─────────────────┐
│   Keycloak       │         │   PostgreSQL    │
│  Authentication  │         │  Data Storage   │
└─────────────────┘         └─────────────────┘
                                   │
                              ┌───────────┐
                              │   MinIO    │
                              │ Object    │
                              │ Storage   │
                              └───────────┘
                                   │
                              ┌───────────┐
                              │   Redis    │
                              │ Cache & MQ │
                              └───────────┘
                                   │
┌─────────────────────────────────────────────────┐
│          iacgenie AI Backend                    │
│  - Token Verification (Keycloak)                │
│  - User Data Storage (PostgreSQL)               │
│  - Role Management (PostgreSQL)                 │
│  - API Keys (PostgreSQL, encrypted)             │
│  - Model Configs (PostgreSQL, encrypted)        │
└─────────────────────────────────────────────────┘
```

### Key Components

1. **Keycloak Authentication**: Handles user authentication, token generation, and verification
2. **PostgreSQL Database**: Stores user data, roles, projects, generations, deployments, and encrypted secrets
3. **MinIO**: Object storage for artifacts and generated files
4. **Redis**: Caching, session management, and message queuing for Celery workers

## Setup Files

### 1. Docker Compose Configuration
**File**: [`iacgenie-ai/backend/docker-compose.yml`](iacgenie-ai/backend/docker-compose.yml)

Defines the PostgreSQL service with:
- PostgreSQL 15 image
- Volume persistence
- Health checks
- Network configuration
- Environment variables

### 2. Backend Dockerfile
**File**: [`iacgenie-ai/backend/Dockerfile`](iacgenie-ai/backend/Dockerfile)

Multi-stage Docker build for the backend with:
- Python 3.11 base image
- PostgreSQL client tools
- Application dependencies
- Health check endpoint

### 3. Environment Configuration
**File**: [`iacgenie-ai/backend/.env`](iacgenie-ai/backend/.env)

Key environment variables:
```bash
DATABASE_PROVIDER=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=iacgenie
POSTGRES_USER=iacgenie
POSTGRES_PASSWORD=iacgenie
```

### 4. Database Initialization Script
**File**: [`iacgenie-ai/backend/scripts/init_postgres.sql`](iacgenie-ai/backend/scripts/init_postgres.sql)

SQL script to initialize database tables:
- `users` table
- `projects` table
- `ai_generations` table
- `deployments` table

### 5. Startup Script
**File**: [`iacgenie-ai/run-local.sh`](iacgenie-ai/run-local.sh)

Automates the startup process:
1. Starts PostgreSQL container
2. Waits for PostgreSQL to be ready
3. Performs health check
4. Starts backend service

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

### Projects Table
```sql
CREATE TABLE projects (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### AI Generations Table
```sql
CREATE TABLE ai_generations (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255),
    model VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    tokens_used INTEGER,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

### Deployments Table
```sql
CREATE TABLE deployments (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    platform VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);
```

## Authentication Flow (Current - Keycloak)

```
1. User signs in with Keycloak (email/password, OAuth, etc.)
   ↓
2. Keycloak returns JWT token
   ↓
3. Backend verifies JWT token signature and expiry
   ↓
4. Backend looks up user in PostgreSQL by Keycloak user ID
   ↓
5. If user exists → Return user data and roles
   If user doesn't exist → Create user in PostgreSQL, then return data
   ↓
6. User can now access protected endpoints with their role
```

## Testing

### Test Scripts

#### 1. PostgreSQL Connection Test
**File**: [`iacgenie-ai/backend/scripts/test_postgres_connection.py`](iacgenie-ai/backend/scripts/test_postgres_connection.py)

Tests:
- Database connection
- Table creation
- User CRUD operations
- Project CRUD operations

**Run**:
```bash
cd iacgenie-ai/backend
python scripts/test_postgres_connection.py
```

> **Note**: The Firebase-PostgreSQL integration test (`test_firebase_postgres_integration.py`) has been removed as Firebase is no longer used.
```

#### 3. Seed Test User
**File**: [`iacgenie-ai/backend/scripts/seed_test_user.py`](iacgenie-ai/backend/scripts/seed_test_user.py)

Creates a test user in PostgreSQL for manual testing.

**Run**:
```bash
cd iacgenie-ai/backend
python scripts/seed_test_user.py
```

## Usage

### Starting the Application

Using the provided startup script:
```bash
./run-local.sh
```

This will:
1. Start PostgreSQL container
2. Wait for PostgreSQL to be ready
3. Perform health check
4. Start the backend service

### Manual Startup

If you prefer to start services manually:

```bash
# Start PostgreSQL
cd iacgenie-ai/backend
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
docker-compose logs -f postgres

# In another terminal, start the backend
cd iacgenie-ai/backend
python main.py
```

### Stopping the Application

```bash
# Stop PostgreSQL container
cd iacgenie-ai/backend
docker-compose down

# Or use Ctrl+C if using run-local.sh
```

## Database Management

### Accessing PostgreSQL

```bash
# Connect to PostgreSQL
docker exec -it iacgenie-postgres psql -U iacgenie -d iacgenie

# List tables
\dt

# Query users
SELECT * FROM users;

# Exit
\q
```

### Backup Database

```bash
# Backup to SQL file
docker exec iacgenie-postgres pg_dump -U iacgenie iacgenie > backup.sql

# Restore from SQL file
docker exec -i iacgenie-postgres psql -U iacgenie iacgenie < backup.sql
```

### Reset Database

```bash
# Stop and remove PostgreSQL container with volumes
cd iacgenie-ai/backend
docker-compose down -v

# Start fresh
docker-compose up -d
```

## Troubleshooting

### PostgreSQL Container Not Starting

**Issue**: Container exits immediately

**Solution**:
```bash
# Check logs
docker-compose logs postgres

# Check if port 5432 is already in use
lsof -i :5432

# Stop conflicting services or change POSTGRES_PORT in .env
```

### Connection Refused

**Issue**: Backend cannot connect to PostgreSQL

**Solution**:
```bash
# Verify PostgreSQL is running
docker-compose ps

# Check connection from backend
cd iacgenie-ai/backend
python scripts/test_postgres_connection.py
```

### User Not Created in PostgreSQL

**Issue**: User not found after login

**Solution**:
```bash
# Verify user exists in PostgreSQL
cd iacgenie-ai/backend
python scripts/seed_test_user.py

# Or check the database directly
docker exec -it iacgenie-postgres psql -U iacgenie -d iacgenie -c "SELECT * FROM users;"
```

### Permission Denied

**Issue**: Cannot access database files

**Solution**:
```bash
# Fix permissions
sudo chown -R $USER:$USER ./data/postgres

# Or use Docker volumes with correct permissions
```

## Configuration Options

### Switching Database Providers

The application supports multiple database providers via the `DATABASE_PROVIDER` environment variable:

```bash
# PostgreSQL (default for development)
DATABASE_PROVIDER=postgres

# SQLite
DATABASE_PROVIDER=sqlite
```

### Connection Pooling

Configure connection pooling in `.env`:

```bash
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
```

### Health Monitoring

Configure health check interval:

```bash
DB_CONNECTION_MONITORING=true
DB_HEALTH_CHECK_INTERVAL=300
```

## Security Considerations

1. **Passwords**: Change default PostgreSQL password in production
2. **Network**: Don't expose PostgreSQL port publicly
3. **SSL**: Enable SSL for PostgreSQL connections in production
4. **Backups**: Regular database backups
5. **Access Control**: Use PostgreSQL user roles and permissions

## Production Deployment

### Using Docker Compose

```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up -d
```

### Using Kubernetes

See `iacgenie-ai/k8s/` for Kubernetes manifests.

### Environment Variables for Production

```bash
DATABASE_PROVIDER=postgres
POSTGRES_HOST=your-postgres-host
POSTGRES_PORT=5432
POSTGRES_DATABASE=iacgenie
POSTGRES_USER=iacgenie
POSTGRES_PASSWORD=your-secure-password
POSTGRES_SSL_MODE=require
```

## Summary

This PostgreSQL setup provides:

✅ **Reliable Data Storage**: PostgreSQL for persistent user data
✅ **Secure Authentication**: Keycloak for authentication
✅ **Automatic User Sync**: Users created automatically on first login
✅ **Role-Based Access**: User roles managed in PostgreSQL
✅ **Easy Development**: Automated startup and testing
✅ **Production Ready**: Scalable and secure for production use

## Files Created/Modified

### Key Files

1. [`iacgenie-ai/backend/docker-compose.yml`](iacgenie-ai/backend/docker-compose.yml) - PostgreSQL service configuration
2. [`iacgenie-ai/backend/scripts/init_postgres.sql`](iacgenie-ai/backend/scripts/init_postgres.sql) - Database initialization
3. [`iacgenie-ai/backend/scripts/test_postgres_connection.py`](iacgenie-ai/backend/scripts/test_postgres_connection.py) - Connection test
4. [`iacgenie-ai/backend/scripts/seed_test_user.py`](iacgenie-ai/backend/scripts/seed_test_user.py) - Test user creation

## Next Steps

1. **Run Tests**: Execute the test scripts to verify the setup
2. **Start Development**: Use `./run-local.sh` to start the application
3. **Test Authentication**: Sign in with Keycloak and verify user creation in PostgreSQL
4. **Customize Configuration**: Adjust environment variables as needed
5. **Prepare for Production**: Review security considerations and configure for production

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the logs: `docker-compose logs postgres`
3. Run the test scripts to identify issues
4. Consult the backend README for additional information
