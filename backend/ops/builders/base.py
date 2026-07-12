import abc
from typing import Dict, Any, Tuple
import logging

from .verification import SequentialVerificationPipeline

logger = logging.getLogger("poltergeist_builder")

class CapabilityBuilder(abc.ABC):
    """
    Base class for all Poltergeist autonomous capability builders.
    Defines the standard interface: prepare -> generate -> compile -> package -> verify
    """
    
    def __init__(self, fingerprint: str, target_revision: int, manifest: Dict[str, Any]):
        self.fingerprint = fingerprint
        self.target_revision = target_revision
        self.manifest = manifest
        self.source_code = ""
        self.artifact_bytes = b""
        
    @abc.abstractmethod
    async def generate_source(self) -> str:
        """
        Generates the raw source code for the capability based on the manifest.
        Must be implemented by specialized builders.
        """
        pass
        
    async def compile_and_package(self, source_code: str) -> bytes:
        """
        Compiles the source code into a deployable artifact format (e.g., standard zip with main.py).
        """
        import zipfile
        import io
        
        # Package into a zip archive in-memory
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("main.py", source_code)
            # Write a standard metadata file if needed
            import json
            zf.writestr("manifest.json", json.dumps(self.manifest))
            
        return mem_zip.getvalue()
        
    async def build(self) -> Tuple[bool, Dict[str, str], bytes]:
        """
        Executes the full build lifecycle.
        Returns (is_successful, verification_results, artifact_bytes)
        """
        logger.info(f"[{self.fingerprint}] Starting builder lifecycle")
        
        try:
            # 1. Generate
            self.source_code = await self.generate_source()
            if not self.source_code:
                return False, {"error": "Generation failed"}, b""
                
            # 2. Package
            self.artifact_bytes = await self.compile_and_package(self.source_code)
            
            # 3. Verify
            is_valid, verification_results = await SequentialVerificationPipeline.run_all_checks(
                self.fingerprint, self.source_code, self.manifest
            )
            
            return is_valid, verification_results, self.artifact_bytes
            
        except Exception as e:
            logger.error(f"[{self.fingerprint}] Builder failed: {e}")
            return False, {"error": str(e)}, b""

