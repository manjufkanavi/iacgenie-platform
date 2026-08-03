# iacgenie AI - Backend Service

A FastAPI-based backend for the iacgenie application that generates infrastructure-as-code using Google's Gemini AI model.

## 🚀 Features

- **AI-Powered Code Generation**: Uses Google Gemini to generate OpenTofu, Docker, and Kubernetes configurations
- **Asynchronous Processing**: Background job processing with real-time status updates
- **Database Storage**: SQLite database for storing projects, files, and deployment logs
- **File Management**: ZIP download and GitHub integration
- **Real-time Logging**: Live console output for generation and deployment steps
- **RESTful API**: Complete API with OpenAPI documentation

## 📋 Prerequisites

- Python 3.8+
- Google Gemini API key
- Redis (optional, for Celery background tasks)
- python-jose[cryptography] for Keycloak JWT verification

## 🛠️ Installation

1. **Clone the repository and navigate to the backend directory:**

   ```bash
   cd iacgenie-ai/backend
   ```

2. **Create a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   ```bash
   # Copy the example environment file
   cp .env.example .env

   # Edit .env and add your Gemini API key
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# AI Model Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///iacgenie.db

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Development Mode
DEBUG=true
MOCK_MODE=false

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# File Storage
STORAGE_PATH=./project-files
MAX_FILE_SIZE=10485760  # 10MB

# Logging
LOG_LEVEL=INFO
```

### Getting a Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key and add it to your `.env` file

## 🚀 Running the Backend

### Option 1: Using the startup script (Recommended)

```bash
python start.py
```

### Option 2: Direct uvicorn command

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Using Python directly

```bash
python main.py
```

The server will start on `http://localhost:8000`

## 📚 API Documentation

Once the server is running, you can access:

- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🔌 API Endpoints

### Core Endpoints

| Method | Endpoint                        | Description               |
| ------ | ------------------------------- | ------------------------- |
| `POST` | `/api/generate`                 | Start code generation job |
| `GET`  | `/api/generate/status/{job_id}` | Get generation status     |
| `POST` | `/api/deploy`                   | Deploy infrastructure     |
| `POST` | `/api/github`                   | Push code to GitHub       |
| `GET`  | `/api/download/{job_id}`        | Download project as ZIP   |
| `GET`  | `/api/logs/{job_id}`            | Get job logs              |
| `GET`  | `/api/health`                   | Health check              |

### Request Examples

#### Start Generation

```bash
curl -X POST "http://localhost:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create an AWS S3 bucket for static website hosting",
    "model": "gemini-2.0-flash-exp",
    "provider": "aws"
  }'
```

#### Check Status

```bash
curl "http://localhost:8000/api/generate/status/{job_id}"
```

#### Deploy Infrastructure

```bash
curl -X POST "http://localhost:8000/api/deploy" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "your-job-id",
    "project_name": "My Infrastructure Project"
  }'
```

## 🗄️ Database Schema

The application uses PostgreSQL as the primary database, MinIO for object storage, and Redis for caching and message queuing.

### Default Provider: PostgreSQL (Development)

For development, PostgreSQL is used as the default database. The database is automatically started when running the application using the provided scripts.

#### PostgreSQL Setup

The PostgreSQL database is configured via Docker Compose. See the `docker-compose.yml` file for configuration details.

**Environment Variables:**
```bash
DATABASE_PROVIDER=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=iacgenie
POSTGRES_USER=iacgenie
POSTGRES_PASSWORD=iacgenie
```

**Database Tables:**

### Users

- `id`: Primary key (Auth provider UID — Keycloak `sub` claim)
- `email`: User email (unique)
- `name`: User name
- `role`: User role (user, admin)
- `is_active`: Boolean (default: true)
- `created_at`: Timestamp
- `updated_at`: Timestamp
- `metadata`: JSON (additional user data)

### Projects

- `id`: Primary key
- `user_id`: Foreign key to users
- `name`: Project name
- `description`: Project description
- `status`: Project status
- `created_at`: Timestamp
- `updated_at`: Timestamp
- `metadata`: JSON (additional project data)

### AI Generations

- `id`: Primary key
- `user_id`: Foreign key to users
- `project_id`: Foreign key to projects
- `model`: AI model used
- `prompt`: Generation prompt
- `response`: AI response
- `status`: Generation status
- `tokens_used`: Number of tokens used
- `duration_ms`: Generation duration in milliseconds
- `created_at`: Timestamp
- `metadata`: JSON (additional generation data)

### Deployments

- `id`: Primary key
- `user_id`: Foreign key to users
- `project_id`: Foreign key to projects
- `platform`: Deployment platform
- `status`: Deployment status
- `url`: Deployment URL
- `created_at`: Timestamp
- `updated_at`: Timestamp
- `metadata`: JSON (additional deployment data)

## 🔐 Keycloak Authentication with PostgreSQL Integration

