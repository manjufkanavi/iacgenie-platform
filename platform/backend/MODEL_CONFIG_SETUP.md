# 🔐 Model Configuration System - iacgenie AI

This document provides a complete guide to the Model Configuration system, which allows users to securely store and manage AI model configurations using PostgreSQL with encrypted API keys.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup Instructions](#setup-instructions)
4. [API Endpoints](#api-endpoints)
5. [Security Features](#security-features)
6. [Usage Examples](#usage-examples)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

## 🎯 Overview

The Model Configuration system provides:

- **Secure Storage**: API keys are encrypted using Fernet (AES-128-CBC) before storing in PostgreSQL
- **User Isolation**: Each user's configurations are stored under their authenticated user ID
- **Project-based Organization**: Configurations are organized by project ID
- **Multi-Provider Support**: Supports Mistral, Gemini, Claude, OpenAI, and custom models
- **Real-time Testing**: Test model configurations before saving
- **CRUD Operations**: Full create, read, update, delete functionality

## 🏗️ Architecture

### Data Flow

```
Frontend → FastAPI → Keycloak Auth → PostgreSQL (Encrypted)
                ↓
            Encryption/Decryption
                ↓
            Model Registry → AI Providers
```

### PostgreSQL Table Structure

**Table: `model_configs`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | VARCHAR | Authenticated user ID |
| `project_id` | VARCHAR | Project identifier |
| `config_data` | JSONB | Encrypted model configuration |
| `created_at` | TIMESTAMPTZ | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | Last update timestamp |

## 🚀 Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Encryption

Generate a Fernet key for API key encryption:

```bash
python setup_encryption.py
```

This will:

- Generate a new Fernet key
- Add it to your `.env` file as `FERNET_KEY`
- Test the encryption/decryption functionality

### 3. Database Setup

Ensure PostgreSQL is running:

1. **Database**: Create the `iacgenie` database
2. **Migrations**: Run Alembic migrations to create tables:

```bash
alembic upgrade head
```

### 4. Environment Variables

Add these to your `.env` file:

```env
# Encryption
FERNET_KEY=your_generated_fernet_key_here

# AI Provider Keys (optional - can be stored per project)
MISTRAL_API_KEY=your_mistral_key
GEMINI_API_KEY=your_gemini_key
CLAUDE_API_KEY=your_claude_key
OPENAI_API_KEY=your_openai_key
```

## 🔌 API Endpoints

### Base URL

```
http://localhost:8000/api/model-config
```

### Authentication

All endpoints require authentication via Bearer token:

```
Authorization: Bearer <api_token>
```

### 1. Save Model Configuration

**POST** `/{project_id}`

Save or update a model configuration for a project.

```json
{
  "provider": "mistral",
  "model_name": "mistralai/mistral-7b-instruct",
  "base_url": "https://openrouter.ai/api/v1/chat/completions",
  "api_key": "sk-your-api-key-here",
  "max_tokens": 8192,
  "temperature": 0.1,
  "timeout": 120,
  "retry_attempts": 3,
  "retry_delay": 1.0,
  "headers": {
    "X-Custom-Header": "value"
  },
  "metadata": {
    "description": "My custom model config"
  }
}
```

**Response:**

```json
{
  "provider": "mistral",
  "model_name": "mistralai/mistral-7b-instruct",
  "base_url": "https://openrouter.ai/api/v1/chat/completions",
  "max_tokens": 8192,
  "temperature": 0.1,
  "timeout": 120,
  "retry_attempts": 3,
  "retry_delay": 1.0,
  "headers": {},
  "metadata": {},
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### 2. Get Model Configuration

**GET** `/{project_id}`

Retrieve a model configuration (API key is not returned for security).

**Response:**

```json
{
  "provider": "mistral",
  "model_name": "mistralai/mistral-7b-instruct",
  "base_url": "https://openrouter.ai/api/v1/chat/completions",
  "max_tokens": 8192,
  "temperature": 0.1,
  "timeout": 120,
  "retry_attempts": 3,
  "retry_delay": 1.0,
  "headers": {},
  "metadata": {},
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### 3. Delete Model Configuration

**DELETE** `/{project_id}`

Delete a model configuration.

**Response:**

```json
{
  "success": true,
  "message": "Model configuration deleted successfully",
  "deleted": true
}
```

### 4. Test Model Configuration

**POST** `/test`

Test a model configuration by making a test API call.

```json
{
  "project_id": "my-project-123"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Model mistralai/mistral-7b-instruct is available and responding",
  "provider": "mistral",
  "model": "mistralai/mistral-7b-instruct",
  "status": "available"
}
```

### 5. List User Projects

**GET** `/projects/list`

List all projects for the authenticated user that have model configurations.

**Response:**

```json
{
  "projects": [
    {
      "project_id": "project-123",
      "project_name": "My Infrastructure Project",
      "provider": "mistral",
      "model_name": "mistralai/mistral-7b-instruct",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

### 6. Get Available Providers

**GET** `/providers/available`

Get information about available AI providers and their default configurations.

**Response:**

```json
{
  "providers": {
    "mistral": {
      "name": "Mistral AI",
      "description": "Mistral AI models via OpenRouter or direct API",
      "default_base_url": "https://openrouter.ai/api/v1/chat/completions",
      "default_model": "mistralai/mistral-7b-instruct",
      "supports": ["OpenRouter", "Direct API"],
      "documentation": "https://docs.mistral.ai/"
    },
    "gemini": {
      "name": "Google Gemini",
      "description": "Google's Gemini models",
      "default_base_url": "https://generativelanguage.googleapis.com/v1beta/models",
      "default_model": "gemini-1.5-pro",
      "supports": ["Direct API"],
      "documentation": "https://ai.google.dev/docs"
    }
  },
  "total": 5
}
```

## 🔒 Security Features

### 1. API Key Encryption

- **Algorithm**: Fernet (AES-128-CBC with PKCS7 padding)
- **Key Derivation**: PBKDF2 with SHA256, 100,000 iterations
- **Storage**: Encrypted keys are base64-encoded before storing in PostgreSQL
- **Access**: Keys are only decrypted when needed for API calls

### 2. User Isolation

- **User ID**: All configurations are scoped to the authenticated user
- **Project Separation**: Each project has its own configuration
- **Access Control**: Users can only access their own configurations

### 3. Input Validation

- **Pydantic Models**: All inputs are validated using Pydantic schemas
- **Provider Validation**: Only supported providers are allowed
- **URL Validation**: Base URLs must be valid HTTP/HTTPS URLs
- **API Key Validation**: Keys cannot be empty

### 4. Error Handling

- **Graceful Failures**: Decryption failures are handled gracefully
- **No Key Exposure**: API keys are never returned in responses
- **Detailed Logging**: All operations are logged for audit purposes

## 💡 Usage Examples

### Frontend Integration

```javascript
// Save model configuration
const saveConfig = async (projectId, config) => {
  const token = await getAuthToken(); // Get token from Keycloak auth flow

  const response = await fetch(`/api/model-config/${projectId}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(config),
  });

  return response.json();
};

// Test configuration
const testConfig = async (projectId) => {
  const token = await getAuthToken(); // Get token from Keycloak auth flow

  const response = await fetch("/api/model-config/test", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ project_id: projectId }),
  });

  return response.json();
};
```

### Python Client

```python
import httpx
import asyncio

async def save_model_config(project_id: str, config: dict, token: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8000/api/model-config/{project_id}",
            json=config,
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()

# Usage
config = {
    "provider": "mistral",
    "model_name": "mistralai/mistral-7b-instruct",
    "base_url": "https://openrouter.ai/api/v1/chat/completions",
    "api_key": "sk-your-key-here",
    "max_tokens": 8192,
    "temperature": 0.1
}

result = asyncio.run(save_model_config("my-project", config, "api-token"))
```

## 🧪 Testing

### Run Test Suite

```bash
python test_model_config.py
```

This will test:

- ✅ Encryption utilities
- ✅ Database service
- ✅ All API endpoints
- ✅ Error handling
- ✅ Security features

### Manual Testing

1. **Setup encryption**:

   ```bash
   python setup_encryption.py
   ```

2. **Start backend**:

   ```bash
   python start.py
   ```

3. **Test endpoints** using curl or Postman:

   ```bash
   # Get available providers
   curl http://localhost:8000/api/model-config/providers/available

   # Save configuration (requires API token)
   curl -X POST http://localhost:8000/api/model-config/test-project \
     -H "Authorization: Bearer YOUR_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"provider":"mistral","model_name":"test","base_url":"https://test.com","api_key":"sk-test"}'
   ```

## 🔧 Troubleshooting

### Common Issues

1. **Encryption Errors**

   - **Problem**: "Failed to decrypt API key"
   - **Solution**: Regenerate Fernet key using `setup_encryption.py`

2. **Database Connection Issues**

   - **Problem**: "Database connection failed"
   - **Solution**: Check PostgreSQL connection settings and ensure database is running

3. **Authentication Errors**

   - **Problem**: "Invalid token" or "Missing token"
   - **Solution**: Ensure API token is valid and properly formatted

4. **Validation Errors**
   - **Problem**: "Missing required field" or "Invalid provider"
   - **Solution**: Check request payload against Pydantic schema

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

Check system health:

```bash
# Backend health
curl http://localhost:8000/health

# Encryption test
python -c "from utils.crypto import encrypt_key, decrypt_key; print('Encryption OK' if decrypt_key(encrypt_key('test')) == 'test' else 'Encryption FAILED')"
```

## 📚 Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Fernet Encryption](https://cryptography.io/en/latest/fernet/)
- [Fernet Encryption](https://cryptography.io/en/latest/fernet/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Validation](https://pydantic-docs.helpmanual.io/)

## 🤝 Contributing

When contributing to the Model Configuration system:

1. **Security First**: Never expose API keys in logs or responses
2. **Test Thoroughly**: Run the test suite before submitting changes
3. **Document Changes**: Update this documentation for any new features
4. **Follow Patterns**: Use existing patterns for consistency

---

**🎉 The Model Configuration system is now ready for production use!**
