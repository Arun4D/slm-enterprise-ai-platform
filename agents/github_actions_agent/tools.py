import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

MOCK_WORKFLOW_LOGS = {
    "build_frontend": {
        "step_name": "npm run build",
        "error_details": "Error: Process completed with exit code 1. JavaScript heap out of memory",
        "runner_os": "ubuntu-latest",
        "suggested_action": "Increase node heap size by configuring NODE_OPTIONS='--max-old-space-size=4096' environment variable in the workflow step.",
    },
    "deploy_image": {
        "step_name": "docker push",
        "error_details": "denied: requested access to the resource is denied. Unauthorized",
        "runner_os": "ubuntu-latest",
        "suggested_action": "Check docker login configurations. Ensure secrets.DOCKER_USERNAME and secrets.DOCKER_PASSWORD are correctly loaded and passed to docker/login-action.",
    },
    "run_tests": {
        "step_name": "pytest tests/",
        "error_details": "ModuleNotFoundError: No module named 'pydantic'",
        "runner_os": "ubuntu-latest",
        "suggested_action": "Pydantic module is missing. Add dependencies installation step `pip install -r requirements.txt` prior to executing pytest.",
    }
}

class GitHubActionsParser:
    """Parses GitHub Actions workflows/logs and suggests deterministic repairs."""

    @staticmethod
    def parse_workflow_failure(log_text: str) -> dict[str, Any]:
        """Parse log text for common errors and map remediation suggestions."""
        log_lower = log_text.lower()
        
        # Check against mock profiles first for standard offline demos
        for key, mock_data in MOCK_WORKFLOW_LOGS.items():
            if key in log_lower or mock_data["error_details"].lower() in log_lower:
                return mock_data

        # Fallback heuristic parser
        if "out of memory" in log_lower or "heap" in log_lower:
            return {
                "step_name": "Build process",
                "error_details": "Out of memory error detected in process heap allocations.",
                "runner_os": "unknown",
                "suggested_action": "Increase heap limits. Configure NODE_OPTIONS='--max-old-space-size=4096' or corresponding JVM parameters.",
            }
        elif "denied" in log_lower or "unauthorized" in log_lower or "login" in log_lower:
            return {
                "step_name": "Outbound authentication",
                "error_details": "Access denied or authentication credentials rejected.",
                "runner_os": "unknown",
                "suggested_action": "Verify credentials, API tokens, or secrets configurations. Ensure correct registry login actions exist.",
            }
        else:
            return {
                "step_name": "General Execution",
                "error_details": "Unknown non-zero exit code detected in pipeline runner process logs.",
                "runner_os": "unknown",
                "suggested_action": "Enable debug logging by configuring RUNNER_DEBUG=true to inspect detailed step trace outputs.",
            }

    @staticmethod
    def validate_workflow(workflow_text: str) -> dict[str, Any]:
        """Validate pasted or uploaded GitHub Actions YAML using offline guardrails."""
        findings: list[dict[str, str]] = []
        normalized = workflow_text.lower()

        if "on:" not in normalized:
            findings.append({
                "severity": "high",
                "rule": "missing_trigger",
                "message": "Workflow does not define an `on:` trigger.",
                "remediation": "Add explicit push, pull_request, workflow_dispatch, or scheduled triggers.",
            })
        if "jobs:" not in normalized or "runs-on:" not in normalized:
            findings.append({
                "severity": "high",
                "rule": "missing_job_runner",
                "message": "Workflow does not define jobs with a runner.",
                "remediation": "Add at least one job with `runs-on: ubuntu-latest` or an approved self-hosted label.",
            })
        if "actions/checkout@" not in normalized:
            findings.append({
                "severity": "medium",
                "rule": "missing_checkout",
                "message": "Workflow does not checkout repository content before build steps.",
                "remediation": "Add `uses: actions/checkout@v4` as the first job step.",
            })
        if re.search(r"uses:\s*[^@\n]+@(main|master|latest)\b", workflow_text, re.IGNORECASE):
            findings.append({
                "severity": "high",
                "rule": "unpinned_action_ref",
                "message": "Action references use mutable branches such as main/master/latest.",
                "remediation": "Pin actions to a version tag or immutable commit SHA.",
            })
        if "pull_request_target:" in normalized:
            findings.append({
                "severity": "critical",
                "rule": "pull_request_target_risk",
                "message": "`pull_request_target` can expose privileged tokens to untrusted code.",
                "remediation": "Use `pull_request` unless elevated repository permissions are explicitly required.",
            })
        if "permissions:" not in normalized:
            findings.append({
                "severity": "medium",
                "rule": "missing_permissions",
                "message": "Workflow does not set least-privilege GitHub token permissions.",
                "remediation": "Add a top-level `permissions:` block, usually `contents: read` by default.",
            })
        if re.search(r"(password|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}", workflow_text, re.IGNORECASE):
            findings.append({
                "severity": "critical",
                "rule": "possible_inline_secret",
                "message": "Potential inline credential detected in workflow content.",
                "remediation": "Move credentials to GitHub Actions secrets or an approved internal vault integration.",
            })
        if "npm install" in normalized:
            findings.append({
                "severity": "low",
                "rule": "non_reproducible_npm_install",
                "message": "`npm install` is less reproducible in CI than `npm ci`.",
                "remediation": "Use `npm ci` when package-lock.json is committed.",
            })
        if "setup-node" in normalized and "cache:" not in normalized:
            findings.append({
                "severity": "low",
                "rule": "missing_node_cache",
                "message": "Node workflow does not configure dependency caching.",
                "remediation": "Set `cache: npm` or the package manager cache under `actions/setup-node`.",
            })
        if "setup-python" in normalized and "cache:" not in normalized:
            findings.append({
                "severity": "low",
                "rule": "missing_python_cache",
                "message": "Python workflow does not configure dependency caching.",
                "remediation": "Set `cache: pip` under `actions/setup-python`.",
            })

        status = "pass" if not findings else "fail"
        return {
            "status": status,
            "findings": findings,
            "finding_count": len(findings),
            "line_count": len(workflow_text.splitlines()),
        }

    @staticmethod
    def generate_workflow(query: str) -> str:
        """Generate approved workflow templates without external LLM execution."""
        normalized = query.lower()
        if "python" in normalized:
            return (
                "name: Python Application CI\n\n"
                "on:\n"
                "  push:\n"
                "    branches: [main]\n"
                "  pull_request:\n"
                "    branches: [main]\n"
                "  workflow_dispatch:\n\n"
                "permissions:\n"
                "  contents: read\n\n"
                "jobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    timeout-minutes: 20\n"
                "    steps:\n"
                "      - name: Checkout repository\n"
                "        uses: actions/checkout@v4\n"
                "      - name: Set up Python\n"
                "        uses: actions/setup-python@v5\n"
                "        with:\n"
                "          python-version: '3.11'\n"
                "          cache: pip\n"
                "      - name: Install dependencies\n"
                "        run: python -m pip install --upgrade pip && pip install -r requirements.txt\n"
                "      - name: Run tests\n"
                "        run: pytest --maxfail=1 --disable-warnings\n"
            )
        return (
            "name: Node.js CI\n\n"
            "on:\n"
            "  push:\n"
            "    branches: [main]\n"
            "  pull_request:\n"
            "    branches: [main]\n"
            "  workflow_dispatch:\n\n"
            "permissions:\n"
            "  contents: read\n\n"
            "jobs:\n"
            "  build:\n"
            "    runs-on: ubuntu-latest\n"
            "    timeout-minutes: 20\n"
            "    env:\n"
            "      NODE_OPTIONS: --max-old-space-size=4096\n"
            "    steps:\n"
            "      - name: Checkout repository\n"
            "        uses: actions/checkout@v4\n"
            "      - name: Set up Node.js\n"
            "        uses: actions/setup-node@v4\n"
            "        with:\n"
            "          node-version: '20'\n"
            "          cache: npm\n"
            "      - name: Install packages\n"
            "        run: npm ci\n"
            "      - name: Build\n"
            "        run: npm run build\n"
            "      - name: Test\n"
            "        run: npm test\n"
        )
