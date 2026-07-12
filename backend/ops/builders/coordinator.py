from typing import Dict, Any, Tuple
import logging

from .openapi_builder import OpenAPIConnectorBuilder
from .transform_builder import PythonTransformBuilder
from .database_builder import DatabaseAdapterBuilder

logger = logging.getLogger("poltergeist_coordinator")

class AutonomousBuilderCoordinator:
    """
    Coordinates capability manufacturing.
    Inspects the requirement fingerprint/manifest and routes to the specialized builder.
    """
    
    @staticmethod
    async def build_capability(
        fingerprint: str, 
        target_revision: int, 
        manifest: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, str], bytes]:
        """
        Routes the build request to the correct specific capability builder.
        Returns (is_successful, verification_results, artifact_bytes)
        """
        capability_type = manifest.get("type", "unknown")
        logger.info(f"[{fingerprint}] Routing build for capability type: {capability_type}")
        
        # 1. Route to specialized builder
        if capability_type == "openapi_connector":
            builder = OpenAPIConnectorBuilder(fingerprint, target_revision, manifest)
        elif capability_type == "python_transform":
            builder = PythonTransformBuilder(fingerprint, target_revision, manifest)
        elif capability_type == "database_adapter":
            builder = DatabaseAdapterBuilder(fingerprint, target_revision, manifest)
        else:
            # Fallback
            logger.warning(f"[{fingerprint}] Unknown capability type '{capability_type}'. Falling back to generic OpenAPI.")
            builder = OpenAPIConnectorBuilder(fingerprint, target_revision, manifest)
            
        # 2. Execute full build lifecycle
        is_valid, verification_results, artifact_bytes = await builder.build()
        
        return is_valid, verification_results, artifact_bytes

