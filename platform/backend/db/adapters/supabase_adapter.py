"""

Supabase database adapter

Implements the IDatabaseAdapter interface for Supabase PostgreSQL

"""

from datetime import datetime

from typing import Dict, List, Optional, Any

import logging

import uuid

import json

from supabase import create_client, Client

from .base import IDatabaseAdapter

from utils.crypto import encrypt_key, decrypt_key

logger = logging.getLogger(__name__)


class SupabaseAdapter(IDatabaseAdapter):
    """Supabase PostgreSQL database adapter"""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.client: Optional[Client] = None
        self._initialized = False

    def _require_client(self) -> Client:
        """Ensure the Supabase client is initialized, raising if not."""
        if self.client is None:
            raise RuntimeError("Supabase client is not initialized")
        return self.client

    async def initialize(self) -> bool:
        """Initialize Supabase connection"""
        try:
            if not self._initialized:
                self.client = create_client(self.supabase_url, self.supabase_key)
                # Test connection
                self._require_client().table("_health_check").select("*").limit(
                    1
                ).execute()
                self._initialized = True
                logger.info("Supabase adapter initialized successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize Supabase adapter: {str(e)}")
            return False
        return True

    async def close(self) -> None:
        """Close Supabase connection"""
        try:
            if self._initialized:
                # Supabase client doesn't require explicit closing
                self._initialized = False
                logger.info("Supabase adapter closed")
        except Exception as e:
            logger.error(f"Error closing Supabase adapter: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """Check Supabase health"""
        try:
            if not self._initialized:
                return {"status": "disconnected", "error": "Not initialized"}
            # Test connection with a simple query
            self._require_client().table("_health_check").select("*").limit(1).execute()
            return {
                "status": "healthy",
                "provider": "supabase",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "supabase",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def _generate_id(self) -> str:
        """Generate a unique ID"""
        return str(uuid.uuid4())

    def _prepare_data(
        self, data: Dict[str, Any], include_timestamps: bool = True
    ) -> Dict[str, Any]:
        """Prepare data for Supabase storage"""
        doc_data = data.copy()
        if include_timestamps:
            now = datetime.utcnow().isoformat()
            doc_data["created_at"] = now
            doc_data["updated_at"] = now
        return doc_data

    # Model Configs Implementation

    async def create_model_config(
        self, user_id: str, project_id: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new model configuration"""
        try:
            # Validate required fields
            if (
                not config.get("provider")
                or not config.get("model_name")
                or not config.get("api_key")
            ):
                raise ValueError("Provider, model_name, and api_key are required")
            # Check for duplicate model configuration
            existing = (
                self._require_client()
                .table("model_configs")
                .select("*")
                .eq("user_id", user_id)
                .eq("project_id", project_id)
                .eq("provider", config["provider"].strip())
                .execute()
            )
            if existing.data:
                raise ValueError(
                    f"Model configuration already exists for provider {config['provider']}"
                )
            # Encrypt the API key
            encrypted_api_key = encrypt_key(config["api_key"])
            # Prepare document data
            doc_data = {
                "user_id": user_id,
                "project_id": project_id,
                "provider": config["provider"].strip(),
                "model_name": config["model_name"].strip(),
                "base_url": config.get("base_url", "").strip(),
                "api_key_encrypted": encrypted_api_key,
                "secure": True,
                "max_tokens": config.get("max_tokens", 8192),
                "temperature": config.get("temperature", 0.1),
                "timeout": config.get("timeout", 120),
                "retry_attempts": config.get("retry_attempts", 3),
                "retry_delay": config.get("retry_delay", 1.0),
                "headers": json.dumps(config.get("headers", {})),
                "metadata": json.dumps(config.get("metadata", {})),
            }
            doc_data = self._prepare_data(doc_data)
            # Insert document
            response = (
                self._require_client().table("model_configs").insert(doc_data).execute()
            )
            if not response.data:
                raise ValueError("Failed to create model config")
            result = response.data[0]
            # Return the saved config (without encrypted key)
            return {
                "id": result["id"],
                "userId": result["user_id"],
                "projectId": result["project_id"],
                "provider": result["provider"],
                "model_name": result["model_name"],
                "base_url": result["base_url"],
                "secure": True,
                "max_tokens": result["max_tokens"],
                "temperature": result["temperature"],
                "timeout": result["timeout"],
                "retry_attempts": result["retry_attempts"],
                "retry_delay": result["retry_delay"],
                "headers": json.loads(result["headers"]),
                "metadata": json.loads(result["metadata"]),
                "createdAt": result["created_at"],
                "updatedAt": result["updated_at"],
            }
        except Exception as e:
            logger.error(f"Failed to create model config: {str(e)}")
            raise

    async def get_model_config(
        self, user_id: str, project_id: str, config_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a model configuration by ID"""
        try:
            response = (
                self._require_client()
                .table("model_configs")
                .select("*")
                .eq("id", config_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not response.data:
                return None
            data = response.data[0]
            # Decrypt the API key
            decrypted_api_key = decrypt_key(data["api_key_encrypted"])
            result = {
                "id": data["id"],
                "userId": data["user_id"],
                "projectId": data["project_id"],
                "provider": data["provider"],
                "model_name": data["model_name"],
                "base_url": data["base_url"],
                "api_key": decrypted_api_key,
                "max_tokens": data.get("max_tokens", 8192),
                "temperature": data.get("temperature", 0.1),
                "timeout": data.get("timeout", 120),
                "retry_attempts": data.get("retry_attempts", 3),
                "retry_delay": data.get("retry_delay", 1.0),
                "headers": json.loads(data.get("headers", "{}")),
                "metadata": json.loads(data.get("metadata", "{}")),
                "createdAt": data.get("created_at"),
                "updatedAt": data.get("updated_at"),
            }
            return result
        except Exception as e:
            logger.error(f"Failed to get model config: {str(e)}")
            raise

    async def list_model_configs(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all model configurations for a project"""
        try:
            response = (
                self._require_client()
                .table("model_configs")
                .select("*")
                .eq("user_id", user_id)
                .eq("project_id", project_id)
                .execute()
            )
            configs = []
            for data in response.data:
                configs.append(
                    {
                        "id": data["id"],
                        "userId": data["user_id"],
                        "projectId": data["project_id"],
                        "provider": data["provider"],
                        "model_name": data["model_name"],
                        "base_url": data["base_url"],
                        "secure": True,
                        "max_tokens": data.get("max_tokens", 8192),
                        "temperature": data.get("temperature", 0.1),
                        "timeout": data.get("timeout", 120),
                        "retry_attempts": data.get("retry_attempts", 3),
                        "retry_delay": data.get("retry_delay", 1.0),
                        "headers": json.loads(data.get("headers", "{}")),
                        "metadata": json.loads(data.get("metadata", "{}")),
                        "createdAt": data.get("created_at"),
                        "updatedAt": data.get("updated_at"),
                    }
                )
            return configs
        except Exception as e:
            logger.error(f"Failed to list model configs: {str(e)}")
            raise

    async def update_model_config(
        self, user_id: str, project_id: str, config_id: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a model configuration"""
        try:
            # Check if config exists
            existing = (
                self._require_client()
                .table("model_configs")
                .select("*")
                .eq("id", config_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not existing.data:
                raise ValueError("Model configuration not found")
            # Prepare update data
            update_data = {}
            if "provider" in config:
                update_data["provider"] = config["provider"].strip()
            if "model_name" in config:
                update_data["model_name"] = config["model_name"].strip()
            if "base_url" in config:
                update_data["base_url"] = config["base_url"].strip()
            if "api_key" in config:
                update_data["api_key_encrypted"] = encrypt_key(config["api_key"])
            if "max_tokens" in config:
                update_data["max_tokens"] = config["max_tokens"]
            if "temperature" in config:
                update_data["temperature"] = config["temperature"]
            if "timeout" in config:
                update_data["timeout"] = config["timeout"]
            if "retry_attempts" in config:
                update_data["retry_attempts"] = config["retry_attempts"]
            if "retry_delay" in config:
                update_data["retry_delay"] = config["retry_delay"]
            if "headers" in config:
                update_data["headers"] = json.dumps(config["headers"])
            if "metadata" in config:
                update_data["metadata"] = json.dumps(config["metadata"])
            update_data["updated_at"] = datetime.utcnow().isoformat()
            # Update document
            response = (
                self._require_client()
                .table("model_configs")
                .update(update_data)
                .eq("id", config_id)
                .execute()
            )
            if not response.data:
                raise ValueError("Failed to update model config")
            # Return updated config
            return await self.get_model_config(user_id, project_id, config_id)  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to update model config: {str(e)}")
            raise

    async def delete_model_config(
        self, user_id: str, project_id: str, config_id: str
    ) -> bool:
        """Delete a model configuration"""
        try:
            response = (
                self._require_client()
                .table("model_configs")
                .delete()
                .eq("id", config_id)
                .eq("user_id", user_id)
                .execute()
            )
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Failed to delete model config: {str(e)}")
            raise

    async def test_model_config(
        self, user_id: str, project_id: str, config_id: str
    ) -> Dict[str, Any]:
        """Test a model configuration"""
        try:
            config = await self.get_model_config(user_id, project_id, config_id)
            if not config:
                raise ValueError("Model configuration not found")
            # Import AI service for testing
            from services.ai_service import ai_service

            # Test the configuration
            test_result = await ai_service.test_model_config(config)  # type: ignore[attr-defined]
            return {
                "success": True,
                "config_id": config_id,
                "test_result": test_result,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to test model config: {str(e)}")
            return {
                "success": False,
                "config_id": config_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    # Git Repositories Implementation

    async def create_git_repository(
        self, user_id: str, project_id: str, repo: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new git repository configuration"""
        try:
            doc_data = {
                "user_id": user_id,
                "project_id": project_id,
                "name": repo["name"],
                "provider": repo["provider"],
                "url": repo["url"],
                "branch": repo.get("branch", "main"),
                "token_encrypted": encrypt_key(repo["token"])
                if "token" in repo
                else None,
                "ssh_key_encrypted": encrypt_key(repo["ssh_key"])
                if "ssh_key" in repo
                else None,
                "metadata": json.dumps(repo.get("metadata", {})),
            }
            doc_data = self._prepare_data(doc_data)
            response = (
                self._require_client()
                .table("git_repositories")
                .insert(doc_data)
                .execute()
            )
            if not response.data:
                raise ValueError("Failed to create git repository")
            result = response.data[0]
            return {
                "id": result["id"],
                "userId": result["user_id"],
                "projectId": result["project_id"],
                "name": result["name"],
                "provider": result["provider"],
                "url": result["url"],
                "branch": result["branch"],
                "metadata": json.loads(result["metadata"]),
                "createdAt": result["created_at"],
                "updatedAt": result["updated_at"],
            }
        except Exception as e:
            logger.error(f"Failed to create git repository: {str(e)}")
            raise

    async def get_git_repository(
        self, user_id: str, project_id: str, repo_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a git repository configuration by ID"""
        try:
            response = (
                self._require_client()
                .table("git_repositories")
                .select("*")
                .eq("id", repo_id)
                .eq("user_id", user_id)
                .execute()
            )
            if not response.data:
                return None
            data = response.data[0]
            # Decrypt sensitive data
            result = {
                "id": data["id"],
                "userId": data["user_id"],
                "projectId": data["project_id"],
                "name": data["name"],
                "provider": data["provider"],
                "url": data["url"],
                "branch": data["branch"],
                "metadata": json.loads(data["metadata"]),
            }
            if data.get("token_encrypted"):
                result["token"] = decrypt_key(data["token_encrypted"])
            if data.get("ssh_key_encrypted"):
                result["ssh_key"] = decrypt_key(data["ssh_key_encrypted"])
            return result
        except Exception as e:
            logger.error(f"Failed to get git repository: {str(e)}")
            raise

    async def list_git_repositories(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all git repository configurations for a project"""
        try:
            response = (
                self._require_client()
                .table("git_repositories")
                .select("*")
                .eq("user_id", user_id)
                .eq("project_id", project_id)
                .execute()
            )
            repos = []
            for data in response.data:
                repos.append(
                    {
                        "id": data["id"],
                        "userId": data["user_id"],
                        "projectId": data["project_id"],
                        "name": data["name"],
                        "provider": data["provider"],
                        "url": data["url"],
                        "branch": data["branch"],
                        "metadata": json.loads(data["metadata"]),
                        "createdAt": data["created_at"],
                        "updatedAt": data["updated_at"],
                    }
                )
            return repos
        except Exception as e:
            logger.error(f"Failed to list git repositories: {str(e)}")
            raise

    async def update_git_repository(
        self, user_id: str, project_id: str, repo_id: str, repo: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a git repository configuration"""
        try:
            update_data = {}
            if "name" in repo:
                update_data["name"] = repo["name"]
            if "provider" in repo:
                update_data["provider"] = repo["provider"]
            if "url" in repo:
                update_data["url"] = repo["url"]
            if "branch" in repo:
                update_data["branch"] = repo["branch"]
            if "token" in repo:
                update_data["token_encrypted"] = encrypt_key(repo["token"])
            if "ssh_key" in repo:
                update_data["ssh_key_encrypted"] = encrypt_key(repo["ssh_key"])
            if "metadata" in repo:
                update_data["metadata"] = json.dumps(repo["metadata"])
            update_data["updated_at"] = datetime.utcnow().isoformat()
            response = (
                self._require_client()
                .table("git_repositories")
                .update(update_data)
                .eq("id", repo_id)
                .execute()
            )
            if not response.data:
                raise ValueError("Failed to update git repository")
            return await self.get_git_repository(user_id, project_id, repo_id)  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to update git repository: {str(e)}")
            raise

    async def delete_git_repository(
        self, user_id: str, project_id: str, repo_id: str
    ) -> bool:
        """Delete a git repository configuration"""
        try:
            response = (
                self._require_client()
                .table("git_repositories")
                .delete()
                .eq("id", repo_id)
                .eq("user_id", user_id)
                .execute()
            )
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Failed to delete git repository: {str(e)}")
            raise

    async def test_git_repository(
        self, user_id: str, project_id: str, repo_id: str
    ) -> Dict[str, Any]:
        """Test a git repository configuration"""
        try:
            repo = await self.get_git_repository(user_id, project_id, repo_id)
            if not repo:
                raise ValueError("Git repository not found")
            # Simple test - try to access the repository
            import httpx

            headers = {}
            if repo.get("token"):
                headers["Authorization"] = f"token {repo['token']}"
            async with httpx.AsyncClient() as client:
                response = await client.get(repo["url"], headers=headers)
                return {
                    "success": response.status_code == 200,
                    "repo_id": repo_id,
                    "status_code": response.status_code,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Failed to test git repository: {str(e)}")
            return {
                "success": False,
                "repo_id": repo_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def create_cloud_credentials(
        self, user_id: str, project_id: str, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create new cloud credentials"""
        raise NotImplementedError(
            "Cloud credentials not yet implemented in Supabase adapter"
        )

    async def get_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cloud credentials by ID"""
        raise NotImplementedError(
            "Cloud credentials not yet implemented in Supabase adapter"
        )

    async def list_cloud_credentials(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all cloud credentials for a project"""
        raise NotImplementedError(
            "Cloud credentials not yet implemented in Supabase adapter"
        )

    async def update_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update cloud credentials"""
        raise NotImplementedError(
            "Cloud credentials not yet implemented in Supabase adapter"
        )

    async def delete_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str
    ) -> bool:
        """Delete cloud credentials"""
        raise NotImplementedError(
            "Cloud credentials not yet implemented in Supabase adapter"
        )

    async def test_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str
    ) -> Dict[str, Any]:
        """Test cloud credentials"""
        raise NotImplementedError(
            "Cloud credentials not yet implemented in Supabase adapter"
        )

    # Team Members

    async def create_team_member(
        self, user_id: str, project_id: str, member: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new team member"""
        raise NotImplementedError(
            "Team members not yet implemented in Supabase adapter"
        )

    async def get_team_member(
        self, user_id: str, project_id: str, member_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a team member by ID"""
        raise NotImplementedError(
            "Team members not yet implemented in Supabase adapter"
        )

    async def list_team_members(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all team members for a project"""
        raise NotImplementedError(
            "Team members not yet implemented in Supabase adapter"
        )

    async def update_team_member(
        self, user_id: str, project_id: str, member_id: str, member: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a team member"""
        raise NotImplementedError(
            "Team members not yet implemented in Supabase adapter"
        )

    async def delete_team_member(
        self, user_id: str, project_id: str, member_id: str
    ) -> bool:
        """Delete a team member"""
        raise NotImplementedError(
            "Team members not yet implemented in Supabase adapter"
        )

    # Integrations

    async def create_integration(
        self, user_id: str, project_id: str, integration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new integration"""
        raise NotImplementedError(
            "Integrations not yet implemented in Supabase adapter"
        )

    async def get_integration(
        self, user_id: str, project_id: str, integration_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get an integration by ID"""
        raise NotImplementedError(
            "Integrations not yet implemented in Supabase adapter"
        )

    async def list_integrations(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all integrations for a project"""
        raise NotImplementedError(
            "Integrations not yet implemented in Supabase adapter"
        )

    async def update_integration(
        self,
        user_id: str,
        project_id: str,
        integration_id: str,
        integration: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an integration"""
        raise NotImplementedError(
            "Integrations not yet implemented in Supabase adapter"
        )

    async def delete_integration(
        self, user_id: str, project_id: str, integration_id: str
    ) -> bool:
        """Delete an integration"""
        raise NotImplementedError(
            "Integrations not yet implemented in Supabase adapter"
        )

    async def test_integration(
        self, user_id: str, project_id: str, integration_id: str
    ) -> Dict[str, Any]:
        """Test an integration"""
        raise NotImplementedError(
            "Integrations not yet implemented in Supabase adapter"
        )

    # Projects

    async def create_project(
        self, user_id: str, project: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new project"""
        raise NotImplementedError("Projects not yet implemented in Supabase adapter")

    async def get_project(
        self, user_id: str, project_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a project by ID"""
        raise NotImplementedError("Projects not yet implemented in Supabase adapter")

    async def list_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """List all projects for a user"""
        raise NotImplementedError("Projects not yet implemented in Supabase adapter")

    async def update_project(
        self, user_id: str, project_id: str, project: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a project"""
        raise NotImplementedError("Projects not yet implemented in Supabase adapter")

    async def delete_project(self, user_id: str, project_id: str) -> bool:
        """Delete a project"""
        raise NotImplementedError("Projects not yet implemented in Supabase adapter")

    # API Keys

    async def create_api_key(
        self, user_id: str, api_key: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new API key"""
        raise NotImplementedError("API keys not yet implemented in Supabase adapter")

    async def get_api_key(self, user_id: str, key_id: str) -> Optional[Dict[str, Any]]:
        """Get an API key by ID"""
        raise NotImplementedError("API keys not yet implemented in Supabase adapter")

    async def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """List all API keys for a user"""
        raise NotImplementedError("API keys not yet implemented in Supabase adapter")

    async def update_api_key(
        self, user_id: str, key_id: str, api_key: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an API key"""
        raise NotImplementedError("API keys not yet implemented in Supabase adapter")

    async def delete_api_key(self, user_id: str, key_id: str) -> bool:
        """Delete an API key"""
        raise NotImplementedError("API keys not yet implemented in Supabase adapter")

    # Audit Logs

    async def create_audit_log(
        self, user_id: str, log: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new audit log entry"""
        raise NotImplementedError("Audit logs not yet implemented in Supabase adapter")

    async def list_audit_logs(
        self, user_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List audit logs with optional filters"""
        raise NotImplementedError("Audit logs not yet implemented in Supabase adapter")

    # Generations

    async def create_generation(
        self, user_id: str, project_id: str, generation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new generation record"""
        raise NotImplementedError("Generations not yet implemented in Supabase adapter")

    async def get_generation(
        self, user_id: str, project_id: str, generation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a generation by ID"""
        raise NotImplementedError("Generations not yet implemented in Supabase adapter")

    async def list_generations(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all generations for a project"""
        raise NotImplementedError("Generations not yet implemented in Supabase adapter")

    async def update_generation(
        self,
        user_id: str,
        project_id: str,
        generation_id: str,
        generation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a generation"""
        raise NotImplementedError("Generations not yet implemented in Supabase adapter")

    async def delete_generation(
        self, user_id: str, project_id: str, generation_id: str
    ) -> bool:
        """Delete a generation"""
        raise NotImplementedError("Generations not yet implemented in Supabase adapter")

    # Deployments

    async def create_deployment(
        self, user_id: str, project_id: str, deployment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new deployment record"""
        raise NotImplementedError("Deployments not yet implemented in Supabase adapter")

    async def get_deployment(
        self, user_id: str, project_id: str, deployment_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a deployment by ID"""
        raise NotImplementedError("Deployments not yet implemented in Supabase adapter")

    async def list_deployments(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all deployments for a project"""
        raise NotImplementedError("Deployments not yet implemented in Supabase adapter")

    async def update_deployment(
        self,
        user_id: str,
        project_id: str,
        deployment_id: str,
        deployment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a deployment"""
        raise NotImplementedError("Deployments not yet implemented in Supabase adapter")

    async def delete_deployment(
        self, user_id: str, project_id: str, deployment_id: str
    ) -> bool:
        """Delete a deployment"""
        raise NotImplementedError("Deployments not yet implemented in Supabase adapter")

    # Billing

    async def create_billing_record(
        self, user_id: str, billing: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new billing record"""
        raise NotImplementedError("Billing not yet implemented in Supabase adapter")

    async def get_billing_record(
        self, user_id: str, billing_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a billing record by ID"""
        raise NotImplementedError("Billing not yet implemented in Supabase adapter")

    async def list_billing_records(self, user_id: str) -> List[Dict[str, Any]]:
        """List all billing records for a user"""
        raise NotImplementedError("Billing not yet implemented in Supabase adapter")

    async def update_billing_record(
        self, user_id: str, billing_id: str, billing: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a billing record"""
        raise NotImplementedError("Billing not yet implemented in Supabase adapter")

    async def delete_billing_record(self, user_id: str, billing_id: str) -> bool:
        """Delete a billing record"""
        raise NotImplementedError("Billing not yet implemented in Supabase adapter")
