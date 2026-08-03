"""

SMTP2GO Email Service for Iacgenie AI

Handles transactional email sending via SMTP2GO API with templates and delivery tracking

Features:

- SMTP2GO API integration for email delivery

- HTML email templates using Jinja2

- Retry logic with exponential backoff

- Support for multiple SMTP ports (2525, 8025, 587, 80, 25)

- Delivery status tracking

Based on SMTP Server Details:

- Server: mail.smtp2go.com

- Port: 2525 (alternative: 8025, 587, 80, 25)

- Username: admin@zencloudsec.com

"""

import os

import logging

from typing import Dict, Any, Optional, List

from datetime import datetime

from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    logger.warning("httpx not installed. Install with: pip install httpx")
    HTTPX_AVAILABLE = False
try:
    from jinja2 import Template
except ImportError:
    logger.warning("Jinja2 not installed. Install with: pip install jinja2")
    _Template: Any = None  # type: ignore[misc,assignment,no-redef]
    Template: Any = None  # type: ignore[misc,assignment,no-redef]


@dataclass
class EmailDeliveryResult:
    """Result of email delivery attempt"""

    success: bool
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    status_code: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0


class SMTP2GOEmailService:
    """
    Email service using SMTP2GO API for transactional emails
    Features:
    - HTML email templates
    - Retry logic (max 3 retries with exponential backoff)
    - Support for multiple ports
    - Delivery tracking
    """

    def __init__(self) -> None:
        # SMTP2GO Configuration from environment or default values
        self.api_key = os.getenv(
            "SMTP2GO_API_KEY", "api-D6548F2A67D64E928B26C119A011C60C"
        )
        self.from_email = os.getenv("EMAIL_FROM_ADDRESS", "admin@zencloudsec.com")
        self.smtp_server = os.getenv("SMTP_SERVER", "mail.smtp2go.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "2525"))
        self.max_retries = int(os.getenv("EMAIL_MAX_RETRIES", "3"))
        self.base_retry_delay = float(os.getenv("EMAIL_RETRY_DELAY", "1.0"))
        self.is_sandbox = os.getenv("SMTP2GO_SANDBOX", "false").lower() == "true"
        # API endpoint
        self.api_base_url = os.getenv(
            "SMTP2GO_API_BASE_URL", "https://api.smtp2go.com/v3/"
        )
        self.api_endpoint = f"{self.api_base_url}email/send"
        # SMTP2GO API authentication headers
        self._headers = {
            "Content-Type": "application/json",
            "X-Smtp2go-Api-Key": self.api_key,
        }
        logger.info(f"SMTP2GO Email Service initialized (sandbox={self.is_sandbox})")
        # Email templates (will be loaded from files or fallback to inline)
        self._templates: Dict[str, str] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load email templates from environment or use inline defaults"""
        # Check for template file paths
        self.verification_template_path = os.getenv(
            "EMAIL_VERIFICATION_TEMPLATE_PATH",
            "backend/templates/verification_email.html",
        )
        self.password_reset_template_path = os.getenv(
            "EMAIL_PASSWORD_RESET_TEMPLATE_PATH",
            "backend/templates/password_reset_email.html",
        )
        self.invitation_template_path = os.getenv(
            "EMAIL_INVITATION_TEMPLATE_PATH", "backend/templates/invitation_email.html"
        )
        # New template paths
        self.welcome_template_path = os.getenv(
            "EMAIL_WELCOME_TEMPLATE_PATH", "backend/templates/welcome_email.html"
        )
        self.deployment_success_template_path = os.getenv(
            "EMAIL_DEPLOYMENT_SUCCESS_TEMPLATE_PATH",
            "backend/templates/deployment_success.html",
        )
        self.generation_complete_template_path = os.getenv(
            "EMAIL_GENERATION_COMPLETE_TEMPLATE_PATH",
            "backend/templates/generation_complete.html",
        )
        self.security_alert_template_path = os.getenv(
            "EMAIL_SECURITY_ALERT_TEMPLATE_PATH",
            "backend/templates/security_alert.html",
        )
        self.login_success_template_path = os.getenv(
            "EMAIL_LOGIN_SUCCESS_TEMPLATE_PATH", "backend/templates/login_success.html"
        )
        # Inline templates as fallback
        self._inline_templates = {
            "verification": """
<!DOCTYPE html>

<html>

<head>
    <meta charset="UTF-8">
    <title>Verify Your Email - Iacgenie AI</title>
</head>

<body
    style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;
    max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
    padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0;">Iacgenie AI</h1>
        <p style="color: white; margin: 5px 0 0;">Infrastructure as Code Generation Platform</p>
    </div>
    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
        <h2>Verify Your Email Address</h2>
        <p>Hello {{ user_name or 'there' }},</p>
        <p>Thank you for signing up with Iacgenie AI!
        Please verify your email address to complete your
        registration and get started with our platform.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ verification_url }}"
            style="background: linear-gradient(135deg, #f6d365 0%,
            #fda085 100%); color: white; padding: 15px 30px;
            text-decoration: none; border-radius: 5px; font-weight: bold;">
            Verify Email Address</a>
        </div>
        <p style="font-size: 14px; color: #666;">Or copy and paste
        this link into your browser:</p>
        <p style="font-size: 12px; color: #999; word-break: break-all;">
        {{ verification_url }}</p>
        <hr style="border: none; border-top: 1px solid #ddd;
        margin: 30px 0;">
        <p style="font-size: 12px; color: #999;">
            If you didn't create an account with Iacgenie AI,
            please ignore this email.<br>
            This verification link will expire in 24 hours.
        </p>
    </div>
    <div style="text-align: center; padding: 20px; color: #999;">
        <p>Iacgenie AI - Making Infrastructure Code Easy</p>
    </div>
