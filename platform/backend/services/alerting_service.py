"""

Alerting Service

Provides monitoring alerts and notifications for system issues

"""

import httpx

from typing import Dict, Any, List

from datetime import datetime, timedelta

from config.logging import get_logger

import os

logger = get_logger("alerting")


class AlertLevel:
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertingService:
    """Alerting and notification service"""

    def __init__(self) -> None:
        self.webhook_url = os.getenv("ALERT_WEBHOOK_URL")
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.email_recipients = os.getenv("ALERT_EMAIL_RECIPIENTS", "").split(",")
        self.alert_history: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            "error_rate": 0.05,  # 5% error rate
            "response_time": 2000,  # 2 seconds
            "cpu_usage": 80,  # 80% CPU
            "memory_usage": 85,  # 85% memory
            "disk_usage": 90,  # 90% disk
        }

    async def check_health_alerts(
        self, health_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check health data for alert conditions"""
        alerts = []
        # Check overall health
        if health_data.get("status") != "healthy":
            alerts.append(
                {
                    "level": AlertLevel.CRITICAL,
                    "title": "System Health Degraded",
                    "message": f"System health check failed: {health_data.get('status')}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": health_data,
                }
            )
        # Check individual components
        checks = health_data.get("checks", {})
        # Database health
        db_health = checks.get("database", {})
        if db_health.get("status") != "healthy":
            alerts.append(
                {
                    "level": AlertLevel.CRITICAL,
                    "title": "Database Health Issue",
                    "message": f"Database health check failed: {db_health.get('error', 'Unknown error')}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": db_health,
                }
            )
        # Redis health
        redis_health = checks.get("redis", {})
        if redis_health.get("status") != "healthy":
            alerts.append(
                {
                    "level": AlertLevel.WARNING,
                    "title": "Redis Health Issue",
                    "message": f"Redis health check failed: {redis_health.get('error', 'Unknown error')}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": redis_health,
                }
            )
        # AI services health
        ai_health = checks.get("ai_services", {})
        if ai_health.get("status") != "healthy":
            alerts.append(
                {
                    "level": AlertLevel.WARNING,
                    "title": "AI Services Health Issue",
                    "message": f"AI services health check failed: {ai_health.get('error', 'Unknown error')}",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": ai_health,
                }
            )
        # System resources
        system_health = checks.get("system_resources", {})
        if system_health.get("status") == "healthy":
            # Check CPU usage
            cpu_percent = system_health.get("cpu_percent", 0)
            if cpu_percent > self.alert_thresholds["cpu_usage"]:
                alerts.append(
                    {
                        "level": AlertLevel.WARNING,
                        "title": "High CPU Usage",
                        "message": f"CPU usage is {cpu_percent}% (threshold: {self.alert_thresholds['cpu_usage']}%)",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {"cpu_percent": cpu_percent},
                    }
                )
            # Check memory usage
            memory = system_health.get("memory", {})
            memory_percent = memory.get("percent_used", 0)
            if memory_percent > self.alert_thresholds["memory_usage"]:
                alerts.append(
                    {
                        "level": AlertLevel.WARNING,
                        "title": "High Memory Usage",
                        "message": (
                            f"Memory usage is {memory_percent}% "
                            f"(threshold: {self.alert_thresholds['memory_usage']}%)"
                        ),
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": memory,
                    }
                )
            # Check disk usage
            disk = system_health.get("disk", {})
            disk_percent = disk.get("percent_used", 0)
            if disk_percent > self.alert_thresholds["disk_usage"]:
                alerts.append(
                    {
                        "level": AlertLevel.WARNING,
                        "title": "High Disk Usage",
                        "message": f"Disk usage is {disk_percent}% (threshold: {self.alert_thresholds['disk_usage']}%)",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": disk,
                    }
                )
        return alerts

    async def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send an alert through configured channels"""
        try:
            # Store alert in history
            self.alert_history.append(alert)
            # Keep only last 100 alerts
            if len(self.alert_history) > 100:
                self.alert_history = self.alert_history[-100:]
            # Send to webhook if configured
            if self.webhook_url:
                await self._send_webhook_alert(alert)
            # Send to Slack if configured
            if self.slack_webhook_url:
                await self._send_slack_alert(alert)
            # Send email if configured
            if self.email_recipients and self.email_recipients[0]:
                await self._send_email_alert(alert)
            logger.info(
                "alert_sent: level=%s title=%s timestamp=%s",
                alert["level"],
                alert["title"],
                alert["timestamp"],
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")
            return False

    async def _send_webhook_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert to webhook URL"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "alert": alert,
                    "service": "iacgenie",
                    "environment": os.getenv("ENVIRONMENT", "development"),
                }
                response = await client.post(self.webhook_url or "", json=payload)
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Webhook alert failed: {str(e)}")

    async def _send_slack_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert to Slack"""
        try:
            # Create Slack message
            color = {
                AlertLevel.INFO: "#36a64f",
                AlertLevel.WARNING: "#ff8c00",
                AlertLevel.ERROR: "#ff0000",
                AlertLevel.CRITICAL: "#8b0000",
            }.get(alert["level"], "#808080")
            slack_payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": alert["title"],
                        "text": alert["message"],
                        "fields": [
                            {
                                "title": "Level",
                                "value": alert["level"].upper(),
                                "short": True,
                            },
                            {
                                "title": "Timestamp",
                                "value": alert["timestamp"],
                                "short": True,
                            },
                        ],
                        "footer": "IaC Genie AI Monitoring",
                    }
                ]
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.slack_webhook_url or "", json=slack_payload
                )
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Slack alert failed: {str(e)}")

    async def _send_email_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert via email"""
        try:
            # This is a basic implementation
            # In production, you'd use a proper email service like SendGrid, SES, etc.
            logger.info(
                f"Email alert would be sent to {self.email_recipients}: {alert['title']}"
            )
        except Exception as e:
            logger.error(f"Email alert failed: {str(e)}")

    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alert history for the specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return [
            alert
            for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) > cutoff_time
        ]

    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert summary for the specified time period"""
        recent_alerts = self.get_alert_history(hours)
        alert_counts = {
            AlertLevel.INFO: 0,
            AlertLevel.WARNING: 0,
            AlertLevel.ERROR: 0,
            AlertLevel.CRITICAL: 0,
        }
        for alert in recent_alerts:
            level = alert.get("level", AlertLevel.INFO)
            alert_counts[level] += 1
        return {
            "total_alerts": len(recent_alerts),
            "alert_counts": alert_counts,
            "time_period_hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
        }


# Global alerting service instance


alerting_service = AlertingService()
