"""
Unit tests for the Ansible Agent and Validator.
"""

import sys
from pathlib import Path
import pytest

# Insert Ansible agent folder to sys.path to enable isolated imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import AnsibleValidator
from main import AnsibleAgent


@pytest.fixture
def agent():
    """Create an AnsibleAgent instance."""
    return AnsibleAgent()


# ===========================================================================
# Validator Unit Tests
# ===========================================================================

def test_generate_playbook_default():
    """Test generating a default Nginx playbook."""
    code = AnsibleValidator.generate_playbook("install nginx")
    assert 'hosts: webservers' in code
    assert 'become: true' in code
    assert 'ansible.builtin.package' in code
    assert 'state: present' in code


def test_generate_playbook_custom():
    """Test custom parameters for Nginx playbook."""
    params = {
        "hosts": "dbservers",
        "become": "false",
        "environment": "staging",
        "owner": "DB_Ops"
    }
    code = AnsibleValidator.generate_playbook("install nginx", params)
    assert 'hosts: dbservers' in code
    assert 'become: false' in code
    assert 'ansible.builtin.package' in code


def test_generate_playbook_dynamic_package():
    """Test generating a dynamic playbook for a custom package (e.g. apache2)."""
    params = {
        "package_name": "apache2",
        "service_name": "apache2",
        "service_state": "started",
        "hosts": "webservers"
    }
    code = AnsibleValidator.generate_playbook("install apache2", params)
    assert 'Ensure apache2 is installed' in code
    assert 'name: apache2' in code
    assert 'Ensure apache2 service is started' in code
    assert 'nginx' not in code.lower()


def test_generate_playbook_azure():
    """Test generating Azure network playbook with custom tags."""
    params = {
        "hosts": "localhost",
        "environment": "testing",
        "owner": "NetworkTeam"
    }
    code = AnsibleValidator.generate_playbook("provision azure network", params)
    assert 'hosts: localhost' in code
    assert 'resource_group_name: rg-platform-network-testing' in code
    assert 'Environment: Testing' in code
    assert 'Owner: NetworkTeam' in code
    assert 'azure.azcollection' in code


def test_validate_playbook_shell_warning():
    """Test that validating a playbook with raw shell usage returns a warning pointing to the collections URL."""
    playbook_content = """
- hosts: all
  name: Install packages
  tasks:
    - name: Run shell install
      shell: apt-get install -y git
    """
    result = AnsibleValidator.validate_playbook(playbook_content)
    assert result["status"] == "fail"
    assert result["finding_count"] > 0
    
    # Check that the remediation includes the requested Ansible Collections link
    remediations = [f["remediation"] for f in result["findings"]]
    assert any("https://docs.ansible.com/projects/ansible/latest/collections/index_module.html" in r for r in remediations)


# ===========================================================================
# Agent Integration Tests
# ===========================================================================

def test_agent_can_handle(agent):
    """Test agent can_handle triggers on Ansible keywords."""
    assert agent.can_handle("generate an ansible playbook") is True
    assert agent.can_handle("validate my playbook site.yml") is True
    assert agent.can_handle("check my springboot server logs") is False


@pytest.mark.anyio
async def test_agent_plan_generation(agent):
    """Test plan structure for generation actions."""
    plan = await agent.plan("create ansible playbook for nginx on staging hosts by DB_Ops", {})
    assert plan["status"] == "success"
    assert plan["context"]["action"] == "generate"
    assert "Assemble playbook metadata" in plan["steps"]


@pytest.mark.anyio
async def test_agent_execute_generation(agent):
    """Test executing a custom generation prompt."""
    plan = await agent.plan("generate nginx playbook on dbservers in dev by dbops", {})
    result = await agent.execute(plan)
    assert result["status"] == "success"
    assert result["result"]["action"] == "generate"
    
    code = result["result"]["code"]
    assert 'hosts: dbservers' in code
    assert 'become: true' in code
    
    generation = result["result"]["generation"]
    assert "dbservers" in generation["description"]


@pytest.mark.anyio
async def test_agent_summarize(agent):
    """Test summarizing the generation result in Markdown."""
    plan = await agent.plan("generate nginx playbook", {})
    result = await agent.execute(plan)
    summary = await agent.summarize(result)
    assert "Generator & Validator" in summary
    assert "hosts: webservers" in summary

