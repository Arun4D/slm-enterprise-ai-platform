"""
Tests for API routes, including dual-agent routing logic.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from app.api.routes import chat_stream
from app.models.chat_models import ChatRequest


@pytest.mark.asyncio
async def test_dual_agent_routing_chat_stream():
    """Test that a query containing 'ansible' and 'terraform' triggers dual agent execution by calling the route handler directly."""
    
    # 1. Setup Mock Agent Registry and Mock Agents
    mock_registry = MagicMock()
    
    mock_ansible = MagicMock()
    mock_ansible.plan = AsyncMock(return_value={
        "status": "success",
        "steps": ["Scan Ansible libraries", "Validate playbook"],
        "context": {"action": "generate"}
    })
    mock_ansible.execute = AsyncMock(return_value={"status": "success", "result": {"action": "generate"}})
    mock_ansible.summarize = AsyncMock(return_value="Ansible Playbook details generated.")

    mock_terraform = MagicMock()
    mock_terraform.plan = AsyncMock(return_value={
        "status": "success",
        "steps": ["Choose HCL resources", "Validate tags"],
        "context": {"action": "generate"}
    })
    mock_terraform.execute = AsyncMock(return_value={"status": "success", "result": {"action": "generate"}})
    mock_terraform.summarize = AsyncMock(return_value="Terraform HCL details generated.")

    def get_agent_side_effect(agent_id):
        if agent_id == "ansible_agent":
            return {"plugin": {"agent": mock_ansible}, "metadata": MagicMock(name="Ansible Agent")}
        elif agent_id == "terraform_agent":
            return {"plugin": {"agent": mock_terraform}, "metadata": MagicMock(name="Terraform Agent")}
        raise Exception("Agent not found")

    mock_registry.get_agent.side_effect = get_agent_side_effect

    # 2. Patch database Session & app globals
    mock_db = MagicMock(spec=Session)
    mock_session = MagicMock()
    mock_session.title = "New Chat"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_session

    with patch("app.main.agent_registry", mock_registry), \
         patch("app.services.memory_repository.MemoryRepository.get_session", return_value=mock_session), \
         patch("app.services.memory_repository.MemoryRepository.add_message") as mock_add_message:

        # Prepare request
        request = ChatRequest(
            session_id="test-session-123",
            message="generate ansible and terraform code for nutanix vm migrate",
            agent_id="auto"
        )
        
        # Call the chat_stream handler directly
        response = await chat_stream(request, mock_db)
        
        # Consume the generator
        events = []
        async for chunk in response.body_iterator:
            lines = chunk.split("\n")
            for line in lines:
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        events.append("[DONE]")
                    else:
                        try:
                            events.append(json.loads(data_str))
                        except json.JSONDecodeError:
                            pass

        # Verify all events are present in sequence
        event_types = [e.get("event") for e in events if isinstance(e, dict)]
        assert "routing" in event_types
        assert "planning" in event_types
        assert "execution" in event_types
        assert "token" in event_types
        assert "session" in event_types
        assert "[DONE]" in events

        # Check routing data message
        routing_events = [e for e in events if isinstance(e, dict) and e.get("event") == "routing"]
        assert any("Dual-Agent Routing" in r.get("data", "") for r in routing_events)

        # Verify both mock agent methods were called
        mock_ansible.plan.assert_called_once()
        mock_ansible.execute.assert_called_once()
        mock_ansible.summarize.assert_called_once()

        mock_terraform.plan.assert_called_once()
        mock_terraform.execute.assert_called_once()
        mock_terraform.summarize.assert_called_once()
