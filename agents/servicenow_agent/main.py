"""
ServiceNow Agent - Main implementation.
Handles incident search, ticket details, RCA extraction, and resolution trends.
"""

import asyncio
import logging
import re
from typing import Any, TYPE_CHECKING

from app.services.plugin_manager import IAgent
from tools.snow_client import ServiceNowClient
from prompts import SERVICENOW_SUMMARY_PROMPT

if TYPE_CHECKING:
    from app.core.slm.service import SLMService

logger = logging.getLogger(__name__)


class ServiceNowAgent(IAgent):
    """
    ServiceNow Agent - Integrates with ServiceNow REST APIs.
    """

    def __init__(self):
        """Initialize the agent."""
        self.name = "servicenow_agent"
        self.version = "1.0.0"
        self._slm_service: "SLMService | None" = None
        
        # Load configurations
        import yaml
        from pathlib import Path
        config_path = Path(__file__).parent / "config.yaml"
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
        except Exception:
            config = {}
            
        api_config = config.get("api", {})
        auth_type = api_config.get("auth_type", "basic")
        username = api_config.get("username", "admin_ops_ai")
        password = api_config.get("password", "secure_password")
        domain = api_config.get("domain", "CORP")
        ntlm_token = api_config.get("ntlm_token", "NTLMSSP...")
        
        self._client = ServiceNowClient(
            offline=api_config.get("offline_mode", True),
            auth_type=auth_type,
            username=username,
            password=password,
            domain=domain,
            ntlm_token=ntlm_token
        )

    def set_slm_service(self, service: "SLMService") -> None:
        """Receive the platform-injected SLM Service."""
        self._slm_service = service

    def can_handle(self, intent: str) -> bool:
        """
        Evaluate if this agent should handle the prompt.
        """
        # --- Fast path: SLM intent classification ---
        if self._slm_service is not None and self._slm_service.available:
            result = self._slm_service.classify_intent_sync(
                intent,
                [
                    ("log_analysis_agent", "Log analysis, error detection, troubleshooting"),
                    ("servicenow_agent", "ServiceNow incident search, ticket lookup, close notes, and incident trends"),
                ],
            )
            if result == "servicenow_agent":
                return True

        # --- Fallback: keyword matching ---
        snow_keywords = [
            "servicenow", "snow", "incident", "incidents", "ticket", "tickets",
            "inc0", "inc1", "inc2", "inc3", "inc4", "inc5", "inc6", "inc7", "inc8", "inc9",
            "rca", "root cause", "close notes", "resolution", "assignee",
            "dba team", "devops team", "db exhaust"
        ]
        normalized_intent = re.sub(r"\s+", " ", intent.lower()).strip()
        return any(kw in normalized_intent for kw in snow_keywords)

    async def plan(self, intent: str, context: dict) -> dict:
        """
        Decompose the user's intent into executable ServiceNow tasks.
        """
        logger.info(f"ServiceNow Agent planning intent: '{intent}'")
        normalized = intent.upper()
        
        # Check for incident ID pattern (e.g. INC00102)
        inc_match = re.search(r"INC\d{3,}", normalized)
        
        action = "search"
        ticket_number = None
        keywords = intent
        
        if inc_match:
            action = "lookup"
            ticket_number = inc_match.group(0)
            steps = [
                f"Verify incident pattern match for {ticket_number}",
                f"Query ServiceNow SysIncident records for {ticket_number}",
                "Extract assignee, state, and SLA status",
                "Extract and parse root cause summary from close notes"
            ]
        elif "TREND" in normalized or "STAT" in normalized or "CHART" in normalized or "SUMMARY" in normalized:
            action = "trends"
            steps = [
                "Scan offline ServiceNow database partitions",
                "Aggregate incidents by assignment group and state",
                "Calculate average resolution times and breach ratios"
            ]
        else:
            # General keyword search
            # Clean up query to find relevant keyword nouns
            keywords = re.sub(r"SEARCH|FIND|SHOW|TICKETS|RELATED TO|ABOUT|FOR", "", normalized).strip()
            steps = [
                f"Sanitize query keywords: '{keywords}'",
                f"Perform indexed search across active and closed incidents",
                "Filter and rank matched records by relevance score"
            ]

        plan_dict = {
            "status": "success",
            "steps": steps,
            "context": {
                "action": action,
                "ticket_number": ticket_number,
                "keywords": keywords,
                "query": intent
            }
        }
        return plan_dict

    async def execute(self, plan: dict) -> dict:
        """
        Execute planning tasks sequentially.
        """
        if plan.get("status") != "success":
            return {"status": "failed", "error": "Invalid plan input"}

        ctx = plan.get("context", {})
        action = ctx.get("action")
        
        logger.info(f"ServiceNow Agent executing action: {action}")
        
        # Simulate slight network API latency
        await asyncio.sleep(0.1)
        
        try:
            if action == "lookup":
                ticket_number = ctx.get("ticket_number", "")
                incident = self._client.lookup_incident(ticket_number)
                return {
                    "status": "success",
                    "result": {
                        "action": "lookup",
                        "found": incident is not None,
                        "incident": incident
                    }
                }
            
            elif action == "trends":
                trends = self._client.get_resolution_trends()
                return {
                    "status": "success",
                    "result": {
                        "action": "trends",
                        "trends": trends
                    }
                }
            
            else:  # Search action
                keywords = ctx.get("keywords", "")
                incidents = self._client.search_incidents(keywords)
                return {
                    "status": "success",
                    "result": {
                        "action": "search",
                        "count": len(incidents),
                        "incidents": incidents
                    }
                }
                
        except Exception as exc:
            logger.error(f"Execution error inside ServiceNow Agent: {exc}")
            return {"status": "failed", "error": str(exc)}

    async def summarize(self, result: dict) -> str:
        """
        Generate a conversational report based on execution results.
        """
        if result.get("status") != "success":
            return "Failed to complete ServiceNow action. Please check logs for detailed error."

        data = result.get("result", {})
        action = data.get("action")

        if action == "lookup":
            found = data.get("found", False)
            if not found:
                return "I searched the ServiceNow incident ledger but could not find a ticket matching that number. Please verify the ID and try again."
            
            inc = data.get("incident", {})
            
            # Formulate markdown summary programmatically
            summary = (
                f"### 🎫 ServiceNow Ticket: {inc['number']}\n\n"
                f"| Parameter | Details |\n"
                f"| :--- | :--- |\n"
                f"| **Short Description** | {inc['short_description']} |\n"
                f"| **Severity Level** | {inc['severity']} |\n"
                f"| **Current State** | `{inc['state']}` |\n"
                f"| **Assignment Group** | {inc['assignment_group']} |\n"
                f"| **Assigned SRE** | {inc['assigned_to']} |\n"
            )
            
            if inc["closed_at"]:
                summary += f"| **Closed Timestamp** | {inc['closed_at']} |\n"
                summary += f"\n**🔧 Root Cause Analysis (RCA) & Close Notes**:\n> {inc['close_notes']}\n"
            else:
                summary += f"| **Closed Timestamp** | *Pending* |\n"
                summary += f"\n**⚠️ Resolution Status**:\nThis ticket is currently `Active` and assigned to **{inc['assigned_to']}** in the **{inc['assignment_group']}** group. No resolution notes are available yet.\n"
            
            return summary

        elif action == "trends":
            trends = data.get("trends", {})
            dist = trends.get("assignment_groups_distribution", {})
            
            dist_rows = "\n".join(f"| {group} | {count} ticket(s) |" for group, count in dist.items())
            
            summary = (
                "### 📈 ServiceNow Platform Trends & Workloads\n\n"
                f"- **Total Monitored Incidents**: {trends['total_incidents']}\n"
                f"- **Closed Cases (Archived)**: {trends['closed_incidents']}\n"
                f"- **Active Backlog (Outstanding)**: {trends['active_incidents']}\n\n"
                "#### 👥 Ticket Distribution by SRE Assignment Group\n"
                "| Support Assignment Group | Assigned Workload |\n"
                "| :--- | :--- |\n"
                f"{dist_rows}\n"
            )
            return summary

        else:  # Search action
            count = data.get("count", 0)
            incidents = data.get("incidents", [])
            
            if count == 0:
                return "I searched the ServiceNow ledger but no tickets matched your keywords. Try widening your search terms."
            
            rows = []
            for inc in incidents:
                state_badge = f"`{inc['state']}`"
                rows.append(f"| {inc['number']} | {inc['short_description']} | {inc['severity']} | {state_badge} |")
                
            summary = (
                f"### 🔍 ServiceNow Search Results ({count} match(es) found)\n\n"
                "| Incident ID | Short Description | Severity | State |\n"
                "| :--- | :--- | :--- | :--- |\n"
                + "\n".join(rows) + "\n\n"
                "To get deep details or RCA close notes for any ticket, simply ask: `show ticket INCXXXXX`."
            )
            return summary
