"""

Notification Service

Provides an abstraction for sending out-of-band notifications such as emails and OTPs.

"""

import logging

from abc import ABC, abstractmethod

from typing import Optional, Any


from services.smtp2go_email_service import get_smtp2go_email_service

logger = logging.getLogger(__name__)


class NotificationManager(ABC):
    """Abstract interface for sending notifications"""

    @abstractmethod
    async def send_otp_email(
        self,
        to_email: str,
        otp: str,
        verify_url: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> Any:
        pass

    @abstractmethod
    async def send_password_reset_email(
        self, to_email: str, reset_url: str, user_name: Optional[str] = None
    ) -> Any:
        pass


class ConsoleNotificationManager(NotificationManager):
    """Notification manager for local development that logs to the console"""

    async def send_otp_email(
        self,
        to_email: str,
        otp: str,
        verify_url: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> Any:
        logger.info("=== CONSOLE NOTIFICATION ===")
        logger.info(f"To: {to_email}")
        logger.info(f"OTP: {otp}")
        if verify_url:
            logger.info(f"Verify URL: {verify_url}")
        logger.info("============================")
        # Simulate SMTP2GO EmailDeliveryResult

        class MockResult:
            success = True
            error_message = None

        return MockResult()

    async def send_password_reset_email(
        self, to_email: str, reset_url: str, user_name: Optional[str] = None
    ) -> Any:
        logger.info("=== CONSOLE NOTIFICATION ===")
        logger.info(f"To: {to_email}")
        logger.info(f"Password Reset URL: {reset_url}")
        logger.info("============================")

        class MockResult:
            success = True
            error_message = None

        return MockResult()


class SMTPNotificationManager(NotificationManager):
    """Notification manager for production that uses SMTP2GO"""

    async def send_otp_email(
        self,
        to_email: str,
        otp: str,
        verify_url: Optional[str] = None,
        user_name: Optional[str] = None,
    ) -> Any:
        smtp_service = await get_smtp2go_email_service()
        return await smtp_service.send_otp_email(
            to_email=to_email, otp=otp, verify_url=verify_url, user_name=user_name
        )

    async def send_password_reset_email(
        self, to_email: str, reset_url: str, user_name: Optional[str] = None
    ) -> Any:
        smtp_service = await get_smtp2go_email_service()
        return await smtp_service.send_password_reset_email(
            to_email=to_email, reset_url=reset_url, user_name=user_name
        )


# Global instances


console_notification_manager = ConsoleNotificationManager()

smtp_notification_manager = SMTPNotificationManager()


def get_notification_manager(env: str = "prod") -> NotificationManager:
    """Factory to get the appropriate notification manager based on environment"""
    if env == "dev" or env == "test":
        return console_notification_manager
    return smtp_notification_manager
