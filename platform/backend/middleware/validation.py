"""

Input validation middleware and Pydantic models

"""

from pydantic import BaseModel, Field, EmailStr

from typing import List, Optional, Dict, Any

from datetime import datetime

import re

# Base Models


class BaseRequest(BaseModel):
    """Base request model with common fields"""

    pass


class BaseResponse(BaseModel):
    """Base response model with common fields"""

    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Project Models


class ProjectCreate(BaseRequest):
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(
        None, max_length=500, description="Project description"
    )
    tags: Optional[List[str]] = Field(
        default=[], max_length=10, description="Project tags"
    )

    def validate_tags(cls, v):
        if v is not None:
            for tag in v:
                if not re.match(r"^[a-zA-Z0-9_-]+$", tag):
                    raise ValueError(
                        "Tags must contain only letters, numbers, underscores, and hyphens"
                    )
        return v


class ProjectUpdate(BaseRequest):
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Project name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Project description"
    )
    tags: Optional[List[str]] = Field(None, max_length=10, description="Project tags")

    def validate_tags(cls, v):
        if v is not None:
            for tag in v:
                if not re.match(r"^[a-zA-Z0-9_-]+$", tag):
                    raise ValueError(
                        "Tags must contain only letters, numbers, underscores, and hyphens"
                    )
        return v

    status: Optional[str] = Field(
        None, pattern="^(active|inactive|archived)$", description="Project status"
    )


# Model Configuration Models


class ModelConfigCreate(BaseRequest):
    provider: str = Field(
        ..., pattern="^(openai|anthropic|google|mistral)$", description="AI provider"
    )
    model_name: str = Field(..., min_length=1, max_length=100, description="Model name")
    base_url: Optional[str] = Field(None, description="Base URL for API")
    api_key: Optional[str] = Field(None, min_length=10, description="API key")
    max_tokens: Optional[int] = Field(
        4000, ge=1, le=100000, description="Maximum tokens"
    )
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Temperature")
    timeout: Optional[int] = Field(30, ge=1, le=300, description="Timeout in seconds")
    retry_attempts: Optional[int] = Field(3, ge=0, le=10, description="Retry attempts")
    retry_delay: Optional[int] = Field(
        1, ge=0, le=60, description="Retry delay in seconds"
    )
    headers: Optional[Dict[str, str]] = Field(
        default={}, description="Additional headers"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default={}, description="Additional metadata"
    )
    secure: Optional[bool] = Field(True, description="Use secure connection")


class ModelConfigUpdate(BaseRequest):
    provider: Optional[str] = Field(
        None, pattern="^(openai|anthropic|google|mistral)$", description="AI provider"
    )
    model_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Model name"
    )
    base_url: Optional[str] = Field(None, description="Base URL for API")
    api_key: Optional[str] = Field(None, min_length=10, description="API key")
    max_tokens: Optional[int] = Field(
        None, ge=1, le=100000, description="Maximum tokens"
    )
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Temperature"
    )
    timeout: Optional[int] = Field(None, ge=1, le=300, description="Timeout in seconds")
    retry_attempts: Optional[int] = Field(
        None, ge=0, le=10, description="Retry attempts"
    )
    retry_delay: Optional[int] = Field(
        None, ge=0, le=60, description="Retry delay in seconds"
    )
    headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    secure: Optional[bool] = Field(None, description="Use secure connection")


# API Key Models


class APIKeyCreate(BaseRequest):
    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    permissions: List[str] = Field(..., min_length=1, description="API key permissions")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    description: Optional[str] = Field(
        None, max_length=500, description="API key description"
    )

    def validate_permissions(cls, v):
        valid_permissions = ["read", "write", "delete", "admin", "billing", "deploy"]
        if v is not None:
            for permission in v:
                if permission not in valid_permissions:
                    raise ValueError(
                        f"Invalid permission: {permission}. Valid permissions: {valid_permissions}"
                    )
        return v


