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
        
        # Extract provider (aws or azure)
        provider = params.get("provider") or ("azure" if any(kw in query.lower() for kw in ["azure", "azurerm"]) else "aws")
        provider = provider.strip().lower()

        # Extract resource type
        res_type = params.get("resource_type") or ("vpc" if any(kw in query.lower() for kw in ["vpc", "network", "vnet", "virtual network"]) else "instance")
        
        if provider == "azure":
            if res_type == "vpc":
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
            else:
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
            else:
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
