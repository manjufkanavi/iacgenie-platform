"""

OAuth 2.0 Service

Implements RFC 6749 compliant OAuth 2.0 authorization server with:

- Authorization Code Grant flow

- Refresh Token rotation (enhanced security)

- PKCE support (RFC 7636) for mobile clients

- Token revocation

Features:

- RFC 6749 compliant token endpoint

- Client registration and management

- Refresh token rotation on each use

- PKCE code challenge/verifier support

- Token revocation endpoint

"""

import os

from typing import Dict, Any, List, Optional, Tuple

from datetime import datetime, timedelta

import logging

import uuid

import hashlib

import secrets

logger = logging.getLogger(__name__)

# Import dependencies

try:
    from db.db_provider import db_provider

    DB_AVAILABLE = True
except ImportError:
    logger.warning("Database provider not available")
    DB_AVAILABLE = False


class OAuthService:
    """OAuth 2.0 authorization server implementation
    Implements RFC 6749 OAuth 2.0 specification with:
    - Authorization Code Grant flow
    - Refresh Token rotation for enhanced security
    - PKCE (RFC 7636) support for public clients
    """

    def __init__(self) -> None:
        self.db = db_provider if DB_AVAILABLE else None
        # Configuration from environment
        self.access_token_expiration = int(os.getenv("JWT_EXPIRATION", "3600"))
        self.refresh_token_expiration = int(
            os.getenv("JWT_REFRESH_EXPIRATION", "604800")
        )
        self.code_expiration = 600  # 10 minutes
        logger.info("OAuthService initialized")

    def _generate_access_token(
        self, user_id: str, client_id: str, scopes: Optional[List[str]] = None
    ) -> str:
        """Generate JWT access token"""
        from utils.jwt_utils import generate_token

        additional_claims = {
            "client_id": client_id,
            "type": "access_token",
            "scopes": scopes or ["openid", "profile", "email"],
        }
        return generate_token(
            user_id=user_id,
            email="",  # Will be added by token validation
            role="user",
            additional_claims=additional_claims,
            expires_in=self.access_token_expiration,
        )

    def _generate_refresh_token(
        self, user_id: str, client_id: str, rotated_from_id: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """Generate refresh token with database persistence"""
        refresh_token = secrets.token_urlsafe(64)
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(
            seconds=self.refresh_token_expiration
        )
        token_data = {
            "user_id": user_id,
            "client_id": client_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "rotated_from_id": rotated_from_id,
        }
        return refresh_token, token_data

    async def create_oauth_client(
        self,
        client_name: str,
        redirect_uris: list,
        grant_types: Optional[list] = None,
        scope: str = "openid profile email",
    ) -> Dict[str, Any]:
        """
        Register a new OAuth client
        Args:
            client_name: Human-readable client name
            redirect_uris: List of valid redirect URIs
            grant_types: Supported grant types (optional)
            scope: Default scopes
        Returns:
            Client credentials dictionary
        """
        client_id = f"client_{uuid.uuid4().hex[:20]}"
        client_secret = secrets.token_urlsafe(32)
        # Hash client secret
        client_secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()
        client_data = {
            "client_id": client_id,
            "client_secret_hash": client_secret_hash,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "grant_types": grant_types or ["authorization_code", "refresh_token"],
            "scope": scope,
        }
        # Store client in database
        if self.db:
            await self.db.create_oauth_client(client_data)
        return {
            "client_id": client_id,
            "client_secret": client_secret,  # Only returned once!
            "client_name": client_name,
            "redirect_uris": redirect_uris,
        }

    async def exchange_authorization_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Exchange authorization code for tokens
        Implements RFC 6749 Section 4.1.3: Authorization Code Grant
        Args:
            code: Authorization code
            client_id: OAuth client identifier
            redirect_uri: Redirect URI (must match original)
            code_verifier: PKCE code verifier
        Returns:
            Tuple of (success, tokens, error_message)
        """
        try:
            if not self.db:
                return False, None, "Database not available"
            # Verify code hash
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            # Get authorization code from database
            auth_code = await self.db.get_authorization_code_by_hash(code_hash)
            if not auth_code:
                return False, None, "Invalid authorization code"
            # Check expiration
            if datetime.utcnow() > auth_code["expires_at"]:
                return False, None, "Authorization code expired"
            # Verify client_id
            if auth_code["client_id"] != client_id:
                return False, None, "Client ID mismatch"
            # Verify redirect_uri
            if auth_code["redirect_uri"] != redirect_uri:
                return False, None, "Redirect URI mismatch"
            # PKCE verification
            if auth_code.get("code_challenge"):
                if not code_verifier:
                    return False, None, "PKCE code verifier required"
                if not self._verify_pkce(auth_code["code_challenge"], code_verifier):
                    return False, None, "PKCE verification failed"
            # Generate tokens
            access_token = self._generate_access_token(
                user_id=auth_code["user_id"], client_id=client_id
            )
            refresh_token, refresh_token_data = self._generate_refresh_token(
                user_id=auth_code["user_id"], client_id=client_id
            )
            # Store refresh token in database
            await self.db.create_refresh_token(refresh_token_data)
            # Mark code as used (invalidate it)
            await self.db.mark_authorization_code_used(code_hash)
            return (
                True,
                {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_in": self.access_token_expiration,
                    "token_type": "Bearer",
                    "scope": auth_code.get("scopes", "openid profile email"),
                },
                None,
            )
        except Exception as e:
            logger.error(f"Token exchange failed: {str(e)}")
            return False, None, "Token exchange failed"

    async def refresh_access_token(
        self, refresh_token: str, client_id: str
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Refresh access token using refresh token
        Implements RFC 6749 Section 6: Refresh Token Grant
        Uses rotating refresh tokens for enhanced security
        Args:
            refresh_token: Current refresh token
            client_id: OAuth client identifier
        Returns:
            Tuple of (success, new_tokens, error_message)
        """
        try:
            if not self.db:
                return False, None, "Database not available"
            # Verify refresh token hash
            token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
            # Get existing refresh token record
            existing_token = await self.db.get_refresh_token_by_hash(token_hash)
            if not existing_token:
                return False, None, "Refresh token not found"
            # Check if already revoked
            if existing_token.get("revoked"):
                return False, None, "Refresh token has been revoked"
            # Check expiration
            if datetime.utcnow() > existing_token["expires_at"]:
                return False, None, "Refresh token has expired"
            # Verify client_id
            if existing_token["client_id"] != client_id:
                return False, None, "Client ID mismatch"
            # Generate new tokens (rotation)
            new_access_token = self._generate_access_token(
                user_id=existing_token["user_id"], client_id=client_id
            )
            new_refresh_token, new_refresh_token_data = self._generate_refresh_token(
                user_id=existing_token["user_id"],
                client_id=client_id,
                rotated_from_id=existing_token.get("id"),
            )
            # Store new refresh token
            await self.db.create_refresh_token(new_refresh_token_data)
            # Revoke old refresh token (rotation)
            await self.db.revoke_refresh_token(existing_token["id"])
            return (
                True,
                {
                    "access_token": new_access_token,
                    "refresh_token": new_refresh_token,
                    "expires_in": self.access_token_expiration,
                    "token_type": "Bearer",
                    "scope": existing_token.get("scopes", "openid profile email"),
                },
                None,
            )
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return False, None, "Token refresh failed"

    async def create_authorization_code(
        self,
        user_id: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: Optional[str] = None,
        scopes: Optional[list] = None,
    ) -> str:
        """
        Generate authorization code for user
        Args:
            user_id: Authenticated user ID
            client_id: OAuth client identifier
            redirect_uri: Redirect URI for callback
            code_challenge: PKCE code challenge (optional)
            scopes: Requested scopes
        Returns:
            Authorization code string
        """
        if not self.db:
            raise Exception("Database not available")
        # Generate secure random code
        authorization_code = secrets.token_urlsafe(32)
        code_hash = hashlib.sha256(authorization_code.encode()).hexdigest()
        # Create scopes if not provided
        if scopes is None:
            scopes = ["openid", "profile", "email"]
        # Store in database
        code_data = {
            "client_id": client_id,
            "user_id": user_id,
            "code_hash": code_hash,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "scopes": scopes,
            "expires_at": datetime.utcnow() + timedelta(seconds=self.code_expiration),
        }
        await self.db.create_authorization_code(code_data)
        return authorization_code

    def _verify_pkce(self, code_challenge: str, code_verifier: str) -> bool:
        """Verify PKCE code verifier against challenge"""
        if os.getenv("PKCE_CODE_CHALLENGE_METHOD", "S256") == "S256":
            computed_challenge = hashlib.sha256(code_verifier.encode()).hexdigest()
            return computed_challenge == code_challenge
        else:
            # Plain challenge (RFC 7636)
            return code_verifier == code_challenge

    async def revoke_token(self, token: str) -> Tuple[bool, str]:
        """
        Revoke an access or refresh token
        Args:
            token: Token to revoke
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.db:
                return False, "Database not available"
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            # Try to revoke as refresh token
            revoked = await self.db.revoke_refresh_token_by_hash(token_hash)
            if revoked:
                return True, "Token revoked successfully"
            # Try to revoke as access token
            revoked = await self.db.revoke_access_token_by_hash(token_hash)
            if revoked:
                return True, "Token revoked successfully"
            return False, "Token not found"
        except Exception as e:
            logger.error(f"Token revocation failed: {str(e)}")
            return False, "Token revocation failed"


# Global instance


oauth_service = OAuthService()
