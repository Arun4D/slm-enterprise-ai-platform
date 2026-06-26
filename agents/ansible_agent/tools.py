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
    logger.error(f"Failed to load config.yaml in ansible_agent tools: {e}")

class AnsibleValidator:
    """Validates playbooks and inventory host reports using offline rules."""

    @staticmethod
    def inspect_playbook(playbook_text: str) -> dict:
        """Inspect playbook structure and warnings."""
        validation = AnsibleValidator.validate_playbook(playbook_text)
        
        syntax_valid = True
        if playbook_text.strip() and ("hosts:" in playbook_text or playbook_text.strip().startswith("-") or playbook_text.strip().startswith("---")):
            try:
                yaml.safe_load(playbook_text)
            except Exception:
                syntax_valid = False
                
        playbook_name = "playbook.yml"
        name_match = re.search(r'\b([a-zA-Z0-9_-]+\.ya?ml)\b', playbook_text)
        if name_match:
            playbook_name = name_match.group(1)
            
        return {
            "syntax_valid": syntax_valid,
            "warnings": [finding["message"] for finding in validation["findings"]],
            "playbook_name": playbook_name,
            "validation": validation,
        }

    @staticmethod
    def get_ping_report(group_name: str) -> list:
        """Fetch ping stats for targeted hosts."""
        group = str(group_name).strip().lower()
        if "local" in group:
            return [
                {"host": "localhost", "ip": "127.0.0.1", "ping_status": "Success", "latency_ms": 0.1}
            ]
        
        prefix = "db" if "db" in group or "data" in group else "web"
        return [
            {"host": f"{prefix}-srv-01", "ip": "10.0.1.10", "ping_status": "Success", "latency_ms": 3.4},
            {"host": f"{prefix}-srv-02", "ip": "10.0.1.11", "ping_status": "Success", "latency_ms": 4.1},
            {"host": f"{prefix}-srv-03", "ip": "10.0.1.12", "ping_status": "Failed (Timeout)", "latency_ms": 0.0}
        ]

    @staticmethod
    def _generate_common_tags(env: str, owner: str, params: dict | None = None) -> str:
        """Generate common tags block dynamically from company standards configuration."""
        if params is None:
            params = {}
        standards = CONFIG.get("company_standards", {})
        required_tags = standards.get("require_tags", ["Environment", "Owner", "ManagedBy"])
        
        tags_dict = {}
        for req_tag in required_tags:
            req_lower = req_tag.lower()
            if req_lower == "environment":
                tags_dict[req_tag] = env
            elif req_lower == "owner":
                tags_dict[req_tag] = owner
            elif req_lower == "managedby":
                tags_dict[req_tag] = "Ansible"
            elif req_lower == "project":
                tags_dict[req_tag] = params.get("project") or "Enterprise_AI_Platform"
            else:
                tags_dict[req_tag] = params.get(req_lower) or "Standard_Value"
                
        lines = [f"      {k}: {v}" for k, v in tags_dict.items()]
        return "    common_tags:\n" + "\n".join(lines)

    @staticmethod
    def validate_playbook(playbook_text: str) -> dict[str, Any]:
        """Validate pasted or uploaded Ansible YAML against company standards configuration."""
        findings: list[dict[str, str]] = []
        normalized = playbook_text.lower()
        
        standards = CONFIG.get("company_standards", {})
        require_task_names = standards.get("require_task_names", True)
        disallow_shell = standards.get("disallow_shell_commands", True)
        require_become = standards.get("require_become_explicit", True)
        enforce_no_log = standards.get("enforce_no_log_for_secrets", True)
        required_tags = standards.get("require_tags", ["Environment", "Owner"])

        if not re.search(r"^\s*-\s+hosts\s*:", playbook_text, re.MULTILINE):
            findings.append({
                "severity": "high",
                "rule": "missing_hosts",
                "message": "Playbook does not define a target `hosts` at play level.",
                "remediation": "Add `- hosts: <group>` at the play level.",
            })
        if "tasks:" not in normalized:
            findings.append({
                "severity": "high",
                "rule": "missing_tasks",
                "message": "Playbook does not define a `tasks:` section.",
                "remediation": "Add a tasks list with named idempotent modules.",
            })
            
        if disallow_shell:
            if re.search(r"ansible\.builtin\.(shell|command)\s*:", normalized) or re.search(r"^\s*(shell|command)\s*:", normalized, re.MULTILINE):
                findings.append({
                    "severity": "medium",
                    "rule": "raw_shell_command",
                    "message": "Playbook uses raw shell/command modules, which violates company standards.",
                    "remediation": "Use purpose-built modules from the official Ansible Collections (e.g. package, service, file, template, user, copy). See documentation: https://docs.ansible.com/projects/ansible/latest/collections/index_module.html",
                })
                
        if re.search(r"\b(apt|yum|dnf|package)\s*:", normalized) and "state:" not in normalized:
            findings.append({
                "severity": "medium",
                "rule": "package_state_missing",
                "message": "Package installation task does not set an explicit state.",
                "remediation": "Set `state: present`, `latest`, or an approved pinned version policy.",
            })
            
        if require_become:
            if "become:" not in normalized and any(term in normalized for term in ["package:", "service:", "apt:", "yum:", "dnf:"]):
                findings.append({
                    "severity": "low",
                    "rule": "missing_become",
                    "message": "Privilege escalation is not explicit for system package/service operations.",
                    "remediation": "Set `become: true` at the play or task level when privileged changes are required.",
                })
                
        if re.search(r"(password|token|secret)\s*:\s*['\"]?[A-Za-z0-9_\-]{8,}", playbook_text, re.IGNORECASE):
            findings.append({
                "severity": "critical",
                "rule": "inline_secret",
                "message": "Potential inline secret detected in playbook content.",
                "remediation": "Move secrets to Ansible Vault or an approved internal secret backend.",
            })
            
        if enforce_no_log:
            if any(term in normalized for term in ["password", "token", "secret", "private_key"]) and "no_log: true" not in normalized:
                findings.append({
                    "severity": "high",
                    "rule": "missing_no_log",
                    "message": "Task processing sensitive variables lacks `no_log: true` protection.",
                    "remediation": "Add `no_log: true` to the task configuration to prevent credential exposure in execution logs.",
                })
                
        if require_task_names:
            if "name:" not in normalized:
                findings.append({
                    "severity": "low",
                    "rule": "unnamed_tasks",
                    "message": "Playbook lacks descriptive task/play names.",
                    "remediation": "Add `name:` fields to plays and tasks for auditable execution output.",
                })

        return {
            "status": "pass" if not findings else "fail",
            "findings": findings,
            "finding_count": len(findings),
            "line_count": len(playbook_text.splitlines()),
        }

    @staticmethod
    def _post_process_playbook(playbook_code: str, env: str, owner: str, params: dict | None = None) -> str:
        """Replace common_tags block with company standard common_tags."""
        tags_block = AnsibleValidator._generate_common_tags(env, owner, params)
        pattern = re.compile(r'common_tags:\s*\n(\s+[A-Za-z0-9_]+:\s*[^\n]+\n*)+', re.DOTALL)
        return pattern.sub(tags_block + "\n", playbook_code)

    @staticmethod
    def generate_playbook(query: str, params: dict | None = None) -> str:
        """Generate approved idempotent Ansible playbooks based on parameters and company standards."""
        raw_playbook = AnsibleValidator._generate_playbook_raw(query, params)
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
        return AnsibleValidator._post_process_playbook(raw_playbook, env, owner, params)

    @staticmethod
    def _generate_playbook_raw(query: str, params: dict | None = None) -> str:
        """Generate raw approved idempotent Ansible playbooks based on parameters."""
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
        
        # Extract hosts
        hosts = params.get("hosts") or "webservers"
        
        # Extract become
        become_val = params.get("become")
        if become_val is None:
            become = "true"
        else:
            become = "true" if str(become_val).lower() in ["true", "yes", "1"] else "false"
            
        # Extract provider
        provider = params.get("provider") or ""
        if not provider:
            if any(kw in query.lower() for kw in ["azure", "azurerm"]):
                provider = "azure"
            elif "nutanix" in query.lower():
                provider = "nutanix"
            elif any(kw in query.lower() for kw in ["vmware", "vcenter"]):
                provider = "vmware"
            elif any(kw in query.lower() for kw in ["servicenow", "snow"]):
                provider = "servicenow"
            else:
                provider = "builtin"
        provider = str(provider).strip().lower()
        
        normalized = query.lower()
        
        if "nutanix" in provider or "nutanix" in normalized:
            vm_name = params.get("vm_name") or "vm-to-migrate"
            target_host = params.get("target_host") or "target-cluster-node"
            play_name = params.get("play_name") or f"Migrate Nutanix Virtual Machine in {env.lower()}"
            
            return (
                f"---\n"
                f"- name: {play_name}\n"
                f"  hosts: {hosts}\n"
                f"  gather_facts: false\n"
                f"  vars:\n"
                f"    nutanix_host: \"localhost\"\n"
                f"    nutanix_username: \"admin\"\n"
                f"    vm_name: \"{vm_name}\"\n"
                f"    target_host_uuid: \"{target_host}\"\n"
                f"    common_tags:\n"
                f"      Environment: {env}\n"
                f"      Owner: {owner}\n"
                f"      ManagedBy: Ansible\n"
                f"  tasks:\n"
                f"    - name: Migrate VM to another host\n"
                f"      nutanix.ncloud.ntnx_vms:\n"
                f"        nutanix_host: \"{{{{ nutanix_host }}}}\"\n"
                f"        nutanix_username: \"{{{{ nutanix_username }}}}\"\n"
                f"        nutanix_password: \"{{{{ vault_nutanix_password }}}}\"\n"
                f"        state: migrate\n"
                f"        vm_name: \"{{{{ vm_name }}}}\"\n"
                f"        host_uuid: \"{{{{ target_host_uuid }}}}\"\n"
            )
            
        if "vmware" in provider or "vmware" in normalized or "vcenter" in normalized:
            vm_name = params.get("vm_name") or "vm-to-migrate"
            target_host = params.get("target_host") or "esxi-host-01"
            play_name = params.get("play_name") or f"Migrate VMware Virtual Machine in {env.lower()}"
            
            return (
                f"---\n"
                f"- name: {play_name}\n"
                f"  hosts: {hosts}\n"
                f"  gather_facts: false\n"
                f"  vars:\n"
                f"    vcenter_hostname: \"vcenter.local\"\n"
                f"    vcenter_username: \"administrator@vsphere.local\"\n"
                f"    vm_name: \"{vm_name}\"\n"
                f"    target_esxi_host: \"{target_host}\"\n"
                f"    common_tags:\n"
                f"      Environment: {env}\n"
                f"      Owner: {owner}\n"
                f"      ManagedBy: Ansible\n"
                f"  tasks:\n"
                f"    - name: Migrate VMware virtual machine (vMotion)\n"
                f"      community.vmware.vmware_guest:\n"
                f"        hostname: \"{{{{ vcenter_hostname }}}}\"\n"
                f"        username: \"{{{{ vcenter_username }}}}\"\n"
                f"        password: \"{{{{ vault_vcenter_password }}}}\"\n"
                f"        validate_certs: false\n"
                f"        name: \"{{{{ vm_name }}}}\"\n"
                f"        esxi_hostname: \"{{{{ target_esxi_host }}}}\"\n"
                f"        state: poweredon\n"
            )
            
        if "servicenow" in provider or "servicenow" in normalized or "snow" in normalized:
            play_name = params.get("play_name") or f"Create ServiceNow Incident in {env.lower()}"
            short_desc = params.get("short_description") or "Automated incident report"
            
            return (
                f"---\n"
                f"- name: {play_name}\n"
                f"  hosts: {hosts}\n"
                f"  gather_facts: false\n"
                f"  vars:\n"
                f"    snow_instance: \"dev12345\"\n"
                f"    snow_username: \"admin\"\n"
                f"    common_tags:\n"
                f"      Environment: {env}\n"
                f"      Owner: {owner}\n"
                f"      ManagedBy: Ansible\n"
                f"  tasks:\n"
                f"    - name: Create incident in ServiceNow\n"
                f"      servicenow.itsm.incident:\n"
                f"        instance: \"{{{{ snow_instance }}}}\"\n"
                f"        username: \"{{{{ snow_username }}}}\"\n"
                f"        password: \"{{{{ vault_snow_password }}}}\"\n"
                f"        state: new\n"
                f"        short_description: \"{short_desc}\"\n"
                f"        description: \"Incident created via Ansible automation\"\n"
                f"        impact: medium\n"
                f"        urgency: medium\n"
            )
            
        if "azure" in provider or "azure" in normalized:
            play_name = params.get("play_name") or f"Provision Azure infrastructure for {env.lower()}"
            return (
                f"---\n"
                f"- name: {play_name}\n"
                f"  hosts: {hosts}\n"
                f"  connection: local\n"
                f"  gather_facts: false\n"
                f"  vars:\n"
                f"    azure_location: eastus\n"
                f"    resource_group_name: rg-platform-network-{env.lower()}\n"
                f"    vnet_name: vnet-platform-{env.lower()}\n"
                f"    vnet_address_prefixes:\n"
                f"      - 10.40.0.0/16\n"
                f"    subnets:\n"
                f"      - name: snet-app\n"
                f"        address_prefix: 10.40.1.0/24\n"
                f"      - name: snet-private-endpoints\n"
                f"        address_prefix: 10.40.2.0/24\n"
                f"    common_tags:\n"
                f"      Environment: {env}\n"
                f"      Owner: {owner}\n"
                f"      ManagedBy: Ansible\n"
                f"  tasks:\n"
                f"    - name: Ensure Azure resource group exists\n"
                f"      azure.azcollection.azure_rm_resourcegroup:\n"
                f"        name: \"{{{{ resource_group_name }}}}\"\n"
                f"        location: \"{{{{ azure_location }}}}\"\n"
                f"        tags: \"{{{{ common_tags }}}}\"\n\n"
                f"    - name: Ensure Azure virtual network exists\n"
                f"      azure.azcollection.azure_rm_virtualnetwork:\n"
                f"        resource_group: \"{{{{ resource_group_name }}}}\"\n"
                f"        name: \"{{{{ vnet_name }}}}\"\n"
                f"        address_prefixes: \"{{{{ vnet_address_prefixes }}}}\"\n"
                f"        tags: \"{{{{ common_tags }}}}\"\n\n"
                f"    - name: Ensure Azure subnets exist\n"
                f"      azure.azcollection.azure_rm_subnet:\n"
                f"        resource_group: \"{{{{ resource_group_name }}}}\"\n"
                f"        virtual_network_name: \"{{{{ vnet_name }}}}\"\n"
                f"        name: \"{{{{ item.name }}}}\"\n"
                f"        address_prefix: \"{{{{ item.address_prefix }}}}\"\n"
                f"      loop: \"{{{{ subnets }}}}\"\n"
            )
        if "update" in normalized or "patch" in normalized or params.get("action") == "update":
            return (
                f"---\n"
                f"- name: Apply safe system package updates\n"
                f"  hosts: {hosts}\n"
                f"  become: {become}\n"
                f"  gather_facts: true\n"
                f"  tasks:\n"
                f"    - name: Update package cache\n"
                f"      ansible.builtin.package:\n"
                f"        update_cache: true\n\n"
                f"    - name: Ensure security packages are current\n"
                f"      ansible.builtin.package:\n"
                f"        name: \"*\"\n"
                f"        state: latest\n"
            )
            
        package_name = params.get("package_name")
        service_name = params.get("service_name")
        service_state = params.get("service_state") or "started"
        
        # If no package or service name is extracted, use Nginx as fallback
        if not package_name and not service_name:
            package_name = "nginx"
            service_name = "nginx"
            
        playbook_parts = [
            f"---\n",
            f"- name: Provision and configure system services\n",
            f"  hosts: {hosts}\n",
            f"  become: {become}\n",
            f"  gather_facts: true\n",
            f"  tasks:\n"
        ]
        
        if package_name:
            playbook_parts.append(
                f"    - name: Ensure {package_name} is installed\n"
                f"      ansible.builtin.package:\n"
                f"        name: {package_name}\n"
                f"        state: present\n\n"
            )
            
        if service_name or package_name:
            svc = service_name or package_name
            playbook_parts.append(
                f"    - name: Ensure {svc} service is {service_state}\n"
                f"      ansible.builtin.service:\n"
                f"        name: {svc}\n"
                f"        state: {service_state}\n"
                f"        enabled: true\n"
            )
            
        return "".join(playbook_parts)

    @staticmethod
    def describe_generated_playbook(query: str, params: dict | None = None) -> dict[str, str]:
        """Return template metadata used for generation summaries."""
        if not params:
            params = {}
            
        env_raw = params.get("environment") or "Production"
        env = env_raw.strip().capitalize()
        owner = params.get("owner") or "Platform_Ops"
        hosts = params.get("hosts") or "webservers"
        
        normalized = query.lower()
        provider = params.get("provider") or ""
        if not provider:
            if any(kw in query.lower() for kw in ["azure", "azurerm"]):
                provider = "azure"
            elif "nutanix" in query.lower():
                provider = "nutanix"
            elif any(kw in query.lower() for kw in ["vmware", "vcenter"]):
                provider = "vmware"
            elif any(kw in query.lower() for kw in ["servicenow", "snow"]):
                provider = "servicenow"
            else:
                provider = "builtin"
        provider = str(provider).strip().lower()
        
        if "nutanix" in provider or "nutanix" in normalized:
            return {
                "template_name": "nutanix_vm_migrate",
                "playbook_name": "nutanix_migrate.yml",
                "title": "Nutanix VM Migration Playbook",
                "description": f"Generated an idempotent Ansible playbook targeting hosts '{hosts}' using `nutanix.ncloud` modules to migrate virtual machines, tagged for Environment '{env}' and Owner '{owner}'.",
                "verification_note": "Requires the `nutanix.ncloud` collection and credentials supplied securely via vault variables.",
                "remediation": "Uses declarative Ansible modules from the Nutanix collection instead of raw scripts.",
            }
        if "vmware" in provider or "vmware" in normalized or "vcenter" in normalized:
            return {
                "template_name": "vmware_vm_migrate",
                "playbook_name": "vmware_migrate.yml",
                "title": "VMware VM Migration Playbook",
                "description": f"Generated an idempotent Ansible playbook targeting hosts '{hosts}' using `community.vmware.vmware_guest` module to manage virtual machine states and host migrations, tagged for Environment '{env}' and Owner '{owner}'.",
                "verification_note": "Requires the `community.vmware` collection and vCenter connection credentials.",
                "remediation": "Ensures idempotent operations on the vCenter API instead of running raw ssh/cli scripts.",
            }
        if "servicenow" in provider or "servicenow" in normalized or "snow" in normalized:
            return {
                "template_name": "servicenow_incident_create",
                "playbook_name": "snow_incident.yml",
                "title": "ServiceNow Incident Creation Playbook",
                "description": f"Generated an idempotent Ansible playbook using `servicenow.itsm.incident` to create incident records, tagged for Environment '{env}' and Owner '{owner}'.",
                "verification_note": "Requires `servicenow.itsm` collection and ServiceNow instance connection variables.",
                "remediation": "API interactions are handled declaratively via the ITSM collection modules.",
            }
        if "azure" in provider or "azure" in normalized:
            return {
                "template_name": "azure_vnet_subnets",
                "playbook_name": "azure_network.yml",
                "title": "Azure VNet and Subnet Provisioning Playbook",
                "description": f"Generated an idempotent Ansible playbook targeting hosts '{hosts}' using `azure.azcollection` modules to create a resource group, virtual network, and subnets tagged for Environment '{env}' and Owner '{owner}'.",
                "verification_note": "Requires `azure.azcollection` and Azure credentials supplied through approved environment variables, managed identity, or enterprise secret injection.",
                "remediation": "No raw shell commands are used. Network CIDRs, region, resource group, and tags are centralized as variables for review before execution.",
            }
        if "update" in normalized or "patch" in normalized or params.get("action") == "update":
            return {
                "template_name": "system_updates",
                "playbook_name": "system_updates.yml",
                "title": "System Package Update Playbook",
                "description": f"Generated an idempotent package maintenance playbook targeting hosts '{hosts}' using Ansible built-in modules.",
                "verification_note": "Review package version policy before using `state: latest` in production maintenance windows.",
                "remediation": "Package actions use declarative modules instead of shell commands.",
            }
            
        package_name = params.get("package_name") or "nginx"
        return {
            "template_name": f"{package_name}_setup",
            "playbook_name": "site.yml",
            "title": f"{package_name.capitalize()} Service Provisioning Playbook",
            "description": f"Generated an idempotent {package_name} setup playbook targeting hosts '{hosts}' using package and service modules.",
            "verification_note": f"Targets the '{hosts}' inventory group and expects privilege escalation for package/service changes.",
            "remediation": "Raw shell commands are replaced with declarative Ansible modules.",
        }
