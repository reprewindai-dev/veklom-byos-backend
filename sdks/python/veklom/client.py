import requests
from typing import Optional, Dict, Any
from pydantic import BaseModel

class Response(BaseModel):
    text: str
    audit_log_id: str
    provider: str
    model: str
    latency_ms: int
    cost_usd: float

class VeklomClient:
    """
    Official Python client for governed inference via the Veklom API.
    """
    def __init__(self, api_key: str, base_url: str = "https://api.veklom.com/api/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "veklom-python-sdk/0.1.0"
        })

    def complete(self, model: str = "llama3.2:latest", messages: Optional[list] = None, prompt: Optional[str] = None, temperature: float = 0.7, **kwargs) -> Response:
        """
        Send a completion request to the governed inference engine.
        
        Args:
            model (str): The requested model identifier.
            messages (list, optional): A list of message dictionaries (e.g. [{"role": "user", "content": "..."}]).
            prompt (str, optional): Convenience shorthand for a single user message.
            temperature (float): Generation temperature.
            **kwargs: Additional parameters to pass to the API.
            
        Returns:
            Response: A structured object containing the text, audit ID, and provider info.
        """
        payload = {
            "model": model,
            "temperature": temperature,
            **kwargs
        }
        if messages is not None:
            payload["messages"] = messages
        elif prompt is not None:
            payload["messages"] = [{"role": "user", "content": prompt}]
        else:
            raise ValueError("Either 'messages' or 'prompt' must be provided.")
        
        url = f"{self.base_url}/ai/complete"
        res = self.session.post(url, json=payload)
        
        if not res.ok:
            raise Exception(f"Veklom API Error [{res.status_code}]: {res.text}")
            
        data = res.json()
        
        return Response(
            text=data.get("response_text", ""),
            audit_log_id=str(data.get("audit_id", "")),
            provider=data.get("provider", "unknown"),
            model=data.get("model", "unknown"),
            latency_ms=data.get("latency_ms", 0),
            cost_usd=data.get("cost_usd", 0.0)
        )
