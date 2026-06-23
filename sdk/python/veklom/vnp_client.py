"""VNP Enterprise Client — Handles route discovery, telemetry emission, and failover."""

import time
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import httpx

from .client import VeklomError

class VNPRouter:
    """
    VNP Enterprise Router for the Python SDK.
    Handles policy-aware routing and automatic telemetry emission.
    """

    def __init__(self, sdk_client, project_id: str, customer_id: str, policy_id: str):
        self.sdk = sdk_client
        self.project_id = project_id
        self.customer_id = customer_id
        self.policy_id = policy_id
        
        # In-memory route cache
        self._route_cache: Dict[str, Dict[str, Any]] = {}

    def _get_routes(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch or retrieve cached routes from VNP Beacon."""
        now = time.time()
        
        if not force_refresh and "routes" in self._route_cache:
            cache_entry = self._route_cache["routes"]
            if now < cache_entry["expires_at"]:
                return cache_entry["data"]

        # Fetch from VNP Beacon
        # Assuming the beacon expects standard auth or no auth depending on setup
        # For SDK, we use the _get from the parent client
        try:
            resp = self.sdk._get(
                f"/beacon/routes/resolve?customer_id={self.customer_id}&project_id={self.project_id}&policy_id={self.policy_id}"
            )
            
            candidates = resp.get("candidates", [])
            route_snapshot_id = resp.get("route_snapshot_id")
            ttl_seconds = resp.get("ttl_seconds", 30)
            
            self._route_cache["routes"] = {
                "data": candidates,
                "snapshot_id": route_snapshot_id,
                "expires_at": now + ttl_seconds
            }
            return candidates
        except Exception as e:
            # Fallback if beacon is unreachable
            return []

    def _emit_usage(
        self, 
        request_id: str,
        api_id: str, 
        provider_id: str, 
        success: bool, 
        response_ms: int, 
        http_status: int,
        retry_count: int,
        failover_count: int,
        billable_units: int,
        route_snapshot_id: str
    ):
        """Emit usage telemetry back to the VNP Control Plane."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Construct the payload according to VNP Ingest Spec
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "api_usage",
            "occurred_at": now,
            "customer_id": self.customer_id,
            "project_id": self.project_id,
            "credential_id": "sdk-cred-auto", # Usually populated by SDK initialization
            "policy_id": self.policy_id,
            "request": {
                "request_id": request_id,
                "api_id": api_id,
                "provider_id": provider_id,
                "provider_region": "unknown",
                "sdk_region": "local",
                "route_snapshot_id": route_snapshot_id
            },
            "usage": {
                "billable_units": billable_units,
                "unit_type": "tokens",
                "success": success,
                "response_ms": response_ms,
                "http_status": http_status,
                "retry_count": retry_count,
                "failover_count": failover_count
            },
            "commercial": {
                "pricing_tier_id": None,
                "preauth_amount_minor": None,
                "final_amount_minor": None,
                "currency": "USD"
            },
            "signature": {
                "alg": "none",
                "key_id": "unsigned",
                "sig": ""
            }
        }
        
        batch = {
            "batch_id": str(uuid.uuid4()),
            "events": [event]
        }
        
        # Fire and forget usage emission
        try:
            self.sdk._post("/ingest/usage-events", batch)
        except Exception:
            pass # Ignore telemetry emission failures in critical path

    def dispatch(self, api_id: str, payload: dict) -> dict:
        """
        Dispatches a payload using policy-aware routing and automatic failover.
        """
        routes = self._get_routes()
        
        # Filter routes by api_id
        valid_routes = [r for r in routes if r.get("api_id") == api_id]
        
        if not valid_routes:
            raise ValueError(f"No VNP routes found for API {api_id}")
            
        request_id = str(uuid.uuid4())
        route_snapshot_id = self._route_cache["routes"]["snapshot_id"]
        
        failover_count = 0
        
        for route in valid_routes:
            endpoint_url = route["endpoint_url"]
            provider_id = route["provider_id"]
            
            start_time = time.time()
            success = False
            status_code = 0
            response_data = None
            billable_units = 0
            
            try:
                # Execute request directly to the provider endpoint
                # In a real SDK this might require provider-specific auth injection
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(endpoint_url, json=payload)
                    status_code = resp.status_code
                    if resp.status_code < 400:
                        success = True
                        response_data = resp.json()
                        # Simple heuristic for tokens
                        billable_units = response_data.get("usage", {}).get("total_tokens", 1)
            except Exception as e:
                status_code = 0
                
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Always emit telemetry
            self._emit_usage(
                request_id=request_id,
                api_id=api_id,
                provider_id=provider_id,
                success=success,
                response_ms=latency_ms,
                http_status=status_code,
                retry_count=0,
                failover_count=failover_count,
                billable_units=billable_units,
                route_snapshot_id=route_snapshot_id
            )
            
            if success:
                return response_data
                
            # If not success, increment failover and try next route
            failover_count += 1
            
        raise VeklomError(500, f"All VNP routes failed for {api_id}. Failovers: {failover_count}")