class APIKeyUpdate(BaseRequest):
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="API key name"
    )
    permissions: Optional[List[str]] = Field(
        None, min_length=1, description="API key permissions"
    )
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    description: Optional[str] = Field(
        None, max_length=500, description="API key description"
    )
    is_active: Optional[bool] = Field(None, description="API key active status")

    def validate_permissions(cls, v):
        valid_permissions = ["read", "write", "delete", "admin", "billing", "deploy"]
        if v is not None:
            for permission in v:
                if permission not in valid_permissions:
                    raise ValueError(
                        f"Invalid permission: {permission}. Valid permissions: {valid_permissions}"
                    )
        return v


# Generation Models


class GenerationCreate(BaseRequest):
    prompt: str = Field(
        ..., min_length=1, max_length=10000, description="Generation prompt"
    )
    model: str = Field(..., min_length=1, max_length=100, description="Model to use")
    provider: str = Field(
        ...,
        pattern="^(openai|anthropic|google|mistral|aws|azure|gcp)$",
        description="Provider",
    )
    max_tokens: Optional[int] = Field(
        None, ge=1, le=100000, description="Maximum tokens"
    )
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Temperature"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default={}, description="Additional metadata"
    )


class GenerationUpdate(BaseRequest):
    status: Optional[str] = Field(
        None,
        pattern="^(pending|processing|completed|failed|cancelled)$",
        description="Generation status",
    )
    progress: Optional[int] = Field(
        None, ge=0, le=100, description="Progress percentage"
    )
    logs: Optional[List[Dict[str, Any]]] = Field(None, description="Generation logs")
    outputs: Optional[Dict[str, Any]] = Field(None, description="Generation outputs")
    error: Optional[str] = Field(None, description="Error message")


# Deployment Models


class DeploymentCreate(BaseRequest):
    generation_id: str = Field(..., min_length=1, description="Generation ID to deploy")
    provider: str = Field(
        ...,
        pattern="^(aws|azure|gcp|terraform|kubernetes)$",
        description="Deployment provider",
    )
    region: Optional[str] = Field(
        None, min_length=1, max_length=50, description="Deployment region"
    )
    credentials_id: Optional[str] = Field(
        None, min_length=1, description="Cloud credentials ID"
    )
    environment: Optional[str] = Field(
        "production",
        pattern="^(development|staging|production)$",
        description="Deployment environment",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default={}, description="Additional metadata"
    )


class DeploymentUpdate(BaseRequest):
    status: Optional[str] = Field(
        None,
        pattern="^(pending|deploying|success|failed|destroyed)$",
        description="Deployment status",
    )
    logs: Optional[List[Dict[str, Any]]] = Field(None, description="Deployment logs")
    outputs: Optional[Dict[str, Any]] = Field(None, description="Deployment outputs")
    error: Optional[str] = Field(None, description="Error message")


# Billing Models


class BillingRecordCreate(BaseRequest):
    amount: float = Field(..., ge=0.0, description="Billing amount")
    currency: str = Field("USD", pattern="^(USD|EUR|GBP|JPY)$", description="Currency")
    description: str = Field(
        ..., min_length=1, max_length=500, description="Billing description"
    )
    billing_period: Optional[str] = Field(
        None,
        pattern="^(monthly|quarterly|yearly|one_time)$",
        description="Billing period",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default={}, description="Additional metadata"
    )


