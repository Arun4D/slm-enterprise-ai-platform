import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

MOCK_NODES = {
    "webserver_group": [
        {"host": "web-srv-01", "ip": "10.0.1.10", "ping_status": "Success", "latency_ms": 3.4},
        {"host": "web-srv-02", "ip": "10.0.1.11", "ping_status": "Success", "latency_ms": 4.1},
        {"host": "web-srv-03", "ip": "10.0.1.12", "ping_status": "Failed (Timeout)", "latency_ms": 0.0}
    ],
    "playbook_validation": {
        "syntax_valid": True,
        "warnings": [
            "Use of raw 'shell' module found. Consider substituting with 'apt' or 'yum' modules for package installations."
        ],
        "playbook_name": "site.yml"
    }
}

class AnsibleValidator:
    """Validates playbooks and inventory host reports using offline rules."""

    @staticmethod
    def inspect_playbook(playbook_text: str) -> dict:
        """Inspect playbook structure and warnings."""
        validation = AnsibleValidator.validate_playbook(playbook_text)
        return {
            **MOCK_NODES["playbook_validation"],
            "warnings": [finding["message"] for finding in validation["findings"]],
            "validation": validation,
        }

    @staticmethod
    def get_ping_report(group_name: str) -> list:
        """Fetch ping stats for targeted hosts."""
        return MOCK_NODES["webserver_group"]

    @staticmethod
    def validate_playbook(playbook_text: str) -> dict[str, Any]:
        """Validate pasted or uploaded Ansible YAML without running Ansible."""
        findings: list[dict[str, str]] = []
        normalized = playbook_text.lower()

        if not re.search(r"^\s*-\s+hosts\s*:", playbook_text, re.MULTILINE):
            findings.append({
                "severity": "high",
                "rule": "missing_hosts",
                "message": "Playbook does not define a `hosts` target.",
                "remediation": "Add `- hosts: <group>` at the play level.",
            })
        if "tasks:" not in normalized:
            findings.append({
                "severity": "high",
                "rule": "missing_tasks",
                "message": "Playbook does not define a `tasks:` section.",
                "remediation": "Add a tasks list with named idempotent modules.",
            })
        if re.search(r"ansible\.builtin\.(shell|command)\s*:", normalized) or re.search(r"^\s*(shell|command)\s*:", normalized, re.MULTILINE):
            findings.append({
                "severity": "medium",
                "rule": "raw_shell_command",
                "message": "Playbook uses shell/command modules, which are harder to make idempotent.",
                "remediation": "Use purpose-built modules from the official Ansible Collections (e.g. package, service, file, template, user, copy). See documentation: https://docs.ansible.com/projects/ansible/latest/collections/index_module.html",
            })
        if re.search(r"\b(apt|yum|dnf|package)\s*:", normalized) and "state:" not in normalized:
            findings.append({
                "severity": "medium",
                "rule": "package_state_missing",
                "message": "Package installation task does not set an explicit state.",
                "remediation": "Set `state: present`, `latest`, or an approved pinned version policy.",
            })
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
        if "name:" not in normalized:
            findings.append({
                "severity": "low",
                "rule": "unnamed_tasks",
                "message": "Playbook lacks descriptive names.",
                "remediation": "Add `name:` fields to plays and tasks for auditable execution output.",
            })

        return {
            "status": "pass" if not findings else "fail",
            "findings": findings,
            "finding_count": len(findings),
            "line_count": len(playbook_text.splitlines()),
        }

    @staticmethod
    def generate_playbook(query: str, params: dict | None = None) -> str:
        """Generate approved idempotent Ansible playbooks based on parameters."""
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
        provider = params.get("provider") or ("azure" if any(kw in query.lower() for kw in ["azure", "azurerm"]) else "builtin")
        provider = str(provider).strip().lower()
        
        normalized = query.lower()
        
        if "azure" in provider or "azure" in normalized:
            return (
                f"---\n"
                f"- name: Provision Azure virtual network and subnets\n"
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
        if "update" in normalized or "patch" in normalized:
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
        return (
            f"---\n"
            f"- name: Install and configure Nginx webserver\n"
            f"  hosts: {hosts}\n"
            f"  become: {become}\n"
            f"  gather_facts: true\n"
            f"  tasks:\n"
            f"    - name: Ensure Nginx is installed\n"
            f"      ansible.builtin.package:\n"
            f"        name: nginx\n"
            f"        state: present\n\n"
            f"    - name: Ensure Nginx service is enabled and running\n"
            f"      ansible.builtin.service:\n"
            f"        name: nginx\n"
            f"        state: started\n"
            f"        enabled: true\n"
        )

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
        provider = params.get("provider") or ("azure" if any(kw in query.lower() for kw in ["azure", "azurerm"]) else "builtin")
        provider = str(provider).strip().lower()
        
        if "azure" in provider or "azure" in normalized:
            return {
                "template_name": "azure_vnet_subnets",
                "playbook_name": "azure_network.yml",
                "title": "Azure VNet and Subnet Provisioning Playbook",
                "description": f"Generated an idempotent Ansible playbook targeting hosts '{hosts}' using `azure.azcollection` modules to create a resource group, virtual network, and subnets tagged for Environment '{env}' and Owner '{owner}'.",
                "verification_note": "Requires `azure.azcollection` and Azure credentials supplied through approved environment variables, managed identity, or enterprise secret injection.",
                "remediation": "No raw shell commands are used. Network CIDRs, region, resource group, and tags are centralized as variables for review before execution.",
            }
        if "update" in normalized or "patch" in normalized:
            return {
                "template_name": "system_updates",
                "playbook_name": "system_updates.yml",
                "title": "System Package Update Playbook",
                "description": f"Generated an idempotent package maintenance playbook targeting hosts '{hosts}' using Ansible built-in modules.",
                "verification_note": "Review package version policy before using `state: latest` in production maintenance windows.",
                "remediation": "Package actions use declarative modules instead of shell commands.",
            }
        return {
            "template_name": "nginx_webserver",
            "playbook_name": "site.yml",
            "title": "Nginx Webserver Provisioning Playbook",
            "description": f"Generated an idempotent webserver setup playbook targeting hosts '{hosts}' using package and service modules.",
            "verification_note": f"Targets the '{hosts}' inventory group and expects privilege escalation for package/service changes.",
            "remediation": "Raw shell commands are replaced with declarative Ansible modules.",
        }
