"""
Terraform Agent implementation.
"""
import logging
from typing import TYPE_CHECKING

from app.services.plugin_manager import IAgent
from tools import TerraformAuditor

if TYPE_CHECKING:
    from app.core.slm.service import SLMService

logger = logging.getLogger(__name__)

class TerraformAgent(IAgent):
    """
    Terraform Agent - Validates cloud provisioning configurations.
    """

    def __init__(self):
        self.name = "terraform_agent"
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
                    ("terraform_agent", "Terraform plans, infrastructure validation, HCL code audits, and secure cloud guardrails"),
                    ("log_analysis_agent", "System log analysis, server exceptions, raw log formats, pattern detection"),
                ]
            )
            if result == "terraform_agent":
                return True

        tf_keywords = ["terraform", "tf plan", "hcl", "infrastructure-as-code", "security group", "guardrail"]
        normalized = intent.lower()
        return any(kw in normalized for kw in tf_keywords)

    async def plan(self, intent: str, context: dict) -> dict:
        """Decompose intent into auditing or generation tasks."""
        logger.info(f"Terraform Agent planning for: '{intent}'")
        
        normalized = intent.lower()
        is_generation = any(kw in normalized for kw in ["generate", "create", "write", "setup", "make", "template", "code"])
        code_text = context.get("code_text") or context.get("uploaded_text") or ""
        validation_requested = any(kw in normalized for kw in ["validate", "review", "audit", "check", "scan"])
        is_validation = bool(context.get("uploaded_files")) or (bool(code_text.strip()) and validation_requested)

        if is_validation and not is_generation:
            action = "validate"
            steps = [
                "Load Terraform HCL or plan content from pasted text or uploaded files",
                "Evaluate public ingress, encryption, tag completeness, and secret hygiene guardrails",
                "Classify compliance severity",
                "Return remediation mapped to enterprise IaC controls"
            ]
        elif is_generation:
            action = "generate"
            steps = [
                "Select compliant cloud resource blueprints",
                "Apply strict tagging compliance criteria",
                "Lock down firewall ingress port guardrails",
                "Format HCL code blocks"
            ]
        else:
            action = "audit"
            steps = [
                "Parse plan attributes",
                "Evaluate rules block in config.yaml",
                "Trigger static security group audits",
                "Examine resource tags completeness"
            ]

        return {
            "status": "success",
            "steps": steps,
            "context": {
                "action": action,
                "query": intent,
                "code_text": code_text,
                "uploaded_files": context.get("uploaded_files", []),
            }
        }

    async def execute(self, plan: dict) -> dict:
        """Execute the plan rules or code generation."""
        if plan.get("status") != "success":
            return {"status": "failed", "error": "Invalid plan input"}

        ctx = plan.get("context", {})
        action = ctx.get("action", "audit")
        query = ctx.get("query", "")

        if action == "generate":
            import re
            
            # 1. Fallback regex parsing logic
            params = {}
            normalized = query.lower()
            
            # Extract provider
            if "azure" in normalized or "azurerm" in normalized:
                params["provider"] = "azure"
            elif "aws" in normalized:
                params["provider"] = "aws"

            # Extract CIDR
            cidr_match = re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}\b', query)
            if cidr_match:
                params["cidr_block"] = cidr_match.group(0)
                
            # Extract environment
            for env in ["development", "production", "staging", "testing", "dev", "prod"]:
                if env in normalized:
                    params["environment"] = env
                    break
                    
            # Extract instance type
            instance_match = re.search(r'\b[a-z0-9]+\.[a-z0-9]+\b', normalized)
            if instance_match and instance_match.group(0) not in ["aws_instance", "var.ami_id"]:
                params["instance_type"] = instance_match.group(0)
                
            # Extract AMI ID
            ami_match = re.search(r'\bami-[a-f0-9]+\b', normalized)
            if ami_match:
                params["ami_id"] = ami_match.group(0)

            # Extract Owner
            owner_match = re.search(r'owner\s*(?:is|=|\s+by\s+)\s*([a-zA-Z0-9_-]+)', normalized)
            if owner_match:
                params["owner"] = owner_match.group(1)
            elif "by " in normalized:
                owner_by_match = re.search(r'by\s+([a-zA-Z0-9_-]+)', normalized)
                if owner_by_match:
                    params["owner"] = owner_by_match.group(1)

            # 2. SLM-based extraction (if available)
            if self._slm_service is not None and self._slm_service.available:
                prompt = (
                    "You are an enterprise cloud architect extraction assistant.\n"
                    "Analyze the user's request and extract Terraform parameters. "
                    "Output ONLY a JSON block with keys 'provider', 'resource_type', 'instance_type', 'ami_id', 'cidr_block', 'environment', 'owner'. "
                    "If a value is not mentioned, use null.\n\n"
                    f"Request: {query}\n"
                    "JSON:\n"
                )
                try:
                    slm_result = await self._slm_service.generate_text(
                        prompt,
                        max_tokens=128,
                        temperature=0.0,
                        stop=["<|end|>", "\n\n"]
                    )
                    if slm_result:
                        import json
                        json_start = slm_result.find("{")
                        json_end = slm_result.rfind("}")
                        if json_start != -1 and json_end != -1:
                            slm_params = json.loads(slm_result[json_start:json_end+1])
                            for k, v in slm_params.items():
                                if v is not None:
                                    params[k] = v
                except Exception as e:
                    logger.error(f"Failed to extract parameters via SLM: {e}")

            # 3. Generate HCL with parameters
            code = TerraformAuditor.generate_hcl(query, params)
            return {
                "status": "success",
                "result": {
                    "action": "generate",
                    "code": code
                }
            }
        elif action == "validate":
            code_text = ctx.get("code_text", "")
            validation = TerraformAuditor.validate_hcl(code_text)
            audit_results = TerraformAuditor.audit_plan(code_text or query)
            return {
                "status": "success",
                "result": {
                    "action": "validate",
                    "validation": validation,
                    "audit": audit_results,
                    "uploaded_files": ctx.get("uploaded_files", []),
                }
            }
        else:
            audit_results = TerraformAuditor.audit_plan(query)
            return {
                "status": "success",
                "result": {
                    "action": "audit",
                    "audit": audit_results
                }
            }

    async def summarize(self, result: dict) -> str:
        """Summarize results in beautiful Markdown."""
        if result.get("status") != "success":
            return "Failed to execute Terraform planning task."

        data = result.get("result", {})
        action = data.get("action", "audit")

        if action == "generate":
            code = data.get("code", "")
            summary = (
                f"### 🛠️ Terraform Infrastructure HCL Code Generator\n\n"
                f"I have generated compliant, highly secure Terraform HCL resources containing mandatory tags and encrypted storage guardrails:\n\n"
                f"```hcl\n"
                f"{code}"
                f"```\n\n"
                f"#### 🔒 Compliant Features Included:\n"
                f"- **Mandatory tagging** details: `'Environment'` and `'Owner'` values are pre-assigned.\n"
                f"- **Security default state**: Root storage blocks have `encrypted = true` enabled."
            )
            return summary
        elif action == "validate":
            validation = data.get("validation", {})
            audit = data.get("audit", {})
            files = data.get("uploaded_files", [])
            findings = validation.get("findings", [])
            findings_md = "\n".join(
                f"- **{item.get('severity', 'info').upper()}** `{item.get('rule')}`: {item.get('message')} Remediation: {item.get('remediation')}"
                for item in findings
            ) or "- No Terraform guardrail violations detected."
            file_note = ", ".join(files) if files else "pasted chat text"
            return (
                "### Terraform HCL / Plan Validation\n\n"
                f"**Input source**: {file_note}\n\n"
                f"**Status**: `{validation.get('status')}` with `{validation.get('finding_count', 0)}` finding(s)\n\n"
                "#### Guardrail Findings\n"
                f"{findings_md}\n\n"
                "#### Compliance Classifier\n"
                f"- Resource: `{audit.get('resource')}`\n"
                f"- Type: `{audit.get('type')}`\n"
                f"- Status: **{audit.get('compliance_status')}**\n"
                f"- Remediation: {audit.get('remediation')}"
            )
        else:
            audit = data.get("audit", {})
            violations_md = ""
            violations = audit.get("violations", [])
            if violations:
                violations_md = "\n".join(f"- ❌ **Violation**: {v}" for v in violations)
            else:
                violations_md = "- 🌟 **No compliance violations detected**."

            summary = (
                f"### 🛠️ Terraform Infrastructure-as-Code Audit\n\n"
                f"| Resource ID | Component Type | Status Level |\n"
                f"| :--- | :--- | :--- |\n"
                f"| `{audit.get('resource')}` | `{audit.get('type')}` | **{audit.get('compliance_status')}** |\n\n"
                f"#### Compliance Findings:\n"
                f"{violations_md}\n\n"
                f"#### 🔧 Recommended Mitigation Steps:\n"
                f"> {audit.get('remediation')}\n"
            )
            return summary
