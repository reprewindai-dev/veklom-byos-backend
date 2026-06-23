"""Veklom Python SDK — official client for the governed inference platform."""

from __future__ import annotations

import json
import os
from typing import AsyncIterator, Dict, Any, Iterator, Optional

import httpx

# ---------------------------------------------------------------------------
# Default base URL — override with VEKLOM_BASE_URL env var or constructor arg.
# The API lives at /api/v1, NOT at a separate api.veklom.com sub-domain for
# self-hosted deployments.  We keep both in the default chain.
# ---------------------------------------------------------------------------
_DEFAULT_BASE = os.getenv("VEKLOM_BASE_URL", "https://veklom.com/api/v1")


class VeklomError(Exception):
    """Raised when the Veklom API returns a non-2xx response."""

    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self.body = body
        super().__init__(f"[HTTP {status}] {body[:300]}")


# ---------------------------------------------------------------------------
# Sync client
# ---------------------------------------------------------------------------

from .vnp_client import VNPRouter, AsyncVNPRouter

class VeklomClient:
    """
    Synchronous Veklom API client.

    Usage::

        client = VeklomClient(api_key="vk-…")

        # One-shot completion
        r = client.complete("Summarise the Veklom governance model.")
        print(r["response_text"])

        # Streaming (yields str chunks)
        for chunk in client.complete_stream("Write a haiku about governed AI."):
            print(chunk, end="", flush=True)

        # Multi-turn chat
        r = client.chat("Hello!", session_id="demo-session")
        print(r["response_text"])

        # List models
        models = client.models()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        base_url: str = _DEFAULT_BASE,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        token = access_token or api_key or os.getenv("VEKLOM_API_KEY")
        if not token:
            raise ValueError(
                "No auth credential found. Pass api_key=, access_token=, or "
                "set the VEKLOM_API_KEY environment variable."
            )
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        # Initialize VNP Enterprise Routing
        # Real-world usage would pull project_id/customer_id from auth context
        self.vnp = VNPRouter(
            sdk_client=self,
            project_id="default-project",
            customer_id="default-customer",
            policy_id="default-policy"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        with httpx.Client(headers=self._headers, timeout=self.timeout) as http:
            resp = http.post(f"{self.base_url}{path}", json=body)
        if resp.status_code >= 400:
            raise VeklomError(resp.status_code, resp.text)
        return resp.json()

    def _get(self, path: str) -> Any:
        with httpx.Client(headers=self._headers, timeout=self.timeout) as http:
            resp = http.get(f"{self.base_url}{path}")
        if resp.status_code >= 400:
            raise VeklomError(resp.status_code, resp.text)
        return resp.json()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete(
        self,
        prompt: str,
        *,
        model: str = "llama3.2:latest",
        temperature: float = 0.7,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Single-shot completion. Returns the full API response dict."""
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "model": model,
            "temperature": temperature,
            **extra,
        }
        return self._post("/ai/complete", body)

    def complete_stream(
        self,
        prompt: str,
        *,
        model: str = "llama3.2:latest",
        temperature: float = 0.7,
        **extra: Any,
    ) -> Iterator[str]:
        """
        Streaming completion. Yields text chunks as they arrive.

        The backend's /ai/inference endpoint is used; chunks are decoded from
        Server-Sent Events (``data: {...}\\n\\n``).  Falls back to returning the
        full response_text when the server does not emit SSE.
        """
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "model": model,
            "temperature": temperature,
            "stream": True,
            **extra,
        }
        with httpx.Client(headers=self._headers, timeout=self.timeout) as http:
            with http.stream("POST", f"{self.base_url}/ai/inference", json=body) as resp:
                if resp.status_code >= 400:
                    resp.read()
                    raise VeklomError(resp.status_code, resp.text)
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            obj = json.loads(payload)
                            # SSE delta format
                            delta = (
                                obj.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            yield payload
                    else:
                        # Non-SSE line — try parsing as full response
                        try:
                            obj = json.loads(line)
                            text = obj.get("response_text", "")
                            if text:
                                yield text
                        except json.JSONDecodeError:
                            pass

    def chat(
        self,
        message: str,
        *,
        session_id: Optional[str] = None,
        model: str = "llama3.2:latest",
        temperature: float = 0.7,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Multi-turn chat with Redis-backed session memory (20-msg / 24h)."""
        body = {
            "messages": [{"role": "user", "content": message}],
            "model": model,
            "temperature": temperature,
            **extra,
        }
        if session_id:
            body["session_id"] = session_id
        return self._post("/ai/chat", body)

    def inference(self, prompt: str, *, model: str = "llama3.2:latest", **extra: Any) -> Dict[str, Any]:
        """Cached smart-tier inference (hot/warm cache aware)."""
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "model": model,
            **extra,
        }
        return self._post("/ai/inference", body)

    def models(self) -> list:
        """Return the list of available models."""
        return self._get("/ai/models")

    def providers(self) -> Dict[str, Any]:
        """Return available providers and default routing order."""
        return self._get("/ai/providers")

    def health(self) -> Dict[str, Any]:
        """Ping the platform health endpoint (no auth required)."""
        with httpx.Client(timeout=10.0) as http:
            base = self.base_url.replace("/api/v1", "")
            resp = http.get(f"{base}/health")
        if resp.status_code >= 400:
            raise VeklomError(resp.status_code, resp.text)
        return resp.json()


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------

class AsyncVeklomClient:
    """
    Async version of VeklomClient — drop-in for asyncio / FastAPI contexts.

    Usage::

        async with AsyncVeklomClient(api_key="vk-…") as client:
            r = await client.complete("Hello!")
            print(r["response_text"])

            async for chunk in client.complete_stream("Write a haiku."):
                print(chunk, end="")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        base_url: str = _DEFAULT_BASE,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        token = access_token or api_key or os.getenv("VEKLOM_API_KEY")
        if not token:
            raise ValueError("No auth credential found.")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self._client: Optional[httpx.AsyncClient] = None
        
        # Initialize VNP Enterprise Routing
        self.vnp = AsyncVNPRouter(
            sdk_client=self,
            project_id="default-project",
            customer_id="default-customer",
            policy_id="default-policy"
        )

    async def __aenter__(self) -> "AsyncVeklomClient":
        self._client = httpx.AsyncClient(headers=self._headers, timeout=self.timeout)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(headers=self._headers, timeout=self.timeout)
        return self._client

    async def complete(
        self,
        prompt: str,
        *,
        model: str = "llama3.2:latest",
        temperature: float = 0.7,
        **extra: Any,
    ) -> Dict[str, Any]:
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "model": model,
            "temperature": temperature,
            **extra,
        }
        resp = await self._http().post(f"{self.base_url}/ai/complete", json=body)
        if resp.status_code >= 400:
            raise VeklomError(resp.status_code, resp.text)
        return resp.json()

    async def complete_stream(
        self,
        prompt: str,
        *,
        model: str = "llama3.2:latest",
        temperature: float = 0.7,
        **extra: Any,
    ) -> AsyncIterator[str]:
        body = {
            "messages": [{"role": "user", "content": prompt}],
            "model": model,
            "temperature": temperature,
            "stream": True,
            **extra,
        }
        async with self._http().stream(
            "POST", f"{self.base_url}/ai/inference", json=body
        ) as resp:
            if resp.status_code >= 400:
                await resp.aread()
                raise VeklomError(resp.status_code, resp.text)
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    payload = line[6:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        obj = json.loads(payload)
                        delta = (
                            obj.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        yield payload
                else:
                    try:
                        obj = json.loads(line)
                        text = obj.get("response_text", "")
                        if text:
                            yield text
                    except json.JSONDecodeError:
                        pass

    async def chat(
        self,
        message: str,
        *,
        session_id: Optional[str] = None,
        model: str = "llama3.2:latest",
        **extra: Any,
    ) -> Dict[str, Any]:
        body = {
            "messages": [{"role": "user", "content": message}],
            "model": model,
            **extra,
        }
        if session_id:
            body["session_id"] = session_id
        resp = await self._http().post(f"{self.base_url}/ai/chat", json=body)
        if resp.status_code >= 400:
            raise VeklomError(resp.status_code, resp.text)
        return resp.json()

    async def models(self) -> list:
        resp = await self._http().get(f"{self.base_url}/ai/models")
        if resp.status_code >= 400:
            raise VeklomError(resp.status_code, resp.text)
        return resp.json()
