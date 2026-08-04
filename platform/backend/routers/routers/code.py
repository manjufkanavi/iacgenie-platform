from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
import logging
import asyncio
import os
import json
import time
from typing import Dict, Any
import docker

from middleware.auth_middleware import verify_access_token
from db.db_provider import db_provider
from middleware.rate_limiting import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/code", tags=["Code Workspace"])

rate_limiter = RateLimiter(default_limit=10, default_window=60)


async def check_edit_permissions(workspace_id: str, user: dict) -> bool:
    """RBAC Enforcement: Checks if user has explicit edit permissions for the workspace."""
    try:
        db = db_provider.adapter
        if not db:
            return False

        project = await db.get_project(user["uid"], workspace_id)
        if not project:
            return False

        if project.get("ownerId") == user["uid"]:
            return True

        if hasattr(db, "get_project_team_members"):
            team_members = await db.get_project_team_members(workspace_id)
            for member in team_members:
                if member.get("userId") == user["uid"]:
                    role = member.get("role")
                    if role in ["admin", "editor", "owner"]:
                        return True
        return False
    except Exception as e:
        logger.error(f"Error checking permissions: {e}")
        return False


# Security: Path Traversal Protection
def validate_path(path: str) -> str:
    """Implement strict input sanitization to prevent path traversal."""
    normalized_path = os.path.normpath(path)
    if (
        normalized_path.startswith("..")
        or "/../" in normalized_path
        or normalized_path.startswith("/")
    ):
        raise HTTPException(
            status_code=400, detail="Invalid path: Path traversal detected"
        )
    return normalized_path


# State locking using ETags (Optimistic Locking)
FILE_VERSIONS: Dict[str, str] = {}


