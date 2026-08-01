"""GPC compliance gate for Phase 3 jurisdiction and residency checks.

The gate is intentionally metadata-driven. Existing graphs without compliance
metadata continue through the existing compiler path. Graphs that explicitly
classify data as restricted must satisfy the matching residency rule before
compile or execute can proceed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from backend.compliance.jurisdiction_detector import DataClassification
from backend.compliance.multi_jurisdiction_enforcement import AutoEnforcementMode, MultiJurisdictionEnforcer

_REGION_TO_LOCATION = {
    "ca-central-1": "quebec",
    "ca-west-1": "canada",
    "on-premise": "canada",
}


@dataclass(frozen=True)
class GPCComplianceGateResult:
    allowed: bool
    message: str
    frameworks: list[str]
    classification: str
    source_location: str
    target_location: str


def enforce_gpc_graph_compliance(graph: Any) -> GPCComplianceGateResult:
    """Run Phase 3 compliance enforcement for a GPC graph.

    Expected graph shape is ``backend.apps.gpc.schemas.GPCPipelineGraph`` but the
    implementation only reads stable fields so it is easy to test and reuse.
    """

    metadata = _metadata(graph)
    classification = _classification(metadata)
    target_location = _location(metadata, "target_location", graph)
    source_location = str(metadata.get("source_location") or target_location)
    user_location = metadata.get("user_location")
    endpoint_host = metadata.get("endpoint_host")
    endpoint_ip = metadata.get("endpoint_ip")

    enforcer = MultiJurisdictionEnforcer(mode=AutoEnforcementMode.STRICT, organization_id=str(getattr(graph, "tenant_id", "default")))
    frameworks = enforcer.auto_load_frameworks(
        endpoint_ip=str(endpoint_ip) if endpoint_ip else None,
        endpoint_host=str(endpoint_host) if endpoint_host else None,
        data_classification=classification,
        user_location=str(user_location) if user_location else source_location,
    )
    allowed, message = enforcer.auto_enforce_residency(
        data_classification=classification,
        source_location=source_location,
        target_location=target_location,
    )
    return GPCComplianceGateResult(
        allowed=allowed,
        message=message,
        frameworks=[framework.value for framework in frameworks],
        classification=classification.value,
        source_location=source_location,
        target_location=target_location,
    )


def _metadata(graph: Any) -> Mapping[str, Any]:
    value = getattr(graph, "metadata", None)
    return value if isinstance(value, Mapping) else {}


def _classification(metadata: Mapping[str, Any]) -> DataClassification:
    raw = str(metadata.get("data_classification") or DataClassification.INTERNAL.value).lower()
    try:
        return DataClassification(raw)
    except ValueError as exc:
        raise ValueError(f"Unsupported data_classification for GPC compliance gate: {raw}") from exc


def _location(metadata: Mapping[str, Any], key: str, graph: Any) -> str:
    if metadata.get(key):
        return str(metadata[key]).lower()
    region = str(getattr(graph, "data_residency_region", "") or "").lower()
    return _REGION_TO_LOCATION.get(region, region or "unknown")