</body>

</html>
            """,
            "password_reset": """
<!DOCTYPE html>

<html>

<head>
    <meta charset="UTF-8">
    <title>Reset Your Password - Iacgenie AI</title>
</head>

<body
    style="font-family: Arial, sans-serif; line-height: 1.6;
    color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #f6d365 0%,
    #fda085 100%); padding: 30px; text-align: center;
    border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0;">Iacgenie AI</h1>
        <p style="color: white; margin: 5px 0 0;">Infrastructure
        as Code Generation Platform</p>
    </div>
    <div style="background: #f9f9f9; padding: 30px;
    border-radius: 0 0 10px 10px;">
        <h2>Reset Your Password</h2>
        <p>Hello {{ user_name or 'there' }},</p>
        <p>We received a request to reset your password
        for your Iacgenie AI account.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ reset_url }}"
            style="background: linear-gradient(135deg, #f6d365 0%,
            #fda085 100%); color: white; padding: 15px 30px;
            text-decoration: none; border-radius: 5px; font-weight: bold;">
            Reset Password</a>
        </div>
        <p style="font-size: 14px; color: #666;">Or copy and paste
        this link into your browser:</p>
        <p style="font-size: 12px; color: #999; word-break: break-all;">
        {{ reset_url }}</p>
        <div style="background: #fff3cd; padding: 15px;
        border-radius: 5px; margin-top: 20px;">
            <p style="color: #856404; margin: 0;">This link will
            expire in 2 hours.</p>
        </div>
        <hr style="border: none; border-top: 1px solid #ddd;
        margin: 30px 0;">
        <p style="font-size: 12px; color: #999;">
            If you didn't request a password reset,
            please ignore this email.<br>
            Your current password will remain unchanged.
        </p>
    </div>
    <div style="text-align: center; padding: 20px; color: #999;">
        <p>Iacgenie AI - Making Infrastructure Code Easy</p>
    </div>
</body>

</html>
            """,
            "invitation": """
<!DOCTYPE html>

<html>

<head>
    <meta charset="UTF-8">
    <title>You've Been Invited - Iacgenie AI</title>
</head>

