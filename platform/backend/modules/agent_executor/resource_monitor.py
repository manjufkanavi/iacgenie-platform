"""Resource monitoring for agent execution."""

import asyncio

from typing import Dict, Any

from .config import config

from .logging import logger


class ResourceMonitor:
    """Monitors resource usage for agent processes."""

    def __init__(self, monitoring_interval: float = 5.0):
        self.monitoring = False
        self._monitoring_interval = monitoring_interval
        self._process_stats: Dict[str, Any] = {}
        self._shutdown_event = asyncio.Event()
        # Use config values with fallback defaults
        self._resource_thresholds = {
            "cpu": getattr(config, "RESOURCE_THRESHOLD_CPU", 80.0),
            "memory": getattr(config, "RESOURCE_THRESHOLD_MEMORY", 1800.0),
        }

    def start_monitoring(self) -> None:
        """Start the monitoring loop."""
        logger.info("Starting resource monitoring")
        self.monitoring = True
        self._shutdown_event.clear()
        self._monitoring_task = asyncio.create_task(self._monitor_loop())

    def stop_monitoring(self) -> None:
        """Stop the monitoring loop."""
        logger.info("Stopping resource monitoring")
        self.monitoring = False
        self._shutdown_event.set()
        if hasattr(self, "_monitoring_task"):
            try:
                self._monitoring_task.cancel()
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while not self._shutdown_event.is_set():
            if not self.monitoring:
                break
            # Monitor each process
            for process_id, process_info in self._process_stats.items():
                try:
                    # Get actual process using psutil
                    import psutil

                    process = psutil.Process(process_info["pid"])
                    # Collect metrics
                    metrics = {
                        "memory_usage_mb": process.memory_info().rss
                        / 1024
                        / 1024,  # Convert to MB
                        "cpu_percent": process.cpu_percent(),
                        "active": process.is_running(),
                        "health_status": "healthy"
                        if process.is_running()
                        else "unhealthy",
                    }
                    # Update metrics
                    self._process_stats[process_id] = metrics
                    # Check resource thresholds
                    if metrics["memory_usage_mb"] > self._resource_thresholds["memory"]:
                        logger.warning(
                            f"Process {process_id} exceeds memory limit",
                            extra={
                                "process_id": process_id,
                                "memory_mb": metrics["memory_usage_mb"],
                                "limit_mb": self._resource_thresholds["memory"],
                            },
                        )
                    if metrics["cpu_percent"] > self._resource_thresholds["cpu"]:
                        logger.warning(
                            f"Process {process_id} exceeds CPU limit",
                            extra={
                                "process_id": process_id,
                                "cpu_percent": metrics["cpu_percent"],
                                "limit_percent": self._resource_thresholds["cpu"],
                            },
                        )
                    # Sleep for monitoring interval
                    await asyncio.sleep(self._monitoring_interval)
                except Exception as e:
                    logger.error(
                        "Monitoring error",
                        extra={"process_id": process_id, "error": str(e)},
                    )

    def get_process_stats(self) -> Dict[str, Any]:
        """Get current process statistics."""
        return self._process_stats

    def add_process(self, process_id: str, pid: int) -> None:
        """Add a process to monitor."""
        self._process_stats[process_id] = {
            "pid": pid,
            "memory_usage_mb": 0,
            "cpu_percent": 0,
            "active": False,
            "health_status": "unknown",
        }

    def remove_process(self, process_id: str) -> None:
        """Remove a process from monitoring."""
        if process_id in self._process_stats:
            del self._process_stats[process_id]
