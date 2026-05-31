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
                "remediation": "Use purpose-built modules such as package, service, file, template, user, or copy.",
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
    def generate_playbook(query: str) -> str:
        """Generate approved idempotent Ansible playbooks."""
        normalized = query.lower()
        if (
            "azure" in normalized
            and any(term in normalized for term in ["vnet", "virtual network", "subnet", "network"])
        ):
            return (
                "---\n"
                "- name: Provision Azure virtual network and subnets\n"
                "  hosts: localhost\n"
                "  connection: local\n"
                "  gather_facts: false\n"
                "  vars:\n"
                "    azure_location: eastus\n"
                "    resource_group_name: rg-platform-network-prod\n"
                "    vnet_name: vnet-platform-prod\n"
                "    vnet_address_prefixes:\n"
                "      - 10.40.0.0/16\n"
                "    subnets:\n"
                "      - name: snet-app\n"
                "        address_prefix: 10.40.1.0/24\n"
                "      - name: snet-private-endpoints\n"
                "        address_prefix: 10.40.2.0/24\n"
                "    common_tags:\n"
                "      Environment: Production\n"
                "      Owner: Platform_Ops\n"
                "      ManagedBy: Ansible\n"
                "  tasks:\n"
                "    - name: Ensure Azure resource group exists\n"
                "      azure.azcollection.azure_rm_resourcegroup:\n"
                "        name: \"{{ resource_group_name }}\"\n"
                "        location: \"{{ azure_location }}\"\n"
                "        tags: \"{{ common_tags }}\"\n\n"
                "    - name: Ensure Azure virtual network exists\n"
                "      azure.azcollection.azure_rm_virtualnetwork:\n"
                "        resource_group: \"{{ resource_group_name }}\"\n"
                "        name: \"{{ vnet_name }}\"\n"
                "        address_prefixes: \"{{ vnet_address_prefixes }}\"\n"
                "        tags: \"{{ common_tags }}\"\n\n"
                "    - name: Ensure Azure subnets exist\n"
                "      azure.azcollection.azure_rm_subnet:\n"
                "        resource_group: \"{{ resource_group_name }}\"\n"
                "        virtual_network_name: \"{{ vnet_name }}\"\n"
                "        name: \"{{ item.name }}\"\n"
                "        address_prefix: \"{{ item.address_prefix }}\"\n"
                "      loop: \"{{ subnets }}\"\n"
            )
        if "update" in normalized or "patch" in normalized:
            return (
                "---\n"
                "- name: Apply safe system package updates\n"
                "  hosts: linux_servers\n"
                "  become: true\n"
                "  gather_facts: true\n"
                "  tasks:\n"
                "    - name: Update package cache\n"
                "      ansible.builtin.package:\n"
                "        update_cache: true\n\n"
                "    - name: Ensure security packages are current\n"
                "      ansible.builtin.package:\n"
                "        name: \"*\"\n"
                "        state: latest\n"
            )
        return (
            "---\n"
            "- name: Install and configure Nginx webserver\n"
            "  hosts: webservers\n"
            "  become: true\n"
            "  gather_facts: true\n"
            "  tasks:\n"
            "    - name: Ensure Nginx is installed\n"
            "      ansible.builtin.package:\n"
            "        name: nginx\n"
            "        state: present\n\n"
            "    - name: Ensure Nginx service is enabled and running\n"
            "      ansible.builtin.service:\n"
            "        name: nginx\n"
            "        state: started\n"
            "        enabled: true\n"
        )

    @staticmethod
    def describe_generated_playbook(query: str) -> dict[str, str]:
        """Return template metadata used for generation summaries."""
        normalized = query.lower()
        if (
            "azure" in normalized
            and any(term in normalized for term in ["vnet", "virtual network", "subnet", "network"])
        ):
            return {
                "template_name": "azure_vnet_subnets",
                "playbook_name": "azure_network.yml",
                "title": "Azure VNet and Subnet Provisioning Playbook",
                "description": "Generated an idempotent Ansible playbook using `azure.azcollection` modules to create a resource group, virtual network, and production-tagged subnets.",
                "verification_note": "Requires `azure.azcollection` and Azure credentials supplied through approved environment variables, managed identity, or enterprise secret injection.",
                "remediation": "No raw shell commands are used. Network CIDRs, region, resource group, and tags are centralized as variables for review before execution.",
            }
        if "update" in normalized or "patch" in normalized:
            return {
                "template_name": "system_updates",
                "playbook_name": "system_updates.yml",
                "title": "System Package Update Playbook",
                "description": "Generated an idempotent package maintenance playbook using Ansible built-in modules.",
                "verification_note": "Review package version policy before using `state: latest` in production maintenance windows.",
                "remediation": "Package actions use declarative modules instead of shell commands.",
            }
        return {
            "template_name": "nginx_webserver",
            "playbook_name": "site.yml",
            "title": "Nginx Webserver Provisioning Playbook",
            "description": "Generated an idempotent webserver setup playbook using package and service modules.",
            "verification_note": "Targets the `webservers` inventory group and expects privilege escalation for package/service changes.",
            "remediation": "Raw shell commands are replaced with declarative Ansible modules.",
        }
