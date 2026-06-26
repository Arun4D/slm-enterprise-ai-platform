import logging
import os
import re
from typing import Any
import yaml

logger = logging.getLogger(__name__)

CONFIG = {}
try:
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            CONFIG = yaml.safe_load(f) or {}
except Exception as e:
    logger.error(f"Failed to load config.yaml in terraform_agent tools: {e}")

PROVIDER_REQUIREMENTS = {
    "aws": {"source": "hashicorp/aws", "version": "~> 5.0"},
    "azurerm": {"source": "hashicorp/azurerm", "version": "~> 3.0"},
    "google": {"source": "hashicorp/google", "version": "~> 5.0"},
    "kubernetes": {"source": "hashicorp/kubernetes", "version": "~> 2.0"},
    "helm": {"source": "hashicorp/helm", "version": "~> 2.0"},
    "vault": {"source": "hashicorp/vault", "version": "~> 4.0"},
    "random": {"source": "hashicorp/random", "version": "~> 3.0"},
    "local": {"source": "hashicorp/local", "version": "~> 2.0"},
    "null": {"source": "hashicorp/null", "version": "~> 3.0"},
    "nutanix": {"source": "nutanix/nutanix", "version": "~> 1.9.0"},
    "vsphere": {"source": "hashicorp/vsphere", "version": "~> 2.6.0"},
}

PROVIDER_ALIASES = {
    "amazon": "aws",
    "aws": "aws",
    "azure": "azurerm",
    "azurerm": "azurerm",
    "gcp": "google",
    "google": "google",
    "google cloud": "google",
    "helm": "helm",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "local": "local",
    "null": "null",
    "random": "random",
    "vault": "vault",
    "nutanix": "nutanix",
    "vsphere": "vsphere",
    "vmware": "vsphere",
}

