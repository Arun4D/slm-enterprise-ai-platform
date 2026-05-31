"""
Monitoring Agent implementation.
"""
import logging
from typing import TYPE_CHECKING

from app.services.plugin_manager import IAgent
from tools import MonitoringScanner

if TYPE_CHECKING:
    from app.core.slm.service import SLMService

logger = logging.getLogger(__name__)

class MonitoringAgent(IAgent):
    """
    Monitoring Agent - Tracks resource utilisation metrics and alerts.
    """

    def __init__(self):
        self.name = "monitoring_agent"
        self.version = "1.0.0"
        self._slm_service: "SLMService | None" = None

    def set_slm_service(self, service: "SLMService") -> None:
        """Receive platform-injected SLM Service."""
        self._slm_service = service

    def can_handle(self, intent: str) -> bool:
        """Check if this agent should handle the intent."""
        if self._slm_service is not None and self._slm_service.available:
            result = self._slm_service.classify_intent_sync(
                intent,
                [
                    ("monitoring_agent", "Monitoring alerts, system resource CPU RAM usage, threshold rules, capacity planning"),
                    ("log_analysis_agent", "System log analysis, server exceptions, raw log formats, pattern detection"),
                ]
            )
            if result == "monitoring_agent":
                return True

        monitor_keywords = ["monitor", "metrics", "cpu percent", "ram utilization", "alerts", "observability", "capacity"]
        normalized = intent.lower()
        return any(kw in normalized for kw in monitor_keywords)

    async def plan(self, intent: str, context: dict) -> dict:
        """Decompose monitoring intent into checks."""
        logger.info(f"Monitoring Agent planning for: '{intent}'")
        
        steps = [
            "Fetch host virtualization performance indicators",
            "Consolidate active service alerts",
            "Calculate capacity bottleneck thresholds"
        ]

        return {
            "status": "success",
            "steps": steps,
            "context": {
                "query": intent
            }
        }

    async def execute(self, plan: dict) -> dict:
        """Execute performance checks."""
        if plan.get("status") != "success":
            return {"status": "failed", "error": "Invalid plan input"}

        metrics = MonitoringScanner.get_resource_metrics()

        return {
            "status": "success",
            "result": {
                "metrics": metrics
            }
        }

    async def summarize(self, result: dict) -> str:
        """Summarize resource logs in beautiful Markdown."""
        if result.get("status") != "success":
            return "Failed to fetch platform metrics."

        data = result.get("result", {})
        metrics = data.get("metrics", {})
        alerts = metrics.get("active_alerts", [])

        alert_rows = []
        for a in alerts:
            lvl_badge = "🚨 CRITICAL" if a["status"] == "CRITICAL" else "⚠️ WARNING"
            alert_rows.append(f"| {a['service']} | {a['metric']} | {lvl_badge} | {a['value']} |")

        summary = (
            f"### 📊 Hypervisor capacity & resource monitor\n\n"
            f"- **Host CPU Utilization**: `{metrics.get('cpu_percent')}%` (Warning status)\n"
            f"- **Host Memory Allocation**: `{metrics.get('memory_percent')}%` (Critical state)\n"
            f"- **Storage Disk Allocation**: `{metrics.get('disk_percent')}%` (Sufficient)\n"
            f"- **Statistical Anomaly Score**: `{metrics.get('anomaly_score')}` (High)\n\n"
            f"#### 🚨 Active Site Reliability Alerts:\n"
            f"| Affected Service | Performance Metric | Severity | Value |\n"
            f"| :--- | :--- | :--- | :--- |\n"
            + "\n".join(alert_rows) + "\n\n"
            f"#### 🔧 Observability Remediation Plan:\n"
            f"> Memory threshold has breached 90%. Schedule immediate microservice replicas recycling or scale vertical host RAM partitions to avoid out-of-memory container crashes."
        )
        return summary
