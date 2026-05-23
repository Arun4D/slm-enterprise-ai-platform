"""
ServiceNow Mock REST Client.
Enables offline incident search, lookup, and similarity mapping.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Core mock database of incident tickets
MOCK_INCIDENTS = [
    {
        "sys_id": "sys_1001",
        "number": "INC00101",
        "short_description": "Database connection pool exhausted on prod-db-server",
        "severity": "1 - Critical (P1)",
        "state": "Closed",
        "assignment_group": "DBA Operations",
        "assigned_to": "Sarah Jenkins",
        "closed_at": "2026-05-20T12:00:00Z",
        "close_notes": "Exhaustion occurred because inactive connection sessions were not reaping. Set idle timeout to 30s and enabled connection leaks harvesting.",
        "category": "database"
    },
    {
        "sys_id": "sys_1002",
        "number": "INC00102",
        "short_description": "Memory leak detected in auth-middleware API containers",
        "severity": "2 - High (P2)",
        "state": "Closed",
        "assignment_group": "Platform Security",
        "assigned_to": "David Vance",
        "closed_at": "2026-05-22T09:30:00Z",
        "close_notes": "Auth middleware failed to release open file descriptors on failed handshake tokens. Patched file read contexts with standard with-blocks.",
        "category": "platform"
    },
    {
        "sys_id": "sys_1003",
        "number": "INC00103",
        "short_description": "Kubernetes auth pod crash-looping under load spikes",
        "severity": "2 - High (P2)",
        "state": "New",
        "assignment_group": "DevOps Engineers",
        "assigned_to": "Alex Mercer",
        "closed_at": None,
        "close_notes": "",
        "category": "kubernetes"
    },
    {
        "sys_id": "sys_1004",
        "number": "INC00104",
        "short_description": "Disk space critical (99% full) on backend-srv-01",
        "severity": "3 - Medium (P3)",
        "state": "Closed",
        "assignment_group": "Cloud Infrastructure",
        "assigned_to": "Elena Rostova",
        "closed_at": "2026-05-21T18:45:00Z",
        "close_notes": "Rotated files were not being compressed properly. Configured logrotate with compress directives and purged stale docker temp cache.",
        "category": "storage"
    },
    {
        "sys_id": "sys_1005",
        "number": "INC00105",
        "short_description": "Network latency spike on gateway routing server",
        "severity": "4 - Low (P4)",
        "state": "Closed",
        "assignment_group": "Global Networking",
        "assigned_to": "Tariq Ali",
        "closed_at": "2026-05-19T14:15:00Z",
        "close_notes": "Flushed redundant routing table paths that were creating localized ping loops during high switch traffic.",
        "category": "networking"
    }
]


class ServiceNowClient:
    """
    ServiceNow client providing mock REST interfaces.
    """

    def __init__(self, offline: bool = True):
        self._offline = offline
        logger.info(f"Initialized ServiceNow Client (offline_mode={offline})")

    def lookup_incident(self, ticket_number: str) -> Optional[dict[str, Any]]:
        """Retrieve details of a single ticket by its number identifier."""
        ticket_number = ticket_number.strip().upper()
        logger.info(f"Looking up incident: {ticket_number}")
        
        for inc in MOCK_INCIDENTS:
            if inc["number"] == ticket_number:
                return inc
        return None

    def search_incidents(self, keyword: str) -> list[dict[str, Any]]:
        """Search incidents containing keyword in short description or category."""
        keyword_clean = keyword.lower().strip()
        logger.info(f"Searching incidents for keyword: '{keyword_clean}'")
        
        matches = []
        for inc in MOCK_INCIDENTS:
            desc = inc["short_description"].lower()
            cat = inc["category"].lower()
            num = inc["number"].lower()
            if keyword_clean in desc or keyword_clean in cat or keyword_clean in num:
                matches.append(inc)
        return matches

    def detect_similar_incidents(self, error_text: str) -> list[dict[str, Any]]:
        """
        Calculates localized token overlap between an error log message
        and closing notes/short descriptions of closed incidents.
        """
        error_tokens = set(error_text.lower().split())
        similar_tickets = []

        for inc in MOCK_INCIDENTS:
            text_to_compare = (
                inc["short_description"] + " " + (inc["close_notes"] or "")
            ).lower()
            inc_tokens = set(text_to_compare.split())
            
            # Intersection score
            common = error_tokens.intersection(inc_tokens)
            score = len(common) / max(1, len(error_tokens))
            
            if score > 0.05:  # Any token overlap matches
                similar_tickets.append((score, inc))

        # Sort by overlap score descending
        similar_tickets.sort(key=lambda x: x[0], reverse=True)
        return [t[1] for t in similar_tickets[:3]]

    def get_resolution_trends(self) -> dict[str, Any]:
        """Compile status and assignment group statistics for dashboard visualizers."""
        total = len(MOCK_INCIDENTS)
        closed = sum(1 for inc in MOCK_INCIDENTS if inc["state"] == "Closed")
        active = total - closed
        
        groups = {}
        for inc in MOCK_INCIDENTS:
            grp = inc["assignment_group"]
            groups[grp] = groups.get(grp, 0) + 1

        return {
            "total_incidents": total,
            "closed_incidents": closed,
            "active_incidents": active,
            "assignment_groups_distribution": groups
        }
