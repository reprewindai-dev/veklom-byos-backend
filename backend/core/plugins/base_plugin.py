from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePlugin(ABC):
    """Abstract base class that all Veklom plugins must implement."""
    
    name: str = "base_plugin"
    version: str = "1.0.0"
    description: str = "Abstract base plugin"

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Called once at plugin load. Set up connections, load models."""
        pass

    @abstractmethod
    async def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Called for each request routed to this plugin."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if plugin is healthy and ready."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up connections on shutdown."""
        pass
