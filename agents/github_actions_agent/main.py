"""
GitHub Actions Agent implementation.
"""
import logging
from typing import TYPE_CHECKING

from app.services.plugin_manager import IAgent
from tools import GitHubActionsParser

if TYPE_CHECKING:
    from app.core.slm.service import SLMService

logger = logging.getLogger(__name__)

class GitHubActionsAgent(IAgent):
    """
    GitHub Actions Agent - Analyzes CI/CD pipeline execution logs.
    """

    def __init__(self):
        self.name = "github_actions_agent"
        self.version = "1.0.0"
        self._slm_service: "SLMService | None" = None

    def set_slm_service(self, service: "SLMService") -> None:
        """Receive platform-injected SLM Service."""
        self._slm_service = service

    def can_handle(self, intent: str) -> bool:
        """Determine if this agent should handle the intent."""
        # Fast-path: SLM intent classification
        if self._slm_service is not None and self._slm_service.available:
            result = self._slm_service.classify_intent_sync(
                intent,
                [
                    ("github_actions_agent", "GitHub Actions workflows, build logs, runner errors, and pipeline repairs"),
                    ("log_analysis_agent", "System log analysis, server exceptions, raw log formats, pattern detection"),
                ]
            )
            if result == "github_actions_agent":
                return True

        # Fallback: Keyword search
        gh_keywords = ["github", "actions", "workflow", "pipeline", "runner", "ci/cd", "build_frontend", "deploy_image"]
        normalized = intent.lower()
        return any(kw in normalized for kw in gh_keywords)

    async def plan(self, intent: str, context: dict) -> dict:
        """Create execution planning structure."""
        logger.info(f"GitHub Actions Agent planning for: '{intent}'")
        
        normalized = intent.lower()
        is_generation = any(kw in normalized for kw in ["generate", "create", "write", "setup", "make", "template", "code"])
        code_text = context.get("code_text") or context.get("uploaded_text") or ""
        validation_requested = any(kw in normalized for kw in ["validate", "review", "audit", "check", "scan"])
        is_validation = bool(context.get("uploaded_files")) or (bool(code_text.strip()) and validation_requested)
        profile = None
        
        if is_validation and not is_generation:
            action = "validate"
            steps = [
                "Load GitHub Actions workflow/log content from pasted text or uploaded files",
                "Validate triggers, jobs, action pinning, secrets hygiene, and least-privilege permissions",
                "Detect runner/build failure signatures when logs are supplied",
                "Return deterministic remediation guidance"
            ]
        elif is_generation:
            action = "generate"
            steps = [
                "Scan workflow templates repository",
                "Select Node/Python pipeline blueprints",
                "Inject actions/checkout and caching optimizations",
                "Format pipeline HCL/YAML code blocks"
            ]
        else:
            action = "analyze"
            # Determine failure profile based on user query keywords
            profile = "general"
            if "frontend" in intent.lower() or "heap" in intent.lower() or "build" in intent.lower():
                profile = "build_frontend"
            elif "deploy" in intent.lower() or "docker" in intent.lower() or "push" in intent.lower():
                profile = "deploy_image"
            elif "test" in intent.lower() or "pytest" in intent.lower():
                profile = "run_tests"

            steps = [
                f"Retrieve workflow execution profile: '{profile}'",
                "Extract process crash-logs and log signatures",
                "Consult pipeline repair index",
                "Synthesize runner debug suggestions"
            ]

        return {
            "status": "success",
            "steps": steps,
            "context": {
                "action": action,
                "profile": profile,
                "query": intent,
                "code_text": code_text,
                "uploaded_files": context.get("uploaded_files", []),
            }
        }

    async def execute(self, plan: dict) -> dict:
        """Execute workflow generation or diagnostic rules."""
        if plan.get("status") != "success":
            return {"status": "failed", "error": "Invalid plan input"}

        ctx = plan.get("context", {})
        action = ctx.get("action", "analyze")

        if action == "generate":
            query = ctx.get("query", "").lower()
            code = GitHubActionsParser.generate_workflow(query)
            return {
                "status": "success",
                "result": {
                    "action": "generate",
                    "code": code
                }
            }
        elif action == "validate":
            code_text = ctx.get("code_text", "")
            validation = GitHubActionsParser.validate_workflow(code_text)
            diagnostics = GitHubActionsParser.parse_workflow_failure(code_text)
            return {
                "status": "success",
                "result": {
                    "action": "validate",
                    "validation": validation,
                    "diagnostics": diagnostics,
                    "uploaded_files": ctx.get("uploaded_files", []),
                }
            }
        else:
            profile = ctx.get("profile", "general")
            diagnostics = GitHubActionsParser.parse_workflow_failure(profile)
            return {
                "status": "success",
                "result": {
                    "action": "analyze",
                    "profile": profile,
                    "diagnostics": diagnostics
                }
            }

    async def summarize(self, result: dict) -> str:
        """Convert results into premium Markdown output."""
        if result.get("status") != "success":
            return "Failed to complete workflow task. Please check system logs."

        data = result.get("result", {})
        action = data.get("action", "analyze")

        if action == "generate":
            code = data.get("code", "")
            summary = (
                f"### ⚙️ GitHub Actions CI/CD Code Generator\n\n"
                f"I have generated a secure, highly optimized GitHub Actions workflow pipeline to fast-track your development:\n\n"
                f"```yaml\n"
                f"{code}"
                f"```\n\n"
                f"#### 🚀 Next Steps:\n"
                f"1. Save this content as `.github/workflows/ci.yml` in your repository root.\n"
                f"2. Commit and push it to trigger the GitHub runner process."
            )
            return summary
        elif action == "validate":
            validation = data.get("validation", {})
            diagnostics = data.get("diagnostics", {})
            files = data.get("uploaded_files", [])
            findings = validation.get("findings", [])
            findings_md = "\n".join(
                f"- **{item.get('severity', 'info').upper()}** `{item.get('rule')}`: {item.get('message')} Remediation: {item.get('remediation')}"
                for item in findings
            ) or "- No GitHub Actions guardrail violations detected."
            file_note = ", ".join(files) if files else "pasted chat text"
            return (
                "### GitHub Actions Workflow Validation\n\n"
                f"**Input source**: {file_note}\n\n"
                f"**Status**: `{validation.get('status')}` with `{validation.get('finding_count', 0)}` finding(s)\n\n"
                "#### Guardrail Findings\n"
                f"{findings_md}\n\n"
                "#### Runner Failure Signal\n"
                f"- Step: `{diagnostics.get('step_name')}`\n"
                f"- Detail: {diagnostics.get('error_details')}\n"
                f"- Repair: {diagnostics.get('suggested_action')}"
            )
        else:
            diag = data.get("diagnostics", {})
            summary = (
                f"### ⚙️ GitHub Actions Workflow Pipeline Analysis\n\n"
                f"| Pipeline Parameter | Details |\n"
                f"| :--- | :--- |\n"
                f"| **Target Step** | `{diag.get('step_name')}` |\n"
                f"| **Workflow Profile** | `{data.get('profile')}` |\n"
                f"| **Runner OS** | `{diag.get('runner_os')}` |\n"
                f"| **Detected Error Details** | *{diag.get('error_details')}* |\n\n"
                f"#### 🔧 Remediation Plan Details:\n"
                f"> {diag.get('suggested_action')}\n\n"
                f"*Tips: You can enable verbose debugging on your GitHub repository by setting the repository secret `ACTIONS_RUNNER_DEBUG=true`.*"
            )
            return summary
