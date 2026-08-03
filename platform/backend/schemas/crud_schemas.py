"""

Strict Pydantic request and response schemas for all dynamic CRUD entities.

Enforces type safety, formats input payloads, and returns standard FastAPI validation schemas.

"""

from pydantic import BaseModel, Field

from typing import Dict, Any, Optional

import re

from schemas.auth import validate_email


class ModelConfigCreate(BaseModel):
    """Schema for creating a model configuration"""

    provider: str = Field(
        ...,
        description="AI provider (Mistral, Gemini, OpenAI, Claude, Llama, Cohere, etc.)",
    )
    model_name: str = Field(..., description="Model name or identifier")
    base_url: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API key for the model")
    max_tokens: int = Field(8192, description="Maximum tokens for generation")
    temperature: float = Field(
        0.1, ge=0.0, le=2.0, description="Temperature for generation"
    )
    timeout: int = Field(120, description="Request timeout in seconds")
    retry_attempts: int = Field(3, description="Number of retry attempts")
    retry_delay: float = Field(1.0, description="Delay between retries in seconds")
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Additional headers"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def validate_provider(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Provider cannot be empty")
        normalized = v.strip().lower()
        provider_mapping = {
            "mistral": "mistral",
            "google": "gemini",
            "gemini": "gemini",
            "openai": "openai",
            "gpt": "openai",
            "anthropic": "claude",
            "claude": "claude",
            "meta": "llama",
            "llama": "llama",
            "cohere": "cohere",
            "custom": "custom",
        }
        return provider_mapping.get(normalized, v.strip())

    def validate_base_url(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Base URL cannot be empty")
        url = v.strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        try:
            if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", url):
                raise ValueError("Invalid URL format")
        except Exception:
            raise ValueError("Invalid URL format")
        return url

    def validate_model_name(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Model name cannot be empty")
        model = v.strip()
        if len(model) < 2:
            raise ValueError("Model name is too short")
        if re.search(r'[<>:"/\\|?*]', model):
            raise ValueError("Model name contains invalid characters")
        return model

    def validate_max_tokens(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Max tokens must be at least 1")
        if v > 100000:
            raise ValueError("Max tokens cannot exceed 100,000")
        return v


class ModelConfigUpdate(BaseModel):
    """Schema for updating an existing model configuration"""

    provider: Optional[str] = Field(None, description="AI provider")
    model_name: Optional[str] = Field(None, description="Model name or identifier")
    base_url: Optional[str] = Field(None, description="API base URL")
    api_key: Optional[str] = Field(None, description="API key for the model")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens for generation")
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Temperature for generation"
    )
    timeout: Optional[int] = Field(None, description="Request timeout in seconds")
    retry_attempts: Optional[int] = Field(None, description="Number of retry attempts")
    retry_delay: Optional[float] = Field(
        None, description="Delay between retries in seconds"
    )
    headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    def validate_provider(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return ModelConfigCreate.validate_provider(v)  # type: ignore[call-arg,arg-type]

    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return ModelConfigCreate.validate_base_url(v)  # type: ignore[call-arg,arg-type]

    def validate_model_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return ModelConfigCreate.validate_model_name(v)  # type: ignore[call-arg,arg-type]


class ModelConfigRotate(BaseModel):
    """Schema for rotating an API key"""

    api_key: str = Field(..., description="New API key")
    expires_at: Optional[str] = Field(None, description="Expiration date in ISO format")


class GitRepositoryCreate(BaseModel):
    """Schema for creating a git repository configuration"""

    name: Optional[str] = Field(
        "Git Repository", description="Human-readable name of the repository"
    )
    provider: Optional[str] = Field(
        "github", description="Git hosting provider (github, gitlab, bitbucket, etc.)"
    )
    url: Optional[str] = Field(None, description="Git clone URL")
    repo_url: Optional[str] = Field(
        None, description="Alternative key name for git clone URL"
    )
    branch: Optional[str] = Field("main", description="Target repository branch")
    token_encrypted: Optional[str] = Field(
        None, description="Encrypted authentication token"
    )
    accessToken: Optional[str] = Field(
        None, description="Alternative key for encrypted auth token"
    )
    token: Optional[str] = Field(None, description="Alternative key for auth token")
    ssh_key_encrypted: Optional[str] = Field(
        None, description="Encrypted private SSH key"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata dictionary"
    )

    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Git repository URL cannot be empty")
        return v


class GitRepositoryUpdate(BaseModel):
    """Schema for updating a git repository configuration"""

    name: Optional[str] = Field(
        None, description="Human-readable name of the repository"
    )
    provider: Optional[str] = Field(None, description="Git hosting provider")
    url: Optional[str] = Field(None, description="Git clone URL")
    repo_url: Optional[str] = Field(
        None, description="Alternative key name for git clone URL"
    )
    branch: Optional[str] = Field(None, description="Target repository branch")
    token_encrypted: Optional[str] = Field(
        None, description="Encrypted authentication token"
    )
    accessToken: Optional[str] = Field(
        None, description="Alternative key for encrypted auth token"
    )
    token: Optional[str] = Field(None, description="Alternative key for auth token")
    ssh_key_encrypted: Optional[str] = Field(
        None, description="Encrypted private SSH key"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata dictionary")


class CloudCredentialsCreate(BaseModel):
    """Schema for creating cloud credentials"""

    name: Optional[str] = Field(
        "Cloud Credentials", description="Friendly name for credentials"
    )
    provider: str = Field(
        ..., description="Cloud provider identifier (aws, gcp, azure, openstack, etc.)"
    )
    region: Optional[str] = Field("", description="Target cloud provider region")
    access_key: Optional[str] = Field(None, description="Cloud access key identifier")
    accessKeyId: Optional[str] = Field(
        None, description="Alternative key name for access key identifier"
    )
    accessKey: Optional[str] = Field(
        None, description="Alternative key name for access key"
    )
    secret_key: Optional[str] = Field(None, description="Cloud secret access key")
    secretAccessKey: Optional[str] = Field(
        None, description="Alternative key name for secret access key"
    )
    secretKey: Optional[str] = Field(
        None, description="Alternative key name for secret key"
    )
    credentials: Optional[Dict[str, Any]] = Field(
        None, description="Raw credentials key-value mappings"
    )
    creds: Optional[Dict[str, Any]] = Field(
        None, description="Alternative key name for raw credentials"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata dictionary"
    )

    def validate_provider(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Provider cannot be empty")
        return v.strip().lower()


class CloudCredentialsUpdate(BaseModel):
    """Schema for updating cloud credentials"""

    name: Optional[str] = Field(None, description="Friendly name for credentials")
    provider: Optional[str] = Field(None, description="Cloud provider identifier")
    region: Optional[str] = Field(None, description="Target cloud provider region")
    access_key: Optional[str] = Field(None, description="Cloud access key identifier")
    accessKeyId: Optional[str] = Field(
        None, description="Alternative key name for access key identifier"
    )
    accessKey: Optional[str] = Field(
        None, description="Alternative key name for access key"
    )
    secret_key: Optional[str] = Field(None, description="Cloud secret access key")
    secretAccessKey: Optional[str] = Field(
        None, description="Alternative key name for secret access key"
    )
    secretKey: Optional[str] = Field(
        None, description="Alternative key name for secret key"
    )
    credentials: Optional[Dict[str, Any]] = Field(
        None, description="Raw credentials key-value mappings"
    )
    creds: Optional[Dict[str, Any]] = Field(
        None, description="Alternative key name for raw credentials"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata dictionary")


class TeamMemberCreate(BaseModel):
    """Schema for adding a new team member to a project"""

    email: str = Field(..., description="Email address of the invited team member")
    name: Optional[str] = Field(None, description="Optional display name of the member")
    role: Optional[str] = Field(
        "viewer",
        description="Access role for the project (owner, admin, editor, viewer)",
    )
    status: Optional[str] = Field(
        "active", description="Account status (active, invited, suspended)"
    )
    permissions: Dict[str, Any] = Field(
        default_factory=dict, description="Custom fine-grained permissions mapping"
    )

    def validate_email_field(cls, v: str) -> str:
        return validate_email(v)

    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return "viewer"
        allowed = ["owner", "admin", "editor", "viewer"]
        if v.strip().lower() not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v.strip().lower()


class TeamMemberUpdate(BaseModel):
    """Schema for updating an existing team member"""

    email: Optional[str] = Field(None, description="Email address of the team member")
    name: Optional[str] = Field(None, description="Display name of the member")
    role: Optional[str] = Field(None, description="Access role for the project")
    status: Optional[str] = Field(None, description="Account status")
    permissions: Optional[Dict[str, Any]] = Field(
        None, description="Custom fine-grained permissions mapping"
    )

    def validate_email_field(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return validate_email(v)

    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return TeamMemberCreate.validate_role(v)  # type: ignore[call-arg,arg-type]


class IntegrationCreate(BaseModel):
    """Schema for configuring a new external integration"""

    name: Optional[str] = Field(
        "Integration", description="Friendly name of the integration"
    )
    type: str = Field(
        ..., description="Type of integration (slack, discord, webhook, email, etc.)"
    )
    configuration: Dict[str, Any] = Field(
        default_factory=dict, description="Key-value config parameters"
    )
    is_active: bool = Field(
        True, description="Whether the integration is currently enabled"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata dictionary"
    )

    def validate_type(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Integration type cannot be empty")
        return v.strip().lower()


class IntegrationUpdate(BaseModel):
    """Schema for updating an integration configuration"""

    name: Optional[str] = Field(None, description="Friendly name of the integration")
    type: Optional[str] = Field(None, description="Type of integration")
    configuration: Optional[Dict[str, Any]] = Field(
        None, description="Key-value config parameters"
    )
    is_active: Optional[bool] = Field(
        None, description="Whether the integration is currently enabled"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata dictionary")


class ApiKeyCreate(BaseModel):
    """Schema for creating an API key"""

    name: str = Field(..., description="Name or description of the API key")
    is_active: bool = Field(True, description="Whether the API key is active")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata dictionary"
    )


class ApiKeyUpdate(BaseModel):
    """Schema for updating an API key"""

    name: Optional[str] = Field(None, description="Name or description of the API key")
    is_active: Optional[bool] = Field(None, description="Whether the API key is active")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata dictionary")


class AuditLogCreate(BaseModel):
    """Schema for creating an audit log entry"""

    action: str = Field(..., description="Action description")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Log action details"
    )


class GenerationCreate(BaseModel):
    """Schema for creating a generation job record"""

    prompt: str = Field(..., description="Generation prompt")
    model: str = Field(..., description="AI model to use")
    provider: str = Field(..., description="Cloud provider")
    model_config_id: Optional[str] = Field(
        None, description="Model configuration reference ID"
    )
    status: str = Field("pending", description="Generation status")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata dictionary"
    )


class GenerationUpdate(BaseModel):
    """Schema for updating a generation job record"""

    prompt: Optional[str] = Field(None, description="Generation prompt")
    model: Optional[str] = Field(None, description="AI model to use")
    provider: Optional[str] = Field(None, description="Cloud provider")
    model_config_id: Optional[str] = Field(
        None, description="Model configuration reference ID"
    )
    status: Optional[str] = Field(None, description="Generation status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata dictionary")


class DeploymentCreate(BaseModel):
    """Schema for creating a deployment record"""

    generationId: str = Field(..., description="Reference generation job ID")
    provider: str = Field(..., description="Cloud provider target")
    region: str = Field(..., description="Cloud region target")
    credentialsId: str = Field(..., description="Cloud credential reference ID")
    status: str = Field("pending", description="Deployment status")


class DeploymentUpdate(BaseModel):
    """Schema for updating a deployment record"""

    generationId: Optional[str] = Field(None, description="Reference generation job ID")
    provider: Optional[str] = Field(None, description="Cloud provider target")
    region: Optional[str] = Field(None, description="Cloud region target")
    credentialsId: Optional[str] = Field(
        None, description="Cloud credential reference ID"
    )
    status: Optional[str] = Field(None, description="Deployment status")


class BillingCreate(BaseModel):
    """Schema for creating a billing record"""

    plan: str = Field(..., description="Subscription plan name")
    usage: Dict[str, Any] = Field(
        default_factory=dict, description="Project usage stats"
    )
    cost: float = Field(0.0, description="Accrued cost in USD")


class BillingUpdate(BaseModel):
    """Schema for updating a billing record"""

    plan: Optional[str] = Field(None, description="Subscription plan name")
    usage: Optional[Dict[str, Any]] = Field(None, description="Project usage stats")
    cost: Optional[float] = Field(None, description="Accrued cost in USD")