<body
    style="font-family: Arial, sans-serif; line-height: 1.6;
    color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #f6d365 0%,
    #fda085 100%); padding: 30px; text-align: center;
    border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0;">Iacgenie AI</h1>
        <p style="color: white; margin: 5px 0 0;">Infrastructure
        as Code Generation Platform</p>
    </div>
    <div style="background: #f9f9f9; padding: 30px;
    border-radius: 0 0 10px 10px;">
        <h2>You've Been Invited to Join Iacgenie AI</h2>
        <p>Hello {{ user_name or 'there' }},</p>
        <p><strong>{{ inviter_name }}</strong> has invited you
        to join their Iacgenie AI team with
        <strong>{{ role }}</strong> access.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ invitation_url }}"
            style="background: linear-gradient(135deg, #f6d365 0%,
            #fda085 100%); color: white; padding: 15px 30px;
            text-decoration: none; border-radius: 5px; font-weight: bold;">
            Join Team</a>
        </div>
        <p style="font-size: 14px; color: #666;">Or copy and paste
        this link into your browser:</p>
        <p style="font-size: 12px; color: #999; word-break: break-all;">
        {{ invitation_url }}</p>
        <div style="background: #d1ecf1; padding: 15px;
        border-radius: 5px; margin-top: 20px;">
            <p style="color: #0c5460; margin: 0;">Create your
            Iacgenie AI account to complete your invitation.</p>
        </div>
        <hr style="border: none; border-top: 1px solid #ddd;
        margin: 30px 0;">
        <p style="font-size: 12px; color: #999;">
            This invitation will expire in 7 days.<br>
            If you didn't expect to receive this invitation,
            please ignore this email.
        </p>
    </div>
    <div style="text-align: center; padding: 20px; color: #999;">
        <p>Iacgenie AI - Making Infrastructure Code Easy</p>
    </div>
</body>

</html>
            """,
            "otp_verification": """
<!DOCTYPE html>

<html>

<head>
    <meta charset="UTF-8">
    <title>Verify Your Email - Iacgenie AI</title>
</head>

<body
    style="font-family: Arial, sans-serif; line-height: 1.6;
    color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #f6d365 0%,
    #fda085 100%); padding: 30px; text-align: center;
    border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0;">Iacgenie AI</h1>
        <p style="color: white; margin: 5px 0 0;">Infrastructure
        as Code Generation Platform</p>
    </div>
    <div style="background: #f9f9f9; padding: 30px;
    border-radius: 0 0 10px 10px;">
        <h2>Your Verification Code</h2>
        <p>Hello {{ user_name or 'there' }},</p>
        <p>Thank you for signing up with Iacgenie AI!
        Please use the verification code below to complete
        your registration:</p>
        <div style="text-align: center; margin: 30px 0;">
            <div style="background: white; border: 2px dashed #f6d365;
            padding: 20px; border-radius: 10px;
            display: inline-block;">
                <span style="font-size: 32px; font-weight: bold;
                color: #f6d365; letter-spacing: 10px;">{{ otp }}</span>
            </div>
        </div>
        <p style="font-size: 14px; color: #666;">This code will
        expire in 10 minutes.</p>
        <div style="background: #fff3cd; padding: 15px;
        border-radius: 5px; margin-top: 20px;">
            <p style="color: #856404; margin: 0;">
            <strong>Don't share this code with anyone!</strong></p>
        </div>
        <hr style="border: none; border-top: 1px solid #ddd;
        margin: 30px 0;">
        <p style="font-size: 12px; color: #999;">
            If you didn't create an account with Iacgenie AI,
            please ignore this email.<br>
            This verification code will expire in 10 minutes.
        </p>
    </div>
    <div style="text-align: center; padding: 20px; color: #999;">
        <p>Iacgenie AI - Making Infrastructure Code Easy</p>
    </div>
</body>

