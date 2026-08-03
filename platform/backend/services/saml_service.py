"""

SAML Authentication Service for Iacgenie AI

Single Sign-On support via SAML 2.0

Features:

- SAML Service Provider (SP) metadata generation

- SAML authentication request creation

- SAML response validation and parsing

- Hybrid auth (email/password + SSO)

"""

import os

import logging

from typing import Dict, Any, Optional, Tuple

from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import SAML library
import importlib.util

_SAML_AVAILABLE = importlib.util.find_spec("onelogin") is not None
try:
    if _SAML_AVAILABLE:
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        from onelogin.saml2.settings import OneLogin_Saml2_Settings

        SAML_AVAILABLE = True
    else:
        SAML_AVAILABLE = False
except ImportError:
    logger.warning(
        "python-saml not installed. Install with: pip install onelogin-python-saml"
    )
    SAML_AVAILABLE = False
try:
    from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser

    IDP_METADATA_AVAILABLE = True
except ImportError:
    logger.warning("IDP metadata parser not available")
    IDP_METADATA_AVAILABLE = False


class SAMLAuthService:
    """
    SAML Service Provider implementation for Iacgenie AI
    Supports:
    - Google Workspace SSO
    - Azure AD Single Sign-On
    - Okta Single Sign-On
    - Other SAML 2.0 compliant IdPs
    Architecture:
    - Service Provider (SP): Iacgenie AI
    - Identity Provider (IdP): Google/Azure/Okta/etc.
    """

    def __init__(self) -> None:
        self.sp_config: Dict[str, Any] = {}
        self.sp_metadata_path = os.getenv(
            "SAML_SP_METADATA_PATH", "/api/auth/saml/metadata"
        )
        self.sp_acs_url = os.getenv(
            "SAML_SP_ASSERTION_CONSUMER_SERVICE_URL", "/api/auth/saml/callback"
        )
        self.sp_single_logout_url = os.getenv(
            "SAML_SP_SINGLE_LOGOUT_URL", "/api/auth/saml/logout"
        )
        self.idp_metadata_url = os.getenv("SAML_IDP_METADATA_URL", "")
        # SP Configuration
        self.sp_config = {
            "strict": True,
            "debug": os.getenv("SAML_DEBUG", "false").lower() == "true",
            "sp": {
                "entityId": os.getenv("SAML_SP_ENTITY_ID", "urn:iacgenie:saml"),
                "assertionConsumerService": {
                    "url": os.getenv(
                        "SAML_SP_ASSERTION_CONSUMER_SERVICE_URL",
                        "http://localhost:5173/api/auth/saml/callback",
                    ),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": os.getenv(
                        "SAML_SP_SINGLE_LOGOUT_URL",
                        "http://localhost:5173/api/auth/saml/logout",
                    ),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
            },
            "security": {
                "authnRequestsSigned": os.getenv(
                    "SAML_AUTHN_REQUESTS_SIGNED", "false"
                ).lower()
                == "true",
                "logoutRequestSigned": os.getenv(
                    "SAML_LOGOUT_REQUEST_SIGNED", "false"
                ).lower()
                == "true",
                "wantAssertionsEncrypted": os.getenv(
                    "SAML_WANT_ASSERTIONS_ENCRYPTED", "true"
                ).lower()
                == "true",
                "wantNameId": os.getenv("SAML_WANT_NAME_ID", "true").lower() == "true",
                "wantMessagesSigned": os.getenv(
                    "SAML_WANT_MESSAGES_SIGNED", "false"
                ).lower()
                == "true",
                "wantAssertionsSigned": os.getenv(
                    "SAML_WANT_ASSERTIONS_SIGNED", "true"
                ).lower()
                == "true",
                "wantNameIdEncrypted": os.getenv(
                    "SAML_WANT_NAME_ID_ENCRYPTED", "false"
                ).lower()
                == "true",
                "requestedAuthnContext": os.getenv(
                    "SAML_REQUESTED_AUTHN_CONTEXT",
                    "urn:oasis:names:tc:SAML:2.0:ac:classes:Password",
                ).lower()
                == "true",
                "signatureAlgorithm": os.getenv(
                    "SAML_SIGNATURE_ALGORITHM",
                    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                ),
                "digestAlgorithm": os.getenv(
                    "SAML_DIGEST_ALGORITHM", "http://www.w3.org/2001/04/xmlenc#sha256"
                ),
                "removeDatanullbytes": True,
            },
        }
        # IdP Configuration (can be loaded from metadata URL or direct config)
        self.idp_config = self._load_idp_config()
        # Role mapping from IdP attributes to Iacgenie roles
        self.role_mapping = {
            "admin": "owner",
            "superadmin": "owner",
            "developer": "user",
            "viewer": "viewer",
            "member": "user",
        }
        logger.info(f"SAML Service initialized (available={SAML_AVAILABLE})")

    def _load_idp_config(self) -> Dict[str, Any]:
        """Load IdP configuration from environment variables or metadata URL"""
        if self.idp_metadata_url:
            try:
                # Parse metadata from URL
                return self._parse_idp_metadata(self.idp_metadata_url)
            except Exception as e:
                logger.warning(f"Failed to load IdP metadata from URL: {e}")
        # Fallback to direct configuration
        return {
            "entityId": os.getenv("SAML_IDP_ENTITY_ID", ""),
            "singleSignOnService": {
                "url": os.getenv("SAML_IDP_SSO_URL", ""),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "singleLogoutService": {
                "url": os.getenv("SAML_IDP_SLO_URL", ""),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": os.getenv("SAML_IDP_X509_CERT", ""),
            "certFingerprint": os.getenv("SAML_IDP_CERT_FINGERPRINT", ""),
            "certFingerprintAlgorithm": os.getenv("SAML_IDP_CERT_ALGORITHM", "sha256"),
        }

    def _parse_idp_metadata(self, metadata_url: str) -> Dict[str, Any]:
        """Parse IdP metadata from URL"""
        if not IDP_METADATA_AVAILABLE:
            raise ImportError("IdPMetadataParser is not available")
        # Parse metadata and get settings
        settings = OneLogin_Saml2_IdPMetadataParser.parse_remote(metadata_url)
        if not settings:
            raise ValueError("Failed to parse IdP metadata")
        # Extract IDP configuration
        idp_config = settings.get_idp_data()
        logger.info(f"Loaded IdP configuration from {metadata_url}")
        return idp_config

    def _get_saml_auth(self, request_data: Dict[str, Any]) -> Optional[Any]:
        """Create and return SAML authentication object"""
        if not SAML_AVAILABLE:
            logger.error("SAML library not available")
            return None
        try:
            # Build request data for python-saml
            {
                "https": "on"
                if os.getenv("SAML_HTTPS", "false").lower() == "true"
                else "off",
                "http_host": request_data.get("http_host", ""),
                "server_port": request_data.get("server_port", ""),
                "script_name": request_data.get("script_name", ""),
                "query_string": request_data.get("query_string", ""),
                "relative_uri": request_data.get("relative_uri", ""),
            }
            # Create SAML authentication object
            auth = OneLogin_Saml2_Auth(
                request_data,
                self.sp_config,
                custom_base_path=os.getenv("SAML_CUSTOM_BASE_PATH", ""),
            )
            # Set IdP configuration
            auth.setup_sp(self.idp_config)
            return auth
        except Exception as e:
            logger.error(f"Failed to create SAML auth object: {e}")
            return None

    def get_sp_metadata(self) -> Dict[str, Any]:
        """Get Service Provider metadata as XML"""
        if not SAML_AVAILABLE:
            return {"error": "SAML library not available"}
        try:
            # Create SP settings
            settings = OneLogin_Saml2_Settings(
                self.sp_config, custom_base_path=os.getenv("SAML_CUSTOM_BASE_PATH", "")
            )
            # Get metadata XML
            metadata = settings.get_sp_metadata()
            # Parse and extract key information
            metadata_dict = {
                "entity_id": self.sp_config["sp"]["entityId"],
                "acs_url": self.sp_config["sp"]["assertionConsumerService"]["url"],
                "slo_url": self.sp_config["sp"]["singleLogoutService"]["url"],
                "metadata_xml": metadata,
                "certificate": self.sp_config.get("security", {}).get("x509cert", ""),
            }
            return metadata_dict
        except Exception as e:
            logger.error(f"Failed to generate SP metadata: {e}")
            return {"error": str(e)}

    async def initiate_sso(self, redirect_url: Optional[str] = None) -> Dict[str, str]:
        """Initiate SAML Single Sign-On flow"""
        if not SAML_AVAILABLE:
            return {"error": "SAML library not available", "redirect_url": ""}
        try:
            # Build request data
            request_data = {
                "https": "on"
                if os.getenv("SAML_HTTPS", "false").lower() == "true"
                else "off",
                "http_host": os.getenv("HOST", "localhost"),
                "server_port": os.getenv("PORT", "8000"),
                "script_name": "/api/auth/saml/acs",
                "query_string": "",
                "relative_uri": "/api/auth/saml/acs",
            }
            # Create SAML auth object
            auth = self._get_saml_auth(request_data)
            if not auth:
                return {
                    "error": "Failed to create SAML auth object",
                    "redirect_url": "",
                }
            # Get login URL
            login_url = auth.login(return_to=redirect_url)
            return {"redirect_url": login_url}
        except Exception as e:
            logger.error(f"SSO initiation failed: {e}")
            return {"error": str(e), "redirect_url": ""}

    async def process_saml_response(
        self, request_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Process SAML response from IdP
        Returns:
            Tuple of (success, user_data, error_message)
        """
        if not SAML_AVAILABLE:
            return False, None, "SAML library not available"
        try:
            # Create SAML auth object
            auth = self._get_saml_auth(request_data)
            if not auth:
                return False, None, "Failed to create SAML auth object"
            # Process response
            auth.process_response()
            # Check for errors
            if auth.get_errors():
                logger.error(f"SAML response errors: {auth.get_errors()}")
                return False, None, f"SAML errors: {', '.join(auth.get_errors())}"
            # Check if user is authenticated
            if not auth.is_authenticated():
                return False, None, "User not authenticated via SAML"
            # Extract user attributes
            user_data = self._extract_user_attributes(auth)
            logger.info(f"SAML authentication successful for {user_data.get('email')}")
            return True, user_data, None
        except Exception as e:
            logger.error(f"SAML response processing failed: {e}")
            return False, None, str(e)

    def _extract_user_attributes(self, auth: Any) -> Dict[str, Any]:
        """Extract user attributes from SAML response"""
        attributes = auth.get_attributes()
        # Map common SAML attributes to user data
        user_data: Dict[str, Any] = {
            "uid": None,
            "email": None,
            "name": None,
            "first_name": None,
            "last_name": None,
            "role": "user",
            "attributes": {},
        }
        # Extract email (common attribute names)
        email_attrs = [
            "email",
            "mail",
            "Email",
            "EMAIL",
            "user.email",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        ]
        for attr in email_attrs:
            if attr in attributes and attributes[attr]:
                user_data["email"] = attributes[attr][0]
                break
        # Extract name
        name_attrs = [
            "name",
            "displayName",
            "DisplayName",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        ]
        for attr in name_attrs:
            if attr in attributes and attributes[attr]:
                user_data["name"] = attributes[attr][0]
                break
        # Extract first name
        first_name_attrs = [
            "firstName",
            "givenName",
            "GivenName",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        ]
        for attr in first_name_attrs:
            if attr in attributes and attributes[attr]:
                user_data["first_name"] = attributes[attr][0]
                break
        # Extract last name
        last_name_attrs = [
            "lastName",
            "surname",
            "Surname",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        ]
        for attr in last_name_attrs:
            if attr in attributes and attributes[attr]:
                user_data["last_name"] = attributes[attr][0]
                break
        # Extract role from SAML attributes
        role_attrs = [
            "role",
            "Role",
            "roles",
            "Roles",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/role",
        ]
        for attr in role_attrs:
            if attr in attributes and attributes[attr]:
                raw_role = attributes[attr][0]
                # Map to Iacgenie role
                user_data["role"] = self.role_mapping.get(raw_role.lower(), "user")
                break
        # Extract user ID (NameID or attribute)
        name_id = auth.get_nameid()
        if name_id:
            user_data["uid"] = name_id
        # Store all attributes
        user_data["attributes"] = dict(attributes)
        return user_data

    async def create_saml_user(
        self, user_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Create or update user based on SAML attributes
        Args:
            user_data: User data extracted from SAML response
        Returns:
            Tuple of (success, user_record, error_message)
        """
        try:
            from db.db_provider import db_provider

            if not user_data.get("email"):
                return False, None, "Email is required for SAML user"
            # Check if user exists
            existing_user = await db_provider.get_user_by_email(user_data["email"])
            if existing_user:
                # Update existing user with SAML attributes
                update_data = {
                    "metadata": {
                        **existing_user.get("metadata", {}),
                        "saml_uid": user_data.get("uid"),
                        "saml_attributes": user_data.get("attributes", {}),
                        "last_saml_login": datetime.utcnow().isoformat(),
                    }
                }
                success = await db_provider.update_user(
                    existing_user["id"], update_data
                )
                if not success:
                    return False, None, "Failed to update user with SAML attributes"
                logger.info(
                    f"Updated existing user {existing_user['id']} with SAML data"
                )
                # Return updated user record
                updated_user = await db_provider.get_user(existing_user["id"])
                if updated_user is None:
                    return False, None, "Failed to fetch updated user"
                return True, self._format_user_record(updated_user), None
            else:
                # Create new user
                import uuid
                from utils.password_utils import hash_password

                user_id = str(uuid.uuid4())
                # Generate random password
                import secrets

                temp_password = secrets.token_urlsafe(32)
                password_hash = hash_password(temp_password)
                user_data_create = {
                    "id": user_id,
                    "email": user_data["email"],
                    "name": user_data.get("name", user_data["email"]),
                    "role": user_data.get("role", "user"),
                    "is_active": True,
                    "password_hash": password_hash,
                    "metadata": {
                        "provider": "saml",
                        "saml_uid": user_data.get("uid"),
                        "saml_attributes": user_data.get("attributes", {}),
                        "first_saml_login": datetime.utcnow().isoformat(),
                    },
                }
                created_user_id = await db_provider.create_user(user_data_create)
                if not created_user_id:
                    return False, None, "Failed to create SAML user"
                logger.info(f"Created new user {created_user_id} from SAML")
                # Fetch and return created user
                created_user = await db_provider.get_user(created_user_id)
                if created_user is None:
                    return False, None, "Failed to fetch created user"
                return True, self._format_user_record(created_user), None
        except Exception as e:
            logger.error(f"Failed to create/update SAML user: {e}")
            return False, None, str(e)

    def _format_user_record(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Format database user record for response"""
        return {
            "uid": user.get("id"),
            "email": user.get("email"),
            "displayName": user.get("name", ""),
            "role": user.get("role", "user"),
            "emailVerified": True,  # SAML users are considered verified
            "saml_linked": True,
        }

    def logout(self, auth: Any) -> str:
        """Initiate SAML logout"""
        if not SAML_AVAILABLE:
            return "/logout"
        try:
            return auth.logout()
        except Exception as e:
            logger.error(f"SAML logout failed: {e}")
            return "/logout"

    def is_configured(self) -> bool:
        """Check if SAML is properly configured"""
        if not SAML_AVAILABLE:
            return False
        idp_config = self.idp_config
        sso_url = idp_config.get("singleSignOnService", {}).get("url")
        cert = idp_config.get("x509cert") or idp_config.get("certFingerprint")
        return bool(sso_url and cert)

    def get_idp_entity_id(self) -> Optional[str]:
        """Get IdP entity ID"""
        return self.idp_config.get("entityId")

    def get_idp_sso_url(self) -> Optional[str]:
        """Get IdP SSO URL"""
        return self.idp_config.get("singleSignOnService", {}).get("url")


# Global instance


saml_auth_service = None


async def get_saml_auth_service() -> Optional[SAMLAuthService]:
    """Get SAML auth service instance"""
    global saml_auth_service
    if saml_auth_service is None:
        saml_auth_service = SAMLAuthService()
    return saml_auth_service if saml_auth_service.is_configured() else None
