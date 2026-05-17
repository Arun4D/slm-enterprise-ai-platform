"""
Log Analysis Agent - Main implementation.

Analyzes logs for errors, patterns, and provides remediation suggestions.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from app.services.plugin_manager import IAgent
from app.security import path_validator
from tools.log_parser import LogAnalyzer, LogParser, LogSummarizer

logger = logging.getLogger(__name__)


class LogAnalysisAgent(IAgent):
    """
    Log Analysis Agent - analyzes logs for errors and patterns.
    
    Handles:
    - Folder and file scanning
    - Multiple log formats (text, JSON)
    - Error detection and classification
    - Pattern extraction
    - Remediation suggestions
    """

    def __init__(self):
        """Initialize the agent."""
        self.name = "log_analysis_agent"
        self.version = "1.0.0"

    def can_handle(self, intent: str) -> bool:
        """
        Check if agent can handle the intent.
        
        Args:
            intent: User intent
            
        Returns:
            True if agent can handle
        """
        log_keywords = [
            "analyze log",
            "scan log",
            "log analysis",
            "check error",
            "find error",
            "any error",
            "error analysis",
            "error",
            "errors",
            "exception",
            "failure",
            "failed",
            "pattern detection",
            "debug",
            "troubleshoot",
            "application started",
            "app started",
            "started",
            "startup",
            "application status",
            "application name",
            "app name",
            "what is the application name",
            "which application",
        ]
        normalized_intent = re.sub(r"\s+", " ", intent.lower()).strip()
        return any(kw in normalized_intent for kw in log_keywords)

    async def plan(self, intent: str, context: dict) -> dict:
        """
        Create execution plan.
        
        Args:
            intent: User intent
            context: Execution context with file paths, etc.
            
        Returns:
            Execution plan
        """
        log_file_path = context.get("log_file_path")
        log_folder_path = context.get("log_folder_path")

        if not log_file_path and not log_folder_path:
            raise ValueError("Either log_file_path or log_folder_path must be provided")

        plan = {
            "intent": intent,
            "steps": [
                {"step": 1, "action": "validate_paths"},
                {"step": 2, "action": "scan_files"},
                {"step": 3, "action": "parse_logs"},
                {"step": 4, "action": "analyze_patterns"},
                {"step": 5, "action": "classify_entries"},
                {"step": 6, "action": "generate_summary"},
            ],
            "log_file_path": log_file_path,
            "log_folder_path": log_folder_path,
        }

        logger.info(f"Plan created for intent: {intent}")
        return plan

    async def execute(self, plan: dict) -> dict:
        """
        Execute the analysis plan.
        
        Args:
            plan: Execution plan
            
        Returns:
            Analysis results
        """
        results = {
            "intent": plan.get("intent", ""),
            "files_analyzed": 0,
            "total_entries": 0,
            "classified_entries": {
                "errors": [],
                "warnings": [],
                "info": [],
            },
            "patterns": [],
            "application_status": {
                "application_started": False,
                "application_name": None,
                "pid": None,
                "port": None,
                "startup_seconds": None,
                "jvm_running_seconds": None,
                "evidence": [],
            },
            "classifier_version": LogAnalyzer.CLASSIFIER_VERSION,
            "query_answer": None,
            "summary": "",
            "errors": [],
        }

        try:
            # Collect log files
            log_files = await self._collect_log_files(plan)
            logger.info(f"Found {len(log_files)} log files to analyze")

            # Analyze each file
            for log_file in log_files:
                try:
                    file_result = await self._analyze_file(log_file)
                    results["files_analyzed"] += 1
                    results["total_entries"] += file_result["entry_count"]

                    results["classified_entries"]["errors"].extend(
                        file_result["classified"]["errors"]
                    )
                    results["classified_entries"]["warnings"].extend(
                        file_result["classified"]["warnings"]
                    )
                    results["classified_entries"]["info"].extend(
                        file_result["classified"]["info"]
                    )
                    results["patterns"].extend(file_result["patterns"])
                    self._merge_application_status(
                        results["application_status"],
                        file_result["application_status"],
                    )

                except Exception as e:
                    logger.error(f"Error analyzing file {log_file}: {e}")
                    results["errors"].append(
                        {"file": str(log_file), "error": str(e)}
                    )

            # Deduplicate patterns
            results["patterns"] = self._deduplicate_patterns(results["patterns"])
            results["query_answer"] = self._build_query_answer(
                results["intent"],
                results["application_status"],
            )

            return results

        except Exception as e:
            logger.error(f"Execution error: {e}")
            results["errors"].append({"step": "execution", "error": str(e)})
            return results

    async def summarize(self, result: dict) -> str:
        """
        Summarize execution result.
        
        Args:
            result: Execution result
            
        Returns:
            Text summary
        """
        summary = "## Log Analysis Results\n\n"

        if result.get("query_answer"):
            summary += f"### Answer\n{result['query_answer']}\n\n"

        summary += f"### Overview\n"
        summary += f"- Files analyzed: {result.get('files_analyzed', 0)}\n"
        summary += f"- Total log entries: {result.get('total_entries', 0)}\n"

        classified = result.get("classified_entries", {})
        summary += f"- Errors found: {len(classified.get('errors', []))}\n"
        summary += f"- Warnings found: {len(classified.get('warnings', []))}\n\n"
        summary += f"- Classifier: {result.get('classifier_version', 'unknown')}\n\n"

        app_status = result.get("application_status", {})
        if app_status:
            summary += "### Application Status\n"
            if app_status.get("application_started"):
                app_name = app_status.get("application_name") or "Application"
                summary += f"- {app_name} started successfully"
                if app_status.get("startup_seconds") is not None:
                    summary += f" in {app_status['startup_seconds']} seconds"
                summary += "\n"
                if app_status.get("port") is not None:
                    summary += f"- Listening port detected: {app_status['port']}\n"
                if app_status.get("pid") is not None:
                    summary += f"- Process ID detected: {app_status['pid']}\n"
            else:
                summary += "- No application startup completion line was detected\n"
            summary += "\n"

        patterns = result.get("patterns", [])
        if patterns:
            summary += f"### Top Error Patterns\n"
            for i, pattern in enumerate(patterns[:5], 1):
                summary += (
                    f"{i}. Pattern: `{pattern['pattern'][:100]}`\n"
                    f"   - Occurrences: {pattern['count']}\n"
                )
                remediation = LogAnalyzer.suggest_remediation(pattern["pattern"])
                summary += f"   - Suggestion: {remediation}\n\n"

        if result.get("errors"):
            summary += f"### Processing Errors\n"
            for error in result["errors"]:
                summary += f"- {error.get('file', 'Unknown')}: {error.get('error', 'Unknown error')}\n"

        return summary

    async def _collect_log_files(self, plan: dict) -> list[Path]:
        """Collect log files to analyze."""
        log_files = []

        # Analyze single file
        if file_path := plan.get("log_file_path"):
            try:
                safe_path = path_validator.sanitize_path(file_path)
                if safe_path.is_file():
                    log_files.append(safe_path)
            except Exception as e:
                logger.error(f"Error validating file path: {e}")

        # Scan folder recursively
        if folder_path := plan.get("log_folder_path"):
            try:
                safe_path = path_validator.sanitize_path(folder_path)
                if safe_path.is_dir():
                    # Find log files
                    log_extensions = [".log", ".txt", ".json", ".jsonl", ".evtx"]
                    for ext in log_extensions:
                        log_files.extend(safe_path.glob(f"**/*{ext}"))
            except Exception as e:
                logger.error(f"Error scanning folder: {e}")

        return list(set(log_files))  # Deduplicate

    async def _analyze_file(self, file_path: Path) -> dict:
        """Analyze a single log file."""
        logger.info(f"Analyzing file: {file_path}")

        # Parse file
        entries = LogParser.parse_file(file_path)
        logger.debug(f"Parsed {len(entries)} entries from {file_path}")

        # Classify entries
        classified = LogAnalyzer.classify_entries(entries)

        # Extract patterns
        error_entries = classified["errors"] + classified["warnings"]
        patterns = LogAnalyzer.extract_patterns(error_entries)
        application_status = LogAnalyzer.detect_application_lifecycle(entries)

        return {
            "file": str(file_path),
            "entry_count": len(entries),
            "classified": classified,
            "patterns": patterns,
            "application_status": application_status,
        }

    @staticmethod
    def _merge_application_status(target: dict, source: dict) -> None:
        """Merge per-file startup signals into the aggregate result."""
        if source.get("application_started"):
            target["application_started"] = True

        for key in [
            "application_name",
            "pid",
            "port",
            "startup_seconds",
            "jvm_running_seconds",
        ]:
            if source.get(key) is not None:
                target[key] = source[key]

        target["evidence"].extend(source.get("evidence", []))
        target["evidence"] = target["evidence"][:5]

    @staticmethod
    def _build_query_answer(intent: str, application_status: dict) -> str | None:
        """Build a direct answer for common operator questions."""
        normalized_intent = re.sub(r"\s+", " ", intent.lower()).strip()
        asks_port = "port" in normalized_intent
        asks_app_name = any(
            phrase in normalized_intent
            for phrase in [
                "application name",
                "app name",
                "what is the application",
                "which application",
                "service name",
            ]
        )
        asks_started = any(
            phrase in normalized_intent
            for phrase in [
                "application started",
                "app started",
                "is running",
                "application running",
                "running in",
                "startup",
            ]
        )

        if asks_app_name:
            app_name = application_status.get("application_name")
            if app_name:
                return f"The application name is {app_name}."
            return "I could not find the application name in the analyzed logs."

        if asks_port:
            port = application_status.get("port")
            app_name = application_status.get("application_name") or "Application"
            if port is not None:
                started = " and started successfully" if application_status.get("application_started") else ""
                return f"{app_name} is running on port {port}{started}."
            return "I could not find a listening port in the analyzed logs."

        if asks_started:
            app_name = application_status.get("application_name") or "Application"
            if application_status.get("application_started"):
                answer = f"{app_name} started successfully"
                if application_status.get("startup_seconds") is not None:
                    answer += f" in {application_status['startup_seconds']} seconds"
                if application_status.get("port") is not None:
                    answer += f" and is listening on port {application_status['port']}"
                return f"{answer}."
            return "I could not find an application startup completion line in the analyzed logs."

        return None

    @staticmethod
    def _deduplicate_patterns(patterns: list[dict]) -> list[dict]:
        """Deduplicate and merge patterns."""
        unique_patterns = {}

        for pattern in patterns:
            key = pattern["pattern"]
            if key not in unique_patterns:
                unique_patterns[key] = pattern
            else:
                unique_patterns[key]["count"] += pattern["count"]

        # Sort by frequency
        return sorted(
            unique_patterns.values(),
            key=lambda x: x["count"],
            reverse=True,
        )[:10]
