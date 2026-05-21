import httpx
from typing import Optional, Dict, Any, List
from .types import CompletionResponse

class VeklomClient:
    def __init__(self, api_key: Optional[str] = None, access_token: Optional[str] = None, base_url: str = "https://veklom.com/api/v1"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.access_token = access_token
        
        self.headers = {"Content-Type": "application/json"}
        if self.access_token:
            self.headers["Authorization"] = f"Bearer {self.access_token}"
        elif self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def _parse_response(self, data: Dict[str, Any]) -> CompletionResponse:
        choices = data.get("choices", [])
        text = choices[0].get("message", {}).get("content", "") if choices else ""
        
        # Parse usage mapping to tokens_used
        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens", usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0))

        provider = data.get("id", "unknown").split("-")[0] if "id" in data else "unknown"
        
        return CompletionResponse(
            id=data.get("id", ""),
            model=data.get("model", "unknown"),
            text=text,
            audit_log_id=data.get("audit_log_id"),
            provider=provider,
            tokens_used=tokens_used,
            cost_usd=data.get("cost_usd", 0.0),
            content_safety_score=data.get("content_safety_score", 1.0),
            raw_response=data
        )

    def complete(self, prompt: str, model: str = "gpt-4o-mini", **kwargs) -> CompletionResponse:
        """Synchronously execute a governed AI inference."""
        payload = {"prompt": prompt, "model": model, **kwargs}
        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            res = client.post("/ai/complete", json=payload)
            res.raise_for_status()
            return self._parse_response(res.json())

    async def complete_async(self, prompt: str, model: str = "gpt-4o-mini", **kwargs) -> CompletionResponse:
        """Asynchronously execute a governed AI inference."""
        payload = {"prompt": prompt, "model": model, **kwargs}
        async with httpx.AsyncClient(base_url=self.base_url, headers=self.headers) as client:
            res = await client.post("/ai/complete", json=payload)
            res.raise_for_status()
            return self._parse_response(res.json())