</html>
            """,
        }

    def _get_template(self, template_name: str) -> str:
        """Get email template content"""
        if template_name in self._templates:
            return self._templates[template_name]
        # Try to load from file first
        template_path = None
        if template_name == "verification":
            template_path = self.verification_template_path
        elif template_name == "password_reset":
            template_path = self.password_reset_template_path
        elif template_name == "invitation":
            template_path = self.invitation_template_path
        elif template_name == "welcome":
            template_path = self.welcome_template_path
        elif template_name == "deployment_success":
            template_path = self.deployment_success_template_path
        elif template_name == "generation_complete":
            template_path = self.generation_complete_template_path
        elif template_name == "security_alert":
            template_path = self.security_alert_template_path
        elif template_name == "login_success":
            template_path = self.login_success_template_path
        if template_path:
            try:
                with open(template_path, "r") as f:
                    content = f.read()
                    self._templates[template_name] = content
                    return content
            except FileNotFoundError:
                logger.warning(
                    f"Template file not found: {template_path}. Using inline template."
                )
            except Exception as e:
                logger.error(f"Failed to load template {template_path}: {e}")
        # Return inline template
        return self._inline_templates.get(template_name, "")

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context"""
        if Template is None:
            logger.warning("Jinja2 not installed, using inline template")
            return self._inline_templates.get(template_name, "")
        template_content = self._get_template(template_name)
        template = Template(template_content)
        # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
        return template.render(**context)

    def _validate_email(self, email: str) -> tuple[bool, Optional[str]]:
        """
        Validate email format and check for common issues
        Returns (is_valid, error_message)
        """
        if not email or not isinstance(email, str):
            return False, "Email is required"
        email = email.strip()
        if not email:
            return False, "Email cannot be empty"
        # Basic email format validation
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            return False, f"Invalid email format: {email}"
        # Check for common disposable/domains that might cause hard bounces
        disposable_domains = [
            "tempmail.com",
            "10minutemail.com",
            "guerrillamail.com",
            "mailinator.com",
            "yopmail.com",
        ]
        domain = email.split("@")[-1].lower()
        if domain in disposable_domains:
            return False, f"Disposable email domain not allowed: {domain}"
        # Check for invalid domain patterns
        if "." not in email.split("@")[-1]:
            return False, f"Invalid domain: {email}"
        # Check email length
        if len(email) > 254:
            return False, "Email address too long"
        if len(email) < 3:
            return False, "Email address too short"
        # Check for whitespace
        if " " in email:
            return False, "Email cannot contain spaces"
        return True, None

    async def _send_email_direct(
        self, to_email: str, subject: str, html_content: str
    ) -> EmailDeliveryResult:
        """Send email directly via SMTP2GO API"""
        if not HTTPX_AVAILABLE:
            logger.error("httpx is not installed. Install with: pip install httpx")
            return EmailDeliveryResult(
                success=False, error_message="httpx library not available"
            )
        # Validate email before attempting to send
        is_valid, error_msg = self._validate_email(to_email)
        if not is_valid:
            logger.warning(f"[SMTP2GO VALIDATION] Rejected email: {error_msg}")
            return EmailDeliveryResult(
                success=False,
                error_message=f"Email validation failed: {error_msg}",
                status_code=400,
            )
        # Validate sender email (SMTP2GO requires verified sender)
        if not self.from_email or "@" not in self.from_email:
            logger.error(
                f"[SMTP2GO VALIDATION] Invalid sender email: {self.from_email}"
            )
            return EmailDeliveryResult(
                success=False,
                error_message=f"Invalid sender email: {self.from_email}",
                status_code=400,
            )
        # Build email payload for SMTP2GO API
        # Reference: https://smtp2go.com/documentation/api/v3/
        # SMTP2GO uses 'sender' field (not 'from') with RFC-5322 format
        payload = {
            "to": [to_email],
            "sender": self.from_email,
            "subject": subject,
            "html_body": html_content,
        }
        if self.is_sandbox:
            payload["sandbox"] = True  # type: ignore[assignment]
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.api_endpoint, json=payload, headers=self._headers
                )
                logger.info(f"[SMTP2GO API] Status Code: {response.status_code}")
                try:
                    result_data = response.json()
                    # Log full response for debugging
                    logger.debug(f"[SMTP2GO API] Full Response: {result_data}")
                    # SMTP2GO returns success with status 200 and data.succeeded > 0 in response body
                    if response.status_code == 200:
                        succeeded = result_data.get("data", {}).get("succeeded", 0)
                        if succeeded > 0 or result_data.get("success", False):
                            message_id = result_data.get("data", {}).get(
                                "email_id"
                            ) or result_data.get("data", {}).get("id")
                            logger.info(
                                f"[SMTP2GO API] SUCCESS: Email sent (ID: {message_id})"
                            )
                            return EmailDeliveryResult(
                                success=True,
                                message_id=message_id,
                                status_code=response.status_code,
                            )
                        else:
                            error_msg = (
                                result_data.get("error") or "Unknown SMTP2GO error"
                            )
                            logger.error(
                                f"[SMTP2GO API] FAILED: {error_msg}. Full response: {result_data}"
                            )
                            # Check for specific error types
                            if "sender" in error_msg.lower():
                                logger.error(
                                    "[SMTP2GO ERROR] Sender email not verified!"
                                )
                            elif "recipient" in error_msg.lower():
                                logger.error("[SMTP2GO ERROR] Recipient email issue")
                            elif "rate" in error_msg.lower():
                                logger.error("[SMTP2GO ERROR] Rate limit exceeded")
                            return EmailDeliveryResult(
                                success=False,
                                error_message=error_msg,
                                status_code=response.status_code,
                            )
                    else:
                        error_msg = f"HTTP {response.status_code}: {result_data}"
                        logger.error(f"[SMTP2GO API] HTTP Error: {error_msg}")
                        # Add more context based on status code
                        if response.status_code == 401:
                            logger.error(
                                "[SMTP2GO ERROR] Invalid API key or unauthorized"
                            )
                        elif response.status_code == 403:
                            logger.error(
                                "[SMTP2GO ERROR] Forbidden - check your plan limits"
                            )
                        elif response.status_code == 404:
                            logger.error("[SMTP2GO ERROR] Endpoint not found")
                        elif response.status_code == 429:
                            logger.error("[SMTP2GO ERROR] Rate limit exceeded")
                        return EmailDeliveryResult(
                            success=False,
                            error_message=error_msg,
                            status_code=response.status_code,
                        )
                except Exception as json_error:
                    # Log raw response for debugging
                    logger.error(f"[SMTP2GO API] JSON parse error: {json_error}")
                    logger.error(
                        f"[SMTP2GO API] Raw response text: {response.text[:500]}"
                    )
                    return EmailDeliveryResult(
                        success=False,
                        error_message=f"JSON parse error: {json_error}",
                        status_code=response.status_code,
                    )
        except httpx.TimeoutException:
            error_msg = "Request timed out after 30 seconds"
            logger.error(f"SMTP2GO API request timeout: {error_msg}")
            return EmailDeliveryResult(success=False, error_message=error_msg)
        except Exception as e:
            logger.error(f"Failed to send email via SMTP2GO: {e}")
            return EmailDeliveryResult(success=False, error_message=str(e))

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from content for plain text version"""
        import re

        clean = re.compile("<.*?>")
        return re.sub(clean, "", html)

    async def send_verification_email(
        self, to_email: str, verification_url: str, user_name: Optional[str] = None
    ) -> EmailDeliveryResult:
        """Send email verification link"""
        subject = "Verify Your Email - Iacgenie AI"
        html_content = self._render_template(
            "verification",
            {"user_name": user_name, "verification_url": verification_url},
        )
        return await self._send_email_with_retry(to_email, subject, html_content)

    async def send_password_reset_email(
        self, to_email: str, reset_url: str, user_name: Optional[str] = None
    ) -> EmailDeliveryResult:
        """Send password reset link"""
        subject = "Reset Your Password - Iacgenie AI"
        html_content = self._render_template(
            "password_reset", {"user_name": user_name, "reset_url": reset_url}
        )
        return await self._send_email_with_retry(to_email, subject, html_content)

    async def send_invitation_email(
        self,
        to_email: str,
        invitation_url: str,
        user_name: Optional[str] = None,
        inviter_name: Optional[str] = None,
        role: str = "user",
    ) -> EmailDeliveryResult:
        """Send team invitation email"""
        subject = "You've Been Invited to Iacgenie AI"
        html_content = self._render_template(
            "invitation",
            {
                "user_name": user_name,
                "inviter_name": inviter_name or "A team member",
                "invitation_url": invitation_url,
                "role": role,
            },
        )
        return await self._send_email_with_retry(to_email, subject, html_content)

    async def send_otp_email(
        self,
        to_email: str,
        otp: str,
        verify_url: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> EmailDeliveryResult:
        """Send OTP verification email
        Args:
            to_email: Recipient email address
            otp: The 6-digit OTP code to send
            verify_url: Optional URL for verification (if user clicks link)
            user_name: Optional display name
        Returns:
            EmailDeliveryResult with success status
        """
        subject = "Your Verification Code - Iacgenie AI"
        html_content = self._render_template(
            "otp_verification",
            {"user_name": user_name, "otp": otp, "verify_url": verify_url},
        )
        return await self._send_email_with_retry(to_email, subject, html_content)

    async def send_welcome_email(
        self,
        to_email: str,
        start_url: str,
        dashboard_url: str,
        docs_url: str,
        user_name: Optional[str] = None,
    ) -> EmailDeliveryResult:
        """Send welcome email after registration
        Args:
            to_email: Recipient email address
            start_url: URL to start building infrastructure
            dashboard_url: URL to dashboard
            docs_url: URL to documentation
            user_name: Optional display name
        Returns:
            EmailDeliveryResult with success status
        """
        subject = "Welcome to Iacgenie AI!"
        html_content = self._render_template(
            "welcome",
            {
                "user_name": user_name,
                "start_url": start_url,
                "dashboard_url": dashboard_url,
                "docs_url": docs_url,
            },
        )
        return await self._send_email_with_retry(to_email, subject, html_content)

    async def send_deployment_success_email(
        self,
        to_email: str,
        deployment_id: str,
        cloud_provider: str,
        region: str,
        generation_id: str,
        elapsed_time: str,
        resources: List[Dict[str, Any]],
        deployments_url: str,
        user_name: Optional[str] = None,
    ) -> EmailDeliveryResult:
        """Send deployment success notification
        Args:
            to_email: Recipient email address
            deployment_id: Deployment identifier
            cloud_provider: Cloud provider name (AWS, GCP, Azure)
            region: Deployment region
            generation_id: Associated generation ID
            elapsed_time: Deployment duration
            resources: List of deployed resources
            deployments_url: URL to view all deployments
            user_name: Optional display name
        Returns:
            EmailDeliveryResult with success status
        """
        subject = "Deployment Successful!"
        html_content = self._render_template(
            "deployment_success",
            {
                "user_name": user_name,
                "deployment_id": deployment_id,
                "cloud_provider": cloud_provider,
                "region": region,
                "generation_id": generation_id,
                "elapsed_time": elapsed_time,
                "resources": resources,
                "deployments_url": deployments_url,
            },
        )
        return await self._send_email_with_retry(to_email, subject, html_content)

    async def send_generation_complete_email(
        self,
        to_email: str,
        generation_id: str,
        ai_model: str,
        cloud_provider: str,
        file_count: int,
        total_lines: int,
        files: List[Dict[str, Any]],
        quality_score: int,
        security_score: int,
        efficiency_score: int,
        dashboard_url: str,
        user_name: Optional[str] = None,
    ) -> EmailDeliveryResult:
        """Send generation completion notification
        Args:
            to_email: Recipient email address
            generation_id: Generation identifier
            ai_model: AI model used for generation
            cloud_provider: Target cloud provider
            file_count: Number of generated files
            total_lines: Total lines of code
            files: List of generated file details
            quality_score: Code quality score (0-100)
            security_score: Security score (0-100)
            efficiency_score: Efficiency score (0-100)
            dashboard_url: URL to view generation details
            user_name: Optional display name
        Returns:
            EmailDeliveryResult with success status
        """
        subject = "Your Infrastructure Code is Ready!"
        html_content = self._render_template(
            "generation_complete",
            {
                "user_name": user_name,
                "generation_id": generation_id,
                "ai_model": ai_model,
                "cloud_provider": cloud_provider,
                "file_count": file_count,
                "total_lines": total_lines,
                "files": files,
                "quality_score": quality_score,
                "security_score": security_score,
                "efficiency_score": efficiency_score,
                "dashboard_url": dashboard_url,
            },
        )
        return await self._send_email_with_retry(to_email, subject, html_content)

    async def send_security_alert_email(
        self,
        to_email: str,
        alert_id: str,
        change_timestamp: str,
        ip_address: str,
        device_info: str,
        location: str,
        security_center_url: str,
        user_name: Optional[str] = None,
    ) -> EmailDeliveryResult:
        """Send security alert for password changes
        Args:
            to_email: Recipient email address
            alert_id: Security alert identifier
            change_timestamp: When password was changed
            ip_address: IP address where change occurred
            device_info: Device information
            location: Location of the change
            security_center_url: URL to secure account
            user_name: Optional display name
        Returns:
            EmailDeliveryResult with success status
        """
        subject = "Security Alert - Password Changed"
        html_content = self._render_template(
            "security_alert",
            {
                "user_name": user_name,
                "alert_id": alert_id,
                "change_timestamp": change_timestamp,
                "ip_address": ip_address,
                "device_info": device_info,
                "location": location,
                "security_center_url": security_center_url,
            },
        )
        return await self._send_email_with_retry(to_email, subject, html_content)

    async def send_login_success_email(
        self,
        to_email: str,
        session_id: str,
        login_timestamp: str,
        ip_address: str,
        device_info: str,
        browser: str,
        location: str,
        security_center_url: str,
        user_name: Optional[str] = None,
    ) -> EmailDeliveryResult:
        """Send login success notification
        Args:
            to_email: Recipient email address
            session_id: Session identifier
            login_timestamp: When login occurred (ISO format)
            ip_address: IP address where login occurred
            device_info: Device information
            browser: Browser name and version
            location: Location of the login
            security_center_url: URL to security settings
            user_name: Optional display name
        Returns:
            EmailDeliveryResult with success status
        """
        subject = "Login Alert - Iacgenie AI"
        html_content = self._render_template(
            "login_success",
            {
                "user_name": user_name,
                "session_id": session_id,
                "login_timestamp": login_timestamp,
                "ip_address": ip_address,
                "device_info": device_info,
                "browser": browser,
                "location": location,
                "security_center_url": security_center_url,
            },
        )
        return await self._send_email_with_retry(to_email, subject, html_content)

    async def _send_email_with_retry(
        self, to_email: str, subject: str, html_content: str
    ) -> EmailDeliveryResult:
        """Send email with retry logic"""
        last_result: Optional[EmailDeliveryResult] = None
        for attempt in range(self.max_retries + 1):
            result = await self._send_email_direct(to_email, subject, html_content)
            if result.success:
                logger.info(f"Email sent successfully to {to_email}")
                return result
            last_result = result
            logger.warning(
                f"Email attempt {attempt + 1} failed: {result.error_message}"
            )
            if attempt < self.max_retries:
                delay = self.base_retry_delay * (2**attempt)
                import asyncio

                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
        logger.error(f"All email delivery attempts failed for {to_email}")
        if last_result:
            return last_result
        return EmailDeliveryResult(
            success=False, error_message="All retry attempts exhausted"
        )

    async def send_email(
        self, to_email: str, subject: str, html_content: str
    ) -> EmailDeliveryResult:
        """Generic email sending method"""
        return await self._send_email_with_retry(to_email, subject, html_content)

    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(self.api_key)

    def get_provider_name(self) -> str:
        """Get email provider name"""
        return "SMTP2GO"

    def get_verification_link(self, user_id: str, token: str) -> str:
        """Generate verification link for email verification"""
        frontend_url = os.getenv("VITE_API_BASE_URL", "http://localhost:5173")
        return f"{frontend_url}/verify-email?token={token}&user_id={user_id}"

    def get_reset_link(self, user_id: str, token: str) -> str:
        """Generate password reset link"""
        frontend_url = os.getenv("VITE_API_BASE_URL", "http://localhost:5173")
        return f"{frontend_url}/reset-password?token={token}&user_id={user_id}"


# Global instance


smtp2go_email_service = SMTP2GOEmailService()


async def get_smtp2go_email_service() -> SMTP2GOEmailService:
    """Get email service instance"""
    global smtp2go_email_service
    if not hasattr(smtp2go_email_service, "initialized"):
        smtp2go_email_service = SMTP2GOEmailService()
    return smtp2go_email_service
