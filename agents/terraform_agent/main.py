"""
Terraform Agent implementation.
"""
import json
import logging
import re
from typing import TYPE_CHECKING, Any

from app.services.plugin_manager import IAgent
from tools import TerraformAuditor, GENERIC_RESOURCE_TYPES

if TYPE_CHECKING:
    from app.core.slm.service import SLMService

logger = logging.getLogger(__name__)

GENERATION_KEYWORDS = {
    "build",
    "code",
    "create",
    "generate",
    "make",
    "provision",
    "scaffold",
    "setup",
    "template",
    "write",
}

TERRAFORM_KEYWORDS = {
    "aws_",
    "azurerm",
    "ec2",
    "gcp",
    "google_",
    "guardrail",
    "hcl",
    "helm",
    "infrastructure-as-code",
    "iac",
    "instance",
    "kubernetes",
    "kubernetes_",
    "module ",
    "provider ",
    "random_",
    "resource group",
    "security group",
    "subnet",
    "terraform",
    "tf plan",
    "vault_",
    "vnet",
    "vpc",
}

VALIDATION_KEYWORDS = {"audit", "check", "review", "scan", "validate"}

TERRAFORM_BLOCK_PATTERN = re.compile(r'\b(resource|module|data|provider|variable|output)\s+"', re.IGNORECASE)

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
        normalized = intent.lower()
        if self._looks_like_terraform_request(normalized):
            return True

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

        return False

    async def plan(self, intent: str, context: dict) -> dict:
        """Decompose intent into auditing or generation tasks."""
        logger.info(f"Terraform Agent planning for: '{intent}'")
        
        normalized = intent.lower()
        is_generation = self._is_generation_request(normalized)
        code_text = context.get("code_text") or context.get("uploaded_text") or ""
        validation_requested = any(kw in normalized for kw in VALIDATION_KEYWORDS)
        pasted_or_uploaded_hcl = bool(code_text.strip()) and bool(TERRAFORM_BLOCK_PATTERN.search(code_text))
        is_validation = bool(context.get("uploaded_files")) or (pasted_or_uploaded_hcl and validation_requested)

        if is_validation:
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
            params = self._extract_parameters_with_rules(query)
            params.update(await self._extract_parameters_with_slm(query))

            code = TerraformAuditor.generate_hcl(query, params)
            validation = TerraformAuditor.validate_hcl(code)
            return {
                "status": "success",
                "result": {
                    "action": "generate",
                    "code": code,
                    "parameters": params,
                    "validation": validation,
                    "generator": "deterministic_template",
                    "query": query,
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
                    "query": query,
                }
            }
        else:
            audit_results = TerraformAuditor.audit_plan(query)
            return {
                "status": "success",
                "result": {
                    "action": "audit",
                    "audit": audit_results,
                    "query": query,
                }
            }

    async def summarize(self, result: dict) -> str:
        """Summarize results in beautiful Markdown."""
        if result.get("status") != "success":
            return "Failed to execute Terraform planning task."

        data = result.get("result", {})
        action = data.get("action", "audit")
        query = data.get("query", "")

        if action == "generate":
            code = data.get("code", "")
            validation = data.get("validation", {})
            params = data.get("parameters", {})
            provider = params.get("provider") or "AWS"
            resource_type = params.get("resource_type") or "Resource"
            
            provider_str = "Azure" if "azure" in str(provider).lower() else "AWS" if "aws" in str(provider).lower() else str(provider).strip().upper()
            resource_str = str(resource_type).strip().replace("_", " ").title()
            if resource_str == "Vpc":
                resource_str = "VPC / VNet"
            elif resource_str == "Instance":
                resource_str = "Compute Instance"

            features = []
            if "tags =" in code or "tags" in code:
                env_val = params.get("environment") or "Production"
                owner_val = params.get("owner") or "Platform_Ops"
                features.append(f"**Mandatory tagging**: Pre-assigned standard company tags (e.g. `Environment = \"{env_val.capitalize()}\"`, `Owner = \"{owner_val}\"`).")
                
            if provider_str == "Azure":
                if "storage" in str(resource_type).lower():
                    features.append("**Secure Storage Defaults**: Configured with strict network rules (`public_network_access_enabled = false`), versioning, and minimal TLS version 1.2.")
                if "webapp" in str(resource_type).lower():
                    features.append("**HTTPS/TLS Enforcement**: Explicitly enabled `https_only = true` and disabled unencrypted FTP deployments (`ftps_state = \"Disabled\"`).")
                if "hub" in query.lower() and "spoke" in query.lower():
                    features.append("**Network Topology Security**: Peerings between Hub and Spoke virtual networks are bidirectionally configured to ensure secure routing boundaries.")
            elif provider_str == "AWS":
                if resource_type == "instance":
                    features.append("**EBS Volume Encryption**: Configured compute instance storage with `encrypted = true` under root block devices.")
                if resource_type == "vpc":
                    features.append("**DNS & Telemetry Logging**: DNS support is enabled alongside AWS VPC Flow Logs routed to CloudWatch Logs for auditability.")
            elif provider_str == "NUTANIX":
                if resource_type == "instance":
                    features.append("**Hyperconverged VM Metrics**: Defined virtual machine socket count, memory footprint, and network bridges mapped to designated subnets.")
            elif provider_str == "VSPHERE":
                if resource_type == "instance":
                    features.append("**Datastore and Pool Allocations**: Managed guest virtualization profiles mapped to corporate resource pools and thin-provisioned datastores.")
            elif provider_str == "KUBERNETES":
                features.append("**Declarative Namespace**: Scaffolds isolated administrative Kubernetes namespaces for workload isolation.")
            elif provider_str == "VAULT":
                features.append("**Secret Encryption**: Defined secure key-value secret configurations on HashiCorp Vault storage engine.")
            elif provider_str == "RANDOM":
                features.append("**Cryptographic Generation**: Scaffolds cryptographically secure random password resource blocks.")
            elif provider_str == "LOCAL":
                features.append("**Declarative File Output**: Scaffolds secure local file configurations with strict permissions.")
                
            if not features:
                features.append("**Standards-Compliant Blueprint**: Standard resource configuration conforming to base corporate architecture guidelines.")
                
            status_text = "Compliant" if validation.get('status') == 'pass' else "Violations Detected"
            features.append(f"**Static Guardrails Scan**: Verified against company standards policy engine (Status: `{status_text}`).")
            
            features_md = "\n".join(f"- {f}" for f in features)

            summary = (
                f"### 🛠️ {provider_str} {resource_str} Terraform HCL Generator\n\n"
                f"I have generated compliant, highly secure Terraform HCL resources containing mandatory tags and encrypted storage guardrails:\n\n"
                f"```hcl\n"
                f"{code}"
                f"```\n\n"
                f"#### Compliant Features Included:\n"
                f"{features_md}"
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
                "### 🛡️ Terraform HCL / Plan Validation\n\n"
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
                violations_md = "\n".join(f"- **Violation**: {v}" for v in violations)
            else:
                violations_md = "- **No compliance violations detected**."

            summary = (
                f"### 🛡️ Terraform Infrastructure-as-Code Audit\n\n"
                f"| Resource ID | Component Type | Status Level |\n"
                f"| :--- | :--- | :--- |\n"
                f"| `{audit.get('resource')}` | `{audit.get('type')}` | **{audit.get('compliance_status')}** |\n\n"
                f"#### Compliance Findings:\n"
                f"{violations_md}\n\n"
                f"#### 🔧 Remediation Plan Details:\n"
                f"> {audit.get('remediation')}\n"
            )
            return summary

    def _looks_like_terraform_request(self, normalized: str) -> bool:
        """Route Terraform/IaC prompts without depending on the SLM."""
        return any(kw in normalized for kw in TERRAFORM_KEYWORDS)

    def _is_generation_request(self, normalized: str) -> bool:
        """Identify Terraform code generation prompts."""
        return any(kw in normalized for kw in GENERATION_KEYWORDS)

    def _extract_parameters_with_rules(self, query: str) -> dict[str, str]:
        """Extract safe template parameters using deterministic rules."""
        params: dict[str, str] = {}
        normalized = query.lower()

        # Check if query contains an explicit resource that is mapped to a generic type (e.g. google_sql_database_instance)
        found_generic = False
        for (prov, rtype), resource_name in GENERIC_RESOURCE_TYPES.items():
            if re.search(rf"\b{resource_name}\b", normalized):
                params["provider"] = prov
                params["resource_type"] = rtype
                found_generic = True
                break

        has_explicit = found_generic
        if not has_explicit:
            # Check for explicit provider resource first (e.g. azurerm_storage_sync, aws_s3_bucket)
            prefixed_resource = re.search(r"\b([a-z][a-z0-9]*)_([a-z0-9_]+)\b", normalized)
            if prefixed_resource:
                prefix = prefixed_resource.group(1)
                known_providers = {
                    "aws", "amazon", "azure", "azurerm", "google", "gcp", "kubernetes", "k8s",
                    "helm", "vault", "random", "local", "null", "nutanix", "vsphere", "vmware",
                    "activedirectory", "ad", "appd", "archive", "awslambda", "awsx", "azure-preview", 
                    "azuread", "azurecaf", "azurestack", "bless", "brightbox", "circleci", "circonus", 
                    "cloudflare", "cloudinit", "confluentcloud", "consul", "ct", "digitalocean", 
                    "dmsnitch", "dns", "ecloud", "eksctl", "elasticsearch", "exoscale", "external", 
                    "fastly", "fortios", "freeipa", "git", "google-beta", "graylog", "gsuite", 
                    "hcloud", "hdns", "helmfile", "heroku", "http", "idm", "infoblox", "javascript", 
                    "jetstream", "jsonnet", "kafka", "kafka-connect", "kubectl", "launchdarkly", 
                    "linode", "matchbox", "msgraph", "ncloud", "netapp-gcp", "newrelic", "njalla", 
                    "nomad", "onelogin", "openshift", "opsgenie", "orion", "outlook", "pass", 
                    "petstore", "pingaccess", "pingfederate", "pnap", "postgresql", "puppetca", 
                    "puppetdb", "pypi", "rancher2", "rke", "rollbar", "safedns", "sakuracloud", 
                    "scaffolding", "sdm", "sentry", "shell", "signalfx", "sops", "stackpath", 
                    "statuspage", "sumologic", "teamcity", "template", "tencentcloud", "testing", 
                    "tfe", "time", "tls", "transip", "transloadit", "triton", "turbot", "ucloud", 
                    "unifi", "vaultutility", "vinyldns", "vmworkstation", "vultr", "windns"
                }
                if prefix in known_providers:
                    provider_map = {
                        "amazon": "aws",
                        "azure": "azurerm",
                        "gcp": "google",
                        "k8s": "kubernetes",
                        "vmware": "vsphere"
                    }
                    params["provider"] = provider_map.get(prefix, prefix)
                    params["resource_type"] = prefixed_resource.group(2).strip("_")
                    has_explicit = True

        if not has_explicit:
            if "azure" in normalized or "azurerm" in normalized:
                params["provider"] = "azurerm"
            elif "aws" in normalized or "ec2" in normalized or "vpc" in normalized:
                params["provider"] = "aws"
            elif "google" in normalized or "gcp" in normalized or "google_" in normalized:
                params["provider"] = "google"
            elif "kubernetes" in normalized or "k8s" in normalized or "kubernetes_" in normalized:
                params["provider"] = "kubernetes"
            elif "helm" in normalized:
                params["provider"] = "helm"
            elif "vault" in normalized or "vault_" in normalized:
                params["provider"] = "vault"
            elif "random_" in normalized or "random provider" in normalized:
                params["provider"] = "random"
            elif "local_" in normalized or "local provider" in normalized:
                params["provider"] = "local"
            elif "null_" in normalized or "null provider" in normalized:
                params["provider"] = "null"
            elif "nutanix" in normalized:
                params["provider"] = "nutanix"
            elif "vmware" in normalized or "vsphere" in normalized or "vcenter" in normalized:
                params["provider"] = "vsphere"

            wants_storage = any(term in normalized for term in ["bucket", "s3", "storage", "storage account"])
            wants_webapp = any(term in normalized for term in ["webapp", "web app", "app service"])
            if wants_storage and wants_webapp:
                params["resource_type"] = "storage_webapp"
            elif wants_storage:
                params["resource_type"] = "storage"
            elif wants_webapp:
                params["resource_type"] = "webapp"
            elif any(term in normalized for term in ["database", "db", "postgres", "postgresql", "rds", "sql"]):
                params["resource_type"] = "database"
            elif any(term in normalized for term in ["vpc", "vnet", "network", "subnet", "resource group"]):
                params["resource_type"] = "vpc"
            elif any(term in normalized for term in ["ec2", "instance", "server", "vm", "virtual machine"]):
                params["resource_type"] = "instance"
            elif any(term in normalized for term in ["firewall", "network security group", "nsg", "security group"]):
                params["resource_type"] = "security_group"
            elif "deployment" in normalized:
                params["resource_type"] = "deployment"
            elif "namespace" in normalized:
                params["resource_type"] = "namespace"
            elif "helm release" in normalized or "chart" in normalized:
                params["resource_type"] = "release"
            elif "secret" in normalized:
                params["resource_type"] = "secret"
            else:
                explicit_resource = re.search(r"\b[a-z][a-z0-9]*_([a-z0-9_]+)\b", normalized)
                if explicit_resource:
                    params["resource_type"] = explicit_resource.group(1).strip("_")

        cidr_match = re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}\b", query)
        if cidr_match:
            params["cidr_block"] = cidr_match.group(0)

        for env in ["development", "production", "staging", "testing", "dev", "prod"]:
            if re.search(rf"\b{env}\b", normalized):
                params["environment"] = env
                break

        instance_match = re.search(r"\b(?:[a-z]\d|t\d|m\d|c\d|r\d|standard_)[a-z0-9_.-]*\b", normalized)
        if instance_match and instance_match.group(0) not in {"aws_instance", "s3", "var.ami_id"}:
            params["instance_type"] = instance_match.group(0)

        ami_match = re.search(r"\bami-[a-f0-9]+\b", normalized)
        if ami_match:
            params["ami_id"] = ami_match.group(0)

        owner_match = re.search(r"\bowner\s*(?:is|=|:)\s*([a-zA-Z0-9_-]+)", query, re.IGNORECASE)
        if owner_match:
            params["owner"] = owner_match.group(1).lower()
        else:
            owner_by_match = re.search(r"\b(?:owned\s+)?by\s+([a-zA-Z0-9_-]+)", query, re.IGNORECASE)
            if owner_by_match:
                params["owner"] = owner_by_match.group(1).lower()

        return params

    async def _extract_parameters_with_slm(self, query: str) -> dict[str, str]:
        """
        Use the local SLM only for parameter extraction.

        Generated Terraform still comes from approved Python templates.
        """
        if self._slm_service is None or not self._slm_service.available:
            return {}

        system_prompt = (
            "You extract Terraform generation parameters for a deterministic template engine. "
            "Return only compact JSON with keys: provider, resource_type, instance_type, "
            "ami_id, cidr_block, environment, owner. "
            "Allowed provider values include aws, azurerm, google, kubernetes, helm, vault, random, local, or null. "
            "Allowed resource_type values include vpc, instance, storage, webapp, storage_webapp, database, "
            "security_group, deployment, namespace, release, secret, file, password, or explicit provider resource suffixes. "
            "Use null for unknown values. Do not write Terraform code."
        )
        prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{query}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        try:
            slm_result = await self._slm_service.generate_text(
                prompt,
                max_tokens=180,
                temperature=0.0,
                stop=["<|im_end|>", "<|endoftext|>"],
            )
            return self._parse_slm_parameter_json(slm_result)
        except Exception as exc:
            logger.error(f"Failed to extract Terraform parameters via SLM: {exc}")
            return {}

    def _parse_slm_parameter_json(self, text: str) -> dict[str, str]:
        """Parse and constrain the SLM's JSON extraction response."""
        if not text:
            return {}

        json_text = text.strip()
        if json_text.startswith("```"):
            json_text = re.sub(r"^```(?:json)?", "", json_text, flags=re.IGNORECASE).strip()
            json_text = re.sub(r"```$", "", json_text).strip()

        json_start = json_text.find("{")
        json_end = json_text.rfind("}")
        if json_start == -1 or json_end == -1:
            return {}

        allowed_keys = {
            "provider",
            "resource_type",
            "instance_type",
            "ami_id",
            "cidr_block",
            "environment",
            "owner",
        }
        raw_params: dict[str, Any] = json.loads(json_text[json_start:json_end + 1])
        params: dict[str, str] = {}
        for key, value in raw_params.items():
            if key not in allowed_keys or value is None:
                continue
            text_value = str(value).strip()
            if text_value in {"", "null", "None"}:
                continue
            params[key] = text_value
        return params
