"""
Unit tests to verify Terraform generation and validation rules for all 1,128 AzureRM resources.
"""

import os
import json
import pytest
import sys
from pathlib import Path

# Add the terraform agent directory to the python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import TerraformAuditor
from main import TerraformAgent

# Load the list of azurerm resources
RESOURCES_JSON_PATH = Path(__file__).resolve().parent / "azurerm_resources.json"


def load_azurerm_resources():
    """Load the azurerm resources from the JSON file."""
    if not RESOURCES_JSON_PATH.exists():
        pytest.fail(f"Could not find azurerm resources JSON file at {RESOURCES_JSON_PATH}")
    with open(RESOURCES_JSON_PATH, "r") as f:
        return json.load(f)


# We parameterize the test with all 1,128 resources so they are all tested individually
# This lists out failures (if any) specifically per resource.
AZURERM_RESOURCES = load_azurerm_resources()


@pytest.fixture
def agent():
    return TerraformAgent()


@pytest.mark.parametrize("resource_suffix", AZURERM_RESOURCES)
def test_azurerm_resource_scaffold_generation(agent, resource_suffix, monkeypatch):
    """
    Test code generation and validation for each of the 1,128 AzureRM resources.
    We verify:
    1. Parameter extraction identifies provider as 'azurerm' and resource_type as the suffix.
    2. HCL generation constructs the correct resource block declaration.
    3. HCL validation passes enterprise security guardrails.
    """
    # Mock network fetching and schema caching to run completely offline
    monkeypatch.setattr(TerraformAuditor, "_fetch_and_parse_schema", lambda p, r: None)
    monkeypatch.setattr(TerraformAuditor, "_get_cached_schema", lambda p, r: None)

    full_resource_name = f"azurerm_{resource_suffix}"
    query = f"generate terraform code for {full_resource_name}"
    
    # 1. Test Parameter Extraction
    params = agent._extract_parameters_with_rules(query)
    assert params.get("provider") == "azurerm", f"Expected provider 'azurerm' for query: {query}"
    
    # Clean the expected suffix mapping
    expected_resource_type = resource_suffix.strip("_")
    if expected_resource_type == "postgresql_flexible_server":
        expected_resource_type = "database"
    elif expected_resource_type == "network_security_group":
        expected_resource_type = "security_group"
        
    assert params.get("resource_type") == expected_resource_type, f"Expected resource_type '{expected_resource_type}' for query: {query}"

    # 2. Test HCL Generation
    code = TerraformAuditor.generate_hcl(query, params)
    
    # Verify the generated resource block signature
    expected_block = f'resource "{full_resource_name}"'
    assert expected_block in code, f"Generated code does not contain resource block '{expected_block}'. Code:\n{code}"

    # 3. Test HCL Validation against company standard guardrails
    validation = TerraformAuditor.validate_hcl(code)
    
    assert validation["status"] == "pass", (
        f"Security validation failed for {full_resource_name}.\n"
        f"Findings: {validation.get('findings')}\n"
        f"Generated Code:\n{code}"
    )
