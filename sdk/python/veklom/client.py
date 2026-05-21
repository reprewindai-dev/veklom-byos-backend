import hmac
import hashlib
from typing import Optional, Union, Dict, Any
from pydantic import BaseModel, Field
import httpx

class VeklomResponse(BaseModel):
    """
    Standardized platform payload structure mapping exactly 
    to the Veklom Governance telemetry engine.
    """
    text: str = Field(..., description="The generated model inference text output")
    audit_log_id: str = Field(..., description="Tamper-evident cryptographic ledger entry signature")
    provider: str = Field(..., description="The physical execution provider routed (e.g., 'ollama' | 'groq')")
    tokens_used: int = Field(..., description="Exact token calculation consumed from the operating reserve")
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="Metadata envelope for audit reviews")

class VeklomClient:
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        access_token: Optional[str] = None,
        base_url: str = "https://api.veklom.com/v1"
    ):
        """
        Initializes the Veklom Control Plane connection interface.
        Accepts either a Vault-issued API Key or a raw JWT access token.
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"
        elif api_key:
            self.headers["X-Veklom-API-Key"] = api_key
        else:
            raise ValueError("Authentication credentials missing. Provide api_key or access_token.")

    def _prepare_payload(self, prompt: str, model: str, **kwargs) -> Dict[str, Any]:
        """Assembles standard corporate workspace variables."""
        return {
            "prompt": prompt,
            "model": model,
            "options": kwargs
        }

    def _process_response(self, json_data: Dict[str, Any]) -> VeklomResponse:
        """Transforms raw REST gateway data into validated Pydantic layouts."""
        return VeklomResponse(
            text=json_data["text"],
            audit_log_id=json_data["audit_log_id"],
            provider=json_data["provider"],
            tokens_used=json_data["tokens_used"],
            raw_payload=json_data.get("metadata", {})
        )

    def complete(self, prompt: str, model: str = "qwen2.5:1.5b", **kwargs) -> VeklomResponse:
        """
        Synchronous inference endpoint block. 
        Checks wallet balance, enforces pre-flight policies, and routes requests.
        """
        payload = self._prepare_payload(prompt, model, **kwargs)
        
        with httpx.Client(headers=self.headers, timeout=60.0) as client:
            response = client.post(f"{self.base_url}/complete", json=payload)
            if response.status_code == 200:
                return self._process_response(response.json())
            
            # Direct intercept for IronGrid Route Optimizer async handshakes
            elif response.status_code == 202:
                raise RuntimeError(
                    f"Transaction deferred by IronGrid: Task actively processing. Polling location: {response.headers.get('Location')}"
                )
            else:
                raise Exception(f"Veklom Governance Blocked Call [{response.status_code}]: {response.text}")

    async def complete_async(self, prompt: str, model: str = "qwen2.5:1.5b", **kwargs) -> VeklomResponse:
        """
        Asynchronous inference engine block. 
        Prevents thread-blocking I/O pauses during massive workforce load cycles.
        """
        payload = self._prepare_payload(prompt, model, **kwargs)
        
        async with httpx.AsyncClient(headers=self.headers, timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/complete", json=payload)
            if response.status_code == 200:
                return self._process_response(response.json())
            elif response.status_code == 202:
                raise RuntimeError(
                    f"Transaction deferred by IronGrid: Task actively processing. Polling location: {response.headers.get('Location')}"
                )
            else:
                raise Exception(f"Veklom Governance Blocked Call [{response.status_code}]: {response.text}")
