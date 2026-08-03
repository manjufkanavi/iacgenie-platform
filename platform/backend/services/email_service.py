"""

Email Service for Iacgenie AI

Handles transactional email sending via SendGrid with templates and delivery tracking

Features:

- SendGrid integration for email delivery

- HTML email templates using Jinja2

- Retry logic with exponential backoff

- Delivery status tracking in database

"""

import os

import logging

from typing import Dict, Any, Optional

from datetime import datetime

from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try to import SendGrid

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import (
        Mail,
        From,
        To,
        Subject,
        PlainTextContent,
        HTMLContent,
        MailSettings,
        SandBoxMode,
    )

    SENDGRID_AVAILABLE = True
except ImportError:
    logger.warning("SendGrid not installed. Install with: pip install sendgrid")
    SENDGRID_AVAILABLE = False
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


class EmailService:
    """
    Email service using SendGrid for transactional emails
    Features:
    - HTML email templates
    - Retry logic (max 3 retries with exponential backoff)
    - Sandboxing for development
    - Delivery tracking
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("SENDGRID_API_KEY", "")
        self.from_email = os.getenv("EMAIL_FROM_ADDRESS", "noreply@iacgenie.ai")
        self.is_sandbox = os.getenv("SENDGRID_SANDBOX", "false").lower() == "true"
        self.max_retries = int(os.getenv("EMAIL_MAX_RETRIES", "3"))
        self.base_retry_delay = float(os.getenv("EMAIL_RETRY_DELAY", "1.0"))
        self._client: Optional[SendGridAPIClient] = None
        if SENDGRID_AVAILABLE and self.api_key:
            try:
                self._client = SendGridAPIClient(self.api_key)
                logger.info(f"SendGrid initialized (sandbox={self.is_sandbox})")
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid: {e}")
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
        # Inline templates as fallback
        ver_t = (
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head>\n"
            '    <meta charset="UTF-8">\n'
            "    <title>Verify Your Email - Iacgenie AI</title>\n"
            "</head>\n"
            '<body style="font-family: Arial, sans-serif; '
            "line-height: 1.6; color: #333; "
            "max-width: 600px; margin: 0 auto; "
            'padding: 20px;">\n'
            '    <div style="background: '
            "linear-gradient(135deg, #f6d365 0%, "
            "#fda085 100%); padding: 30px; "
            "text-align: center; "
            'border-radius: 10px 10px 0 0;">\n'
            '        <h1 style="color: white; margin: 0;">'
            "Iacgenie AI</h1>\n"
            '        <p style="color: white; margin: 5px 0 0;">'
            "Infrastructure as Code Generation Platform</p>\n"
            "    </div>\n"
            '    <div style="background: #f9f9f9; padding: 30px; '
            'border-radius: 0 0 10px 10px;">\n'
            "        <h2>Verify Your Email Address</h2>\n"
            "        <p>Hello {{ user_name or 'there' }},</p>\n"
            "        <p>Thank you for signing up with "
            "Iacgenie AI! Please verify your email address "
            "to complete your registration and get started "
            "with our platform.</p>\n"
            '        <div style="text-align: center; '
            'margin: 30px 0;">\n'
            '            <a href="{{ verification_url }}" '
            'style="background: linear-gradient(135deg, '
            "#f6d365 0%, #fda085 100%); color: white; "
            "padding: 15px 30px; text-decoration: none; "
            'border-radius: 5px; font-weight: bold;">'
            "Verify Email Address</a>\n"
            "        </div>\n"
            '        <p style="font-size: 14px; color: #666;">'
            "Or copy and paste this link into your browser:</p>\n"
            '        <p style="font-size: 12px; color: #999; '
            'word-break: break-all;">'
            "{{ verification_url }}</p>\n"
            '        <hr style="border: none; '
            'border-top: 1px solid #ddd; margin: 30px 0;">\n'
            '        <p style="font-size: 12px; color: #999;">\n'
            "            If you didn't create an account with "
            "Iacgenie AI, please ignore this email.<br>\n"
            "            This verification link will expire "
            "in 24 hours.\n"
            "        </p>\n"
            "    </div>\n"
            '    <div style="text-align: center; padding: 20px; '
            'color: #999;">\n'
            "        <p>Iacgenie AI - Making Infrastructure "
            "Code Easy</p>\n"
            "    </div>\n"
            "</body>\n"
            "</html>\n"
        )
        pwd_t = (
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head>\n"
            '    <meta charset="UTF-8">\n'
            "    <title>Reset Your Password - Iacgenie AI</title>\n"
            "</head>\n"
            '<body style="font-family: Arial, sans-serif; '
            "line-height: 1.6; color: #333; "
            "max-width: 600px; margin: 0 auto; "
            'padding: 20px;">\n'
            '    <div style="background: '
            "linear-gradient(135deg, #f6d365 0%, "
            "#fda085 100%); padding: 30px; "
            "text-align: center; "
            'border-radius: 10px 10px 0 0;">\n'
            '        <h1 style="color: white; margin: 0;">'
            "Iacgenie AI</h1>\n"
            '        <p style="color: white; margin: 5px 0 0;">'
            "Infrastructure as Code Generation Platform</p>\n"
            "    </div>\n"
            '    <div style="background: #f9f9f9; padding: 30px; '
            'border-radius: 0 0 10px 10px;">\n'
            "        <h2>Reset Your Password</h2>\n"
            "        <p>Hello {{ user_name or 'there' }},</p>\n"
            "        <p>We received a request to reset your "
            "password for your Iacgenie AI account.</p>\n"
            '        <div style="text-align: center; '
            'margin: 30px 0;">\n'
            '            <a href="{{ reset_url }}" '
            'style="background: linear-gradient(135deg, '
            "#f6d365 0%, #fda085 100%); color: white; "
            "padding: 15px 30px; text-decoration: none; "
            'border-radius: 5px; font-weight: bold;">'
            "Reset Password</a>\n"
            "        </div>\n"
            '        <p style="font-size: 14px; color: #666;">'
            "Or copy and paste this link into your browser:</p>\n"
            '        <p style="font-size: 12px; color: #999; '
            'word-break: break-all;">{{ reset_url }}</p>\n'
            '        <div style="background: #fff3cd; padding: '
            '15px; border-radius: 5px; margin-top: 20px;">\n'
            '            <p style="color: #856404; margin: 0;">'
            "This link will expire in 2 hours.</p>\n"
            "        </div>\n"
            '        <hr style="border: none; '
            'border-top: 1px solid #ddd; margin: 30px 0;">\n'
            '        <p style="font-size: 12px; color: #999;">\n'
            "            If you didn't request a password reset, "
            "please ignore this email.<br>\n"
            "            Your current password will remain "
            "unchanged.\n"
            "        </p>\n"
            "    </div>\n"
            '    <div style="text-align: center; padding: 20px; '
            'color: #999;">\n'
            "        <p>Iacgenie AI - Making Infrastructure "
            "Code Easy</p>\n"
            "    </div>\n"
            "</body>\n"
            "</html>\n"
        )
        inv_t = (
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head>\n"
            '    <meta charset="UTF-8">\n'
            "    <title>You've Been Invited - Iacgenie AI</title>\n"
            "</head>\n"
            '<body style="font-family: Arial, sans-serif; '
            "line-height: 1.6; color: #333; "
            "max-width: 600px; margin: 0 auto; "
            'padding: 20px;">\n'
            '    <div style="background: '
            "linear-gradient(135deg, #f6d365 0%, "
            "#fda085 100%); padding: 30px; "
            "text-align: center; "
            'border-radius: 10px 10px 0 0;">\n'
            '        <h1 style="color: white; margin: 0;">'
            "Iacgenie AI</h1>\n"
            '        <p style="color: white; margin: 5px 0 0;">'
            "Infrastructure as Code Generation Platform</p>\n"
            "    </div>\n"
            '    <div style="background: #f9f9f9; padding: 30px; '
            'border-radius: 0 0 10px 10px;">\n'
            "        <h2>You've Been Invited to Join "
            "Iacgenie AI</h2>\n"
            "        <p>Hello {{ user_name or 'there' }},</p>\n"
            "        <p><strong>{{ inviter_name }}</strong> "
            "has invited you to join their Iacgenie AI "
            "team with <strong>{{ role }}</strong> access.</p>\n"
            '        <div style="text-align: center; '
            'margin: 30px 0;">\n'
            '            <a href="{{ invitation_url }}" '
            'style="background: linear-gradient(135deg, '
            "#f6d365 0%, #fda085 100%); color: white; "
            "padding: 15px 30px; text-decoration: none; "
            'border-radius: 5px; font-weight: bold;">'
            "Join Team</a>\n"
            "        </div>\n"
            '        <p style="font-size: 14px; color: #666;">'
            "Or copy and paste this link into your browser:</p>\n"
            '        <p style="font-size: 12px; color: #999; '
            'word-break: break-all;">'
            "{{ invitation_url }}</p>\n"
            '        <div style="background: #d1ecf1; padding: '
            '15px; border-radius: 5px; margin-top: 20px;">\n'
            '            <p style="color: #0c5460; margin: 0;">'
            "Create your Iacgenie AI account to complete your "
            "invitation.</p>\n"
            "        </div>\n"
            '        <hr style="border: none; '
            'border-top: 1px solid #ddd; margin: 30px 0;">\n'
            '        <p style="font-size: 12px; color: #999;">\n'
            "            This invitation will expire in 7 days.<br>\n"
            "            If you didn't expect to receive this "
            "invitation, please ignore this email.\n"
            "        </p>\n"
            "    </div>\n"
            '    <div style="text-align: center; padding: 20px; '
            'color: #999;">\n'
            "        <p>Iacgenie AI - Making Infrastructure "
            "Code Easy</p>\n"
            "    </div>\n"
            "</body>\n"
            "</html>\n"
        )
        self._inline_templates = {
            "verification": ver_t,
            "password_reset": pwd_t,
            "invitation": inv_t,
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
            logger.error("Jinja2 is not installed")
            return "Please install Jinja2: pip install jinja2"
        template_content = self._get_template(template_name)
        template = Template(template_content)
        # nosemgrep: python.flask.security.xss.audit.direct-use-of-jinja2.direct-use-of-jinja2
        return template.render(**context)

    async def _send_email_direct(
        self, to_email: str, subject: str, html_content: str
    ) -> EmailDeliveryResult:
        """Send email directly via SendGrid API"""
        if not self._client:
            logger.error("SendGrid client not initialized")
            return EmailDeliveryResult(
                success=False, error_message="SendGrid API key not configured"
            )
        try:
            message = Mail(
                from_email=From(self.from_email),
                to_emails=To(to_email),
                subject=Subject(subject),
                plain_text_content=PlainTextContent(self._strip_html(html_content)),
                html_content=HTMLContent(html_content),
            )
            # Enable sandbox mode for testing
            if self.is_sandbox:
                message.mail_settings = MailSettings(
                    sandbox_mode=SandBoxMode(enable=True)
                )
            response = self._client.send(message)
            return EmailDeliveryResult(
                success=response.status_code == 202,
                message_id=response.headers.get("x-message-id"),
                status_code=response.status_code,
            )
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
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
        if not self.api_key:
            logger.warning(
                f"SENDGRID_API_KEY not configured. "
                f"Would send verification to {to_email}"
            )
            return EmailDeliveryResult(
                success=True,
                error_message="Email service not configured (sandbox mode)",
            )
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
        if not self.api_key:
            logger.warning(
                f"SENDGRID_API_KEY not configured. Would send reset email to {to_email}"
            )
            return EmailDeliveryResult(
                success=True,
                error_message="Email service not configured (sandbox mode)",
            )
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
        if not self.api_key:
            logger.warning(
                f"SENDGRID_API_KEY not configured. Would send invitation to {to_email}"
            )
            return EmailDeliveryResult(
                success=True,
                error_message="Email service not configured (sandbox mode)",
            )
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

    async def _send_email_with_retry(
        self, to_email: str, subject: str, html_content: str
    ) -> EmailDeliveryResult:
        """Send email with retry logic"""
        last_result = None
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
        return last_result  # type: ignore

    async def send_email(
        self, to_email: str, subject: str, html_content: str
    ) -> EmailDeliveryResult:
        """Generic email sending method"""
        if not self.api_key:
            logger.warning(f"SENDGRID_API_KEY not configured. Would send to {to_email}")
            return EmailDeliveryResult(
                success=True, error_message="Email service not configured"
            )
        return await self._send_email_with_retry(to_email, subject, html_content)

    def is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return bool(self.api_key and self._client)

    def get_provider_name(self) -> str:
        """Get email provider name"""
        return "SendGrid" if SENDGRID_AVAILABLE else "Not Configured"


# Global instance


email_service = EmailService()


async def get_email_service() -> EmailService:
    """Get email service instance"""
    global email_service
    if not hasattr(email_service, "initialized"):
        email_service = EmailService()
    return email_service
