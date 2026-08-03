# Persistence API Documentation

## Overview

The Persistence API provides HTTP endpoints for session lifecycle management, iterations, artifacts, and idempotency. All endpoints are prefixed with `/api/persistence` and require authentication via Bearer token.

## Authentication

Most endpoints require authentication. Include your API token in the Authorization header:

```http
Authorization: Bearer <your-api-token>
```

## Endpoints

### Session States

#### Create Session
**POST** `/api/persistence/sessions`

Create a new session state record.

**Request Body:**
```json
{
  "build_id": "unique-build-id",
  "user_id": "user-uuid",
  "prompt": "Generate a OpenTofu script for AWS EC2",
  "git_repo_url": "https://github.com/user/repo",
  "git_branch": "main",
  "ci_provider": "github",
  "ci_inputs": {}
}
```

**Response:**
```json
{
  "success": true,
  "message": "Session created successfully",
  "data": {
    "id": "session-uuid",
    "build_id": "unique-build-id",
    "user_id": "user-uuid",
    "status": "CREATED"
  }
}
```

**Status Codes:**
- `200`: Session created successfully
- `400`: Missing required field (build_id)
- `500`: Failed to create session

#### Get Session
**GET** `/api/persistence/sessions/{session_id}`

Get session state by ID.

**Response:**
```json
{
  "success": true,
  "message": "Session retrieved successfully",
  "data": {
    "id": "session-uuid",
    "build_id": "unique-build-id",
    "user_id": "user-uuid",
    "status": "CREATED"
  }
}
```

**Status Codes:**
- `200`: Session retrieved successfully
- `404`: Session not found

#### Update Session
**PUT** `/api/persistence/sessions/{session_id}`

Update session state.

**Request Body:**
```json
{
  "status": "CODING",
  "current_iteration": 1,
  "git_repo_url": "https://github.com/user/repo",
  "git_branch": "main",
  "git_commit_sha": "abc123",
  "ci_provider": "github",
  "ci_run_id": "run-123",
  "deployment_status": "pending"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Session updated successfully",
  "data": {
    "id": "session-uuid",
    "status": "CODING",
    "current_iteration": 1
  }
}
```

**Status Codes:**
- `200`: Session updated successfully
- `404`: Session not found

#### List Sessions
**GET** `/api/persistence/sessions`

List session states with optional filters.

