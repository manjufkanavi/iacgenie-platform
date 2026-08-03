"""
Cloud Credentials Router

Manages cloud provider credentials (AWS, GCP, Azure) for a project.

All metadata is persisted in PostgreSQL via the db_provider adapter.
Sensitive credential values are stored in OpenBao (SecretManager).

Authentication: Keycloak-issued JWT verified by auth_middleware.
"""

import json
import logging

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db.db_provider import db_provider
from db.adapters.base import IDatabaseAdapter
from middleware.auth_middleware import verify_access_token
from config.roles import is_admin
from modules.secret_store.secret_manager import SecretManager
from modules.secret_store.config import SecretStoreConfig
from modules.secret_store.audit_logger import AuditLogger
from modules.secret_store.exceptions import (
    SecretNotFoundError,
    SecretAlreadyExistsError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cloud-credentials", tags=["cloud-credentials"])


# ---------------------------------------------------------------------------
# DB dependency — mirrors the pattern in routers/crud.py
# ---------------------------------------------------------------------------


async def get_db() -> IDatabaseAdapter:
    """Get the active database adapter."""
    return db_provider.adapter


# ---------------------------------------------------------------------------
# RBAC dependency — Owner/Admin only for credential write operations
# ---------------------------------------------------------------------------


def require_admin_or_owner(
    user: Dict[str, Any] = Depends(verify_access_token),
) -> Dict[str, Any]:
    """
    Dependency that allows only admin or project-owner users.
    Viewers and developers receive HTTP 403.
    """
    role = user.get("role", "user")
    if not is_admin(role):
        uid = user.get("uid", "unknown")
        logger.warning(
            f"RBAC denied: user={uid} role={role} attempted credential write operation"
        )
        raise HTTPException(
            status_code=403,
            detail={
                "error": "FORBIDDEN",
                "message": "Admin or Owner privileges are required to manage cloud credentials.",
                "code": "CREDENTIALS_WRITE_FORBIDDEN",
            },
        )
    return user


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class CloudCredentialsRequest(BaseModel):
    name: str = Field(..., description="Credentials name")
    provider: str = Field(..., description="Cloud provider (aws, gcp, azure)")
    credentials: Dict[str, Any] = Field(
        ..., description="Provider-specific credentials"
    )
    region: str = Field(default="", description="Default region")


class CloudCredentialsResponse(BaseModel):
    id: str
    name: str
    provider: str
    region: str
    status: str = "active"
    is_active: bool = True
    lastVerified: Optional[str] = None
    expiresAt: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class CloudCredentialsListResponse(BaseModel):
    credentials: List[Dict[str, Any]]
    total: int


class BulkCredentialIdsRequest(BaseModel):
    credential_ids: List[str] = Field(
        ..., min_length=1, description="List of credential IDs"
    )


class BulkCredentialResult(BaseModel):
    cred_id: str
    success: bool
    message: str


class BulkCredentialsResponse(BaseModel):
    results: List[BulkCredentialResult]
    total: int
    successes: int
    failures: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _secret_manager() -> SecretManager:
    return SecretManager(SecretStoreConfig.from_env())


def _audit_logger() -> AuditLogger:
    return AuditLogger(SecretStoreConfig.from_env())


def _default_expires_at(provider: str) -> str:
    """Calculate a sensible default expiry date based on provider."""
    now = datetime.utcnow()
    days = {"aws": 90, "azure": 90, "gcp": 365}.get(provider.lower(), 180)
    return (now + timedelta(days=days)).isoformat()


def _row_to_api(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise a DB row dict to the API response shape."""
    meta = row.get("metadata") or {}
    created_at = row.get("created_at")
    updated_at = row.get("updated_at")
    return {
        "id": row.get("id"),
        "name": row.get("name") or meta.get("name", ""),
        "provider": row.get("provider", ""),
        "region": meta.get("region", ""),
        "status": "active" if row.get("is_active", True) else "inactive",
        "is_active": row.get("is_active", True),
        "lastVerified": meta.get("lastVerified"),
        "expiresAt": meta.get("expiresAt"),
        "createdAt": created_at.isoformat() if created_at else None,
        "updatedAt": updated_at.isoformat() if updated_at else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/{project_id}", response_model=CloudCredentialsListResponse)
async def list_cloud_credentials(
    project_id: str,
    user: Dict[str, Any] = Depends(verify_access_token),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """List all cloud credentials for a project."""
    try:
        uid = user.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid user token")

        rows = await db.list_cloud_credentials(uid, project_id)
        credentials = [_row_to_api(r) for r in rows]
        return {"credentials": credentials, "total": len(credentials)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list cloud credentials: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list cloud credentials: {e}"
        )


@router.post("/{project_id}", status_code=201)
async def create_cloud_credentials(
    project_id: str,
    creds: CloudCredentialsRequest,
    user: Dict[str, Any] = Depends(require_admin_or_owner),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Create a new cloud credentials configuration."""
    try:
        uid = user.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid user token")

        provider = creds.provider.strip().lower()
        name = creds.name.strip()

        # Store actual credentials in OpenBao
        try:
            sm = _secret_manager()
            sm.create_secret(
                tenant_id=uid,
                secret_name=name,
                value=json.dumps(creds.credentials),
                secret_type="cloud_credentials",
                metadata={
                    "provider": provider,
                    "project_id": project_id,
                    "region": creds.region.strip(),
                },
                provider=provider,
            )
        except SecretAlreadyExistsError:
            raise HTTPException(
                status_code=400,
                detail=f"Cloud credentials with name '{name}' already exists in secret store",
            )
        except Exception as e:
            logger.error(f"Failed to store credentials in OpenBao: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to store credentials in secret store",
            )

        # Persist metadata in Postgres
        db_payload = {
            "name": name,
            "provider": provider,
            "credentials": {},  # never store raw creds in Postgres
            "is_active": True,
            "metadata": {
                "name": name,
                "region": creds.region.strip(),
                "expiresAt": _default_expires_at(provider),
            },
        }
        cred_id = await db.create_cloud_credentials(uid, project_id, db_payload)

        # Audit
        try:
            _audit_logger().log_secret_create(
                user_id=uid,
                secret_name=name,
                secret_type="cloud_credentials",
                success=True,
            )
        except Exception:
            pass

        logger.info(
            f"Cloud credentials created: user={uid} project={project_id} name={name}"
        )
        return {"id": cred_id, "name": name, "provider": provider, "status": "active"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create cloud credentials: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create cloud credentials: {e}"
        )


@router.put("/{project_id}/{cred_id}")
async def update_cloud_credentials(
    project_id: str,
    cred_id: str,
    creds: CloudCredentialsRequest,
    user: Dict[str, Any] = Depends(require_admin_or_owner),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Update an existing cloud credentials configuration."""
    try:
        uid = user.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid user token")

        # Verify credential exists
        existing = await db.get_cloud_credentials(uid, project_id, cred_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Cloud credentials not found")

        old_name = (
            existing.get("name") or (existing.get("metadata") or {}).get("name", "")
        ).strip()
        new_name = creds.name.strip()
        provider = creds.provider.strip().lower()

        # Update OpenBao secret
        try:
            sm = _secret_manager()
            # Delete old, create new (handles name changes too)
            try:
                sm.delete_secret(tenant_id=uid, secret_name=old_name, provider=provider)
            except SecretNotFoundError:
                pass
            sm.create_secret(
                tenant_id=uid,
                secret_name=new_name,
                value=json.dumps(creds.credentials),
                secret_type="cloud_credentials",
                metadata={
                    "provider": provider,
                    "project_id": project_id,
                    "region": creds.region.strip(),
                },
                provider=provider,
            )
        except Exception as e:
            logger.error(f"Failed to update credentials in OpenBao: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to update credentials in secret store",
            )

        # Update metadata in Postgres
        update_payload = {
            "name": new_name,
            "provider": provider,
            "metadata": {
                "name": new_name,
                "region": creds.region.strip(),
                "expiresAt": _default_expires_at(provider),
            },
        }
        await db.update_cloud_credentials(uid, project_id, cred_id, update_payload)

        # Audit
        try:
            _audit_logger().log_secret_update(
                user_id=uid,
                secret_name=new_name,
                success=True,
            )
        except Exception:
            pass

        logger.info(
            f"Cloud credentials updated: user={uid} project={project_id} cred={cred_id}"
        )
        return {
            "id": cred_id,
            "name": new_name,
            "provider": provider,
            "status": "active",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update cloud credentials: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update cloud credentials: {e}"
        )


@router.delete("/{project_id}/{cred_id}")
async def delete_cloud_credentials(
    project_id: str,
    cred_id: str,
    user: Dict[str, Any] = Depends(require_admin_or_owner),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Delete a cloud credentials configuration."""
    try:
        uid = user.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid user token")

        existing = await db.get_cloud_credentials(uid, project_id, cred_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Cloud credentials not found")

        meta = existing.get("metadata") or {}
        secret_name = existing.get("name") or meta.get("name") or ""
        provider = existing.get("provider")

        # Remove from OpenBao
        if secret_name and provider:
            try:
                _secret_manager().delete_secret(
                    tenant_id=uid, secret_name=secret_name, provider=provider
                )
            except SecretNotFoundError:
                pass  # Already removed or never existed
            except Exception as e:
                logger.warning(
                    f"Failed to delete from OpenBao (proceeding with DB delete): {e}"
                )

        # Delete metadata from Postgres
        success = await db.delete_cloud_credentials(uid, project_id, cred_id)
        if not success:
            raise HTTPException(status_code=404, detail="Cloud credentials not found")

        # Audit
        try:
            _audit_logger().log_secret_delete(
                user_id=uid,
                secret_name=secret_name or cred_id,
                success=True,
            )
        except Exception:
            pass

        logger.info(
            f"Cloud credentials deleted: user={uid} project={project_id} cred={cred_id}"
        )
        return {"message": "Cloud credentials deleted successfully", "id": cred_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete cloud credentials: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete cloud credentials: {e}"
        )


@router.post("/{project_id}/{cred_id}/test")
async def test_cloud_credentials(
    project_id: str,
    cred_id: str,
    user: Dict[str, Any] = Depends(verify_access_token),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Test a cloud credentials configuration."""
    try:
        uid = user.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid user token")

        existing = await db.get_cloud_credentials(uid, project_id, cred_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Cloud credentials not found")

        meta = existing.get("metadata") or {}
        secret_name = existing.get("name") or meta.get("name") or ""
        provider = existing.get("provider", "")

        # Read credentials from OpenBao
        try:
            sm = _secret_manager()
            vault_secret = sm.read_secret(
                tenant_id=uid,
                secret_name=secret_name,
                provider=provider,
            )
            credentials = json.loads(vault_secret.value)
        except SecretNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="Credentials not found in secret store",
            )
        except Exception as e:
            logger.error(f"Failed to read credentials from OpenBao: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to read credentials from secret store",
            )

        # Test the credentials against the cloud provider
        result = await _test_provider_credentials(provider, credentials, secret_name)

        # Update lastVerified in metadata if test passed
        if result.get("success"):
            updated_meta = {**meta, "lastVerified": datetime.utcnow().isoformat()}
            await db.update_cloud_credentials(
                uid, project_id, cred_id, {"metadata": updated_meta}
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test cloud credentials: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to test cloud credentials: {e}"
        )


@router.post("/{project_id}/bulk/verify")
async def bulk_verify_cloud_credentials(
    project_id: str,
    req: BulkCredentialIdsRequest,
    user: Dict[str, Any] = Depends(verify_access_token),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Test multiple cloud credentials in bulk."""
    try:
        uid = user.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid user token")

        results = []
        for cred_id in req.credential_ids:
            try:
                existing = await db.get_cloud_credentials(uid, project_id, cred_id)
                if not existing:
                    results.append(
                        BulkCredentialResult(
                            cred_id=cred_id, success=False, message="Not found"
                        )
                    )
                    continue
                meta = existing.get("metadata") or {}
                secret_name = existing.get("name") or meta.get("name") or ""
                provider = existing.get("provider", "")
                sm = _secret_manager()
                vault_secret = sm.read_secret(
                    tenant_id=uid, secret_name=secret_name, provider=provider
                )
                credentials = json.loads(vault_secret.value)
                result = await _test_provider_credentials(
                    provider, credentials, secret_name
                )
                results.append(
                    BulkCredentialResult(
                        cred_id=cred_id,
                        success=result.get("success", False),
                        message=result.get("message", "Test completed"),
                    )
                )
            except Exception as e:
                results.append(
                    BulkCredentialResult(cred_id=cred_id, success=False, message=str(e))
                )

        successes = sum(1 for r in results if r.success)
        return {
            "results": [r.model_dump() for r in results],
            "total": len(results),
            "successes": successes,
            "failures": len(results) - successes,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to bulk verify cloud credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to bulk verify: {e}")


@router.post("/{project_id}/bulk/revoke")
async def bulk_revoke_cloud_credentials(
    project_id: str,
    req: BulkCredentialIdsRequest,
    user: Dict[str, Any] = Depends(require_admin_or_owner),
    db: IDatabaseAdapter = Depends(get_db),
) -> Any:
    """Revoke multiple cloud credentials in bulk (set is_active=False)."""
    try:
        uid = user.get("uid")
        if not uid:
            raise HTTPException(status_code=401, detail="Invalid user token")

        results = []
        for cred_id in req.credential_ids:
            try:
                existing = await db.get_cloud_credentials(uid, project_id, cred_id)
                if not existing:
                    results.append(
                        BulkCredentialResult(
                            cred_id=cred_id, success=False, message="Not found"
                        )
                    )
                    continue
                await db.update_cloud_credentials(
                    uid, project_id, cred_id, {"is_active": False}
                )
                results.append(
                    BulkCredentialResult(
                        cred_id=cred_id, success=True, message="Revoked"
                    )
                )
            except Exception as e:
                results.append(
                    BulkCredentialResult(cred_id=cred_id, success=False, message=str(e))
                )

        successes = sum(1 for r in results if r.success)
        return {
            "results": [r.model_dump() for r in results],
            "total": len(results),
            "successes": successes,
            "failures": len(results) - successes,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to bulk revoke cloud credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to bulk revoke: {e}")


# ---------------------------------------------------------------------------
# Cloud provider test helpers
# ---------------------------------------------------------------------------


async def _test_provider_credentials(
    provider: str, credentials: Dict[str, Any], name: str
) -> Dict[str, Any]:
    """Dispatch to the correct cloud provider test function."""
    provider_lower = provider.lower()
    if provider_lower == "aws":
        return await _test_aws(credentials, name)
    elif provider_lower == "gcp":
        return await _test_gcp(credentials, name)
    elif provider_lower == "azure":
        return await _test_azure(credentials, name)
    else:
        return {
            "success": False,
            "message": f"Unsupported cloud provider: {provider}",
            "details": {"provider": provider, "name": name},
            "statusCode": 400,
        }


async def _test_aws(credentials: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Test AWS credentials by listing S3 buckets."""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        session = boto3.Session(
            aws_access_key_id=credentials.get("access_key_id"),
            aws_secret_access_key=credentials.get("secret_access_key"),
            region_name=credentials.get("region", "us-east-1"),
        )
        s3 = session.client("s3")
        response = s3.list_buckets()
        return {
            "success": True,
            "message": "AWS credentials are valid",
            "details": {
                "provider": "aws",
                "name": name,
                "account_id": response.get("Owner", {}).get("ID"),
                "bucket_count": len(response.get("Buckets", [])),
                "buckets": [b["Name"] for b in response.get("Buckets", [])[:5]],
            },
            "statusCode": 200,
        }
    except NoCredentialsError:
        return {
            "success": False,
            "message": "AWS credentials are invalid or missing",
            "details": {
                "provider": "aws",
                "name": name,
                "error": "No credentials found",
            },
            "statusCode": 401,
        }
    except ClientError as e:
        return {
            "success": False,
            "message": f"AWS credentials test failed: {e.response['Error']['Message']}",
            "details": {
                "provider": "aws",
                "name": name,
                "error": e.response["Error"]["Message"],
                "error_code": e.response["Error"]["Code"],
            },
            "statusCode": e.response["ResponseMetadata"]["HTTPStatusCode"],
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"AWS credentials test failed: {e}",
            "details": {"provider": "aws", "name": name, "error": str(e)},
            "statusCode": 500,
        }


async def _test_gcp(credentials: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Test GCP credentials by listing storage buckets."""
    try:
        from google.cloud import storage
        from google.auth.exceptions import DefaultCredentialsError

        client = storage.Client.from_service_account_info(credentials)
        buckets = list(client.list_buckets(max_results=5))
        return {
            "success": True,
            "message": "GCP credentials are valid",
            "details": {
                "provider": "gcp",
                "name": name,
                "project_id": client.project,
                "bucket_count": len(buckets),
                "buckets": [b.name for b in buckets],
            },
            "statusCode": 200,
        }
    except DefaultCredentialsError:
        return {
            "success": False,
            "message": "GCP credentials are invalid or missing",
            "details": {
                "provider": "gcp",
                "name": name,
                "error": "No credentials found",
            },
            "statusCode": 401,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"GCP credentials test failed: {e}",
            "details": {"provider": "gcp", "name": name, "error": str(e)},
            "statusCode": 500,
        }


async def _test_azure(credentials: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Test Azure credentials by listing resource groups."""
    try:
        from azure.identity import ClientSecretCredential
        from azure.mgmt.resource import ResourceManagementClient
        from azure.core.exceptions import ClientAuthenticationError

        credential = ClientSecretCredential(
            tenant_id=credentials.get("tenant_id"),
            client_id=credentials.get("client_id"),
            client_secret=credentials.get("client_secret"),
        )
        client = ResourceManagementClient(
            credential, credentials.get("subscription_id")
        )
        resource_groups = list(client.resource_groups.list(maxresults=5))
        return {
            "success": True,
            "message": "Azure credentials are valid",
            "details": {
                "provider": "azure",
                "name": name,
                "subscription_id": credentials.get("subscription_id"),
                "resource_group_count": len(resource_groups),
                "resource_groups": [rg.name for rg in resource_groups],
            },
            "statusCode": 200,
        }
    except ClientAuthenticationError:
        return {
            "success": False,
            "message": "Azure credentials are invalid or missing",
            "details": {
                "provider": "azure",
                "name": name,
                "error": "Authentication failed",
            },
            "statusCode": 401,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Azure credentials test failed: {e}",
            "details": {"provider": "azure", "name": name, "error": str(e)},
            "statusCode": 500,
        }
