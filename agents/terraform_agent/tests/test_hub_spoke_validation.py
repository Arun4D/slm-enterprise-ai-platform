"""
New test case for validating the Azure Hub-and-Spoke virtual network peered HCL code.
"""

import sys
from pathlib import Path
import pytest

# Ensure the parent directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import TerraformAuditor
from main import TerraformAgent

@pytest.mark.anyio
async def test_azure_hub_spoke_model_validation():
    """
    Verify that generating Azure Hub and Spoke model HCL works correctly
    and passing it through the validation guardrails succeeds with zero findings.
    """
    agent = TerraformAgent()
    
    # 1. Plan for Azure Hub and Spoke code generation
    query = "generate terraform code for azure hub and spoke model with environment staging by NetworkOps"
    context = {}
    
    plan_result = await agent.plan(query, context)
    assert plan_result["status"] == "success"
    assert plan_result["context"]["action"] == "generate"
    
    # 2. Execute plan to generate the HCL code
    exec_result = await agent.execute(plan_result)
    assert exec_result["status"] == "success"
    assert exec_result["result"]["action"] == "generate"
    
    generated_code = exec_result["result"]["code"]
    
    # 3. Assert correct resource definitions are in the generated HCL code
    assert 'resource "azurerm_resource_group" "rg"' in generated_code
    assert 'name     = "rg-hub-spoke-staging"' in generated_code
    assert 'resource "azurerm_virtual_network" "hub"' in generated_code
    assert 'resource "azurerm_virtual_network" "spoke"' in generated_code
    assert 'resource "azurerm_virtual_network_peering" "hub_to_spoke"' in generated_code
    assert 'resource "azurerm_virtual_network_peering" "spoke_to_hub"' in generated_code
    
    # Check compliance tags
    assert 'Environment = "Staging"' in generated_code
    assert 'Owner       = "networkops"' in generated_code
    
    # 4. Perform static security auditing / validation on the generated HCL code
    validation_result = TerraformAuditor.validate_hcl(generated_code)
    
    # Assert validation passes with zero findings/violations
    assert validation_result["status"] == "pass"
    assert validation_result["finding_count"] == 0
    assert len(validation_result["findings"]) == 0
    
    print("\n✓ Azure Hub-and-Spoke model HCL validation passed with zero security violations.")