**Query Parameters:**
- `user_id`: Filter by user ID
- `status`: Filter by session status (CREATED, CODING, VALIDATING, PLANNING, APPLYING, TESTING, GIT_PUSH, CI_TRIGGER, CI_MONITOR, COMPLETED, FAILED, HUMAN_REVIEW)
- `limit`: Number of results (default: 100)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "success": true,
  "message": "Sessions retrieved successfully",
  "data": [
    {
      "id": "session-uuid",
      "build_id": "unique-build-id",
      "user_id": "user-uuid",
      "status": "CREATED"
    }
  ]
}
```

### Iterations

#### Create Iteration
**POST** `/api/persistence/sessions/{session_id}/iterations`

Create a new iteration record.

**Request Body:**
```json
{
  "iteration_num": 0,
  "error": null,
  "artifacts": []
}
```

**Response:**
```json
{
  "success": true,
  "message": "Iteration created successfully",
  "data": {
    "id": "iteration-uuid",
    "session_id": "session-uuid",
    "iteration_num": 0,
    "artifacts": []
  }
}
```

#### List Iterations
**GET** `/api/persistence/sessions/{session_id}/iterations`

List iterations for a session.

**Response:**
```json
{
  "success": true,
  "message": "Iterations retrieved successfully",
  "data": [
    {
      "id": "iteration-uuid",
      "session_id": "session-uuid",
      "iteration_num": 0,
      "artifacts": []
    }
  ]
}
```

### Artifacts

#### Create Artifact
**POST** `/api/persistence/sessions/{session_id}/artifacts`

Create a new artifact record.

**Request Body:**
```json
{
  "iteration_num": 0,
  "artifact_type": "code",
  "storage_path": "/path/to/file",
  "content_type": "text/plain"
}
```

**Artifact Types:**
- `code`: Generated code files
- `log`: Log files
- `plan`: Plan files
- `output`: Output files

**Response:**
```json
{
  "success": true,
  "message": "Artifact created successfully",
  "data": {
    "id": "artifact-uuid",
    "session_id": "session-uuid",
    "iteration_num": 0,
    "type": "code",
    "storage_path": "/path/to/file"
  }
}
```

#### List Artifacts
**GET** `/api/persistence/sessions/{session_id}/artifacts`

List artifacts for a session.

**Query Parameters:**
- `iteration_num`: Filter by iteration number (optional)

**Response:**
```json
{
  "success": true,
  "message": "Artifacts retrieved successfully",
  "data": [
    {
      "id": "artifact-uuid",
      "session_id": "session-uuid",
      "iteration_num": 0,
      "type": "code"
    }
  ]
}
```

### User Repository Configurations

#### Create User Repo Config
**POST** `/api/persistence/user-repo-configs`

Create a new user repository configuration.

**Request Body:**
```json
{
  "repo_url": "https://github.com/user/repo",
  "default_branch": "main",
  "git_provider": "github",
  "credentials_ref": "vault/path/to/creds",
  "ci_provider": "github",
  "ci_workflow_id": ".github/workflows/deploy.yml"
}
```

**Response:**
```json
{
  "success": true,
  "message": "User repo config created successfully",
  "data": {
    "id": "config-uuid",
    "user_id": "user-uuid",
    "repo_url": "https://github.com/user/repo"
  }
}
```

#### Get User Repo Config
**GET** `/api/persistence/user-repo-configs/{repo_url}`

Get user repository configuration by repo URL.

**Response:**
```json
{
  "success": true,
  "message": "User repo config retrieved successfully",
  "data": {
    "id": "config-uuid",
    "user_id": "user-uuid",
    "repo_url": "https://github.com/user/repo"
  }
}
```

#### List User Repo Configs
**GET** `/api/persistence/user-repo-configs`

List all repository configurations for the authenticated user.

**Response:**
```json
{
  "success": true,
  "message": "User repo configs retrieved successfully",
  "data": [
    {
      "id": "config-uuid",
      "user_id": "user-uuid",
      "repo_url": "https://github.com/user/repo"
    }
  ]
}
```

### Idempotency

#### Check Idempotency
**POST** `/api/persistence/idempotency/check`

Check if an idempotency key exists and return cached result.

**Request Body:**
```json
{
  "idempotency_key": "unique-key-for-request"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Idempotency check completed",
  "data": {
    "idempotency_key": "unique-key-for-request",
    "result": {"status": "success"}
  }
}
```

#### Create Idempotency Record
**POST** `/api/persistence/idempotency/record`

Create a new idempotency record with TTL.

**Request Body:**
```json
{
  "idempotency_key": "unique-key-for-request",
  "result": {"status": "success"},
  "ttl_seconds": 3600
}
```

**Response:**
```json
{
  "success": true,
  "message": "Idempotency record created successfully",
  "data": {
    "idempotency_key": "unique-key-for-request"
  }
}
```

### Health Check

#### Persistence Health Check
**GET** `/api/persistence/health`

Check if the persistence layer is healthy.

**Response:**
```json
{
  "success": true,
  "message": "Persistence health check completed",
  "data": {
    "status": "healthy",
    "initialized": true
  }
}
```

## Session Status Values

Sessions can have the following status values:
- `CREATED`: Session created
- `CODING`: Code generation in progress
- `VALIDATING`: Validation in progress
- `PLANNING`: Planning phase
- `APPLYING`: Apply phase
- `TESTING`: Testing phase
- `GIT_PUSH`: Git push in progress
- `CI_TRIGGER`: CI trigger in progress
- `CI_MONITOR`: CI monitoring in progress
- `COMPLETED`: Session completed successfully
- `FAILED`: Session failed
- `HUMAN_REVIEW`: Awaiting human review

## Artifact Types

Artifacts can have the following types:
- `code`: Generated code files
- `log`: Log files
- `plan`: Plan files
- `output`: Output files

## Error Response Format

All errors follow the standardized error response format:

```json
{
  "success": false,
  "error": {
    "message": "Error description",
    "code": "ERROR_CODE",
    "statusCode": 400,
    "details": {}
  }
}
```

## Rate Limiting

API endpoints are protected by rate limiting:
- **CRUD Operations**: 100 requests per hour
- **Admin Operations**: 10 requests per hour

## Examples

### Complete Session Lifecycle

```bash
# 1. Create session
curl -X POST http://localhost:8000/api/persistence/sessions \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "build_id": "build-123",
    "user_id": "user-456",
    "prompt": "Generate a OpenTofu script for AWS EC2"
  }'

# 2. Update session status
curl -X PUT http://localhost:8000/api/persistence/sessions/{session_id} \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "CODING",
    "current_iteration": 1
  }'

# 3. Create iteration
curl -X POST http://localhost:8000/api/persistence/sessions/{session_id}/iterations \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "iteration_num": 0,
    "artifacts": []
  }'

# 4. Create artifact
curl -X POST http://localhost:8000/api/persistence/sessions/{session_id}/artifacts \
  -H "Authorization: Bearer <api-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "iteration_num": 0,
    "artifact_type": "code",
    "storage_path": "/path/to/file.txt",
    "content_type": "text/plain"
  }'

# 5. List artifacts
curl -X GET http://localhost:8000/api/persistence/sessions/{session_id}/artifacts \
  -H "Authorization: Bearer <api-token>"
```
