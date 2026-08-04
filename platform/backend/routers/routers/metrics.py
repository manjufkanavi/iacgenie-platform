import logging
from typing import Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, Integer

from middleware.auth_middleware import verify_access_token
from models.domain.generation_metrics import GenerationMetrics
from db.adapters.postgres_adapter import postgres_adapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("", include_in_schema=False)
async def get_prometheus_metrics():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/{project_id}")
async def get_project_metrics(
    project_id: str,
    range: str = "last-30-days",
    user: Any = Depends(verify_access_token),
) -> Any:
    """Get dynamic cost analytics and generation metrics for a project."""
    try:
        uid = user.get("uid")
        if not uid:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Invalid user token"},
            )

        if not postgres_adapter._is_initialized:
            # Fallback or error if DB isn't initialized
            return JSONResponse(
                status_code=503,
                content={"success": False, "message": "Database not initialized"},
            )

        # Calculate time range
        now = datetime.utcnow()
        if range == "last-7-days":
            start_date = now - timedelta(days=7)
        elif range == "this-month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            # default last 30 days
            start_date = now - timedelta(days=30)

        async with postgres_adapter.async_session_factory() as session:  # type: ignore[misc]
            # 1. Total Generations & Success Rate
            # We treat failover as a "success" functionally but can track it separately.
            # Assuming every record in GenerationMetrics is a generation attempt.
            stmt_totals = select(
                func.count().label("total_gens"),  # type: ignore[misc]
                func.sum(GenerationMetrics.total_cost).label("total_cost"),
                func.sum(func.cast(GenerationMetrics.failover_occurred, Integer)).label(
                    "failovers"
                ),
            ).where(
                GenerationMetrics.project_id == project_id,
                GenerationMetrics.created_at >= start_date,
            )

            result = await session.execute(stmt_totals)
            totals_row = result.fetchone()

            total_gens = totals_row.total_gens if totals_row else 0
            current_cost = (
                totals_row.total_cost if totals_row and totals_row.total_cost else 0.0
            )
            _ = totals_row.failovers if totals_row and totals_row.failovers else 0

            # Simple success rate metric (just illustrative if we don't have hard failure states in this table)
            success_rate = 100.0

            # 2. Daily Generations (Generations Over Time)
            stmt_daily = (
                select(
                    func.date_trunc("day", GenerationMetrics.created_at).label("day"),
                    func.count().label("count"),  # type: ignore[misc]
                )
                .where(
                    GenerationMetrics.project_id == project_id,
                    GenerationMetrics.created_at >= start_date,
                )
                .group_by("day")
                .order_by("day")
            )

            result_daily = await session.execute(stmt_daily)
            generations_over_time = [
                {"date": row.day.strftime("%Y-%m-%d"), "count": row.count}
                for row in result_daily.fetchall()
            ]

            # 3. Model Performance
            stmt_model = (
                select(
                    GenerationMetrics.requested_model,
                    GenerationMetrics.provider,
                    func.count().label("usage_count"),  # type: ignore[misc]
                )
                .where(
                    GenerationMetrics.project_id == project_id,
                    GenerationMetrics.created_at >= start_date,
                )
                .group_by(GenerationMetrics.requested_model, GenerationMetrics.provider)
            )

            result_model = await session.execute(stmt_model)
            model_performance = [
                {
                    "modelName": row.requested_model,
                    "provider": row.provider,
                    "successRate": 100.0,  # Placeholder
                    "usageCount": row.usage_count,
                }
                for row in result_model.fetchall()
            ]

        # Simple projections
        days_in_range = (now - start_date).days or 1
        daily_burn_rate = current_cost / days_in_range
        projected_cost = (
            current_cost + (daily_burn_rate * (30 - days_in_range))
            if days_in_range < 30
            else current_cost
        )

        payload = {
            "metrics": {
                "totalGenerations": total_gens,
                "totalDeployments": 0,  # Deployments would be fetched from deployment_table
                "successRate": success_rate,
            },
            "cost": {
                "currentMonthCost": round(current_cost, 2),
                "projectedEndOfMonthCost": round(projected_cost, 2),
                "savingsVsLastMonth": 0,  # Would require previous month query
            },
            "generationsOverTime": generations_over_time,
            "deploymentsOverTime": [],
            "modelPerformance": model_performance,
            "cloudProviderDistribution": [],  # Usually fetched from deployments
        }

        return JSONResponse(
            status_code=200, content={"success": True, "result": payload}
        )

    except Exception as e:
        logger.error(f"Failed to aggregate metrics: {str(e)}")
        return JSONResponse(
            status_code=500, content={"success": False, "message": str(e)}
        )