class AsyncVNPRouter:
    """
    VNP Enterprise Router for the Async Python SDK.
    """

    def __init__(self, sdk_client, project_id: str, customer_id: str, policy_id: str):
        self.sdk = sdk_client
        self.project_id = project_id
        self.customer_id = customer_id
        self.policy_id = policy_id
        self._route_cache: Dict[str, Dict[str, Any]] = {}

    async def _get_routes(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        now = time.time()
        
        if not force_refresh and "routes" in self._route_cache:
            cache_entry = self._route_cache["routes"]
            if now < cache_entry["expires_at"]:
                return cache_entry["data"]

        try:
            resp = await self.sdk._http().get(
                f"{self.sdk.base_url}/beacon/routes/resolve?customer_id={self.customer_id}&project_id={self.project_id}&policy_id={self.policy_id}"
            )
            
            if resp.status_code < 400:
                data = resp.json()
                candidates = data.get("candidates", [])
                route_snapshot_id = data.get("route_snapshot_id")
                ttl_seconds = data.get("ttl_seconds", 30)
                
                self._route_cache["routes"] = {
                    "data": candidates,
                    "snapshot_id": route_snapshot_id,
                    "expires_at": now + ttl_seconds
                }
                return candidates
        except Exception:
            pass
        return []

    async def _emit_usage(self, **kwargs):
        now = datetime.now(timezone.utc).isoformat()
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "api_usage",
            "occurred_at": now,
            "customer_id": self.customer_id,
            "project_id": self.project_id,
            "credential_id": "sdk-cred-auto",
            "policy_id": self.policy_id,
            "request": {
                "request_id": kwargs["request_id"],
                "api_id": kwargs["api_id"],
                "provider_id": kwargs["provider_id"],
                "provider_region": "unknown",
                "sdk_region": "local",
                "route_snapshot_id": kwargs["route_snapshot_id"]
            },
            "usage": {
                "billable_units": kwargs["billable_units"],
                "unit_type": "tokens",
                "success": kwargs["success"],
                "response_ms": kwargs["response_ms"],
                "http_status": kwargs["http_status"],
                "retry_count": kwargs["retry_count"],
                "failover_count": kwargs["failover_count"]
            },
            "commercial": {
                "pricing_tier_id": None,
                "preauth_amount_minor": None,
                "final_amount_minor": None,
                "currency": "USD"
            },
            "signature": {
                "alg": "none",
                "key_id": "unsigned",
                "sig": ""
            }
        }
        
        batch = {
            "batch_id": str(uuid.uuid4()),
            "events": [event]
        }
        
        try:
            # We don't await this if we want fire and forget, but in Python async 
            # creating a task is better.
            asyncio.create_task(self.sdk._http().post(f"{self.sdk.base_url}/ingest/usage-events", json=batch))
        except Exception:
            pass

    async def dispatch(self, api_id: str, payload: dict) -> dict:
        routes = await self._get_routes()
        valid_routes = [r for r in routes if r.get("api_id") == api_id]
        
        if not valid_routes:
            raise ValueError(f"No VNP routes found for API {api_id}")
            
        request_id = str(uuid.uuid4())
        route_snapshot_id = self._route_cache["routes"]["snapshot_id"]
        
        failover_count = 0
        
        for route in valid_routes:
            endpoint_url = route["endpoint_url"]
            provider_id = route["provider_id"]
            
            start_time = time.time()
            success = False
            status_code = 0
            response_data = None
            billable_units = 0
            
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(endpoint_url, json=payload)
                    status_code = resp.status_code
                    if resp.status_code < 400:
                        success = True
                        response_data = resp.json()
                        billable_units = response_data.get("usage", {}).get("total_tokens", 1)
            except Exception:
                status_code = 0
                
            latency_ms = int((time.time() - start_time) * 1000)
            
            await self._emit_usage(
                request_id=request_id,
                api_id=api_id,
                provider_id=provider_id,
                success=success,
                response_ms=latency_ms,
                http_status=status_code,
                retry_count=0,
                failover_count=failover_count,
                billable_units=billable_units,
                route_snapshot_id=route_snapshot_id
            )
            
            if success:
                return response_data
                
            failover_count += 1
            
        raise VeklomError(500, f"All VNP routes failed for {api_id}. Failovers: {failover_count}")
