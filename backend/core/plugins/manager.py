import os
import sys
import logging
import importlib
from pathlib import Path
from typing import Dict, Any, Type, Optional

from backend.core.plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)

class PluginManager:
    """Manages the lifecycle, discovery, and registry of all Veklom plugins."""
    
    def __init__(self):
        self._registry: Dict[str, BasePlugin] = {}
        self._plugin_classes: Dict[str, Type[BasePlugin]] = {}
        
        # Determine the plugins directory path
        core_dir = Path(__file__).resolve().parent.parent.parent
        self.plugins_dir = core_dir / "plugins"
        
    async def discover_plugins(self) -> None:
        """Dynamically loads plugin modules from the plugins directory."""
        if not self.plugins_dir.exists():
            logger.info(f"Plugins directory not found at {self.plugins_dir}. Skipping auto-discovery.")
            return

        # Ensure plugins dir is in sys.path
        if str(self.plugins_dir.parent) not in sys.path:
            sys.path.insert(0, str(self.plugins_dir.parent))

        for entry in self.plugins_dir.iterdir():
            if entry.is_dir() and not entry.name.startswith("__"):
                plugin_file = entry / "plugin.py"
                if plugin_file.exists():
                    try:
                        module_name = f"backend.plugins.{entry.name}.plugin"
                        module = importlib.import_module(module_name)
                        
                        # Find the BasePlugin implementation in the module
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (
                                isinstance(attr, type) 
                                and issubclass(attr, BasePlugin) 
                                and attr is not BasePlugin
                            ):
                                plugin_id = attr.name
                                self._plugin_classes[plugin_id] = attr
                                logger.info(f"Discovered plugin: {plugin_id} v{attr.version}")
                    except Exception as e:
                        logger.error(f"Failed to load plugin from {entry.name}: {str(e)}")

    async def initialize_plugin(self, plugin_id: str, config: Dict[str, Any]) -> None:
        """Initializes a discovered plugin with the given config."""
        plugin_class = self._plugin_classes.get(plugin_id)
        if not plugin_class:
            raise ValueError(f"Plugin {plugin_id} not found in discovered classes.")
            
        plugin_instance = plugin_class()
        await plugin_instance.initialize(config)
        self._registry[plugin_id] = plugin_instance
        logger.info(f"Initialized plugin: {plugin_id}")

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """Returns the initialized plugin instance."""
        return self._registry.get(plugin_id)
        
    def list_discovered_plugins(self) -> Dict[str, Any]:
        """Returns metadata for all discovered plugin classes."""
        return {
            plugin_id: {
                "name": cls.name,
                "version": cls.version,
                "description": cls.description,
            }
            for plugin_id, cls in self._plugin_classes.items()
        }

    async def shutdown_all(self) -> None:
        """Calls shutdown on all initialized plugins."""
        for plugin_id, plugin in self._registry.items():
            try:
                await plugin.shutdown()
                logger.info(f"Shut down plugin: {plugin_id}")
            except Exception as e:
                logger.error(f"Error shutting down plugin {plugin_id}: {str(e)}")
        self._registry.clear()

# Global Singleton
plugin_manager = PluginManager()
