"""
Log parsing and analysis tools for the Log Analysis Agent.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class LogParser:
    """Parse various log file formats."""

    @staticmethod
    def parse_text_log(content: str) -> list[dict[str, Any]]:
        """
        Parse plain text log format.
        
        Extracts timestamp, level, and message from common log formats.
        """
        entries = []
        lines = content.split("\n")

        for line in lines:
            if not line.strip():
                continue

            entry = {
                "timestamp": None,
                "level": "INFO",
                "level_detected": False,
                "message": line,
                "raw": line,
            }

            # Try to extract timestamp
            timestamp_match = re.search(r"\[?(\d{4}-\d{2}-\d{2}[T ]?\d{2}:\d{2}:\d{2})\]?", line)
            if timestamp_match:
                entry["timestamp"] = timestamp_match.group(1)

            # Try to extract log level
            level_match = re.search(r"\b(DEBUG|INFO|WARNING|ERROR|CRITICAL|FATAL)\b", line, re.I)
            if level_match:
                entry["level"] = level_match.group(1).upper()
                entry["level_detected"] = True

            entries.append(entry)

        return entries

    @staticmethod
    def parse_json_log(content: str) -> list[dict[str, Any]]:
        """Parse JSON/JSONL log format."""
        entries = []

        for line in content.split("\n"):
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON line: {line[:100]}")
                continue

        return entries

    @classmethod
    def parse_file(cls, file_path: Path) -> list[dict[str, Any]]:
        """Parse log file based on format."""
        if not file_path.exists():
            raise FileNotFoundError(f"Log file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Determine format
        if file_path.suffix == ".json" or file_path.suffix == ".jsonl":
            return cls.parse_json_log(content)
        else:
            return cls.parse_text_log(content)


class LogAnalyzer:
    """Analyze parsed log entries for patterns and issues."""

    CLASSIFIER_VERSION = "explicit-level-first-v2"
    ERROR_KEYWORDS = ["error", "exception", "failed", "critical", "fatal", "severe"]
    WARNING_KEYWORDS = ["warning", "warn", "deprecated"]
    ERROR_LEVELS = {"ERROR", "CRITICAL", "FATAL", "SEVERE"}
    WARNING_LEVELS = {"WARNING", "WARN"}
    NON_PROBLEM_LEVELS = {"TRACE", "DEBUG", "INFO"}

    @classmethod
    def classify_entries(cls, entries: list[dict[str, Any]]) -> dict[str, list[dict]]:
        """Classify entries by severity level."""
        classified = {
            "errors": [],
            "warnings": [],
            "info": [],
        }

        for entry in entries:
            message = entry.get("message", "").lower()
            level = entry.get("level", "INFO").upper()
            level_detected = entry.get("level_detected", "level" in entry)

            if level in cls.ERROR_LEVELS:
                classified["errors"].append(entry)
            elif level in cls.WARNING_LEVELS:
                classified["warnings"].append(entry)
            elif level_detected and level in cls.NON_PROBLEM_LEVELS:
                classified["info"].append(entry)
            elif any(kw in message for kw in cls.ERROR_KEYWORDS):
                classified["errors"].append(entry)
            elif any(kw in message for kw in cls.WARNING_KEYWORDS):
                classified["warnings"].append(entry)
            else:
                classified["info"].append(entry)

        return classified

    @classmethod
    def detect_application_lifecycle(cls, entries: list[dict[str, Any]]) -> dict[str, Any]:
        """Detect common application startup signals from parsed logs."""
        status: dict[str, Any] = {
            "application_started": False,
            "application_name": None,
            "pid": None,
            "port": None,
            "startup_seconds": None,
            "jvm_running_seconds": None,
            "evidence": [],
        }

        for entry in entries:
            message = entry.get("message", "")

            starting_match = re.search(
                r"\bStarting\s+(?P<app>[\w.$-]+)\b.*?\bwith PID\s+(?P<pid>\d+)",
                message,
            )
            if starting_match:
                status["application_name"] = starting_match.group("app")
                status["pid"] = int(starting_match.group("pid"))
                status["evidence"].append(message[:300])

            port_match = re.search(
                r"\bTomcat (?:initialized with|started on) port(?:\(s\))?:?\s+(?P<port>\d+)",
                message,
            )
            if port_match:
                status["port"] = int(port_match.group("port"))

            started_match = re.search(
                r"\bStarted\s+(?P<app>[\w.$-]+)\s+in\s+(?P<startup>[\d.]+)\s+seconds"
                r"(?:\s+\(JVM running for\s+(?P<jvm>[\d.]+)\))?",
                message,
            )
            if started_match:
                status["application_started"] = True
                status["application_name"] = started_match.group("app")
                status["startup_seconds"] = float(started_match.group("startup"))
                if started_match.group("jvm"):
                    status["jvm_running_seconds"] = float(started_match.group("jvm"))
                status["evidence"].append(message[:300])

        return status

    @classmethod
    def extract_patterns(cls, entries: list[dict[str, Any]], limit: int = 10) -> list[dict]:
        """Extract error patterns from log entries."""
        patterns = {}

        for entry in entries:
            message = entry.get("message", "")

            # Generalize message by replacing numbers and IDs
            generalized = re.sub(r"\d+", "N", message)
            generalized = re.sub(r"[a-f0-9]{8}-[a-f0-9]{4}", "UUID", generalized)

            if generalized not in patterns:
                patterns[generalized] = {
                    "pattern": generalized,
                    "count": 0,
                    "samples": [],
                    "level": entry.get("level", "INFO"),
                }

            patterns[generalized]["count"] += 1
            if len(patterns[generalized]["samples"]) < 3:
                patterns[generalized]["samples"].append(entry.get("message", "")[:200])

        # Sort by frequency
        sorted_patterns = sorted(
            patterns.values(),
            key=lambda x: x["count"],
            reverse=True,
        )[:limit]

        return sorted_patterns

    @classmethod
    def suggest_remediation(cls, pattern: str) -> str:
        """Suggest remediation for error patterns."""
        pattern_lower = pattern.lower()

        suggestions = {
            "connection": "Check network connectivity and service availability",
            "timeout": "Increase timeout threshold or optimize performance",
            "memory": "Review memory usage and increase heap size if needed",
            "disk": "Check disk space and clean up temporary files",
            "authentication": "Verify credentials and authentication configuration",
            "permission": "Check file/resource permissions and access controls",
            "not found": "Verify resource exists or check file paths",
        }

        for keyword, suggestion in suggestions.items():
            if keyword in pattern_lower:
                return suggestion

        return "Investigate error logs and check system configuration"


class LogSummarizer:
    """Summarize analysis results."""

    @staticmethod
    def summarize(
        classified_entries: dict,
        patterns: list[dict],
        file_name: str = "logs",
    ) -> str:
        """Create a text summary of log analysis."""
        summary = f"# Log Analysis Summary: {file_name}\n\n"

        # Overview
        total_errors = len(classified_entries["errors"])
        total_warnings = len(classified_entries["warnings"])
        summary += f"## Overview\n"
        summary += f"- **Errors**: {total_errors}\n"
        summary += f"- **Warnings**: {total_warnings}\n"
        summary += f"- **Info Messages**: {len(classified_entries['info'])}\n\n"

        # Top patterns
        if patterns:
            summary += f"## Top Error Patterns\n"
            for i, pattern in enumerate(patterns[:5], 1):
                summary += (
                    f"{i}. **Occurrence**: {pattern['count']} times\n"
                    f"   - Pattern: `{pattern['pattern'][:100]}`\n"
                )
                if pattern["samples"]:
                    summary += f"   - Sample: {pattern['samples'][0][:100]}\n"
                summary += "\n"

        return summary
