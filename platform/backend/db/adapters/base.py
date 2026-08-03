"""

Base database adapter interface

Defines the contract that all database adapters must implement

"""

from abc import ABC, abstractmethod

from typing import Dict, List, Optional, Any


class IDatabaseAdapter(ABC):
    """Base interface for all database adapters"""

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the database connection"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the database connection"""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check database health and return status"""
        raise NotImplementedError()

    async def create_model_config(
        self, user_id: str, project_id: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new model configuration"""
        raise NotImplementedError()

    @abstractmethod
    async def get_model_config(
        self, user_id: str, project_id: str, config_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a model configuration by ID"""
        pass

    @abstractmethod
    async def list_model_configs(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all model configurations for a project"""
        pass

    @abstractmethod
    async def update_model_config(
        self, user_id: str, project_id: str, config_id: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a model configuration"""
        pass

    @abstractmethod
    async def delete_model_config(
        self, user_id: str, project_id: str, config_id: str
    ) -> bool:
        """Delete a model configuration"""
        pass

    @abstractmethod
    async def test_model_config(
        self, user_id: str, project_id: str, config_id: str
    ) -> Dict[str, Any]:
        """Test a model configuration"""
        pass

    async def create_git_repository(
        self, user_id: str, project_id: str, repo: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new git repository configuration"""
        raise NotImplementedError()

    @abstractmethod
    async def get_git_repository(
        self, user_id: str, project_id: str, repo_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a git repository configuration by ID"""
        pass

    @abstractmethod
    async def list_git_repositories(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all git repository configurations for a project"""
        pass

    @abstractmethod
    async def update_git_repository(
        self, user_id: str, project_id: str, repo_id: str, repo: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a git repository configuration"""
        pass

    @abstractmethod
    async def delete_git_repository(
        self, user_id: str, project_id: str, repo_id: str
    ) -> bool:
        """Delete a git repository configuration"""
        pass

    @abstractmethod
    async def test_git_repository(
        self, user_id: str, project_id: str, repo_id: str
    ) -> Dict[str, Any]:
        """Test a git repository configuration"""
        pass

    @abstractmethod
    async def get_repo_config(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Get repository configuration by primary key (bypasses user/project scoping)"""
        pass

    async def create_cloud_credentials(
        self, user_id: str, project_id: str, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create new cloud credentials"""
        raise NotImplementedError()

    @abstractmethod
    async def get_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cloud credentials by ID"""
        pass

    @abstractmethod
    async def list_cloud_credentials(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all cloud credentials for a project"""
        pass

    @abstractmethod
    async def update_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update cloud credentials"""
        pass

    @abstractmethod
    async def delete_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str
    ) -> bool:
        """Delete cloud credentials"""
        pass

    @abstractmethod
    async def test_cloud_credentials(
        self, user_id: str, project_id: str, cred_id: str
    ) -> Dict[str, Any]:
        """Test cloud credentials"""
        pass

    async def create_team_member(
        self, user_id: str, project_id: str, member: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new team member"""
        raise NotImplementedError()

    @abstractmethod
    async def get_team_member(
        self, user_id: str, project_id: str, member_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a team member by ID"""
        pass

    @abstractmethod
    async def list_team_members(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all team members for a project"""
        pass

    @abstractmethod
    async def update_team_member(
        self, user_id: str, project_id: str, member_id: str, member: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a team member"""
        pass

    @abstractmethod
    async def delete_team_member(
        self, user_id: str, project_id: str, member_id: str
    ) -> bool:
        """Delete a team member"""
        pass

    async def create_integration(
        self, user_id: str, project_id: str, integration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new integration"""
        raise NotImplementedError()

    @abstractmethod
    async def get_integration(
        self, user_id: str, project_id: str, integration_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get an integration by ID"""
        pass

    @abstractmethod
    async def list_integrations(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all integrations for a project"""
        pass

    @abstractmethod
    async def update_integration(
        self,
        user_id: str,
        project_id: str,
        integration_id: str,
        integration: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an integration"""
        pass

    @abstractmethod
    async def delete_integration(
        self, user_id: str, project_id: str, integration_id: str
    ) -> bool:
        """Delete an integration"""
        pass

    @abstractmethod
    async def test_integration(
        self, user_id: str, project_id: str, integration_id: str
    ) -> Dict[str, Any]:
        """Test an integration"""
        pass

    async def create_project(
        self, user_id: str, project: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new project"""
        raise NotImplementedError()

    @abstractmethod
    async def get_project(
        self, user_id: str, project_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a project by ID"""
        pass

    @abstractmethod
    async def list_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """List all projects for a user"""
        pass

    @abstractmethod
    async def update_project(
        self, user_id: str, project_id: str, project: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a project"""
        pass

    @abstractmethod
    async def delete_project(self, user_id: str, project_id: str) -> bool:
        """Delete a project"""
        pass

    async def create_api_key(
        self, user_id: str, api_key: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new API key"""
        raise NotImplementedError()

    @abstractmethod
    async def get_api_key(self, user_id: str, key_id: str) -> Optional[Dict[str, Any]]:
        """Get an API key by ID"""
        pass

    @abstractmethod
    async def list_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """List all API keys for a user"""
        pass

    @abstractmethod
    async def update_api_key(
        self, user_id: str, key_id: str, api_key: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an API key"""
        pass

    @abstractmethod
    async def delete_api_key(self, user_id: str, key_id: str) -> bool:
        """Delete an API key"""
        pass

    async def create_audit_log(
        self, user_id: str, log: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new audit log entry"""
        raise NotImplementedError()

    @abstractmethod
    async def list_audit_logs(
        self, user_id: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List audit logs with optional filters"""
        pass

    async def create_generation(
        self, user_id: str, project_id: str, generation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new generation record"""
        raise NotImplementedError()

    @abstractmethod
    async def get_generation(
        self, user_id: str, project_id: str, generation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a generation by ID"""
        pass

    @abstractmethod
    async def list_generations(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all generations for a project"""
        pass

    @abstractmethod
    async def update_generation(
        self,
        user_id: str,
        project_id: str,
        generation_id: str,
        generation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a generation"""
        pass

    @abstractmethod
    async def delete_generation(
        self, user_id: str, project_id: str, generation_id: str
    ) -> bool:
        """Delete a generation"""
        pass

    # ---- generation_jobs (primary table) ----

    async def create_generation_job(
        self, job_data: Dict[str, Any], job_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a new generation job record"""
        raise NotImplementedError()

    @abstractmethod
    async def get_generation_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a generation job by ID"""
        pass

    @abstractmethod
    async def list_generation_jobs(self, project_id: str) -> List[Dict[str, Any]]:
        """List all generation jobs for a project"""
        pass

    @abstractmethod
    async def update_generation_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update a generation job"""
        pass

    @abstractmethod
    async def delete_generation_job(self, job_id: str) -> bool:
        """Delete a generation job"""
        pass

    @abstractmethod
    async def list_running_jobs(self) -> List[Dict[str, Any]]:
        """List all generation jobs currently in 'running' status."""
        pass

    @abstractmethod
    async def find_recent_running_jobs(
        self, prompt_text: str, max_age_minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """Find running jobs with matching prompt created within max_age_minutes."""
        pass

    async def create_deployment(
        self, user_id: str, project_id: str, deployment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new deployment record"""
        raise NotImplementedError()

    @abstractmethod
    async def get_deployment(
        self, user_id: str, project_id: str, deployment_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a deployment by ID"""
        pass

    @abstractmethod
    async def list_deployments(
        self, user_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """List all deployments for a project"""
        pass

    @abstractmethod
    async def update_deployment(
        self,
        user_id: str,
        project_id: str,
        deployment_id: str,
        deployment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update a deployment"""
        pass

    @abstractmethod
    async def delete_deployment(
        self, user_id: str, project_id: str, deployment_id: str
    ) -> bool:
        """Delete a deployment"""
        pass

    async def create_billing_record(
        self, user_id: str, billing: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new billing record"""
        raise NotImplementedError()

    @abstractmethod
    async def get_billing_record(
        self, user_id: str, billing_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a billing record by ID"""
        pass

    @abstractmethod
    async def list_billing_records(self, user_id: str) -> List[Dict[str, Any]]:
        """List all billing records for a user"""
        pass

    @abstractmethod
    async def update_billing_record(
        self, user_id: str, billing_id: str, billing: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a billing record"""
        pass

    @abstractmethod
    async def delete_billing_record(self, user_id: str, billing_id: str) -> bool:
        """Delete a billing record"""
        pass

    async def create_webhook(
        self, user_id: str, webhook: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new webhook"""
        raise NotImplementedError()

    @abstractmethod
    async def get_webhook(
        self, user_id: str, webhook_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a webhook by ID"""
        pass

    @abstractmethod
    async def list_webhooks(self, user_id: str) -> List[Dict[str, Any]]:
        """List all webhooks for a user"""
        pass

    @abstractmethod
    async def update_webhook(
        self, user_id: str, webhook_id: str, webhook: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a webhook"""
        pass

    @abstractmethod
    async def delete_webhook(self, user_id: str, webhook_id: str) -> bool:
        """Delete a webhook"""
        pass

    @abstractmethod
    async def get_webhook_by_id(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """Get a webhook by ID (for incoming webhooks)"""
        pass

    @abstractmethod
    async def create_webhook_log(
        self, user_id: str, webhook_id: str, log: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a webhook delivery log"""
        pass

    @abstractmethod
    async def get_webhook_logs(
        self, user_id: str, webhook_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get webhook delivery logs"""
        pass

    @abstractmethod
    async def create_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Create a webhook event (for incoming webhooks)"""
        pass

    @abstractmethod
    async def list_webhook_events(
        self, user_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List webhook events for a user"""
        pass

    @abstractmethod
    async def get_webhook_event(
        self, user_id: str, event_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a webhook event by ID"""
        pass

    @abstractmethod
    async def get_webhook_stats(self, user_id: str) -> Dict[str, Any]:
        """Get webhook statistics for a user"""
        pass

    @abstractmethod
    async def update_webhook_event(
        self, user_id: str, event_id: str, event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a webhook event"""
        pass

    async def list_all_users(self) -> List[Dict[str, Any]]:
        """List all users (admin only)"""
        raise NotImplementedError()

    @abstractmethod
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user (admin only)"""
        pass

    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user by ID (admin only)"""
        pass

    @abstractmethod
    async def update_user(
        self, user_id: str, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a user (admin only)"""
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user (admin only)"""
        pass

    @abstractmethod
    async def list_all_projects(self) -> List[Dict[str, Any]]:
        """List all projects (admin only)"""
        pass

    @abstractmethod
    async def get_project_admin(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a project by ID (admin only)"""
        pass

    @abstractmethod
    async def update_project_admin(
        self, project_id: str, project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a project (admin only)"""
        pass

    @abstractmethod
    async def create_project_admin(
        self, project_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new project (admin only)"""
        pass

    @abstractmethod
    async def find_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a project by name (admin only)"""
        pass

    @abstractmethod
    async def delete_project_admin(self, project_id: str) -> bool:
        """Delete a project (admin only)"""
        pass

    @abstractmethod
    async def assign_user_to_project(self, user_id: str, project_id: str) -> None:
        """Assign a user to a project (admin only)"""
        pass

    @abstractmethod
    async def unassign_user_from_project(self, user_id: str, project_id: str) -> None:
        """Unassign a user from a project (admin only)"""
        pass

    @abstractmethod
    async def is_user_assigned_to_project(self, user_id: str, project_id: str) -> bool:
        """Check if a user is assigned to a project (admin only)"""
        pass

    @abstractmethod
    async def get_project_members_admin(self, project_id: str) -> List[Any]:
        """Get all members of a project (admin only)"""
        pass

    @abstractmethod
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics (admin only)"""
        pass

    @abstractmethod
    async def get_user_stats(self) -> Dict[str, Any]:
        """Get user statistics (admin only)"""
        pass

    @abstractmethod
    async def get_project_stats(self) -> Dict[str, Any]:
        """Get project statistics (admin only)"""
        pass

    async def validate_api_key(
        self, user_id: str, provider: str, api_key: str
    ) -> Dict[str, Any]:
        """Validate an API key for a provider"""
        raise NotImplementedError()