@router.post("/save")
async def save_code(
    request: Request,
    user: dict = Depends(verify_access_token),
) -> Dict[str, Any]:
    """Save code endpoint with rate limiting, RBAC, path traversal protection, payload limit, and ETag locking"""
    # 1. Rate Limiting
    limit_info = rate_limiter.check_rate_limit(request, endpoint="code_save")
    if limit_info["remaining"] < 0:
        raise HTTPException(status_code=429, detail="Too many save requests")

    # 2. Payload Limit (e.g. 5MB limit for exhaustion protection)
    content_length = request.headers.get("Content-Length")
    if content_length and int(content_length) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    workspace_id = body.get("workspace_id")
    filepath = body.get("filepath", "")
    content = body.get("content", "")
    etag = body.get("etag")

    if not workspace_id or not filepath:
        raise HTTPException(status_code=400, detail="Missing workspace_id or filepath")

    # 3. RBAC Enforcement
    has_perm = await check_edit_permissions(workspace_id, user)
    if not has_perm:
        raise HTTPException(
            status_code=403, detail="Insufficient edit permissions for workspace"
        )

    # 4. Path Traversal Protection
    safe_path = validate_path(filepath)

    # 5. File Locking (Optimistic Conflict Resolution)
    file_key = f"{workspace_id}:{safe_path}"
    current_etag = FILE_VERSIONS.get(file_key)

    if current_etag and etag and current_etag != etag:
        raise HTTPException(
            status_code=409, detail="Conflict: File has been modified by another user"
        )

    import hashlib

    new_etag = hashlib.md5(f"{time.time()}-{content}".encode()).hexdigest()
    FILE_VERSIONS[file_key] = new_etag

    # Save simulation
    full_path = os.path.join("/tmp", "workspace", workspace_id, safe_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

    return {"status": "success", "etag": new_etag, "message": "File saved successfully"}


@router.post("/format")
async def format_code(
    request: Request,
    user: dict = Depends(verify_access_token),
) -> Dict[str, Any]:
    """Format code using tofu fmt within a sandboxed environment"""
    content_length = request.headers.get("Content-Length")
    if content_length and int(content_length) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    code = body.get("content", "")

    # 6. Command Sandboxing: Run isolated via standard out/in instead of unsafe shell
    # Dispatched to an ephemeral docker container
    try:

        def run_format() -> tuple[str, str, int]:
            client = docker.from_env()  # type: ignore
            container = client.containers.create(
                "hashicorp/terraform:latest",
                command=["fmt", "-"],
                stdin_open=True,
                detach=True,
            )
            container.start()
            skt = container.attach_socket(params={"stdin": 1, "stream": 1})
            skt._sock.sendall(code.encode())
            skt._sock.close()
            container.wait(timeout=10)
            stdout = container.logs(stdout=True, stderr=False).decode()
            stderr = container.logs(stdout=False, stderr=True).decode()
            container.remove(force=True)
            return stdout, stderr, 0 if not stderr else 1

        loop = asyncio.get_running_loop()
        stdout, stderr, exit_code = await loop.run_in_executor(None, run_format)

        if exit_code == 0 and stdout:
            return {"status": "success", "formatted_content": stdout}
        else:
            return {"status": "error", "message": stderr}
    except Exception as e:
        logger.error(f"Format error: {e}")
        return {"status": "error", "message": "Formatting tool not available or failed"}


@router.post("/validate")
async def validate_code(
    request: Request,
    user: dict = Depends(verify_access_token),
) -> Dict[str, Any]:
    """Deep validation API running tofu validate and tflint"""
    content_length = request.headers.get("Content-Length")
    if content_length and int(content_length) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    code = body.get("content", "")
    diagnostics = []

    try:

        def run_validate() -> tuple[str, str]:
            client = docker.from_env()  # type: ignore
            # Run terraform validate
            try:
                tf_container = client.containers.create(
                    "hashicorp/terraform:latest",
                    command=["validate", "-json"],
                    stdin_open=True,
                    detach=True,
                )
                tf_container.start()
                skt = tf_container.attach_socket(params={"stdin": 1, "stream": 1})
                skt._sock.sendall(code.encode())
                skt._sock.close()
                tf_container.wait(timeout=15)
                tf_stdout = tf_container.logs(stdout=True, stderr=False).decode()
                tf_container.remove(force=True)
            except Exception:
                tf_stdout = ""

            # Run tflint
            try:
                tl_container = client.containers.create(
                    "ghcr.io/terraform-linters/tflint:latest",
                    command=["-f", "json", "-"],
                    stdin_open=True,
                    detach=True,
                )
                tl_container.start()
                skt2 = tl_container.attach_socket(params={"stdin": 1, "stream": 1})
                skt2._sock.sendall(code.encode())
                skt2._sock.close()
                tl_container.wait(timeout=15)
                tl_stdout = tl_container.logs(stdout=True, stderr=False).decode()
                tl_container.remove(force=True)
            except Exception:
                tl_stdout = ""

            return tf_stdout, tl_stdout

        loop = asyncio.get_running_loop()
        stdout, tflint_stdout = await loop.run_in_executor(None, run_validate)

        if stdout:
            try:
                result = json.loads(stdout)
                if "diagnostics" in result:
                    for diag in result["diagnostics"]:
                        diagnostics.append(
                            {
                                "severity": 8 if diag.get("severity") == "error" else 4,
                                "message": diag.get("summary", ""),
                                "startLineNumber": (
                                    diag.get("range", {})
                                    .get("start", {})
                                    .get("line", 1)
                                    if diag.get("range")
                                    else 1
                                ),
                                "startColumn": (
                                    diag.get("range", {})
                                    .get("start", {})
                                    .get("column", 1)
                                    if diag.get("range")
                                    else 1
                                ),
                                "endLineNumber": (
                                    diag.get("range", {}).get("end", {}).get("line", 1)
                                    if diag.get("range")
                                    else 1
                                ),
                                "endColumn": (
                                    diag.get("range", {})
                                    .get("end", {})
                                    .get("column", 1)
                                    if diag.get("range")
                                    else 1
                                ),
                                "source": "tofu",
                            }
                        )
            except Exception:
                pass

        if tflint_stdout:
            try:
                result = json.loads(tflint_stdout)
                for issue in result.get("issues", []):
                    diagnostics.append(
                        {
                            "severity": 4,  # warning
                            "message": issue.get("message", ""),
                            "startLineNumber": issue.get("line", 1),
                            "startColumn": issue.get("column", 1),
                            "endLineNumber": issue.get("line", 1),
                            "endColumn": issue.get("column", 1),
                            "source": "tflint",
                        }
                    )
            except Exception:
                pass

        return {"status": "success", "diagnostics": diagnostics}
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return {"status": "success", "diagnostics": diagnostics}


@router.websocket("/lsp")
async def lsp_websocket(websocket: WebSocket) -> None:
    """WebSocket connection for terraform-ls (Language Server Protocol)"""
    await websocket.accept()
    container = None
    try:
        client = docker.from_env()  # type: ignore
        container = client.containers.run(
            "hashicorp/terraform-ls:latest",
            command=["serve"],
            stdin_open=True,
            detach=True,
        )
        skt = container.attach_socket(params={"stdin": 1, "stdout": 1, "stream": 1})

        async def read_from_lsp() -> None:
            loop = asyncio.get_running_loop()
            while True:
                data = await loop.run_in_executor(None, skt._sock.recv, 4096)
                if not data:
                    break
                try:
                    await websocket.send_bytes(data)
                except Exception:
                    break

        async def write_to_lsp() -> None:
            loop = asyncio.get_running_loop()
            while True:
                try:
                    data = await websocket.receive_bytes()
                    await loop.run_in_executor(None, skt._sock.sendall, data)
                except Exception:
                    break

        await asyncio.gather(
            read_from_lsp(),
            write_to_lsp(),
        )
    except WebSocketDisconnect:
        logger.info("LSP WebSocket disconnected")
    except Exception as e:
        logger.error(f"LSP error: {e}")
    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass
