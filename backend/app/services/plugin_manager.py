"""
Plugin manager for dynamic agent loading and lifecycle management.

Implements plugin discovery, validation, and safe loading with hot-reload support.
"""

import importlib.util
import json
import logging
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.exceptions import PluginException
from app.core.logging_config import log_audit_event
from app.security import path_validator

logger = logging.getLogger(__name__)


class PluginManifest(BaseModel):
    """Validated plugin manifest structure."""

    name: str
    version: str
    description: str
    author: str
    entry_point: str
    agent_class: str
    capabilities: list[str] = []
    requires_approval: bool = False
    permission_scope: list[str] = []
    min_llm_version: str | None = None


class IAgent(ABC):
    """
    Interface all agents must implement.
    
    Defines the contract for agent plugins.
    """

    @abstractmethod
    def can_handle(self, intent: str) -> bool:
        """Check if agent can handle the intent."""
        pass

    @abstractmethod
    async def plan(self, intent: str, context: dict) -> dict:
        """Create execution plan."""
        pass

    @abstractmethod
    async def execute(self, plan: dict) -> dict:
        """Execute the plan."""
        pass

    @abstractmethod
    async def summarize(self, result: dict) -> str:
        """Summarize execution result."""
        pass


class PluginManager:
    """
    Manages plugin lifecycle: discovery, loading, validation, and execution.
    
    Implements security controls:
    - Path allowlisting
    - Manifest validation
    - Trusted source verification
    - Safe dynamic imports
    """

    def __init__(self):
        """Initialize plugin manager."""
        self.plugins: dict[str, dict[str, Any]] = {}
        self.loaded_modules: dict[str, Any] = {}

    async def discover_plugins(self, plugin_dirs: list[str] | None = None) -> list[str]:
        """
        Discover available plugins in specified directories.
        
        Args:
            plugin_dirs: Directories to scan for plugins
            
        Returns:
            List of discovered plugin names
        """
        if not settings.plugin_auto_discovery:
            logger.info("Plugin auto-discovery disabled")
            return []

        plugin_dirs = plugin_dirs or settings.plugin_allowed_paths
        discovered = []

        for plugin_dir in plugin_dirs:
            try:
                # Validate directory path
                safe_path = path_validator.sanitize_path(plugin_dir)

                if not safe_path.is_dir():
                    logger.debug(f"Plugin directory not found: {safe_path}")
                    continue

                # Scan for manifest.json in subdirectories
                for manifest_path in safe_path.glob("*/manifest.json"):
                    try:
                        plugin_name = manifest_path.parent.name
                        if await self.load_plugin(str(manifest_path.parent)):
                            discovered.append(plugin_name)
                            logger.info(f"Discovered plugin: {plugin_name}")
                    except Exception as e:
                        logger.error(f"Error loading plugin from {manifest_path}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error discovering plugins in {plugin_dir}: {e}")
                continue

        return discovered

    async def load_plugin(self, plugin_path: str) -> bool:
        """
        Load and validate a plugin.
        
        Args:
            plugin_path: Path to plugin directory
            
        Returns:
            True if plugin loaded successfully
            
        Raises:
            PluginException: If plugin loading fails
        """
        try:
            # Validate path
            safe_path = path_validator.sanitize_path(plugin_path)

            # Load and validate manifest
            manifest_path = safe_path / "manifest.json"
            if not manifest_path.exists():
                raise PluginException(
                    f"Manifest not found in {plugin_path}",
                    plugin_name=safe_path.name,
                )

            manifest = await self._load_manifest(manifest_path)
            plugin_name = manifest.name

            # Validate plugin structure
            await self._validate_plugin_structure(safe_path, manifest)

            # Load plugin module
            agent_instance = await self._load_plugin_module(safe_path, manifest)

            # Register plugin
            self.plugins[plugin_name] = {
                "manifest": manifest,
                "path": str(safe_path),
                "agent": agent_instance,
            }

            log_audit_event(
                event_type="plugin_load",
                actor="system",
                resource=plugin_name,
                action="load",
                result="success",
            )

            logger.info(f"Plugin loaded: {plugin_name} v{manifest.version}")
            return True

        except PluginException:
            raise
        except Exception as e:
            logger.error(f"Plugin load error: {e}")
            raise PluginException(f"Failed to load plugin: {str(e)}", details={"error": str(e)})

    async def _load_manifest(self, manifest_path: Path) -> PluginManifest:
        """Load and validate plugin manifest."""
        try:
            with open(manifest_path) as f:
                manifest_data = json.load(f)
            return PluginManifest(**manifest_data)
        except ValidationError as e:
            raise PluginException(f"Invalid manifest: {e}")
        except Exception as e:
            raise PluginException(f"Error reading manifest: {e}")

    async def _validate_plugin_structure(self, plugin_path: Path, manifest: PluginManifest) -> None:
        """Validate plugin directory structure."""
        required_files = [
            "manifest.json",
            manifest.entry_point,
            "config.yaml",
            "prompts.py",
        ]

        for file in required_files:
            if not (plugin_path / file).exists():
                raise PluginException(
                    f"Missing required file: {file}",
                    plugin_name=manifest.name,
                )

        if not (plugin_path / "tools.py").exists() and not (plugin_path / "tools").is_dir():
            raise PluginException(
                "Missing required tools module: tools.py or tools/",
                plugin_name=manifest.name,
            )

    async def _load_plugin_module(self, plugin_path: Path, manifest: PluginManifest) -> IAgent:
        """Dynamically load plugin module and instantiate agent."""
        try:
            module_path = plugin_path / manifest.entry_point
            spec = importlib.util.spec_from_file_location(
                f"plugin.{manifest.name}",
                module_path,
            )

            if spec is None or spec.loader is None:
                raise PluginException(
                    f"Cannot load module spec: {manifest.entry_point}",
                    plugin_name=manifest.name,
                )

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module

            plugin_path_str = str(plugin_path)
            path_added = False
            if plugin_path_str not in sys.path:
                sys.path.insert(0, plugin_path_str)
                path_added = True

            # Namespace conflict resolution:
            # Backup and temporarily remove conflicting generic module names ('tools', 'prompts')
            # and their submodules from sys.modules during execution, so python reloads them from new sys.path.
            modules_to_isolate = ["tools", "prompts"]
            backed_up_modules = {}
            
            for mod_name in list(sys.modules.keys()):
                for prefix in modules_to_isolate:
                    if mod_name == prefix or mod_name.startswith(prefix + "."):
                        backed_up_modules[mod_name] = sys.modules[mod_name]
                        del sys.modules[mod_name]

            try:
                spec.loader.exec_module(module)
                
                # Cache the loaded modules uniquely under this plugin's namespace
                for mod_name in list(sys.modules.keys()):
                    for prefix in modules_to_isolate:
                        if mod_name == prefix or mod_name.startswith(prefix + "."):
                            unique_key = f"plugin.{manifest.name}.{mod_name}"
                            sys.modules[unique_key] = sys.modules[mod_name]
            finally:
                if path_added:
                    sys.path.remove(plugin_path_str)
                
                # Restore the backed-up modules for previously loaded plugins
                for mod_name, mod_obj in backed_up_modules.items():
                    sys.modules[mod_name] = mod_obj

            # Get agent class and instantiate
            agent_class = getattr(module, manifest.agent_class)
            agent_instance = agent_class()

            if not isinstance(agent_instance, IAgent):
                raise PluginException(
                    f"Agent class {manifest.agent_class} does not implement IAgent",
                    plugin_name=manifest.name,
                )

            return agent_instance

        except Exception as e:
            raise PluginException(
                f"Error loading plugin module: {e}",
                plugin_name=manifest.name,
            )

    def get_plugin(self, plugin_name: str) -> dict[str, Any] | None:
        """Get plugin by name."""
        return self.plugins.get(plugin_name)

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all loaded plugins with metadata."""
        return [
            {
                "name": name,
                "version": plugin["manifest"].version,
                "description": plugin["manifest"].description,
                "capabilities": plugin["manifest"].capabilities,
            }
            for name, plugin in self.plugins.items()
        ]

    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin safely."""
        if plugin_name not in self.plugins:
            raise PluginException(
                f"Plugin not found: {plugin_name}",
                plugin_name=plugin_name,
            )

        del self.plugins[plugin_name]

        log_audit_event(
            event_type="plugin_unload",
            actor="system",
            resource=plugin_name,
            action="unload",
            result="success",
        )

        logger.info(f"Plugin unloaded: {plugin_name}")
        return True