The application uses **self-hosted Keycloak** for OAuth2/OIDC authentication and PostgreSQL for user data storage.

1. **Keycloak Authentication**: OAuth2 Authorization Code Flow with PKCE; tokens validated via JWKS
2. **PostgreSQL Storage**: Persistent user data, roles, and application state
3. **Automatic User Sync**: Users are automatically created in PostgreSQL on first login from Keycloak claims

### How It Works

1. **Token Acquisition**: Keycloak issues an access token after user login
2. **Token Verification**: The backend fetches Keycloak's JWKS and verifies the JWT signature and issuer
3. **User Lookup**: User data is fetched from PostgreSQL using the Keycloak `sub` UID
4. **Auto-Creation**: If a user doesn't exist in PostgreSQL, they are automatically created from the token claims
5. **Role Management**: User roles are stored in PostgreSQL and retrieved during authentication

### Keycloak Setup

Start the bundled Keycloak + PostgreSQL container:

```bash
# From project root
docker compose -f docker-compose.keycloak.yml up -d --build
```

See [KEYCLOAK_AUTH_SETUP.md](../KEYCLOAK_AUTH_SETUP.md) for full setup, configuration, and administration instructions.

### Testing the Integration

Run the integration validation script:

```bash
cd backend
./venv/bin/python3 scripts/seed_and_validate.py
```

This script tests:
- Keycloak container health
- Backend health
- User token acquisition via Resource Owner Password Credentials grant
- Token verification against the backend `/api/auth/token/verify` endpoint
- User sync to PostgreSQL

### Available Database Providers

The application supports multiple database providers via the `DATABASE_PROVIDER` environment variable:

The database adapter is implemented in `db/adapters/`. Currently `postgres` is the active provider.

## 🔄 Background Tasks

The application supports background task processing using Celery:

### Starting Celery Worker (Optional)

```bash
# Install Redis first (if not already installed)
# On macOS: brew install redis
# On Ubuntu: sudo apt-get install redis-server

# Start Redis
redis-server

# In another terminal, start Celery worker
celery -A celery_worker.celery_app worker --loglevel=info
```

## 🧪 Testing

### Manual Testing

1. Start the backend server
2. Use the interactive API docs at http://localhost:8000/docs
3. Test the generation endpoint with a sample prompt

### Health Check

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "version": "2.0.0"
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Missing Gemini API Key**

   - Error: "Gemini API key not configured"
   - Solution: Add your API key to the `.env` file

2. **CORS Errors**

   - Error: Frontend can't connect to backend
   - Solution: Check that the frontend URL is in `ALLOWED_ORIGINS`

3. **Database Errors**

   - Error: Database connection issues
   - Solution: Check that the database file is writable

4. **Port Already in Use**
   - Error: "Address already in use"
   - Solution: Change the port in `.env` or kill the existing process

### Logs

Check the console output for detailed error messages. The application logs:

- API requests and responses
- AI generation progress
- Database operations
- Error details

## 🔧 Development

### Project Structure

```
backend/
├── main.py              # FastAPI application
├── celery_worker.py     # Background task worker
├── start.py            # Startup script
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── .env               # Environment variables (create this)
```

### Adding New Features

1. **New API Endpoints**: Add to `main.py`
2. **Database Models**: Update the schema in `init_db()`
3. **Background Tasks**: Add to `celery_worker.py`
4. **AI Integration**: Extend the `GeminiService` class

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Add docstrings to functions
- Handle errors gracefully

## 📄 License

This project is part of iacgenie AI. See the main project license for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:

1. Check the troubleshooting section
2. Review the API documentation
3. Open an issue on GitHub

## 🔐 CORS Configuration (Cross-Origin Resource Sharing)

This backend uses FastAPI's built-in `CORSMiddleware` to allow frontend clients to make API requests.

### ✅ Current Allowed Origins

- http://localhost:5173
- http://localhost:3000
- http://localhost:8000
- https://iacgenie.yourdomain.com  (update for production)

If you host your frontend on a new domain, just add that domain to `config/cors.py`.

### 🚨 Why This Matters

Without setting CORS, browsers block frontend JavaScript from making requests to another domain (like your backend) due to security.

If you see this error:

Access to fetch at 'http://localhost:8000/...' from origin 'https://iacgenie...' has been blocked by CORS policy

...then the backend has not allowed the frontend domain. This is fixed by allowing it in CORS.

### 🛠 How to Update Allowed Origins

1. Open `config/cors.py`
2. Add or remove domains in `ALLOWED_ORIGINS`
3. Redeploy backend

✅ Final Checklist

| Task                                   | Status |
| -------------------------------------- | ------ |
| CORS config created in config/cors.py  | ✅     |
| Middleware added to main.py            | ✅     |
| Keycloak and localhost origins allowed | ✅     |
| README updated                         | ✅     |
| CORS error fixed during login |        |
