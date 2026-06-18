"""
Unit tests for the Terraform Agent and Auditor.
"""

import sys
from pathlib import Path
import pytest

# Insert Terraform agent folder to sys.path to enable isolated imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import TerraformAuditor
from main import TerraformAgent


@pytest.fixture
def agent():
    """Create a TerraformAgent instance."""
    return TerraformAgent()


# ===========================================================================
# Auditor Unit Tests
# ===========================================================================

def test_generate_hcl_default_vpc():
    """Test generating a default VPC when no custom parameters are supplied."""
    code = TerraformAuditor.generate_hcl("create vpc")
    assert 'resource "aws_vpc" "main"' in code
    assert 'cidr_block           = "10.0.0.0/16"' in code
    assert 'Environment = "Production"' in code
    assert 'Owner       = "Platform_Ops"' in code


def test_generate_hcl_custom_vpc():
    """Test that custom parameters (CIDR, environment, owner) are reflected in generated HCL."""
    params = {
        "resource_type": "vpc",
        "cidr_block": "192.168.1.0/24",
        "environment": "staging",
        "owner": "DevOps_Team"
    }
    code = TerraformAuditor.generate_hcl("create vpc", params)
    assert 'cidr_block           = "192.168.1.0/24"' in code
    assert 'Environment = "Staging"' in code
    assert 'Owner       = "DevOps_Team"' in code


def test_generate_hcl_custom_instance():
    """Test that custom instance type, AMI, and tags are reflected in the instance template."""
    params = {
        "resource_type": "instance",
        "instance_type": "t3.micro",
        "ami_id": "ami-0c55b159cbfafe1f0",
        "environment": "development",
        "owner": "AppSupport"
    }
    code = TerraformAuditor.generate_hcl("create instance", params)
    assert 'instance_type               = "t3.micro"' in code
    assert 'ami                         = "ami-0c55b159cbfafe1f0"' in code
    assert 'Environment = "Development"' in code
    assert 'Owner       = "AppSupport"' in code


# ===========================================================================
# Agent Integration Tests
# ===========================================================================

def test_agent_can_handle(agent):
    """Test agent can_handle triggers on Terraform keywords."""
    assert agent.can_handle("generate a terraform plan") is True
    assert agent.can_handle("validate my hcl code") is True
    assert agent.can_handle("check my springboot server logs") is False


@pytest.mark.anyio
async def test_agent_plan_generation(agent):
    """Test plan structure for generation actions."""
    plan = await agent.plan("create secure vpc in dev owned by database", {})
    assert plan["status"] == "success"
    assert plan["context"]["action"] == "generate"
    assert "Select compliant cloud resource blueprints" in plan["steps"]


@pytest.mark.anyio
async def test_agent_execute_generation(agent):
    """Test executing a custom generation prompt."""
    plan = await agent.plan("generate secure vpc with cidr 192.168.5.0/24 in staging by dbops", {})
    result = await agent.execute(plan)
    assert result["status"] == "success"
    assert result["result"]["action"] == "generate"
    
    code = result["result"]["code"]
    assert 'cidr_block           = "192.168.5.0/24"' in code
    assert 'Environment = "Staging"' in code
    assert 'Owner       = "dbops"' in code


@pytest.mark.anyio
async def test_agent_summarize(agent):
    """Test summarizing the generation result in Markdown."""
    plan = await agent.plan("generate secure vpc in dev", {})
    result = await agent.execute(plan)
    summary = await agent.summarize(result)
    assert "Terraform Infrastructure HCL Code Generator" in summary
    assert "resource \"aws_vpc\"" in summary
