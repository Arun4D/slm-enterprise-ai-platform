import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

MOCK_PLANS = {
    "insecure_sg": {
        "resource": "aws_security_group.allow_all",
        "type": "security_group",
        "violations": [
            "Ingress port 22 allows open public access (0.0.0.0/0)",
            "Ingress port 80 lacks SSL/TLS enforcement"
        ],
        "compliance_status": "Non-Compliant (High Risk)",
        "remediation": "Restrict port 22 ingress to corporate VPN blocks or bastion CIDRs. Enable SSL/TLS redirection on load balancers."
    },
    "missing_tags": {
        "resource": "aws_instance.web",
        "type": "ec2_instance",
        "violations": [
            "Missing mandatory tag: 'Environment'",
            "Missing mandatory tag: 'Owner'"
        ],
        "compliance_status": "Non-Compliant (Audit Warning)",
        "remediation": "Update the tags block in `main.tf` to inject 'Environment = \"Production\"' and 'Owner = \"DBA_Ops\"'."
    }
}

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
}

class TerraformAuditor:
    """Audits Terraform plan/HCL data against static security guardrails."""

    @staticmethod
    def audit_plan(plan_text: str) -> dict:
        """Parse plan query and return compliance audits."""
        plan_lower = plan_text.lower()
        if "security" in plan_lower or "sg" in plan_lower or "ingress" in plan_lower or "port" in plan_lower:
            return MOCK_PLANS["insecure_sg"]
        elif "tag" in plan_lower or "instance" in plan_lower or "owner" in plan_lower:
            return MOCK_PLANS["missing_tags"]
        else:
            return {
                "resource": "aws_vpc.main",
                "type": "vpc",
                "violations": [],
                "compliance_status": "Compliant",
                "remediation": "No guardrail violations detected in this planned resource segment."
            }

    @staticmethod
    def validate_hcl(hcl_text: str) -> dict[str, Any]:
        """Validate Terraform HCL or plan text without executing Terraform."""
        findings: list[dict[str, str]] = []
        normalized = hcl_text.lower()

        if not re.search(r'\b(resource|module|data)\s+"', hcl_text):
            findings.append({
                "severity": "medium",
                "rule": "no_terraform_blocks",
                "message": "No Terraform resource/module/data blocks were detected.",
                "remediation": "Upload a `.tf` file or paste HCL/plan content that includes Terraform blocks.",
            })
        if re.search(r'cidr_blocks\s*=\s*\[[^\]]*"0\.0\.0\.0/0"', hcl_text) and re.search(r'from_port\s*=\s*(22|3389)', hcl_text):
            findings.append({
                "severity": "critical",
                "rule": "public_admin_ingress",
                "message": "Public ingress is open to an administrative port.",
                "remediation": "Restrict SSH/RDP to corporate VPN or bastion CIDRs.",
            })
        if re.search(r'from_port\s*=\s*80', hcl_text) and 'aws_lb_listener' not in normalized and '443' not in normalized:
            findings.append({
                "severity": "medium",
                "rule": "plain_http_exposure",
                "message": "Port 80 exposure appears without an HTTPS listener or redirect.",
                "remediation": "Prefer TLS on 443 and redirect HTTP to HTTPS at the load balancer.",
            })
        if 'encrypted = true' not in normalized and any(term in normalized for term in ['aws_instance', 'aws_ebs_volume', 'root_block_device']):
            findings.append({
                "severity": "high",
                "rule": "missing_storage_encryption",
                "message": "Compute/storage resources do not clearly enable encryption.",
                "remediation": "Set `encrypted = true` for EBS/root block devices and use approved KMS keys where required.",
            })
        if 'tags' not in normalized:
            findings.append({
                "severity": "medium",
                "rule": "missing_tags_block",
                "message": "No tags block detected.",
                "remediation": "Add mandatory tags such as Environment, Owner, CostCenter, and ManagedBy.",
            })
        else:
            for required_tag in ["environment", "owner"]:
                if required_tag not in normalized:
                    findings.append({
                        "severity": "medium",
                        "rule": f"missing_{required_tag}_tag",
                        "message": f"Mandatory tag `{required_tag.title()}` is missing.",
                        "remediation": f"Add `{required_tag.title()}` to every resource tags block or module tag map.",
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
    def generate_hcl(query: str, params: dict | None = None) -> str:
        """Generate approved Terraform HCL starter blocks based on parameters."""
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
        res_type = TerraformAuditor._detect_resource_type(query_lower, res_type_raw)
        
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
            if prefix in PROVIDER_REQUIREMENTS:
                return prefix

        return "aws"

    @staticmethod
    def _detect_resource_type(query_lower: str, res_type_raw: str) -> str:
        """Detect the intended resource family without provider-specific hallucination."""
        combined = f"{res_type_raw} {query_lower}".strip()
        for resource_type, hints in RESOURCE_HINTS.items():
            if any(hint in combined for hint in hints):
                return resource_type

        explicit_resource = re.search(r'\b[a-z][a-z0-9]*_([a-z0-9_]+)\b', combined)
        if explicit_resource:
            return explicit_resource.group(1).strip("_")

        return res_type_raw or "resource"

    @staticmethod
    def _generate_provider_scaffold(provider: str, res_type: str, env: str, owner: str, query: str) -> str:
        """Generate a provider-aware scaffold when no approved deep template exists."""
        requirement = PROVIDER_REQUIREMENTS.get(
            provider,
            {"source": f"hashicorp/{provider}", "version": ">= 0.0.0"},
        )
        resource_type = GENERIC_RESOURCE_TYPES.get(
            (provider, res_type),
            f"{provider}_{TerraformAuditor._slug(res_type)}",
        )
        resource_name = TerraformAuditor._slug(res_type or "generated")

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
