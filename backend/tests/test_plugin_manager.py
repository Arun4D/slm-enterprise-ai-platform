"""
Tests for plugin manager.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import PluginException
from app.services.plugin_manager import PluginManager, PluginManifest


@pytest.fixture
def plugin_manager():
    """Create plugin manager instance."""
    return PluginManager()


@pytest.mark.asyncio
async def test_plugin_discovery_disabled(plugin_manager):
    """Test that discovery respects disable flag."""
    with patch("app.services.plugin_manager.settings.plugin_auto_discovery", False):
        result = await plugin_manager.discover_plugins()
        assert result == []


@pytest.mark.asyncio
async def test_load_plugin_manifest_validation(plugin_manager):
    """Test manifest validation."""
    with patch("app.services.plugin_manager.path_validator.sanitize_path") as mock_path:
        mock_path.side_effect = Exception("Path validation failed")
        
        with pytest.raises(PluginException):
            await plugin_manager.load_plugin("/invalid/path")


@pytest.mark.asyncio
async def test_list_plugins(plugin_manager):
    """Test listing plugins."""
    result = plugin_manager.list_plugins()
    assert isinstance(result, list)


def test_plugin_manifest_validation():
    """Test PluginManifest validation."""
    valid_manifest = {
        "name": "test_agent",
        "version": "1.0.0",
        "description": "Test agent",
        "author": "Test Author",
        "entry_point": "main.py",
        "agent_class": "TestAgent",
    }
    
    manifest = PluginManifest(**valid_manifest)
    assert manifest.name == "test_agent"
    assert manifest.version == "1.0.0"