class BillingRecordUpdate(BaseRequest):
    amount: Optional[float] = Field(None, ge=0.0, description="Billing amount")
    currency: Optional[str] = Field(
        None, pattern="^(USD|EUR|GBP|JPY)$", description="Currency"
    )
    description: Optional[str] = Field(
        None, min_length=1, max_length=500, description="Billing description"
    )
    status: Optional[str] = Field(
        None, pattern="^(pending|paid|failed|cancelled)$", description="Payment status"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


# Team Member Models


class TeamMemberCreate(BaseRequest):
    email: EmailStr = Field(..., description="Team member email")
    name: str = Field(..., min_length=1, max_length=100, description="Team member name")
    role: str = Field(
        ..., pattern="^(owner|admin|editor|viewer)$", description="Team member role"
    )
    permissions: Optional[List[str]] = Field(
        default=[], description="Specific permissions"
    )

    def validate_permissions(cls, v):
        valid_permissions = ["read", "write", "delete", "admin", "billing", "deploy"]
        if v is not None:
            for permission in v:
                if permission not in valid_permissions:
                    raise ValueError(
                        f"Invalid permission: {permission}. Valid permissions: {valid_permissions}"
                    )
        return v


class TeamMemberUpdate(BaseRequest):
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Team member name"
    )
    role: Optional[str] = Field(
        None, pattern="^(owner|admin|editor|viewer)$", description="Team member role"
    )
    permissions: Optional[List[str]] = Field(None, description="Specific permissions")
    status: Optional[str] = Field(
        None, pattern="^(pending|active|inactive)$", description="Member status"
    )

    def validate_permissions(cls, v):
        valid_permissions = ["read", "write", "delete", "admin", "billing", "deploy"]
        if v is not None:
            for permission in v:
                if permission not in valid_permissions:
                    raise ValueError(
                        f"Invalid permission: {permission}. Valid permissions: {valid_permissions}"
                    )
        return v


# Integration Models


class IntegrationCreate(BaseRequest):
    type: str = Field(
        ...,
        pattern="^(slack|discord|email|webhook|github|gitlab)$",
        description="Integration type",
    )
    name: str = Field(..., min_length=1, max_length=100, description="Integration name")
    config: Dict[str, Any] = Field(..., description="Integration configuration")
    events: Optional[List[str]] = Field(
        default=[], description="Events to trigger integration"
    )

    def validate_events(cls, v):
        valid_events = [
            "generation.completed",
            "generation.failed",
            "deployment.completed",
            "deployment.failed",
            "project.created",
            "project.updated",
            "project.deleted",
            "user.created",
            "user.updated",
            "billing.charged",
            "billing.failed",
        ]
        if v is not None:
            for event in v:
                if event not in valid_events:
                    raise ValueError(
                        f"Invalid event: {event}. Valid events: {valid_events}"
                    )
        return v


class IntegrationUpdate(BaseRequest):
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Integration name"
    )
    config: Optional[Dict[str, Any]] = Field(
        None, description="Integration configuration"
    )
    events: Optional[List[str]] = Field(
        None, description="Events to trigger integration"
    )
    is_active: Optional[bool] = Field(None, description="Integration active status")

    def validate_events(cls, v):
        valid_events = [
            "generation.completed",
            "generation.failed",
            "deployment.completed",
            "deployment.failed",
            "project.created",
            "project.updated",
            "project.deleted",
            "user.created",
            "user.updated",
            "billing.charged",
            "billing.failed",
        ]
        if v is not None:
            for event in v:
                if event not in valid_events:
                    raise ValueError(
                        f"Invalid event: {event}. Valid events: {valid_events}"
                    )
        return v


# Cloud Credentials Models


class CloudCredentialsCreate(BaseRequest):
    provider: str = Field(
        ...,
        pattern="^(aws|azure|gcp|digitalocean|linode)$",
        description="Cloud provider",
    )
    name: str = Field(..., min_length=1, max_length=100, description="Credentials name")
    region: Optional[str] = Field(
        None, min_length=1, max_length=50, description="Default region"
    )
    access_key: Optional[str] = Field(None, min_length=10, description="Access key")
    secret_key: Optional[str] = Field(None, min_length=10, description="Secret key")
    metadata: Optional[Dict[str, Any]] = Field(
        default={}, description="Additional metadata"
    )