KNOWN_PROVIDERS = {
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


RESOURCE_HINTS = {
    "storage_webapp": ["storage account and azure webapp", "storage account and webapp", "storage and webapp"],
    "storage": ["bucket", "blob", "s3", "storage", "storage account"],
    "webapp": ["app service", "web app", "webapp"],
    "vpc": ["network", "subnet", "virtual network", "vnet", "vpc"],
    "database": ["database", "db", "postgres", "postgresql", "rds", "sql"],
    "instance": ["compute", "ec2", "instance", "server", "virtual machine", "vm"],
    "security_group": ["firewall", "network security group", "nsg", "security group"],
    "deployment": ["deployment"],
    "namespace": ["namespace"],
    "release": ["chart", "helm release", "release"],
    "secret": ["secret"],
    "file": ["file"],
    "password": ["password"],
}

GENERIC_RESOURCE_TYPES = {
    ("aws", "storage"): "aws_s3_bucket",
    ("aws", "database"): "aws_db_instance",
    ("aws", "security_group"): "aws_security_group",
    ("azurerm", "database"): "azurerm_postgresql_flexible_server",
    ("azurerm", "security_group"): "azurerm_network_security_group",
    ("google", "storage"): "google_storage_bucket",
    ("google", "instance"): "google_compute_instance",
    ("google", "vpc"): "google_compute_network",
    ("google", "database"): "google_sql_database_instance",
    ("kubernetes", "deployment"): "kubernetes_deployment_v1",
    ("kubernetes", "namespace"): "kubernetes_namespace_v1",
    ("helm", "release"): "helm_release",
    ("vault", "secret"): "vault_kv_secret_v2",
    ("random", "password"): "random_password",
    ("local", "file"): "local_file",
    ("null", "resource"): "null_resource",
    ("nutanix", "instance"): "nutanix_virtual_machine",
    ("vsphere", "instance"): "vsphere_virtual_machine",
}

REQUIRED_FIELDS_REGISTRY = {
    "aws_datasync_task": (
        "  destination_location_arn = \"arn:aws:datasync:us-east-1:123456789012:location/loc-destination\"\n"
        "  source_location_arn      = \"arn:aws:datasync:us-east-1:123456789012:location/loc-source\"\n"
        "  name                     = \"example-datasync-task\"\n"
    ),
    "azurerm_storage_sync": (
        "  name                = \"example-storage-sync\"\n"
        "  resource_group_name = \"example-resources\"\n"
        "  location            = \"West Europe\"\n"
    ),
    "aws_datasync_location_s3": (
        "  s3_bucket_arn = \"arn:aws:s3:::example-bucket\"\n"
        "  subdirectory  = \"/prefix\"\n"
        "  s3_config {\n"
        "    bucket_access_role_arn = \"arn:aws:iam::123456789012:role/datasync-access-role\"\n"
        "  }\n"
    ),
    "aws_datasync_location_smb": (
        "  server_hostname = \"nas.example.com\"\n"
        "  subdirectory    = \"/share\"\n"
        "  user            = \"username\"\n"
        "  password        = \"secretpassword\"\n"
    ),
}

class TerraformAuditor:
    """Audits Terraform plan/HCL data against static security guardrails."""

    @staticmethod
    def audit_plan(plan_text: str) -> dict:
        """Parse plan query and return compliance audits."""
        plan_lower = plan_text.lower()
        violations = []
        
        resource = "aws_vpc.main"
        resource_type = "vpc"
        
        resource_match = re.search(r'resource\s+"([^"]+)"\s+"([^"]+)"', plan_text)
        if resource_match:
            resource_type = resource_match.group(1)
            resource = f"{resource_type}.{resource_match.group(2)}"
        else:
            if "security_group" in plan_lower or "sg" in plan_lower or "ingress" in plan_lower or "port" in plan_lower:
                resource = "aws_security_group.allow_all"
                resource_type = "security_group"
            elif "instance" in plan_lower or "ec2" in plan_lower or "vm" in plan_lower:
                resource = "aws_instance.web"
                resource_type = "ec2_instance"
            elif "s3" in plan_lower or "bucket" in plan_lower or "storage" in plan_lower:
                resource = "aws_s3_bucket.storage"
                resource_type = "s3_bucket"
        
        if "0.0.0.0/0" in plan_text or "allow_all" in plan_lower or "security" in plan_lower or "sg" in plan_lower or "ingress" in plan_lower or "port" in plan_lower:
            has_ingress_22 = "22" in plan_text or "ssh" in plan_lower or "3389" in plan_text or "rdp" in plan_lower or not ("resource" in plan_text)
            has_ingress_80 = "80" in plan_text or "http" in plan_lower or not ("resource" in plan_text)
            
            if has_ingress_22:
                violations.append("Ingress port 22 allows open public access (0.0.0.0/0)")
            if has_ingress_80:
                violations.append("Ingress port 80 lacks SSL/TLS enforcement")
                
        if "tag" in plan_lower or "instance" in plan_lower or "owner" in plan_lower or "environment" in plan_lower:
            standards = CONFIG.get("company_standards", {})
            required_tags = standards.get("required_tags", ["Environment", "Owner"])
            
            for tag in required_tags:
                if f"{tag.lower()} =" not in plan_lower and f'"{tag.lower()}"' not in plan_lower and f"'{tag.lower()}'" not in plan_lower:
                    violations.append(f"Missing mandatory tag: '{tag}'")

        if any(term in plan_lower for term in ["instance", "ebs", "volume", "storage", "encryption", "encrypt"]):
            if "encrypted = true" not in plan_lower and "encrypted" not in plan_lower:
                violations.append("Compute/storage resources do not clearly enable storage-at-rest encryption")

        if violations:
            is_high_risk = any("port 22" in v or "public access" in v or "credentials" in v for v in violations)
            compliance_status = "Non-Compliant (High Risk)" if is_high_risk else "Non-Compliant (Audit Warning)"
            
            remediations = []
            if any("port 22" in v for v in violations):
                remediations.append("Restrict port 22 ingress to corporate VPN blocks or bastion CIDRs.")
            if any("port 80" in v for v in violations):
                remediations.append("Enable SSL/TLS redirection on load balancers.")
            if any("tag" in v for v in violations):
                remediations.append(f"Update the tags block in HCL to inject mandatory company tags ({', '.join(required_tags)}).")
            if any("encryption" in v for v in violations):
                remediations.append("Set `encrypted = true` for volume/storage blocks.")
                
            reremediation = " ".join(remediations) or "Address the identified static configuration guardrail violations."
        else:
            compliance_status = "Compliant"
            reremediation = "No guardrail violations detected in this planned resource segment."
            
        return {
            "resource": resource,
            "type": resource_type,
            "violations": violations,
            "compliance_status": compliance_status,
            "remediation": rerremediation
        }

    @staticmethod
    def _generate_tags_block(env: str, owner: str, params: dict | None = None) -> str:
        """Generate tags block dynamically from company standards configuration."""
        if params is None:
            params = {}
        standards = CONFIG.get("company_standards", {})
        required_tags = standards.get("required_tags", ["Environment", "Owner", "ManagedBy"])
        
        tags_dict = {}
        for req_tag in required_tags:
            req_lower = req_tag.lower()
            if req_lower == "environment":
                tags_dict[req_tag] = env
            elif req_lower == "owner":
                tags_dict[req_tag] = owner
            elif req_lower == "managedby":
                tags_dict[req_tag] = "Terraform"
            elif req_lower == "project":
                tags_dict[req_tag] = params.get("project") or "Enterprise_AI_Platform"
            else:
                tags_dict[req_tag] = params.get(req_lower) or "Standard_Value"
                
        lines = [f"    {k.ljust(11)} = \"{v}\"" for k, v in tags_dict.items()]
        return "  tags = {\n" + "\n".join(lines) + "\n  }"

    @staticmethod
    def validate_hcl(hcl_text: str) -> dict[str, Any]:
        """Validate Terraform HCL or plan text against company standards configuration."""
        findings: list[dict[str, str]] = []
        normalized = hcl_text.lower()
        
        standards = CONFIG.get("company_standards", {})
        enforce_tags = standards.get("enforce_tags", True)
        required_tags = standards.get("required_tags", ["Environment", "Owner"])
        require_encryption = standards.get("require_encryption", True)
        enforce_tls = standards.get("enforce_tls", True)
        min_tls = standards.get("min_tls_version", "1.2")
        disallow_public_ingress = standards.get("disallow_public_ingress", True)

        if not re.search(r'\b(resource|module|data)\s+"', hcl_text):
            findings.append({
                "severity": "medium",
                "rule": "no_terraform_blocks",
                "message": "No Terraform resource/module/data blocks were detected.",
                "remediation": "Upload a `.tf` file or paste HCL/plan content that includes Terraform blocks.",
            })
            
        if disallow_public_ingress:
            if re.search(r'cidr_blocks\s*=\s*\[[^\]]*"0\.0\.0\.0/0"', hcl_text) and re.search(r'from_port\s*=\s*(22|3389)', hcl_text):
                findings.append({
                    "severity": "critical",
                    "rule": "public_admin_ingress",
                    "message": "Public ingress is open to administrative ports (22/3389). This violates company standards.",
                    "remediation": "Restrict SSH/RDP to corporate VPN blocks or bastion CIDRs.",
                })
                
        if enforce_tls:
            if re.search(r'from_port\s*=\s*80', hcl_text) and 'aws_lb_listener' not in normalized and '443' not in normalized:
                findings.append({
                    "severity": "medium",
                    "rule": "plain_http_exposure",
                    "message": "Port 80 exposure appears without HTTPS/TLS configuration.",
                    "remediation": f"Prefer TLS on port 443 and enforce min TLS version {min_tls}.",
                })
                
        if require_encryption:
            if 'encrypted = true' not in normalized and any(term in normalized for term in ['aws_instance', 'aws_ebs_volume', 'root_block_device']):
                findings.append({
                    "severity": "high",
                    "rule": "missing_storage_encryption",
                    "message": "Compute/storage resources do not clearly enable storage-at-rest encryption.",
                    "remediation": "Set `encrypted = true` for volume/storage blocks and configure approved encryption keys.",
                })
                
        if enforce_tags:
            if 'tags' not in normalized:
                findings.append({
                    "severity": "medium",
                    "rule": "missing_tags_block",
                    "message": "Resource tags block is missing.",
                    "remediation": f"Add the resource tags block containing required company tags: {', '.join(required_tags)}.",
                })
            else:
                for req_tag in required_tags:
                    if req_tag.lower() not in normalized:
                        findings.append({
                            "severity": "medium",
                            "rule": f"missing_{req_tag.lower()}_tag",
                            "message": f"Mandatory company standard tag '{req_tag}' is missing from the resource.",
                            "remediation": f"Define the '{req_tag}' tag in your resource tags configuration.",
                        })

        if re.search(r'(access_key|secret_key)\s*=', hcl_text, re.IGNORECASE):
            findings.append({
                "severity": "critical",
                "rule": "inline_cloud_secret",
                "message": "Provider credentials appear to be hard-coded.",
                "remediation": "Remove static credentials and use environment, workload identity, or vault-backed injection.",
            })

        return {
            "status": "pass" if not findings else "fail",
            "findings": findings,
            "finding_count": len(findings),
            "line_count": len(hcl_text.splitlines()),
        }

    @staticmethod
    def _post_process_tags(hcl: str, env: str, owner: str, params: dict | None = None) -> str:
        """Replace all tags = { ... } blocks with the company standard tags block."""
        tags_block = TerraformAuditor._generate_tags_block(env, owner, params)
        pattern = re.compile(r'tags\s*=\s*\{[^\}]*\}', re.DOTALL)
        return pattern.sub(tags_block, hcl)

    @staticmethod
    def generate_hcl(query: str, params: dict | None = None) -> str:
        """Generate approved Terraform HCL starter blocks based on parameters and company standards."""
        raw_hcl = TerraformAuditor._generate_hcl_raw(query, params)
        if not params:
            params = {}
        env_raw = params.get("environment") or "Production"
        env_map = {
            "dev": "Development",
            "prod": "Production",
            "staging": "Staging",
            "testing": "Testing",
            "development": "Development",
            "production": "Production"
        }
        env = env_map.get(env_raw.lower().strip(), env_raw.strip().capitalize())
        owner = (params.get("owner") or "Platform_Ops").strip()
        return TerraformAuditor._post_process_tags(raw_hcl, env, owner, params)

    @staticmethod
    def _generate_hcl_raw(query: str, params: dict | None = None) -> str:
        """Generate raw Terraform HCL starter blocks based on parameters."""
        if not params:
            params = {}
            
        # Extract environment
        env_raw = params.get("environment") or "Production"
        env_map = {
            "dev": "Development",
            "prod": "Production",
            "staging": "Staging",
            "testing": "Testing",
            "development": "Development",
            "production": "Production"
        }
        env = env_map.get(env_raw.lower().strip(), env_raw.strip().capitalize())
        
        # Extract owner
        owner = params.get("owner") or "Platform_Ops"
        owner = owner.strip()
        
        query_lower = query.lower()
        provider_raw = (params.get("provider") or "").strip().lower()
        provider = TerraformAuditor._detect_provider(query_lower, provider_raw)

        # Extract resource type
        res_type_raw = (params.get("resource_type") or "").strip().lower()
        res_type = TerraformAuditor._detect_resource_type(query_lower, res_type_raw, provider)
        
        if provider == "azurerm":
            is_hub_spoke = "hub" in query_lower and "spoke" in query_lower
            if is_hub_spoke:
                return (
                    f"resource \"azurerm_resource_group\" \"rg\" {{\n"
                    f"  name     = \"rg-hub-spoke-{env.lower()}\"\n"
                    f"  location = \"eastus2\"\n\n"
                    f"  tags = {{\n"
                    f"    Environment = \"{env}\"\n"
                    f"    Owner       = \"{owner}\"\n"
                    f"    ManagedBy   = \"Terraform\"\n"
                    f"  }}\n"
                    f"}}\n\n"
                    f"resource \"azurerm_virtual_network\" \"hub\" {{\n"
                    f"  name                = \"vnet-hub\"\n"
                    f"  address_space       = [\"10.0.0.0/16\"]\n"
                    f"  location            = azurerm_resource_group.rg.location\n"
                    f"  resource_group_name = azurerm_resource_group.rg.name\n\n"
                    f"  tags = {{\n"
                    f"    Environment = \"{env}\"\n"
                    f"    Owner       = \"{owner}\"\n"
                    f"  }}\n"
                    f"}}\n\n"
                    f"resource \"azurerm_virtual_network\" \"spoke\" {{\n"
                    f"  name                = \"vnet-spoke\"\n"
                    f"  address_space       = [\"10.1.0.0/16\"]\n"
                    f"  location            = azurerm_resource_group.rg.location\n"
                    f"  resource_group_name = azurerm_resource_group.rg.name\n\n"
                    f"  tags = {{\n"
                    f"    Environment = \"{env}\"\n"
                    f"    Owner       = \"{owner}\"\n"
                    f"  }}\n"
                    f"}}\n\n"
                    f"resource \"azurerm_virtual_network_peering\" \"hub_to_spoke\" {{\n"
                    f"  name                         = \"peer-hub-to-spoke\"\n"
                    f"  resource_group_name          = azurerm_resource_group.rg.name\n"
                    f"  virtual_network_name         = azurerm_virtual_network.hub.name\n"
                    f"  remote_virtual_network_id    = azurerm_virtual_network.spoke.id\n"
                    f"  allow_virtual_network_access = true\n"
                    f"  allow_forwarded_traffic      = true\n"
                    f"}}\n\n"
                    f"resource \"azurerm_virtual_network_peering\" \"spoke_to_hub\" {{\n"
                    f"  name                         = \"peer-spoke-to-hub\"\n"
                    f"  resource_group_name          = azurerm_resource_group.rg.name\n"
                    f"  virtual_network_name         = azurerm_virtual_network.spoke.name\n"
                    f"  remote_virtual_network_id    = azurerm_virtual_network.hub.id\n"
                    f"  allow_virtual_network_access = true\n"
                    f"  allow_forwarded_traffic      = true\n"
                    f"}}\n"
                )
            elif res_type in {"storage", "webapp", "storage_webapp"}:
                storage_block = ""
                webapp_block = ""
                if res_type in {"storage", "storage_webapp"}:
                    storage_block = (
                        f"resource \"azurerm_storage_account\" \"app\" {{\n"
                        f"  name                            = \"stsecure{env.lower()}001\"\n"
                        f"  resource_group_name             = azurerm_resource_group.rg.name\n"
                        f"  location                        = azurerm_resource_group.rg.location\n"
                        f"  account_tier                    = \"Standard\"\n"
                        f"  account_replication_type        = \"ZRS\"\n"
                        f"  min_tls_version                 = \"TLS1_2\"\n"
                        f"  allow_nested_items_to_be_public = false\n"
                        f"  shared_access_key_enabled       = false\n"
                        f"  public_network_access_enabled   = false\n"
                        f"  infrastructure_encryption_enabled = true\n\n"
                        f"  blob_properties {{\n"
                        f"    versioning_enabled  = true\n"
                        f"    change_feed_enabled = true\n\n"
                        f"    delete_retention_policy {{\n"
                        f"      days = 30\n"
                        f"    }}\n\n"
                        f"    container_delete_retention_policy {{\n"
                        f"      days = 30\n"
                        f"    }}\n"
                        f"  }}\n\n"
                        f"  tags = {{\n"
                        f"    Environment = \"{env}\"\n"
                        f"    Owner       = \"{owner}\"\n"
                        f"    ManagedBy   = \"Terraform\"\n"
                        f"  }}\n"
                        f"}}\n"
                    )
                if res_type in {"webapp", "storage_webapp"}:
                    webapp_block = (
                        f"resource \"azurerm_service_plan\" \"app\" {{\n"
                        f"  name                = \"asp-secure-{env.lower()}\"\n"
                        f"  resource_group_name = azurerm_resource_group.rg.name\n"
                        f"  location            = azurerm_resource_group.rg.location\n"
                        f"  os_type             = \"Linux\"\n"
                        f"  sku_name            = \"P1v3\"\n\n"
                        f"  tags = {{\n"
                        f"    Environment = \"{env}\"\n"
                        f"    Owner       = \"{owner}\"\n"
                        f"    ManagedBy   = \"Terraform\"\n"
                        f"  }}\n"
                        f"}}\n\n"
                        f"resource \"azurerm_linux_web_app\" \"app\" {{\n"
                        f"  name                = \"web-secure-{env.lower()}\"\n"
                        f"  resource_group_name = azurerm_resource_group.rg.name\n"
                        f"  location            = azurerm_resource_group.rg.location\n"
                        f"  service_plan_id     = azurerm_service_plan.app.id\n"
                        f"  https_only          = true\n\n"
                        f"  identity {{\n"
                        f"    type = \"SystemAssigned\"\n"
                        f"  }}\n\n"
                        f"  site_config {{\n"
                        f"    always_on              = true\n"
                        f"    ftps_state             = \"Disabled\"\n"
                        f"    minimum_tls_version    = \"1.2\"\n"
                        f"    scm_minimum_tls_version = \"1.2\"\n\n"
                        f"    application_stack {{\n"
                        f"      python_version = \"3.11\"\n"
                        f"    }}\n"
                        f"  }}\n\n"
                        f"  logs {{\n"
                        f"    detailed_error_messages = true\n"
                        f"    failed_request_tracing  = true\n\n"
                        f"    application_logs {{\n"
                        f"      file_system_level = \"Information\"\n"
                        f"    }}\n\n"
                        f"    http_logs {{\n"
                        f"      file_system {{\n"
                        f"        retention_in_days = 7\n"
                        f"        retention_in_mb   = 35\n"
                        f"      }}\n"
                        f"    }}\n"
                        f"  }}\n\n"
                        f"  app_settings = {{\n"
                        f"    WEBSITE_RUN_FROM_PACKAGE = \"1\"\n"
                        f"  }}\n\n"
                        f"  tags = {{\n"
                        f"    Environment = \"{env}\"\n"
                        f"    Owner       = \"{owner}\"\n"
                        f"    ManagedBy   = \"Terraform\"\n"
                        f"  }}\n"
                        f"}}\n"
                    )

                return (
                    f"resource \"azurerm_resource_group\" \"rg\" {{\n"
                    f"  name     = \"rg-secure-{env.lower()}\"\n"
                    f"  location = \"eastus2\"\n\n"
                    f"  tags = {{\n"
                    f"    Environment = \"{env}\"\n"
                    f"    Owner       = \"{owner}\"\n"
                    f"    ManagedBy   = \"Terraform\"\n"
                    f"  }}\n"
                    f"}}\n\n"
                    f"{storage_block}"
                    + ("\n" if storage_block and webapp_block else "")
                    + f"{webapp_block}"
                )
            elif res_type == "vpc":
                cidr = params.get("cidr_block") or "10.0.0.0/16"
                return (
                    f"resource \"azurerm_resource_group\" \"rg\" {{\n"
                    f"  name     = \"rg-secure-{env.lower()}\"\n"
                    f"  location = \"eastus2\"\n\n"
                    f"  tags = {{\n"
                    f"    Environment = \"{env}\"\n"
                    f"    Owner       = \"{owner}\"\n"
                    f"    ManagedBy   = \"Terraform\"\n"
                    f"  }}\n"
                    f"}}\n\n"
                    f"resource \"azurerm_virtual_network\" \"vnet\" {{\n"
                    f"  name                = \"vnet-main\"\n"
                    f"  address_space       = [\"{cidr}\"]\n"
                    f"  location            = azurerm_resource_group.rg.location\n"
                    f"  resource_group_name = azurerm_resource_group.rg.name\n\n"
                    f"  tags = {{\n"
                    f"    Environment = \"{env}\"\n"
                    f"    Owner       = \"{owner}\"\n"
                    f"    ManagedBy   = \"Terraform\"\n"
                    f"  }}\n"
                    f"}}\n"
                )
            elif res_type == "instance":
                vm_size = params.get("instance_type") or "Standard_D2s_v3"
                return (
                    f"resource \"azurerm_resource_group\" \"rg\" {{\n"
                    f"  name     = \"rg-secure-{env.lower()}\"\n"
                    f"  location = \"eastus2\"\n\n"
                    f"  tags = {{\n"
                    f"    Environment = \"{env}\"\n"
                    f"    Owner       = \"{owner}\"\n"
                    f"    ManagedBy   = \"Terraform\"\n"
                    f"  }}\n"
                    f"}}\n\n"
                    f"resource \"azurerm_linux_virtual_machine\" \"vm\" {{\n"
                    f"  name                            = \"vm-secure-app\"\n"
                    f"  resource_group_name             = azurerm_resource_group.rg.name\n"
                    f"  location                        = azurerm_resource_group.rg.location\n"
                    f"  size                            = \"{vm_size}\"\n"
                    f"  admin_username                  = \"adminuser\"\n"
                    f"  disable_password_authentication = true\n\n"
                    f"  network_interface_ids = [\n"
                    f"    azurerm_network_interface.nic.id,\n"
                    f"  ]\n\n"
                    f"  os_disk {{\n"
                    f"    caching              = \"ReadWrite\"\n"
                    f"    storage_account_type = \"StandardSSD_LRS\"\n"
                    f"    disk_encryption_set_id = var.disk_encryption_set_id\n"
                    f"  }}\n\n"
                    f"  source_image_reference {{\n"
                    f"    publisher = \"Canonical\"\n"
                    f"    offer     = \"0001-com-ubuntu-server-jammy\"\n"
                    f"    sku       = \"22_04-lts\"\n"
                    f"    version   = \"latest\"\n"
                    f"  }}\n\n"
                    f"  tags = {{\n"
                    f"    Environment = \"{env}\"\n"
                    f"    Owner       = \"{owner}\"\n"
                    f"    ManagedBy   = \"Terraform\"\n"
                    f"  }}\n"
                    f"}}\n"
                )
            else:
                return TerraformAuditor._generate_provider_scaffold(provider, res_type, env, owner, query)
        elif provider == "aws":
            if res_type == "vpc":
                cidr = params.get("cidr_block") or "10.0.0.0/16"
                return (
                    f"resource \"aws_vpc\" \"main\" {{\n"
                    f"  cidr_block           = \"{cidr}\"\n"
                    f"  enable_dns_support   = true\n"
                    f"  enable_dns_hostnames = true\n\n"
                    f"  tags = {{\n"
                    f"    Name        = \"main-vpc\"\n"
                    f"    Environment = \"{env}\"\n"
                    f"    Owner       = \"{owner}\"\n"
                    f"    ManagedBy   = \"Terraform\"\n"
                    f"  }}\n"
                    f"}}\n\n"
                    f"resource \"aws_flow_log\" \"vpc\" {{\n"
                    f"  log_destination      = aws_cloudwatch_log_group.vpc_flow.arn\n"
                    f"  log_destination_type = \"cloud-watch-logs\"\n"
                    f"  traffic_type         = \"ALL\"\n"
                    f"  vpc_id               = aws_vpc.main.id\n"
                    f"  iam_role_arn         = aws_iam_role.vpc_flow_logs.arn\n"
                    f"}}\n"
                )
            elif res_type == "instance":
                instance_type = params.get("instance_type") or "t3.medium"
                ami_id = params.get("ami_id") or "var.ami_id"
                if ami_id != "var.ami_id" and not ami_id.startswith('"'):
                    ami_id = f'"{ami_id}"'
                    
                return (
                    f"resource \"aws_instance\" \"secure_app\" {{\n"
                    f"  ami                         = {ami_id}\n"
                    f"  instance_type               = \"{instance_type}\"\n"
                    f"  subnet_id                   = var.private_subnet_id\n"
                    f"  vpc_security_group_ids      = [aws_security_group.app.id]\n"
                    f"  associate_public_ip_address = false\n\n"
                    f"  metadata_options {{\n"
                    f"    http_endpoint = \"enabled\"\n"
                    f"    http_tokens   = \"required\"\n"
                    f"  }}\n\n"
                    f"  root_block_device {{\n"
                    f"    encrypted   = true\n"
                    f"    volume_type = \"gp3\"\n"
                    f"  }}\n\n"
                    f"  tags = {{\n"
                    f"    Name        = \"secure-app\"\n"
                    f"    Environment = \"{env}\"\n"
                    f"    Owner       = \"{owner}\"\n"
                    f"    ManagedBy   = \"Terraform\"\n"
                    f"  }}\n"
                    f"}}\n"
                )
            else:
                return TerraformAuditor._generate_provider_scaffold(provider, res_type, env, owner, query)
        elif provider == "nutanix":
            if res_type == "instance":
                return (
                    f"resource \"nutanix_virtual_machine\" \"vm\" {{\n"
                    f"  name                 = \"vm-nutanix-{env.lower()}\"\n"
                    f"  description          = \"Managed virtual machine on Nutanix cluster\"\n"
                    f"  num_vcpus_per_socket = 2\n"
                    f"  num_sockets          = 1\n"
                    f"  memory_size_mib      = 4096\n\n"
                    f"  cluster_uuid         = var.nutanix_cluster_uuid\n\n"
                    f"  nic_list_status {{\n"
                    f"    subnet_uuid = var.nutanix_subnet_uuid\n"
                    f"  }}\n\n"
                    f"  disk_list {{\n"
                    f"    data_source_reference = {{\n"
                    f"      kind = \"image\"\n"
                    f"      uuid = var.nutanix_image_uuid\n"
                    f"    }}\n"
                    f"  }}\n\n"
                    f"  tags = {{\n"
                    f"    Environment = \"{env}\"\n"
                    f"    Owner       = \"{owner}\"\n"
                    f"    ManagedBy   = \"Terraform\"\n"
                    f"  }}\n"
                    f"}}\n"
                )
            else:
                return TerraformAuditor._generate_provider_scaffold(provider, res_type, env, owner, query)
        elif provider == "vsphere":
            if res_type == "instance":
                return (
                    f"resource \"vsphere_virtual_machine\" \"vm\" {{\n"
                    f"  name             = \"vm-vsphere-{env.lower()}\"\n"
                    f"  resource_pool_id = data.vsphere_resource_pool.pool.id\n"
                    f"  datastore_id     = data.vsphere_datastore.datastore.id\n"
                    f"  num_cpus         = 2\n"
                    f"  memory           = 4096\n"
                    f"  guest_id         = \"ubuntu64Guest\"\n\n"
                    f"  network_interface {{\n"
                    f"    network_id = data.vsphere_network.network.id\n"
                    f"  }}\n\n"
                    f"  disk {{\n"
                    f"    label            = \"disk0\"\n"
                    f"    size             = 20\n"
                    f"    thin_provisioned = true\n"
                    f"  }}\n\n"
                    f"  tags = [\n"
                    f"    \"Environment:{env}\",\n"
                    f"    \"Owner:{owner}\"\n"
                    f"  ]\n"
                    f"}}\n"
                )
            else:
                return TerraformAuditor._generate_provider_scaffold(provider, res_type, env, owner, query)

        return TerraformAuditor._generate_provider_scaffold(provider, res_type, env, owner, query)

    @staticmethod
    def _detect_provider(query_lower: str, provider_raw: str) -> str:
        """Detect Terraform provider by explicit parameter, alias, or resource prefix."""
        for candidate in [provider_raw, query_lower]:
            for alias, canonical in PROVIDER_ALIASES.items():
                if alias and alias in candidate:
                    return canonical

        prefixed_resource = re.search(r'\b([a-z][a-z0-9]*)_[a-z0-9_]+\b', query_lower)
        if prefixed_resource:
            prefix = prefixed_resource.group(1)
            if prefix in KNOWN_PROVIDERS or prefix in PROVIDER_REQUIREMENTS:
                return prefix

        return "aws"

    @staticmethod
    def _detect_resource_type(query_lower: str, res_type_raw: str, provider: str | None = None) -> str:
        """Detect the intended resource family without provider-specific hallucination."""
        # 1. Check if query contains an explicit resource that is mapped to a generic type (e.g. google_sql_database_instance)
        for (prov, rtype), resource_name in GENERIC_RESOURCE_TYPES.items():
            if re.search(rf"\b{resource_name}\b", query_lower) or re.search(rf"\b{resource_name}\b", res_type_raw):
                return rtype

        # 2. Check for explicit provider resource first (e.g. azurerm_storage_sync, aws_s3_bucket)
        for text in [res_type_raw, query_lower]:
            explicit_resource = re.search(r'\b[a-z][a-z0-9]*_([a-z0-9_]+)\b', text)
            if explicit_resource:
                parts = explicit_resource.group(0).split("_", 1)
                if len(parts) == 2:
                    matched_prov = PROVIDER_ALIASES.get(parts[0], parts[0])
                    if provider:
                        if matched_prov == provider:
                            return parts[1]
                    else:
                        if parts[0] in KNOWN_PROVIDERS or parts[0] in PROVIDER_REQUIREMENTS:
                            return parts[1]

        combined = f"{res_type_raw} {query_lower}".strip()
        for resource_type, hints in RESOURCE_HINTS.items():
            if any(hint in combined for hint in hints):
                return resource_type

        explicit_resource = re.search(r'\b[a-z][a-z0-9]*_([a-z0-9_]+)\b', combined)
        if explicit_resource:
            parts = explicit_resource.group(0).split("_", 1)
            if len(parts) == 2:
                matched_prov = PROVIDER_ALIASES.get(parts[0], parts[0])
                if provider:
                    if matched_prov == provider:
                        return parts[1]
                else:
                    if parts[0] in KNOWN_PROVIDERS or parts[0] in PROVIDER_REQUIREMENTS:
                        return parts[1]
            return explicit_resource.group(1).strip("_")

        return res_type_raw or "resource"

    @staticmethod
    def _parse_hcl_fields(fields_str: str) -> dict[str, str]:
        """Parse HCL fields string into a dictionary."""
        fields = {}
        for line in fields_str.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"^([a-z0-9_]+)\s*=\s*(.*)$", line, re.IGNORECASE)
            if match:
                fields[match.group(1).strip()] = match.group(2).strip()
        return fields

    @staticmethod
    def _extract_query_assignments(query: str) -> dict[str, str]:
        """Dynamically extract argument assignments from the user query."""
        assignments = {}
        # Pattern 1: key = "value" or key = value
        pattern1 = re.finditer(r'\b([a-z0-9_]+)\s*=\s*(["\'])(.*?)\2', query, re.IGNORECASE)
        for m in pattern1:
            assignments[m.group(1).lower()] = m.group(3)
            
        # Pattern 2: key = number or boolean
        pattern2 = re.finditer(r'\b([a-z0-9_]+)\s*=\s*\b(true|false|[0-9.]+)\b', query, re.IGNORECASE)
        for m in pattern2:
            assignments[m.group(1).lower()] = m.group(2)

        # Pattern 3: "with <key> set to <value>" or "with <key> of <value>"
        pattern3 = re.finditer(r'\bwith\s+([a-z0-9_]+)\s+(?:set\s+to|of|as|=)\s+([^,\s]+)', query, re.IGNORECASE)
        for m in pattern3:
            key = m.group(1).lower()
            if key not in assignments:
                val = m.group(2).strip("\"'")
                assignments[key] = val
                
        return assignments

    @staticmethod
    def _get_cached_provider(provider: str) -> dict | None:
        """Get the cached provider requirement if it exists."""
        import json
        try:
            cache_dir = os.path.join(os.path.dirname(__file__), ".schema_cache")
            cache_path = os.path.join(cache_dir, f"_provider_{provider}.json")
            if os.path.exists(cache_path):
                with open(cache_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    @staticmethod
    def _save_cached_provider(provider: str, requirement: dict) -> None:
        """Save a provider requirement to the local cache folder."""
        import json
        try:
            cache_dir = os.path.join(os.path.dirname(__file__), ".schema_cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f"_provider_{provider}.json")
            with open(cache_path, "w") as f:
                json.dump(requirement, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def _get_provider_requirement(provider: str) -> dict:
        """Get provider source and version requirements, fetching from registry if not hardcoded."""
        canonical_prov = PROVIDER_ALIASES.get(provider, provider)
        if canonical_prov in PROVIDER_REQUIREMENTS:
            return PROVIDER_REQUIREMENTS[canonical_prov]

        cached = TerraformAuditor._get_cached_provider(canonical_prov)
        if cached:
            return cached

        # Query Registry API dynamically
        try:
            import urllib.request
            import json
            namespace = "hashicorp"
            if "/" in canonical_prov:
                namespace, provider_name = canonical_prov.split("/", 1)
            else:
                provider_name = canonical_prov

            url = f"https://registry.terraform.io/v1/providers/{namespace}/{provider_name}"
            req = urllib.request.Request(url, headers={'User-Agent': 'AntigravityAgent/1.0'})
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read())
                version = data.get("version") or "1.0.0"
                version_parts = version.split(".")
                if len(version_parts) >= 2:
                    version_req = f"~> {version_parts[0]}.{version_parts[1]}"
                else:
                    version_req = f"~> {version}"

                source = f"{namespace}/{provider_name}"
                github_url = data.get("source")
                if github_url and "github.com/" in github_url:
                    github_parts = github_url.split("github.com/")[-1].split("/")
                    if len(github_parts) >= 2:
                        source = f"{github_parts[0]}/{github_parts[1].replace('terraform-provider-', '')}"

                requirement = {
                    "source": source,
                    "version": version_req
                }
                TerraformAuditor._save_cached_provider(canonical_prov, requirement)
                PROVIDER_REQUIREMENTS[canonical_prov] = requirement
                return requirement
        except Exception:
            pass

        # Fallback
        fallback = {"source": f"hashicorp/{canonical_prov}", "version": ">= 0.0.0"}
        PROVIDER_REQUIREMENTS[canonical_prov] = fallback
        return fallback

    @staticmethod
    def _get_cached_schema(provider: str, resource_type: str) -> dict | None:
        """Get the cached schema for a resource type if it exists."""
        import json
        try:
            cache_dir = os.path.join(os.path.dirname(__file__), ".schema_cache")
            cache_path = os.path.join(cache_dir, f"{provider}_{resource_type}.json")
            if os.path.exists(cache_path):
                with open(cache_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    @staticmethod
    def _save_cached_schema(provider: str, resource_type: str, schema: dict) -> None:
        """Save a resource schema to the cache."""
        import json
        try:
            cache_dir = os.path.join(os.path.dirname(__file__), ".schema_cache")
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f"{provider}_{resource_type}.json")
            with open(cache_path, "w") as f:
                json.dump(schema, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def _fetch_and_parse_schema(provider: str, resource_type: str) -> dict | None:
        """Fetch raw documentation markdown and parse required arguments."""
        import urllib.request
        canonical_prov = PROVIDER_ALIASES.get(provider, provider)
        
        # Get organization and repo name from requirements source
        req = TerraformAuditor._get_provider_requirement(canonical_prov)
        if req:
            source = req["source"]
            org, repo = source.split("/")
            repo_name = f"terraform-provider-{repo}"
        else:
            org = "hashicorp"
            repo_name = f"terraform-provider-{canonical_prov}"

        # Suffix must be stripped of provider prefix
        suffix = resource_type
        if suffix.startswith(f"{canonical_prov}_"):
            suffix = suffix[len(canonical_prov)+1:]
            
        urls = []
        for branch in ["main", "master"]:
            urls.extend([
                f"https://raw.githubusercontent.com/{org}/{repo_name}/{branch}/website/docs/r/{suffix}.html.markdown",
                f"https://raw.githubusercontent.com/{org}/{repo_name}/{branch}/website/docs/r/{suffix}.html.md",
                f"https://raw.githubusercontent.com/{org}/{repo_name}/{branch}/docs/resources/{suffix}.markdown",
                f"https://raw.githubusercontent.com/{org}/{repo_name}/{branch}/docs/resources/{suffix}.md"
            ])
        
        markdown_text = None
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'AntigravityAgent/1.0'})
                with urllib.request.urlopen(req, timeout=5) as res:
                    markdown_text = res.read().decode('utf-8')
                    break
            except Exception:
                continue
                
        if not markdown_text:
            return None

        # Extract Arguments Reference section
        args_idx = markdown_text.find("## Arguments Reference")
        if args_idx == -1:
            args_idx = markdown_text.find("## Argument Reference")
        if args_idx == -1:
            args_section = markdown_text
        else:
            next_sec_idx = markdown_text.find("## ", args_idx + 3)
            if next_sec_idx == -1:
                args_section = markdown_text[args_idx:]
            else:
                args_section = markdown_text[args_idx:next_sec_idx]

        # Split top-level from nested blocks to avoid field overlap
        block_start_match = re.search(r'(?:An|The|A)\s+`[a-zA-Z0-9_]+`\s+block\s+supports', args_section, re.IGNORECASE)
        if block_start_match:
            top_level_text = args_section[:block_start_match.start()]
        else:
            top_level_text = args_section

        # Find top-level bullet points
        pattern = r'(?:\*|-)\s+`([a-zA-Z0-9_]+)`\s+-\s+\((Required|Optional)\)(.*?)(?=(?:\*|-)\s+`|\Z)'
        matches = re.findall(pattern, top_level_text, re.DOTALL)
        
        required_args = {}
        for name, req_status, desc in matches:
            if req_status == "Required":
                desc_clean = desc.strip().lower()
                is_block = "block as defined below" in desc_clean or "blocks as defined below" in desc_clean or "structure as defined below" in desc_clean
                required_args[name] = {
                    "type": "block" if is_block else "field",
                    "desc": desc.strip()
                }
                
        block_patterns = r'(?:An|The)\s+`([a-zA-Z0-9_]+)`\s+block\s+supports\s+the\s+following:(.*?)(?=(?:An|The)\s+`[a-zA-Z0-9_]+`\s+block\s+supports|\Z)'
        block_matches = re.findall(block_patterns, args_section, re.DOTALL | re.IGNORECASE)
        
        nested_blocks = {}
        for block_name, block_content in block_matches:
            block_fields = re.findall(r'(?:\*|-)\s+`([a-zA-Z0-9_]+)`\s+-\s+\((Required|Optional)\)', block_content)
            req_fields = [f_name for f_name, f_status in block_fields if f_status == "Required"]
            nested_blocks[block_name.lower()] = req_fields

        schema = {}
        for arg_name, arg_info in required_args.items():
            if arg_info["type"] == "block" and arg_name.lower() in nested_blocks:
                schema[arg_name] = {
                    "type": "block",
                    "fields": nested_blocks[arg_name.lower()]
                }
            else:
                schema[arg_name] = "field"
                
        return schema

    @staticmethod
    def _format_dummy_value(name: str, parent_block: str | None = None) -> str:
        name_lower = name.lower()
        if name_lower == "resource_group_name":
            return "azurerm_resource_group.rg.name"
        elif name_lower == "location":
            return "azurerm_resource_group.rg.location"
        elif name_lower == "name":
            return f'"{parent_block}-name"' if parent_block else '"example-resource"'
        elif name_lower == "type":
            if parent_block == "identity":
                return '"SystemAssigned"'
            return '"example-type"'
        elif "arn" in name_lower:
            return '"arn:aws:..."'
        elif "id" in name_lower:
            return '"example-id"'
        elif "enabled" in name_lower or "enable_" in name_lower:
            return "true"
        elif "ip_address" in name_lower or "cidr" in name_lower:
            return '"10.0.0.0/24"'
        else:
            return f'"example-{name_lower.replace("_", "-")}"'

    @staticmethod
    def _generate_provider_scaffold(provider: str, res_type: str, env: str, owner: str, query: str) -> str:
        """Generate a provider-aware scaffold when no approved deep template exists."""
        requirement = TerraformAuditor._get_provider_requirement(provider)
        resource_type = GENERIC_RESOURCE_TYPES.get(
            (provider, res_type),
            f"{provider}_{TerraformAuditor._slug(res_type)}",
        )
        resource_name = TerraformAuditor._slug(res_type or "generated")

        # Try dynamic schema extraction first
        schema = TerraformAuditor._get_cached_schema(provider, res_type)
        if not schema:
            schema = TerraformAuditor._fetch_and_parse_schema(provider, res_type)
            if schema:
                TerraformAuditor._save_cached_schema(provider, res_type, schema)

        # Get user assignments from query
        user_assigns = TerraformAuditor._extract_query_assignments(query)

        hcl_fields = ""
        if schema:
            # Generate from dynamic schema
            # Render fields
            for k, v in schema.items():
                if v == "field":
                    if k in user_assigns:
                        val = user_assigns[k]
                        if not (val.lower() in ["true", "false"] or re.match(r"^[0-9.]+$", val) or (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")) or re.match(r"^(var\.|local\.|aws_|google_|azurerm_|[a-zA-Z0-9_]+\.)", val)):
                            val = f'"{val}"'
                    else:
                        val = TerraformAuditor._format_dummy_value(k)
                    hcl_fields += f"  {k:<30} = {val}\n"
            
            # Render blocks
            for k, v in schema.items():
                if isinstance(v, dict) and v.get("type") == "block":
                    hcl_fields += f"  {k} {{\n"
                    for f in v.get("fields", []):
                        if f in user_assigns:
                            val = user_assigns[f]
                            if not (val.lower() in ["true", "false"] or re.match(r"^[0-9.]+$", val) or (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")) or re.match(r"^(var\.|local\.|aws_|google_|azurerm_|[a-zA-Z0-9_]+\.)", val)):
                                val = f'"{val}"'
                        else:
                            val = TerraformAuditor._format_dummy_value(f, parent_block=k)
                        hcl_fields += f"    {f:<28} = {val}\n"
                    hcl_fields += "  }\n"
            if hcl_fields:
                hcl_fields += "\n"
        else:
            # Fall back to original registry-based/stub logic
            defaults = TerraformAuditor._parse_hcl_fields(REQUIRED_FIELDS_REGISTRY.get(resource_type, ""))
            merged = {}
            for k, v in defaults.items():
                merged[k] = v
            for k, v in user_assigns.items():
                if v.lower() in ["true", "false"] or re.match(r"^[0-9.]+$", v):
                    merged[k] = v
                elif (v.startswith("\"") and v.endswith("\"")) or (v.startswith("'") and v.endswith("'")):
                    merged[k] = v
                else:
                    if re.match(r"^(var\.|local\.|aws_|google_|azurerm_|[a-zA-Z0-9_]+\.)", v):
                        merged[k] = v
                    else:
                        merged[k] = f"\"{v}\""

            for k, v in merged.items():
                hcl_fields += f"  {k:<30} = {v}\n"
            if hcl_fields:
                hcl_fields += "\n"

        return (
            f"terraform {{\n"
            f"  required_providers {{\n"
            f"    {provider} = {{\n"
            f"      source  = \"{requirement['source']}\"\n"
            f"      version = \"{requirement['version']}\"\n"
            f"    }}\n"
            f"  }}\n"
            f"}}\n\n"
            f"provider \"{provider}\" {{\n"
            f"  # Configure credentials, region, endpoint, or context through environment variables or backend-managed secrets.\n"
            f"}}\n\n"
            f"resource \"{resource_type}\" \"{resource_name}\" {{\n"
            f"  # Generated deterministic scaffold for: {TerraformAuditor._sanitize_comment(query)}\n"
            f"  # Complete required arguments from the pinned provider documentation before apply.\n\n"
            f"{hcl_fields}"
            f"  tags = {{\n"
            f"    Environment = \"{env}\"\n"
            f"    Owner       = \"{owner}\"\n"
            f"    ManagedBy   = \"Terraform\"\n"
            f"  }}\n"
            f"}}\n"
        )

    @staticmethod
    def _slug(value: str) -> str:
        """Return a Terraform identifier-safe slug."""
        slug = re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")
        return slug or "generated"

    @staticmethod
    def _sanitize_comment(value: str) -> str:
        """Keep generated comments single-line and non-executable."""
        return re.sub(r"\s+", " ", value).replace("*/", "").strip()[:160]
