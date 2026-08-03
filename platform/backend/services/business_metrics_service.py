"""

Business Metrics Service

Provides custom business metrics and KPIs for Iacgenie AI

"""

from datetime import datetime

from typing import Dict, Any, Optional

from prometheus_client import Counter, Histogram, Gauge, Summary

from config.logging import get_logger

logger = get_logger("business_metrics")


class BusinessMetricsService:
    """Business metrics collection service"""

    def __init__(self) -> None:
        # User metrics
        self.active_users = Gauge(
            "active_users_total",
            "Total number of active users",
            ["user_type", "subscription_tier"],
        )
        self.user_registrations = Counter(
            "user_registrations_total",
            "Total user registrations",
            ["source", "user_type"],
        )
        self.user_logins = Counter(
            "user_logins_total", "Total user logins", ["method", "success"]
        )
        # Project metrics
        self.active_projects = Gauge(
            "active_projects_total",
            "Total number of active projects",
            ["project_type", "status"],
        )
        self.project_creations = Counter(
            "project_creations_total",
            "Total project creations",
            ["project_type", "user_type"],
        )
        # AI Generation metrics
        self.ai_generations = Counter(
            "ai_generations_total",
            "Total AI generations",
            ["model", "status", "user_type"],
        )
        self.ai_generation_duration = Histogram(
            "ai_generation_duration_seconds",
            "AI generation duration in seconds",
            ["model", "generation_type"],
        )
        self.ai_generation_tokens = Summary(
            "ai_generation_tokens_total",
            "Total tokens used in AI generations",
            ["model", "generation_type"],
        )
        # Deployment metrics
        self.deployments = Counter(
            "deployments_total",
            "Total deployments",
            ["platform", "status", "user_type"],
        )
        self.deployment_duration = Histogram(
            "deployment_duration_seconds",
            "Deployment duration in seconds",
            ["platform", "deployment_type"],
        )
        # Revenue metrics
        self.revenue = Counter(
            "revenue_total",
            "Total revenue in USD",
            ["subscription_tier", "payment_method"],
        )
        self.subscriptions = Counter(
            "subscriptions_total", "Total subscriptions", ["tier", "status", "source"]
        )
        # API usage metrics
        self.api_requests = Counter(
            "api_requests_total",
            "Total API requests",
            ["endpoint", "method", "user_type"],
        )
        self.api_rate_limits = Counter(
            "api_rate_limits_total",
            "Total API rate limit hits",
            ["endpoint", "user_type"],
        )
        # Error metrics
        self.business_errors = Counter(
            "business_errors_total",
            "Total business logic errors",
            ["error_type", "severity", "user_type"],
        )
        # Feature usage metrics
        self.feature_usage = Counter(
            "feature_usage_total",
            "Total feature usage",
            ["feature", "user_type", "subscription_tier"],
        )
        # Integration metrics
        self.integrations = Counter(
            "integrations_total",
            "Total integrations",
            ["platform", "status", "user_type"],
        )
        # File processing metrics
        self.file_uploads = Counter(
            "file_uploads_total",
            "Total file uploads",
            ["file_type", "size_category", "user_type"],
        )
        self.file_processing_duration = Histogram(
            "file_processing_duration_seconds",
            "File processing duration in seconds",
            ["file_type", "processing_type"],
        )

    def record_user_registration(self, source: str, user_type: str) -> None:
        """Record a user registration"""
        self.user_registrations.labels(source=source, user_type=user_type).inc()
        logger.info(f"User registration recorded: {source}, {user_type}")

    def record_user_login(self, method: str, success: bool) -> None:
        """Record a user login attempt"""
        self.user_logins.labels(method=method, success=str(success).lower()).inc()
        logger.info(f"User login recorded: {method}, success={success}")

    def record_project_creation(self, project_type: str, user_type: str) -> None:
        """Record a project creation"""
        self.project_creations.labels(
            project_type=project_type, user_type=user_type
        ).inc()
        logger.info(f"Project creation recorded: {project_type}, {user_type}")

    def record_ai_generation(
        self, model: str, status: str, user_type: str, tokens: Optional[int] = None
    ) -> None:
        """Record an AI generation"""
        self.ai_generations.labels(
            model=model, status=status, user_type=user_type
        ).inc()
        if tokens is not None:
            self.ai_generation_duration.labels(
                model=model, generation_type="standard"
            ).observe(tokens)
        if tokens is not None:
            self.ai_generation_tokens.labels(
                model=model, generation_type="standard"
            ).observe(tokens)
        logger.info(f"AI generation recorded: {model}, {status}, {user_type}")

    def record_deployment(
        self,
        platform: str,
        status: str,
        user_type: str,
        duration: Optional[float] = None,
    ) -> None:
        """Record a deployment"""
        self.deployments.labels(
            platform=platform, status=status, user_type=user_type
        ).inc()
        if duration is not None:
            self.deployment_duration.labels(
                platform=platform, deployment_type="standard"
            ).observe(duration)
        logger.info(f"Deployment recorded: {platform}, {status}, {user_type}")

    def record_revenue(
        self, amount: float, subscription_tier: str, payment_method: str
    ) -> None:
        """Record revenue"""
        self.revenue.labels(
            subscription_tier=subscription_tier, payment_method=payment_method
        ).inc(amount)
        logger.info(
            f"Revenue recorded: ${amount}, {subscription_tier}, {payment_method}"
        )

    def record_subscription(self, tier: str, status: str, source: str) -> None:
        """Record a subscription"""
        self.subscriptions.labels(tier=tier, status=status, source=source).inc()
        logger.info(f"Subscription recorded: {tier}, {status}, {source}")

    def record_api_request(self, endpoint: str, method: str, user_type: str) -> None:
        """Record an API request"""
        self.api_requests.labels(
            endpoint=endpoint, method=method, user_type=user_type
        ).inc()

    def record_api_rate_limit(self, endpoint: str, user_type: str) -> None:
        """Record an API rate limit hit"""
        self.api_rate_limits.labels(endpoint=endpoint, user_type=user_type).inc()
        logger.warning(f"API rate limit hit: {endpoint}, {user_type}")

    def record_business_error(
        self, error_type: str, severity: str, user_type: str
    ) -> None:
        """Record a business logic error"""
        self.business_errors.labels(
            error_type=error_type, severity=severity, user_type=user_type
        ).inc()
        logger.error(f"Business error recorded: {error_type}, {severity}, {user_type}")

    def record_feature_usage(
        self, feature: str, user_type: str, subscription_tier: str
    ) -> None:
        """Record feature usage"""
        self.feature_usage.labels(
            feature=feature, user_type=user_type, subscription_tier=subscription_tier
        ).inc()
        logger.info(
            f"Feature usage recorded: {feature}, {user_type}, {subscription_tier}"
        )

    def record_integration(self, platform: str, status: str, user_type: str) -> None:
        """Record an integration"""
        self.integrations.labels(
            platform=platform, status=status, user_type=user_type
        ).inc()
        logger.info(f"Integration recorded: {platform}, {status}, {user_type}")

    def record_file_upload(
        self,
        file_type: str,
        size_category: str,
        user_type: str,
        duration: Optional[float] = None,
    ) -> None:
        """Record a file upload"""
        self.file_uploads.labels(
            file_type=file_type, size_category=size_category, user_type=user_type
        ).inc()
        if duration is not None:
            self.file_processing_duration.labels(
                file_type=file_type, processing_type="upload"
            ).observe(duration)
        logger.info(f"File upload recorded: {file_type}, {size_category}, {user_type}")

    def update_active_users(
        self, count: int, user_type: str, subscription_tier: str
    ) -> None:
        """Update active users count"""
        self.active_users.labels(
            user_type=user_type, subscription_tier=subscription_tier
        ).set(count)

    def update_active_projects(
        self, count: int, project_type: str, status: str
    ) -> None:
        """Update active projects count"""
        self.active_projects.labels(project_type=project_type, status=status).set(count)

    def get_business_summary(self) -> Dict[str, Any]:
        """Get business metrics summary"""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "user_registrations": "Tracked via Prometheus",
                "ai_generations": "Tracked via Prometheus",
                "deployments": "Tracked via Prometheus",
                "revenue": "Tracked via Prometheus",
                "api_requests": "Tracked via Prometheus",
            },
            "note": "All metrics are exposed via /api/metrics endpoint",
        }


# Global instance


business_metrics = BusinessMetricsService()