class CloudCredentialsUpdate(BaseRequest):
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Credentials name"
    )
    region: Optional[str] = Field(
        None, min_length=1, max_length=50, description="Default region"
    )
    access_key: Optional[str] = Field(None, min_length=10, description="Access key")
    secret_key: Optional[str] = Field(None, min_length=10, description="Secret key")
    is_active: Optional[bool] = Field(None, description="Credentials active status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


# Git Repository Models


class GitRepositoryCreate(BaseRequest):
    name: str = Field(..., min_length=1, max_length=100, description="Repository name")
    url: str = Field(..., pattern="^https?://.*", description="Repository URL")
    branch: str = Field(
        "main", min_length=1, max_length=100, description="Default branch"
    )
    provider: str = Field(
        ..., pattern="^(github|gitlab|bitbucket|azure)$", description="Git provider"
    )
    token: Optional[str] = Field(None, min_length=10, description="Access token")
    ssh_key: Optional[str] = Field(None, description="SSH key")
    metadata: Optional[Dict[str, Any]] = Field(
        default={}, description="Additional metadata"
    )


class GitRepositoryUpdate(BaseRequest):
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Repository name"
    )
    url: Optional[str] = Field(
        None, pattern="^https?://.*", description="Repository URL"
    )
    branch: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Default branch"
    )
    token: Optional[str] = Field(None, min_length=10, description="Access token")
    ssh_key: Optional[str] = Field(None, description="SSH key")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


# Webhook Models


class WebhookCreate(BaseRequest):
    name: str = Field(..., min_length=1, max_length=100, description="Webhook name")
    url: str = Field(..., pattern="^https?://.*", description="Webhook URL")
    events: List[str] = Field(
        ..., min_length=1, description="Events to trigger webhook"
    )
    secret: Optional[str] = Field(None, min_length=10, description="Webhook secret")
    headers: Optional[Dict[str, str]] = Field(
        default={}, description="Additional headers"
    )
    retry_count: Optional[int] = Field(3, ge=0, le=10, description="Retry count")
    timeout: Optional[int] = Field(30, ge=1, le=300, description="Timeout in seconds")


class WebhookUpdate(BaseRequest):
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Webhook name"
    )
    url: Optional[str] = Field(None, pattern="^https?://.*", description="Webhook URL")
    events: Optional[List[str]] = Field(
        None, min_length=1, description="Events to trigger webhook"
    )
    secret: Optional[str] = Field(None, min_length=10, description="Webhook secret")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")
    retry_count: Optional[int] = Field(None, ge=0, le=10, description="Retry count")
    timeout: Optional[int] = Field(None, ge=1, le=300, description="Timeout in seconds")
    is_active: Optional[bool] = Field(None, description="Webhook active status")


# Audit Log Models


class AuditLogCreate(BaseRequest):
    action: str = Field(
        ..., min_length=1, max_length=100, description="Action performed"
    )
    resource: str = Field(
        ..., min_length=1, max_length=200, description="Resource affected"
    )
    details: Optional[str] = Field(None, max_length=1000, description="Action details")
    ip_address: Optional[str] = Field(
        None, pattern=r"^(\d{1,3}\.){3}\d{1,3}$", description="IP address"
    )
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent")
    metadata: Optional[Dict[str, Any]] = Field(
        default={}, description="Additional metadata"
    )


# API Key Validation Models


class APIKeyValidation(BaseRequest):
    provider: str = Field(
        ...,
        pattern="^(openai|anthropic|google|mistral|aws|azure|gcp)$",
        description="Provider",
    )
    api_key: str = Field(..., min_length=10, description="API key to validate")


# Code Generation Models


class CodeGenerationRequest(BaseRequest):
    prompt: str = Field(
        ..., min_length=1, max_length=10000, description="Generation prompt"
    )
    model: str = Field(..., min_length=1, max_length=100, description="Model to use")
    provider: str = Field(
        ...,
        pattern="^(openai|anthropic|google|mistral|aws|azure|gcp)$",
        description="Provider",
    )
    project_id: str = Field(..., min_length=1, description="Project ID")
    max_tokens: Optional[int] = Field(
        None, ge=1, le=100000, description="Maximum tokens"
    )
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Temperature"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default={}, description="Additional metadata"
    )


# Admin Models


class UserCreate(BaseRequest):
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., min_length=1, max_length=100, description="User name")
    role: str = Field(..., pattern="^(admin|user|viewer)$", description="User role")
    is_active: Optional[bool] = Field(True, description="User active status")


class UserUpdate(BaseRequest):
    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="User name"
    )
    role: Optional[str] = Field(
        None, pattern="^(admin|user|viewer)$", description="User role"
    )
    is_active: Optional[bool] = Field(None, description="User active status")
