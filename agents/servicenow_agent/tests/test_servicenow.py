"""
Tests for ServiceNow Agent plugin and Mock REST client.
"""

import sys
from pathlib import Path
import pytest

# Insert ServiceNow agent folder to sys.path to enable isolated imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.snow_client import ServiceNowClient
from main import ServiceNowAgent


@pytest.fixture
def client():
    """Create a ServiceNowClient instance."""
    return ServiceNowClient(offline=True)


@pytest.fixture
def agent():
    """Create a ServiceNowAgent instance."""
    return ServiceNowAgent()


# ===========================================================================
# Client Unit Tests
# ===========================================================================

def test_lookup_incident_success(client):
    """Test retrieving details of an existing ticket."""
    inc = client.lookup_incident("INC00102")
    assert inc is not None
    assert inc["number"] == "INC00102"
    assert "Memory leak" in inc["short_description"]
    assert inc["category"] == "platform"


def test_lookup_incident_failure(client):
    """Test retrieving details of an invalid ticket."""
    inc = client.lookup_incident("INC99999")
    assert inc is None


def test_search_incidents_by_category(client):
    """Test searching incidents using category keyword."""
    incidents = client.search_incidents("database")
    assert len(incidents) >= 1
    assert incidents[0]["number"] == "INC00101"


def test_search_incidents_by_desc(client):
    """Test searching incidents using description text."""
    incidents = client.search_incidents("leak")
    assert len(incidents) == 1
    assert incidents[0]["number"] == "INC00102"


def test_detect_similar_incidents(client):
    """Test TF-IDF overlap similarity matching against logs."""
    similar = client.detect_similar_incidents("Critical pool exhaustion in our database connection settings")
    assert len(similar) >= 1
    # INC00101 contains database connection pool exhausted close notes
    assert similar[0]["number"] == "INC00101"


def test_get_resolution_trends(client):
    """Test aggregate status and assignment workload trends."""
    trends = client.get_resolution_trends()
    assert trends["total_incidents"] == 5
    assert trends["closed_incidents"] == 4
    assert trends["active_incidents"] == 1
    assert "DBA Operations" in trends["assignment_groups_distribution"]


# ===========================================================================
# Agent Unit Tests
# ===========================================================================

def test_agent_can_handle_intent(agent):
    """Test keyword and direct match handling queries."""
    assert agent.can_handle("show ticket INC00102") is True
    assert agent.can_handle("find database failures in snow") is True
    assert agent.can_handle("analyze ticket resolution trends") is True
    assert agent.can_handle("unrelated prompt about coding python") is False


@pytest.mark.asyncio
async def test_agent_plan_lookup(agent):
    """Test planning a ticket lookup action."""
    plan_dict = await agent.plan("show incident INC00102", {})
    assert plan_dict["status"] == "success"
    assert len(plan_dict["steps"]) > 0
    assert plan_dict["context"]["action"] == "lookup"
    assert plan_dict["context"]["ticket_number"] == "INC00102"


@pytest.mark.asyncio
async def test_agent_plan_trends(agent):
    """Test planning a stats/trends action."""
    plan_dict = await agent.plan("give me incident resolution trends", {})
    assert plan_dict["status"] == "success"
    assert plan_dict["context"]["action"] == "trends"


@pytest.mark.asyncio
async def test_agent_execute_lookup_success(agent):
    """Test execution workflow for looking up an existing ticket."""
    plan_dict = await agent.plan("get details for INC00101", {})
    result = await agent.execute(plan_dict)
    
    assert result["status"] == "success"
    assert result["result"]["found"] is True
    assert result["result"]["incident"]["number"] == "INC00101"


@pytest.mark.asyncio
async def test_agent_execute_search(agent):
    """Test execution workflow for searching incident logs."""
    plan_dict = await agent.plan("find tickets about disk space critical", {})
    result = await agent.execute(plan_dict)
    
    assert result["status"] == "success"
    assert result["result"]["count"] >= 1
    assert result["result"]["incidents"][0]["number"] == "INC00104"


@pytest.mark.asyncio
async def test_agent_summarize_lookup(agent):
    """Test generation of SRE markdown report for single ticket lookup."""
    plan_dict = await agent.plan("show INC00104", {})
    result = await agent.execute(plan_dict)
    summary = await agent.summarize(result)
    
    assert "INC00104" in summary
    assert "Disk space critical" in summary
    assert "logrotate" in summary
