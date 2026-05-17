"""
Agent registry and lifecycle management.

Maintains agent health, metadata, and execution context.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from app.core.exceptions import AgentException, ResourceNotFoundException
from app.core.logging_config import log_audit_event
from app.models import AgentMetadata, AgentRegistry, AgentStatus
from app.services.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for all agents.
    
    Manages:
    - Agent metadata and discovery
    - Health monitoring
    - Execution context
    - Lifecycle tracking
    """

    def __init__(self, plugin_manager: PluginManager):
        """
        Initialize registry.
        
        Args:
            plugin_manager: PluginManager instance
        """
        self.plugin_manager = plugin_manager
        self.agents: dict[str, Any] = {}

    async def initialize(self) -> None:
        """Discover and register all available agents."""
        logger.info("Initializing agent registry...")

        # Discover plugins
        plugins = await self.plugin_manager.discover_plugins()
        logger.info(f"Discovered {len(plugins)} plugins")

        # Register each plugin as an agent
        for plugin_name in plugins:
            try:
                await self.register_agent(plugin_name)
            except Exception as e:
                logger.error(f"Error registering agent {plugin_name}: {e}")

    async def register_agent(self, agent_id: str) -> AgentRegistry:
        """
        Register an agent in the registry.
        
        Args:
            agent_id: Unique agent identifier
            
        Returns:
            Agent registry entry
            
        Raises:
            AgentException: If agent cannot be registered
        """
        plugin = self.plugin_manager.get_plugin(agent_id)
        if not plugin:
            raise AgentException(f"Plugin not found: {agent_id}", agent_name=agent_id)

        manifest = plugin["manifest"]
        metadata = AgentMetadata(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            author=manifest.author,
            tags=[],
            capabilities=manifest.capabilities,
            requires_approval=manifest.requires_approval,
            permission_scope=manifest.permission_scope,
        )

        agent_entry = {
            "id": agent_id,
            "metadata": metadata,
            "status": AgentStatus.HEALTHY,
            "enabled": True,
            "plugin": plugin,
            "last_health_check": datetime.utcnow(),
        }

        self.agents[agent_id] = agent_entry

        log_audit_event(
            event_type="agent_register",
            actor="system",
            resource=agent_id,
            action="register",
            result="success",
        )

        logger.info(f"Agent registered: {agent_id}")
        return agent_entry

    def get_agent(self, agent_id: str) -> Any:
        """
        Get agent by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent registry entry
            
        Raises:
            ResourceNotFoundException: If agent not found
        """
        if agent_id not in self.agents:
            raise ResourceNotFoundException("Agent", agent_id)
        return self.agents[agent_id]

    def list_agents(self) -> list[dict[str, Any]]:
        """List all registered agents."""
        return [
            {
                "id": agent_id,
                "name": entry["metadata"].name,
                "version": entry["metadata"].version,
                "status": entry["status"].value,
                "capabilities": entry["metadata"].capabilities,
                "enabled": entry["enabled"],
            }
            for agent_id, entry in self.agents.items()
        ]

    async def health_check(self, agent_id: str) -> bool:
        """
        Check agent health status.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if agent is healthy
        """
        agent = self.get_agent(agent_id)
        try:
            agent_instance = agent["plugin"]["agent"]

            # Verify agent implements required interface
            assert hasattr(agent_instance, "can_handle")
            assert hasattr(agent_instance, "plan")
            assert hasattr(agent_instance, "execute")
            assert hasattr(agent_instance, "summarize")

            agent["status"] = AgentStatus.HEALTHY
            agent["last_health_check"] = datetime.utcnow()
            return True

        except Exception as e:
            logger.error(f"Health check failed for {agent_id}: {e}")
            agent["status"] = AgentStatus.UNHEALTHY
            agent["error_message"] = str(e)
            return False

    async def health_check_all(self) -> dict[str, bool]:
        """Perform health checks on all agents."""
        results = {}
        tasks = [self.health_check(agent_id) for agent_id in self.agents.keys()]
        health_statuses = await asyncio.gather(*tasks, return_exceptions=True)

        for agent_id, status in zip(self.agents.keys(), health_statuses):
            results[agent_id] = status if isinstance(status, bool) else False

        return results

    def enable_agent(self, agent_id: str) -> None:
        """Enable an agent."""
        agent = self.get_agent(agent_id)
        agent["enabled"] = True

        log_audit_event(
            event_type="agent_enable",
            actor="system",
            resource=agent_id,
            action="enable",
            result="success",
        )

    def disable_agent(self, agent_id: str) -> None:
        """Disable an agent."""
        agent = self.get_agent(agent_id)
        agent["enabled"] = False

        log_audit_event(
            event_type="agent_disable",
            actor="system",
            resource=agent_id,
            action="disable",
            result="success",
        )

    async def execute_agent(
        self,
        agent_id: str,
        intent: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute an agent.
        
        Args:
            agent_id: Agent to execute
            intent: User intent/query
            context: Execution context
            
        Returns:
            Execution result
        """
        agent = self.get_agent(agent_id)

        if not agent["enabled"]:
            raise AgentException(f"Agent is disabled: {agent_id}", agent_name=agent_id)

        agent_instance = agent["plugin"]["agent"]

        try:
            # Check if agent can handle intent
            if not agent_instance.can_handle(intent):
                raise AgentException(
                    f"Agent cannot handle intent: {intent}",
                    agent_name=agent_id,
                )

            # Create execution plan
            plan = await agent_instance.plan(intent, context)

            # Execute plan
            result = await agent_instance.execute(plan)

            # Summarize result
            summary = await agent_instance.summarize(result)

            log_audit_event(
                event_type="agent_execute",
                actor="user",
                resource=agent_id,
                action="execute",
                result="success",
                details={"intent": intent},
            )

            return {
                "agent_id": agent_id,
                "status": "success",
                "result": result,
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"Agent execution error: {e}")

            log_audit_event(
                event_type="agent_execute",
                actor="user",
                resource=agent_id,
                action="execute",
                result="failure",
                details={"error": str(e)},
            )

            raise AgentException(
                f"Agent execution failed: {str(e)}",
                agent_name=agent_id,
                details={"error": str(e)},
            )
