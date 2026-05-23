"""
Log Analysis Agent - Main implementation.

Analyzes logs for errors, patterns, and provides remediation suggestions.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, TYPE_CHECKING

from app.core.config import settings
from app.services.plugin_manager import IAgent
from app.security import path_validator
from tools.log_parser import LogAnalyzer, LogParser, LogSummarizer

if TYPE_CHECKING:
    from app.core.slm.service import SLMService

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
        self._slm_service: "SLMService | None" = None

    def set_slm_service(self, service: "SLMService") -> None:
        """
        Receive the SLM service from the platform at startup.

        Called by the application lifespan handler after agent
        discovery. When set, the agent uses SLM for intent
        classification, remediation suggestions, and summaries.
        When None, falls back to deterministic logic.
        """
        self._slm_service = service

    def can_handle(self, intent: str) -> bool:
        """
        Check if agent can handle the intent.

        Uses SLM intent classification when available, falling back
        to keyword matching when the SLM is unavailable.

        Args:
            intent: User intent

        Returns:
            True if agent can handle
        """
        # --- Fast path: SLM intent classification ---
        if self._slm_service is not None and self._slm_service.available:
            result = self._slm_service.classify_intent_sync(
                intent,
                [
                    ("log_analysis_agent", "Log analysis, error detection, troubleshooting"),
                    ("servicenow_agent", "ServiceNow ticket management"),
                    ("github_agent", "GitHub CI/CD and repository management"),
                ],
            )
            if result == "log_analysis_agent":
                return True
            # If SLM classified as something else, still check keywords
            # as a safety net (SLMs can misclassify short queries)

        # --- Fallback: keyword matching ---
        log_keywords = [
            "analyze log", "scan log", "log analysis",
            "check error", "find error", "any error",
            "error analysis", "error", "errors",
            "exception", "failure", "failed",
            "pattern detection", "debug", "troubleshoot",
            "application started", "app started",
            "started", "startup",
            "application status", "application name",
            "app name", "what is the application name",
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
            "start_time": context.get("start_time"),
            "end_time": context.get("end_time"),
            "history": context.get("history", []),
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
            
            if not log_files:
                results["summary"] = (
                    "### ⚠️ SRE Action Required: No Log File Detected\n\n"
                    "The **SLM AI Operations Platform** has classified your intent under the **Log Analysis Agent**.\n\n"
                    "To execute SRE diagnostics and retrieve automated suggestions:\n"
                    "- Please **attach or select a log file** (use the *📁 Add log file attachment* button below).\n"
                    "- Or **select a target agent and directory** manually to initialize analysis.\n\n"
                    "No log file was detected in the active workspace session."
                )
                return results

            logger.info(f"Found {len(log_files)} log files to analyze")

            # Extract datetime limits from plan context and query intent
            intent = plan.get("intent", "")
            extracted_start, extracted_end = self._extract_datetime_range(intent)
            start_time = plan.get("start_time") or extracted_start
            end_time = plan.get("end_time") or extracted_end

            if start_time or end_time:
                logger.info(f"Applying datetime range filter: {start_time} to {end_time}")

            # Analyze each file
            for log_file in log_files:
                try:
                    file_result = await self._analyze_file(log_file, start_time, end_time)
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

        Uses SLM to generate a natural-language summary when available,
        falling back to structured markdown when the SLM is unavailable.

        Args:
            result: Execution result

        Returns:
            Text summary
        """
        # --- Fast path: SLM-generated summary ---
        if self._slm_service is not None and self._slm_service.available:
            slm_summary = await self._slm_service.summarize_analysis(result)
            if slm_summary:
                header = "## Log Analysis Results (AI-Generated)\n\n"
                if result.get("query_answer"):
                    header += f"### Answer\n{result['query_answer']}\n\n"
                return header + slm_summary

        # --- Fallback: deterministic summary ---
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
                exact_log = pattern["samples"][0] if pattern.get("samples") else pattern["pattern"]
                summary += (
                    f"{i}. Log Entry: `{exact_log[:120]}`\n"
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
        # If no files found, check if the user pasted raw log content in the chat message (intent)
        # or in any of the previous user messages in this session history
        if not log_files:
            pasted_content = None
            intent_text = plan.get("intent", "")
            
            def is_log_dump(text: str) -> bool:
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if len(lines) < 2:
                    return False
                log_indicators = ["INFO", "WARN", "ERROR", "DEBUG", "FATAL", "Exception", "---", "PID", "c.e.demo", "Tomcat", "at ", "   at "]
                matches = sum(1 for line in lines if any(ind in line for ind in log_indicators))
                return (matches / len(lines)) >= 0.3

            if is_log_dump(intent_text):
                pasted_content = intent_text
                logger.info("Auto-detected raw log dump in current query.")
            else:
                # If not, look backward through the session history for the most recent log dump
                history = plan.get("history", [])
                for past_msg in reversed(history):
                    if is_log_dump(past_msg):
                        pasted_content = past_msg
                        logger.info("Auto-detected raw log dump in session history.")
                        break
            
            if not pasted_content:
                # SRE User Request: Only generate fallback logs for the exact demo prompt!
                # Otherwise, return empty log list so we explicitly ask SRE operators to upload a file.
                normalized = intent_text.lower().replace("remidation", "remediation")
                if "find error and give me remediation step" in normalized:
                    logger.info("No logs found. Generating pre-loaded demo corporate database startup logs.")
                    pasted_content = (
                        "2026-05-17 19:05:01.123  INFO 28432 --- [main] c.e.demo.DemoApplication                : Starting DemoApplication using Java 17.0.10 on My-Laptop with PID 28432\n"
                        "2026-05-17 19:05:01.125  INFO 28432 --- [main] c.e.demo.DemoApplication                : No active profile set, falling back to 1 default profile: \"default\"\n"
                        "2026-05-17 19:05:02.542  INFO 28432 --- [main] o.s.b.w.embedded.tomcat.TomcatWebServer  : Tomcat initialized with port(s): 9080 (http)\n"
                        "2026-05-17 19:05:02.810  INFO 28432 --- [main] o.a.c.c.CouchbaseConnectionFactory      : Node localhost/127.0.0.1:11210 heartbeat failed or timed out.\n"
                        "2026-05-17 19:05:02.815  WARN 28432 --- [main] o.a.c.c.CouchbaseConnectionFactory      : Connection to Couchbase cluster lost. Attempting automatic reconnection in 5000ms...\n"
                        "2026-05-17 19:05:03.211  INFO 28432 --- [main] o.s.b.w.embedded.tomcat.TomcatWebServer  : Tomcat started on port(s): 9080 (http) with context path ''\n"
                        "2026-05-17 19:05:03.225  INFO 28432 --- [main] c.e.demo.DemoApplication                : Started DemoApplication in 2.654 seconds (JVM running for 3.12)\n"
                        "2026-05-17 19:05:05.100  INFO 28432 --- [nio-9080-exec-1] o.a.c.c.CouchbaseConnectionFactory      : Reconnection attempt 1 to Couchbase cluster.\n"
                        "2026-05-17 19:05:05.105  WARN 28432 --- [nio-9080-exec-1] o.a.c.c.CouchbaseConnectionFactory      : Couchbase connection still unavailable, retrying...\n"
                        "2026-05-17 19:05:10.100  INFO 28432 --- [nio-9080-exec-1] o.a.c.c.CouchbaseConnectionFactory      : Reconnection attempt 2 successful. Connected to Couchbase cluster.\n"
                        "2026-05-17 19:06:01.001  INFO 28432 --- [nio-9080-exec-2] c.e.demo.controller.UserController     : Fetching user details for user ID: 1001\n"
                        "2026-05-17 19:06:02.002  INFO 28432 --- [nio-9080-exec-2] c.e.demo.controller.UserController     : User 1001 details successfully retrieved.\n"
                        "2026-05-17 19:06:15.321  INFO 28432 --- [nio-9080-exec-3] c.e.demo.controller.UserController     : Creating new user with username: operator\n"
                        "2026-05-17 19:06:15.999  INFO 28432 --- [nio-9080-exec-3] c.e.demo.controller.UserController     : User operator created with ID: 1002\n"
                        "2026-05-17 19:07:01.200  INFO 28432 --- [nio-9080-exec-4] c.e.demo.controller.UserController     : Authenticating user ID: 1002 with password: SuperSecretPassword123\n"
                        "2026-05-17 19:07:01.205  INFO 28432 --- [nio-9080-exec-4] c.e.demo.controller.UserController     : Authentication successful for user ID: 1002\n"
                        "2026-05-17 19:07:05.110  INFO 28432 --- [nio-9080-exec-5] c.e.demo.controller.UserController     : Request received for user ID: 9999\n"
                        "2026-05-17 19:07:05.115  ERROR 28432 --- [nio-9080-exec-5] c.e.demo.controller.UserController     : Database connection lost while fetching user details for user ID: 9999\n"
                        "2026-05-17 19:07:09.512 ERROR 28432 --- [nio-8080-exec-5] c.e.demo.controller.UserController     : Exception caught while processing request for user ID: 9999\n"
                        "2026-05-17 19:07:10.001  INFO 28432 --- [nio-9080-exec-6] c.e.demo.controller.UserController     : Retry request received for user ID: 9999\n"
                        "2026-05-17 19:07:11.002  INFO 28432 --- [nio-9080-exec-6] c.e.demo.controller.UserController     : Request for user ID: 9999 completed successfully after fallback database retry."
                    )
            
            if pasted_content:
                try:
                    upload_dir = Path(folder_path or str(Path(settings.runtime_workspace_path) / "uploads"))
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    pasted_file = upload_dir / "pasted_log_snippet.log"
                    with open(pasted_file, "w", encoding="utf-8") as f:
                        f.write(pasted_content)
                    log_files.append(pasted_file)
                except Exception as e:
                    logger.error(f"Failed to save pasted log content: {e}")

        return list(set(log_files))  # Deduplicate

    async def _analyze_file(self, file_path: Path, start_time: str | None = None, end_time: str | None = None) -> dict:
        """Analyze a single log file."""
        logger.info(f"Analyzing file: {file_path}")

        # Parse file
        entries = LogParser.parse_file(file_path)
        logger.debug(f"Parsed {len(entries)} entries from {file_path}")

        # Filter entries by datetime boundary range
        entries = LogParser.filter_entries_by_datetime(entries, start_time, end_time)
        logger.info(f"Filtered to {len(entries)} entries in range {start_time} - {end_time}")

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

    @staticmethod
    def _extract_datetime_range(text: str) -> tuple[str | None, str | None]:
        """Extract start and end datetime from text query."""
        # Look for patterns like "between YYYY-MM-DD HH:MM:SS and YYYY-MM-DD HH:MM:SS"
        # or "after YYYY-MM-DD HH:MM:SS"
        # or "before YYYY-MM-DD HH:MM:SS"
        normalized = text.lower()
        
        start_time = None
        end_time = None

        # YYYY-MM-DD HH:MM(:SS)? pattern
        dt_pattern = r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?)"
        dates = re.findall(dt_pattern, text)
        
        if len(dates) >= 2:
            start_time = dates[0] if len(dates[0]) == 19 else dates[0] + ":00"
            end_time = dates[1] if len(dates[1]) == 19 else dates[1] + ":59"
        elif len(dates) == 1:
            if "after" in normalized or "from" in normalized:
                start_time = dates[0] if len(dates[0]) == 19 else dates[0] + ":00"
            elif "before" in normalized or "to" in normalized:
                end_time = dates[0] if len(dates[0]) == 19 else dates[0] + ":59"
        
        # Fallback to YYYY-MM-DD format
        if not start_time and not end_time:
            date_pattern = r"(\d{4}-\d{2}-\d{2})"
            dates_only = re.findall(date_pattern, text)
            if len(dates_only) >= 2:
                start_time = dates_only[0] + " 00:00:00"
                end_time = dates_only[1] + " 23:59:59"
            elif len(dates_only) == 1:
                if "after" in normalized or "from" in normalized:
                    start_time = dates_only[0] + " 00:00:00"
                elif "before" in normalized or "to" in normalized:
                    end_time = dates_only[0] + " 23:59:59"
                else:
                    # Single date filter: exact day
                    start_time = dates_only[0] + " 00:00:00"
                    end_time = dates_only[0] + " 23:59:59"

        return start_time, end_time
