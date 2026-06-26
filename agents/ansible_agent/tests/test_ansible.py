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


def test_generate_playbook_nutanix():
    """Test generating Nutanix vm migration playbook with custom tags."""
    params = {
        "hosts": "localhost",
        "environment": "testing",
        "owner": "NutanixTeam",
        "vm_name": "production-db-01",
        "target_host": "cluster-node-02"
    }
    code = AnsibleValidator.generate_playbook("generate ansible code for nutanix vm migrate", params)
    assert 'hosts: localhost' in code
    assert 'vm_name: "production-db-01"' in code
    assert 'target_host_uuid: "cluster-node-02"' in code
    assert 'nutanix.ncloud.ntnx_vms' in code



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


def test_validate_playbook_no_log_warning():
    """Test that validating a playbook with secret/password variables without no_log: true raises a warning."""
    playbook_content = """
- hosts: all
  name: Configure database
  tasks:
    - name: Set db password variable
      ansible.builtin.set_fact:
        db_password: "supersecretpassword"
    """
    result = AnsibleValidator.validate_playbook(playbook_content)
    assert result["status"] == "fail"
    assert any(finding["rule"] == "missing_no_log" for finding in result["findings"])


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


def test_generate_dynamic_copy():
    """Test generating a playbook using the copy module schema."""
    code = AnsibleValidator.generate_playbook("generate playbook for ansible.builtin.copy")
    assert "ansible.builtin.copy:" in code
    assert 'dest: "/path/to/file"' in code
    assert 'become: true' in code


def test_generate_dynamic_user():
    """Test generating a playbook using the user module schema."""
    code = AnsibleValidator.generate_playbook("generate playbook for user module")
    assert "ansible.builtin.user:" in code
    assert 'name: "example-name"' in code


def test_generate_dynamic_with_no_log(monkeypatch):
    """Test that a sensitive field triggers no_log: true automatically in dynamic playbooks."""
    schema = {
        "admin_password": {
            "type": "string",
            "required": True
        }
    }
    monkeypatch.setattr(AnsibleValidator, "_get_cached_module_schema", lambda x: schema)
    
    code = AnsibleValidator.generate_playbook("generate playbook for custom.secret.module")
    assert "admin_password:" in code
    assert "no_log: true" in code


def test_dynamic_scraper_offline(monkeypatch):
    """Test that the scraper can fetch and parse required fields from HTML documentation."""
    dummy_html = """
    <html>
      <body>
        <div class="ansibleOptionAnchor" id="parameter-api_key"></div>
        <p class="ansible-option-title" id="param-api_key"><strong>api_key</strong></p>
        <p class="ansible-option-type-line"><span class="ansible-option-type">string</span> / <span class="ansible-option-required">required</span></p>

        <div class="ansibleOptionAnchor" id="parameter-password"></div>
        <p class="ansible-option-title" id="param-password"><strong>password</strong></p>
        <p class="ansible-option-type-line"><span class="ansible-option-type">string</span> / <span class="ansible-option-required">required</span></p>

        <div class="ansibleOptionAnchor" id="parameter-optional_field"></div>
        <p class="ansible-option-title" id="param-optional_field"><strong>optional_field</strong></p>
        <p class="ansible-option-type-line"><span class="ansible-option-type">string</span></p>
      </body>
    </html>
    """
    
    class DummyResponse:
        def read(self):
            return dummy_html.encode('utf-8')
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_urlopen(*args, **kwargs):
        return DummyResponse()

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    # Force call fetch to bypass cache
    schema = AnsibleValidator._fetch_and_parse_module_schema("community.general.custom_module")
    assert schema is not None
    assert "api_key" in schema
    assert schema["api_key"]["required"] is True
    assert "password" in schema
    assert schema["password"]["required"] is True
    assert "optional_field" in schema
    assert schema["optional_field"]["required"] is False


def test_generate_invalid_module_raises_error():
    """Test that requesting a non-existent module raises ValueError."""
    with pytest.raises(ValueError) as excinfo:
        AnsibleValidator.generate_playbook("generate ansible code for cpm_time_config")
    assert "No such ansible module exists: cpm_time_config" in str(excinfo.value)


@pytest.mark.anyio
async def test_agent_execute_invalid_module_returns_failed(agent):
    """Test that executing a plan for an invalid module returns a failed status JSON."""
    plan = await agent.plan("generate ansible code for cpm_time_config", {})
    result = await agent.execute(plan)
    assert result["status"] == "failed"
    assert "No such ansible module exists: cpm_time_config" in result["error"]


