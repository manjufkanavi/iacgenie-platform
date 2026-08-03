"""

Database Provider

PostgreSQL-only database provider with middleware abstraction layer

Manages database connections and provides unified interface through adapter pattern

"""

import asyncio

from typing import Dict, Any, Optional, List

from config.logging import get_logger

from services.metrics_service import metrics_service

from services.business_metrics_service import business_metrics

logger = get_logger("db.provider")

# Determine which adapter to use based on DATABASE_PROVIDER env var

import os

DATABASE_PROVIDER = os.getenv("DATABASE_PROVIDER", "postgres")

logger.info(f"[DEBUG DB] DATABASE_PROVIDER is hardcoded to: {DATABASE_PROVIDER}")

# Import the appropriate adapter

logger.info("[DEBUG DB] Using PostgreSQL adapter")
from db.adapters.postgres_adapter import postgres_adapter

adapter_to_use: Any = postgres_adapter


class DatabaseProvider:
    """Database provider supporting both SQLite and PostgreSQL"""

    def __init__(self) -> None:
        self.provider = DATABASE_PROVIDER  # Use configured provider
        self.adapter: Any = None
        self._is_initialized = False
        self._health_check_task = None

    async def initialize(self) -> bool:
        """Initialize database provider based on DATABASE_PROVIDER env var"""
        try:
            logger.info(f"[DEBUG DB] Initializing database provider: {self.provider}")
            # Initialize the appropriate adapter based on DATABASE_PROVIDER
            logger.info("[DEBUG DB] Initializing PostgreSQL adapter")
            self.adapter = postgres_adapter
            # Try to initialize the adapter, if it fails raise exception
            _adapter = self.adapter
            result = await _adapter.initialize()
            if not result:
                error_msg = f"{self.provider} adapter initialization failed"
                logger.error(error_msg)
                raise Exception(error_msg)
            self._is_initialized = True
            logger.info(
                f"[DEBUG DB] Database provider {self.provider} initialized successfully"
            )
            logger.info(f"[DEBUG DB] Adapter type: {type(self.adapter).__name__}")
            # Record metrics
            business_metrics.record_integration(self.provider, "success", "system")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database provider: {str(e)}")
            business_metrics.record_integration(self.provider, "failed", "system")
            raise  # Re-raise exception instead of returning False

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        if not self._is_initialized or not self.adapter:
            return {"error": "Database not initialized"}
        try:
            if hasattr(self.adapter, "get_connection_stats"):
                return await self.adapter.get_connection_stats()
            elif hasattr(self.adapter, "get_database_stats"):
                return await self.adapter.get_database_stats()
            else:
                return {"error": "Stats not available for this adapter"}
        except Exception as e:
            logger.error(f"Failed to get connection stats: {str(e)}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        if not self._is_initialized or not self.adapter:
            return {
                "status": "disconnected",
                "provider": self.provider,
                "error": "Database not initialized",
                "timestamp": asyncio.get_event_loop().time(),
            }
        try:
            start_time = asyncio.get_event_loop().time()
            # Perform health check based on adapter type
            if hasattr(self.adapter, "health_check"):
                result = self.adapter.health_check()
            else:
                # Default health check
                result = {
                    "status": "healthy",
                    "provider": self.provider,
                    "timestamp": asyncio.get_event_loop().time(),
                }
            duration = (asyncio.get_event_loop().time() - start_time) * 1000
            # Record metrics
            metrics_service.record_database_health_check(
                self.provider, result.get("status") == "healthy", duration
            )
            return result
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            metrics_service.record_database_health_check(self.provider, False, 0)
            return {
                "status": "unhealthy",
                "provider": self.provider,
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time(),
            }

    async def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a database query"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "execute_query"):
            return await self.adapter.execute_query(query, params)
        else:
            raise NotImplementedError("Query execution not supported by this adapter")

    async def execute_command(
        self, command: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a database command"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "execute_command"):
            return await self.adapter.execute_command(command, params)
        else:
            raise NotImplementedError("Command execution not supported by this adapter")

    async def get_session(self):
        """Get database session"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_session"):
            return self.adapter.get_session()
        elif hasattr(self.adapter, "get_connection"):
            return self.adapter.get_connection()
        else:
            raise NotImplementedError(
                "Session management not supported by this adapter"
            )

    # User operations

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_user"):
            return await self.adapter.get_user(user_id)
        else:
            raise NotImplementedError("User operations not supported by this adapter")

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_user_by_email"):
            return await self.adapter.get_user_by_email(email)
        else:
            raise NotImplementedError("User operations not supported by this adapter")

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Create a new user"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_user"):
            return await self.adapter.create_user(user_data)
        else:
            raise NotImplementedError("User operations not supported by this adapter")

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user data"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "update_user"):
            return await self.adapter.update_user(user_id, updates)
        else:
            raise NotImplementedError("User operations not supported by this adapter")

    # Refresh token operations

    async def create_refresh_token(self, token_data: Dict[str, Any]) -> Optional[str]:
        """Create refresh token"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_refresh_token"):
            return await self.adapter.create_refresh_token(token_data)
        else:
            raise NotImplementedError(
                "Refresh token operations not supported by this adapter"
            )

    # Project operations

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_project"):
            return await self.adapter.get_project(project_id)
        else:
            raise NotImplementedError(
                "Project operations not supported by this adapter"
            )

    # Deployment operations

    async def get_deployment(self, dep_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment by ID"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_deployment"):
            return await self.adapter.get_deployment(dep_id)
        return None

    async def list_deployments(self, user_id: str, project_id: str) -> list:
        """List deployments"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "list_deployments"):
            return await self.adapter.list_deployments(user_id, project_id)
        return []

    async def create_deployment(self, data: Dict[str, Any]) -> Optional[str]:
        """Create deployment"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_deployment"):
            return await self.adapter.create_deployment(data)
        return None

    async def update_deployment(self, dep_id: str, data: Dict[str, Any]) -> bool:
        """Update deployment"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "update_deployment"):
            return await self.adapter.update_deployment(dep_id, data)
        return False

    async def delete_deployment(self, dep_id: str) -> bool:
        """Delete deployment"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "delete_deployment"):
            return await self.adapter.delete_deployment(dep_id)
        return False

    async def create_project(self, project_data: Dict[str, Any]) -> Optional[str]:
        """Create a new project"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_project"):
            return await self.adapter.create_project(project_data)
        else:
            raise NotImplementedError(
                "Project operations not supported by this adapter"
            )

    # Generation operations

    async def record_generation(self, generation_data: Dict[str, Any]) -> Optional[str]:
        """Record an AI generation"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "record_generation"):
            return await self.adapter.record_generation(generation_data)
        else:
            raise NotImplementedError(
                "Generation operations not supported by this adapter"
            )

    async def create_generation(
        self, user_id: str, project_id: str, generation: Dict[str, Any]
    ) -> Optional[str]:
        """Create a new AI generation"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_generation"):
            return await self.adapter.create_generation(user_id, project_id, generation)
        return None

    async def get_generation(
        self, user_id: str, project_id: str, generation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get AI generation record"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_generation"):
            return await self.adapter.get_generation(user_id, project_id, generation_id)
        return None

    async def list_generations(self, user_id: str, project_id: str) -> list:
        """List AI generations"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "list_generations"):
            return await self.adapter.list_generations(user_id, project_id)
        return []

    async def update_generation(
        self,
        user_id: str,
        project_id: str,
        generation_id: str,
        generation: Dict[str, Any],
    ) -> bool:
        """Update AI generation"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "update_generation"):
            return await self.adapter.update_generation(
                user_id, project_id, generation_id, generation
            )
        return False

    async def delete_generation(
        self, user_id: str, project_id: str, generation_id: str
    ) -> bool:
        """Delete AI generation"""
        if not self._is_initialized or not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "delete_generation"):
            return await self.adapter.delete_generation(
                user_id, project_id, generation_id
            )
        return False

    async def close(self) -> None:
        """Close database connections"""
        try:
            if self.adapter and hasattr(self.adapter, "close"):
                await self.adapter.close()
            logger.info(f"{self.provider} database provider closed successfully")
        except Exception as e:
            logger.error(f"Error closing {self.provider} database provider: {str(e)}")

    # OAuth operations - delegate to adapter

    async def create_oauth_client(self, client_data: Dict[str, Any]) -> Optional[str]:
        """Create OAuth client"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_oauth_client"):
            return await self.adapter.create_oauth_client(client_data)
        return None

    async def get_client_by_id(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get OAuth client by ID"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_client_by_id"):
            return await self.adapter.get_client_by_id(client_id)
        return None

    async def list_clients(self, user_id: str) -> Any:
        """List OAuth clients"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "list_clients"):
            return await self.adapter.list_clients(user_id)
        return []

    async def update_client(self, client_id: str, redirect_uris: list) -> bool:
        """Update OAuth client"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "update_client"):
            return await self.adapter.update_client(client_id, redirect_uris)
        return False

    async def delete_client(self, client_id: str) -> bool:
        """Delete OAuth client"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "delete_client"):
            return await self.adapter.delete_client(client_id)
        return False

    async def create_authorization_code(
        self, code_data: Dict[str, Any]
    ) -> Optional[str]:
        """Create authorization code"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_authorization_code"):
            return await self.adapter.create_authorization_code(code_data)
        return None

    async def get_authorization_code_by_hash(
        self, code_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get authorization code by hash"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_authorization_code_by_hash"):
            return await self.adapter.get_authorization_code_by_hash(code_hash)
        return None

    async def mark_authorization_code_used(self, code_hash: str) -> bool:
        """Mark authorization code as used"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "mark_authorization_code_used"):
            return await self.adapter.mark_authorization_code_used(code_hash)
        return False

    async def get_refresh_token_by_hash(
        self, token_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Get refresh token by hash"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_refresh_token_by_hash"):
            return await self.adapter.get_refresh_token_by_hash(token_hash)
        return None

    async def revoke_refresh_token(self, token_id: str) -> bool:
        """Revoke refresh token"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "revoke_refresh_token"):
            return await self.adapter.revoke_refresh_token(token_id)
        return False

    async def revoke_refresh_token_by_hash(self, token_hash: str) -> bool:
        """Revoke refresh token by hash"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "revoke_refresh_token_by_hash"):
            return await self.adapter.revoke_refresh_token_by_hash(token_hash)
        return False

    async def revoke_access_token_by_hash(self, token_hash: str) -> bool:
        """Revoke access token by hash"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "revoke_access_token_by_hash"):
            return await self.adapter.revoke_access_token_by_hash(token_hash)
        return False

    # Keycloak refresh token operations

    async def set_keycloak_refresh_token(self, user_id: str, token: str) -> bool:
        """Store or update the Keycloak refresh token for a user"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "set_keycloak_refresh_token"):
            return await self.adapter.set_keycloak_refresh_token(user_id, token)
        return False

    async def get_keycloak_refresh_token(self, user_id: str) -> Optional[str]:
        """Retrieve the stored Keycloak refresh token for a user"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_keycloak_refresh_token"):
            return await self.adapter.get_keycloak_refresh_token(user_id)
        return None

    async def revoke_keycloak_refresh_token(self, user_id: str) -> bool:
        """Clear the stored Keycloak refresh token for a user"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "revoke_keycloak_refresh_token"):
            return await self.adapter.revoke_keycloak_refresh_token(user_id)
        return False

    # Generation Job operations

    async def create_generation_job(
        self, job_data: Dict[str, Any], job_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a new generation job"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_generation_job"):
            return await self.adapter.create_generation_job(job_data, job_id=job_id)
        return None

    async def update_generation_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update a generation job"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "update_generation_job"):
            return await self.adapter.update_generation_job(job_id, updates)
        return False

    async def get_generation_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a generation job by ID"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_generation_job"):
            return await self.adapter.get_generation_job(job_id)
        return None

    async def get_generation_metrics(self) -> Dict[str, Any]:
        """Get aggregate metrics for generations"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_generation_metrics"):
            return await self.adapter.get_generation_metrics()
        return {"total": 0, "by_status": {}, "by_provider": {}}

    async def list_running_jobs(self) -> List[Dict[str, Any]]:
        """List all generation jobs currently in 'running' status."""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "list_running_jobs"):
            return await self.adapter.list_running_jobs()
        return []

    async def find_recent_running_jobs(
        self, prompt_text: str, max_age_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """Find running jobs created within max_age_minutes with matching prompt."""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "find_recent_running_jobs"):
            return await self.adapter.find_recent_running_jobs(
                prompt_text, max_age_minutes
            )
        return []

    # Git repository operations

    async def get_repo_config(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Get repository configuration by ID (queries by primary key)"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_git_repository"):
            # Query by ID directly since we don't have user/project context here
            query = "SELECT * FROM git_repositories WHERE id = ?"
            result = await self.adapter.execute_query(query, {"id": repo_id})
            if result:
                row = result[0]
                return {
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "project_id": row["project_id"],
                    "name": row["name"],
                    "provider": row["provider"],
                    "url": row["url"],
                    "branch": row.get("branch", "main"),
                    "token_encrypted": row.get("token_encrypted"),
                    "ssh_key_encrypted": row.get("ssh_key_encrypted"),
                    "metadata": self.adapter._deserialize_metadata(row.get("metadata"))
                    if hasattr(self.adapter, "_deserialize_metadata")
                    else None,
                }
        return None

    async def find_repo_by_url(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """Find a repository configuration by URL (case-insensitive, token-stripped)."""
        import re

        if not self.adapter:
            raise RuntimeError("Database not initialized")
        # Normalize URL: strip tokens, lowercase, remove trailing slash
        normalized = re.sub(
            r"(https://)([^@]+@)?(.*)", r"\1\3", repo_url.strip("/").lower()
        )
        if hasattr(self.adapter, "execute_query"):
            # Query all repos and filter by normalized URL
            query = "SELECT * FROM git_repositories"
            rows = await self.adapter.execute_query(query, {})
            for row in rows:
                metadata = (
                    self.adapter._deserialize_metadata(row.get("metadata"))
                    if hasattr(self.adapter, "_deserialize_metadata")
                    else {}
                )
                row_url_val = row.get("repo_url") or row.get("url") or ""
                row_url = re.sub(
                    r"(https://)([^@]+@)?(.*)",
                    r"\1\3",
                    str(row_url_val).strip("/").lower(),
                )
                if row_url == normalized:
                    return {
                        "id": row["id"],
                        "user_id": row["user_id"],
                        "project_id": row["project_id"],
                        "name": metadata.get("name", "Git Repository"),
                        "provider": row.get("provider", "github"),
                        "url": row_url_val,
                        "branch": row.get("branch", "main"),
                        "token_encrypted": row.get("token_encrypted"),
                        "ssh_key_encrypted": row.get("ssh_key_encrypted"),
                        "metadata": metadata,
                    }
        return None

    # Model config operations

    async def create_model_config(
        self, uid: str, project_id: str, config: Dict[str, Any]
    ) -> Optional[str]:
        """Create a new model configuration"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_model_config"):
            return await self.adapter.create_model_config(uid, project_id, config)
        return None

    async def get_model_config(
        self, uid: str, project_id: str, config_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get model config by ID"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_model_config"):
            return await self.adapter.get_model_config(uid, project_id, config_id)
        return None

    async def list_model_configs(
        self, uid: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List model configurations"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "list_model_configs"):
            return await self.adapter.list_model_configs(uid, project_id)
        return []

    async def update_model_config(
        self, uid: str, project_id: str, config_id: str, config: Dict[str, Any]
    ) -> bool:
        """Update model configuration"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "update_model_config"):
            return await self.adapter.update_model_config(
                uid, project_id, config_id, config
            )
        return False

    async def delete_model_config(
        self, uid: str, project_id: str, config_id: str
    ) -> bool:
        """Delete model configuration"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "delete_model_config"):
            return await self.adapter.delete_model_config(uid, project_id, config_id)
        return False

    # API key operations

    async def create_api_key(
        self, uid: str, api_key_data: Dict[str, Any]
    ) -> Optional[str]:
        """Create a new API key"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_api_key"):
            return await self.adapter.create_api_key(uid, api_key_data)
        return None

    async def get_api_key(self, uid: str, key_id: str) -> Optional[Dict[str, Any]]:
        """Get API key by ID"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_api_key"):
            return await self.adapter.get_api_key(uid, key_id)
        return None

    async def list_api_keys(self, uid: str) -> List[Dict[str, Any]]:
        """List API keys for a user"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "list_api_keys"):
            return await self.adapter.list_api_keys(uid)
        return []

    async def update_api_key(
        self, uid: str, key_id: str, api_key_data: Dict[str, Any]
    ) -> bool:
        """Update an API key"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "update_api_key"):
            return await self.adapter.update_api_key(uid, key_id, api_key_data)
        return False

    async def delete_api_key(self, uid: str, key_id: str) -> bool:
        """Delete an API key"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "delete_api_key"):
            return await self.adapter.delete_api_key(uid, key_id)
        return False

    # Audit log operations

    async def create_audit_log(
        self, uid: str, log_data: Dict[str, Any]
    ) -> Optional[str]:
        """Create an audit log entry"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_audit_log"):
            return await self.adapter.create_audit_log(uid, log_data)
        return None

    async def list_audit_logs(
        self, uid: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List audit logs for a user"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "list_audit_logs"):
            return await self.adapter.list_audit_logs(uid, filters)
        return []

    # Team member operations

    async def create_team_member(
        self, uid: str, project_id: str, member: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a team member"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_team_member"):
            return await self.adapter.create_team_member(uid, project_id, member)
        return {}

    async def get_team_member(
        self, uid: str, project_id: str, member_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a team member by ID"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_team_member"):
            return await self.adapter.get_team_member(uid, project_id, member_id)
        return None

    async def list_team_members(
        self, uid: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List team members for a project"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "list_team_members"):
            return await self.adapter.list_team_members(uid, project_id)
        return []

    async def update_team_member(
        self, uid: str, project_id: str, member_id: str, member_data: Dict[str, Any]
    ) -> bool:
        """Update a team member"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "update_team_member"):
            return await self.adapter.update_team_member(
                uid, project_id, member_id, member_data
            )
        return False

    async def delete_team_member(
        self, uid: str, project_id: str, member_id: str
    ) -> bool:
        """Delete a team member"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "delete_team_member"):
            return await self.adapter.delete_team_member(uid, project_id, member_id)
        return False

    # Integration operations

    async def create_integration(
        self, uid: str, project_id: str, integration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an integration"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "create_integration"):
            return await self.adapter.create_integration(uid, project_id, integration)
        return {}

    async def get_integration(
        self, uid: str, project_id: str, integration_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get an integration by ID"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "get_integration"):
            return await self.adapter.get_integration(uid, project_id, integration_id)
        return None

    async def list_integrations(
        self, uid: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List integrations for a project"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "list_integrations"):
            return await self.adapter.list_integrations(uid, project_id)
        return []

    async def update_integration(
        self,
        uid: str,
        project_id: str,
        integration_id: str,
        integration_data: Dict[str, Any],
    ) -> bool:
        """Update an integration"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "update_integration"):
            return await self.adapter.update_integration(
                uid, project_id, integration_id, integration_data
            )
        return False

    async def delete_integration(
        self, uid: str, project_id: str, integration_id: str
    ) -> bool:
        """Delete an integration"""
        if not self.adapter:
            raise RuntimeError("Database not initialized")
        if hasattr(self.adapter, "delete_integration"):
            return await self.adapter.delete_integration(
                uid, project_id, integration_id
            )
        return False


# Global database provider instance


db_provider: DatabaseProvider = DatabaseProvider()
