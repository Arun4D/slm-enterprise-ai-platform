import logging

logger = logging.getLogger(__name__)

MOCK_METRICS = {
    "system_stats": {
        "cpu_percent": 88.5,
        "memory_percent": 91.2,
        "disk_percent": 74.8,
        "active_alerts": [
            {"service": "auth-service", "metric": "HTTP 5xx error rate", "status": "CRITICAL", "value": "8.4%"},
            {"service": "prod-db-01", "metric": "Disk read latency", "status": "WARNING", "value": "45ms"}
        ],
        "anomaly_score": 0.85
    }
}

class MonitoringScanner:
    """Aggregates metrics and checks resource thresholds."""

    @staticmethod
    def get_resource_metrics() -> dict:
        """Fetch current monitoring diagnostics."""
        return MOCK_METRICS["system_stats"]
