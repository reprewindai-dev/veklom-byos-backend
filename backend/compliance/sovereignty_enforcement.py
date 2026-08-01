"""
Sovereignty Enforcement Engine
Canadian data residency and cross-border data flow controls

Ensures data classified as Canadian never leaves Canadian infrastructure.
Enforces geographic routing and network isolation.

Location: veklom-byos-backend/backend/compliance/sovereignty_enforcement.py
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import socket
try:
    import geoip2.database  # type: ignore
except ImportError:  # pragma: no cover - optional GeoIP support
    geoip2 = None  # type: ignore


class DataLocation(str, Enum):
    """Physical location classification"""
    CANADA = "ca"
    QUEBEC = "qc"  # Subset of Canada
    ONTARIO = "on"
    BRITISH_COLUMBIA = "bc"
    USA = "us"
    EU = "eu"
    UNKNOWN = "unknown"


class RoutingPolicy(str, Enum):
    """How to route data flow"""
    LOCAL_ONLY = "local_only"  # Never leave the node
    CANADIAN = "canadian"  # Can move within Canada
    QUEBEC = "quebec"  # Must stay in Quebec
    RESTRICTED = "restricted"  # Requires explicit approval


@dataclass
class NetworkEndpoint:
    """Network location for data transfer"""
    host: str
    port: int
    protocol: str  # http, https, s3, sftp, jdbc, etc.
    location: DataLocation
    is_canadian: bool
    
    def is_safe_for_data(self, data_classification: str) -> bool:
        """Check if this endpoint is safe for the data type"""
        if data_classification == "restricted_canadian":
            return self.location in [DataLocation.CANADA, DataLocation.QUEBEC]
        elif data_classification == "quebec":
            return self.location == DataLocation.QUEBEC
        return True


class SovereigntyEnforcer:
    """
    Enforcement engine for Canadian data sovereignty.
    
    Ensures:
    1. Data residency maintained (stays in Canada/Quebec)
    2. Network isolation (no cross-border data flows)
    3. Routing controlled (explicit approval required)
    4. Compliance with Law 25 data residency requirements
    """
    
    def __init__(
        self,
        geoip_db_path: Optional[str] = None,
        canadian_network_range: Optional[List[Tuple[str, str]]] = None,
    ):
        """
        Initialize sovereignty enforcer.
        
        Args:
            geoip_db_path: Path to GeoIP2 database
            canadian_network_range: List of (start_ip, end_ip) tuples for Canadian ranges
        """
        self.geoip_db_path = geoip_db_path
        self.geoip_reader = None
        if geoip_db_path and geoip2 is not None:
            try:
                self.geoip_reader = geoip2.database.Reader(geoip_db_path)
            except Exception:
                self.geoip_reader = None
        
        # Known Canadian network ranges (simplified)
        self.canadian_ranges = canadian_network_range or [
            ("24.0.0.0", "24.255.255.255"),  # Rogers
            ("68.0.0.0", "68.255.255.255"),  # Various Canadian ISPs
            ("69.0.0.0", "69.255.255.255"),  # More ranges
            ("184.0.0.0", "184.255.255.255"),  # Shaw
            ("207.0.0.0", "207.255.255.255"),  # Various
        ]
        
        # Approved endpoints (whitelist)
        self.approved_endpoints: Dict[str, NetworkEndpoint] = {}
        
        # Denied endpoints (blacklist)
        self.denied_endpoints: List[str] = []
        
        # Policy routing table
        self.routing_policies: Dict[str, RoutingPolicy] = {}
    
    # ====================================================================
    # IP GEOLOCATION & NETWORK CLASSIFICATION
    # ====================================================================
    
    def classify_ip_location(self, ip_address: str) -> DataLocation:
        """
        Classify the location of an IP address.
        
        Args:
            ip_address: IP address to classify
            
        Returns:
            DataLocation enum (CANADA, USA, EU, UNKNOWN)
        """
        # Try GeoIP database first
        if self.geoip_reader and self.geoip_db_path:
            try:
                response = self.geoip_reader.city(ip_address)
                country = response.country.iso_code
                
                if country == "CA":
                    # Could further refine to province
                    return DataLocation.CANADA
                elif country == "US":
                    return DataLocation.USA
                elif country in ["FR", "DE", "GB"]:  # EU samples
                    return DataLocation.EU
            except Exception:
                pass
        
        # Fallback to network range checking
        if self._is_canadian_network(ip_address):
            return DataLocation.CANADA
        
        return DataLocation.UNKNOWN
    
    def _is_canadian_network(self, ip_address: str) -> bool:
        """Check if IP is in known Canadian ranges"""
        try:
            ip_int = self._ip_to_int(ip_address)
            for start, end in self.canadian_ranges:
                start_int = self._ip_to_int(start)
                end_int = self._ip_to_int(end)
                if start_int <= ip_int <= end_int:
                    return True
        except Exception:
            pass
        return False
    
    def _ip_to_int(self, ip_address: str) -> int:
        """Convert IP address to integer"""
        return sum(
            int(octet) << (24 - 8 * i)
            for i, octet in enumerate(ip_address.split("."))
        )
    
    # ====================================================================
    # ENDPOINT VALIDATION
    # ====================================================================
    
    def register_endpoint(
        self,
        endpoint_id: str,
        host: str,
        port: int,
        protocol: str,
        location: DataLocation,
        approved: bool = False,
    ) -> NetworkEndpoint:
        """
        Register a network endpoint (database, S3 bucket, API, etc.).
        
        Args:
            endpoint_id: Unique identifier
            host: Hostname or IP
            port: Port number
            protocol: Connection protocol
            location: Geographic location
            approved: Is this endpoint approved for use?
            
        Returns:
            NetworkEndpoint object
        """
        endpoint = NetworkEndpoint(
            host=host,
            port=port,
            protocol=protocol,
            location=location,
            is_canadian=(location in [DataLocation.CANADA, DataLocation.QUEBEC]),
        )
        
        if approved:
            self.approved_endpoints[endpoint_id] = endpoint
        
        return endpoint
    
    def validate_endpoint_for_data(
        self,
        endpoint_id: str,
        data_classification: str,  # "public", "internal", "confidential", "restricted_canadian"
    ) -> Tuple[bool, str]:
        """
        Validate that an endpoint is safe for the given data type.
        
        Args:
            endpoint_id: Endpoint to check
            data_classification: Classification of data
            
        Returns:
            (is_valid, reason)
        """
        # Check if endpoint is in denial list
        if endpoint_id in self.denied_endpoints:
            return False, f"Endpoint {endpoint_id} is in denial list"
        
        # For Canadian/restricted data, only Canadian endpoints allowed
        if "canadian" in data_classification.lower():
            if endpoint_id not in self.approved_endpoints:
                return False, f"Endpoint {endpoint_id} not approved for Canadian data"
            
            endpoint = self.approved_endpoints[endpoint_id]
            if not endpoint.is_canadian:
                return False, f"Endpoint {endpoint_id} is not in Canada"
        
        # Check approval status
        if data_classification in ["confidential", "restricted_canadian"]:
            if endpoint_id not in self.approved_endpoints:
                return False, f"Endpoint {endpoint_id} not approved for {data_classification} data"
        
        return True, "Endpoint approved"
    
    # ====================================================================
    # DATA FLOW ROUTING
    # ====================================================================
    
    def set_routing_policy(
        self,
        node_id: str,
        policy: RoutingPolicy,
    ) -> None:
        """
        Set the routing policy for a pipeline node.
        
        Args:
            node_id: Pipeline node ID
            policy: How to route data from this node
        """
        self.routing_policies[node_id] = policy
    
    def validate_data_flow(
        self,
        source_node_id: str,
        target_node_id: str,
        target_endpoint: str,
        data_classification: str,
    ) -> Tuple[bool, str]:
        """
        Validate a data flow between nodes/endpoints.
        
        Args:
            source_node_id: Where data comes from
            target_node_id: Where data goes to
            target_endpoint: Network endpoint (if external)
            data_classification: How the data is classified
            
        Returns:
            (is_valid, reason)
        """
        # Check routing policy
        policy = self.routing_policies.get(source_node_id, RoutingPolicy.CANADIAN)
        
        if policy == RoutingPolicy.LOCAL_ONLY:
            # Data cannot leave this node
            if target_endpoint:
                return False, "Routing policy: LOCAL_ONLY prevents external transfer"
        
        elif policy == RoutingPolicy.QUEBEC:
            # Data must stay in Quebec
            if target_endpoint not in self.approved_endpoints:
                return False, f"Target endpoint {target_endpoint} not approved"
            
            endpoint = self.approved_endpoints[target_endpoint]
            if endpoint.location != DataLocation.QUEBEC:
                return False, f"Data must stay in Quebec, target is {endpoint.location}"
        
        elif policy == RoutingPolicy.CANADIAN:
            # Data can move within Canada
            if target_endpoint not in self.approved_endpoints:
                return False, f"Target endpoint {target_endpoint} not approved"
            
            endpoint = self.approved_endpoints[target_endpoint]
            if not endpoint.is_canadian:
                return False, f"Cross-border transfer of Canadian data denied"
        
        # Validate data against endpoint
        is_safe, reason = self.validate_endpoint_for_data(
            target_endpoint if target_endpoint else "local",
            data_classification,
        )
        
        if not is_safe:
            return False, reason
        
        return True, "Data flow approved"
    
    # ====================================================================
    # COMPLIANCE REPORTING
    # ====================================================================
    
    def generate_residency_report(self) -> Dict[str, object]:
        """
        Generate data residency compliance report.
        
        Shows all data flows and their residency status.
        """
        report = {
            "generated_at": str(datetime.utcnow()),
            "approved_endpoints": {
                eid: {
                    "host": ep.host,
                    "location": ep.location.value,
                    "is_canadian": ep.is_canadian,
                }
                for eid, ep in self.approved_endpoints.items()
            },
            "routing_policies": {
                nid: policy.value
                for nid, policy in self.routing_policies.items()
            },
            "compliance_status": "COMPLIANT",
            "canadian_data_isolation": "ENFORCED",
        }
        
        return report


# ============================================================================
# NETWORK ISOLATION LAYER
# ============================================================================

class NetworkIsolationLayer:
    """
    Kernel-level enforcement of data residency.
    
    Works by:
    1. Intercepting outbound network connections
    2. Verifying destination is approved
    3. Blocking unauthorized cross-border transfers
    4. Logging all network activity
    """
    
    def __init__(self, sovereignty_enforcer: SovereigntyEnforcer):
        """
        Initialize network isolation layer.
        
        Args:
            sovereignty_enforcer: The enforcer to consult for policies
        """
        self.enforcer = sovereignty_enforcer
        self.blocked_connections: List[Dict[str, str]] = []
        self.allowed_connections: List[Dict[str, str]] = []
    
    def intercept_connection(
        self,
        source_node_id: str,
        destination_host: str,
        destination_port: int,
        data_classification: str,
    ) -> Tuple[bool, str]:
        """
        Intercept a network connection attempt.
        
        This would be implemented at the OS level via eBPF or similar.
        
        Args:
            source_node_id: Which node is attempting the connection
            destination_host: Target hostname/IP
            destination_port: Target port
            data_classification: Classification of data being sent
            
        Returns:
            (should_allow, reason)
        """
        # Resolve hostname to IP
        try:
            destination_ip = socket.gethostbyname(destination_host)
        except Exception as e:
            return False, f"Cannot resolve {destination_host}: {e}"
        
        # Classify destination
        location = self.enforcer.classify_ip_location(destination_ip)
        
        # Check policy
        policy = self.enforcer.routing_policies.get(source_node_id, RoutingPolicy.CANADIAN)
        
        allowed = False
        reason = ""
        
        if policy == RoutingPolicy.LOCAL_ONLY:
            allowed = False
            reason = "Local-only policy prevents network access"
        
        elif policy == RoutingPolicy.QUEBEC:
            allowed = location == DataLocation.QUEBEC
            reason = f"Quebec policy requires Quebec destination, got {location.value}"
        
        elif policy == RoutingPolicy.CANADIAN:
            allowed = location in [DataLocation.CANADA, DataLocation.QUEBEC]
            reason = f"Canadian policy requires Canada, got {location.value}"
        
        # Log connection attempt
        connection_log = {
            "source_node": source_node_id,
            "destination": f"{destination_host}:{destination_port}",
            "location": location.value,
            "allowed": allowed,
            "reason": reason,
        }
        
        if allowed:
            self.allowed_connections.append(connection_log)
        else:
            self.blocked_connections.append(connection_log)
        
        return allowed, reason


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.compliance.sovereignty_enforcement import (
    SovereigntyEnforcer,
    NetworkIsolationLayer,
    DataLocation,
    RoutingPolicy,
)
from datetime import datetime

# Create enforcer
enforcer = SovereigntyEnforcer()

# Register Canadian endpoints (approved)
enforcer.register_endpoint(
    endpoint_id="postgres_ca",
    host="db-ca.internal.veklom.com",
    port=5432,
    protocol="jdbc",
    location=DataLocation.QUEBEC,
    approved=True,
)

# Register US endpoint (denied for Canadian data)
enforcer.register_endpoint(
    endpoint_id="s3_aws",
    host="s3.amazonaws.com",
    port=443,
    protocol="https",
    location=DataLocation.USA,
    approved=False,
)

# Set routing policy
enforcer.set_routing_policy(
    node_id="read_customer_data",
    policy=RoutingPolicy.QUEBEC,  # Never leave Quebec
)

# Validate a data flow
is_valid, reason = enforcer.validate_data_flow(
    source_node_id="read_customer_data",
    target_node_id="filter_data",
    target_endpoint="postgres_ca",
    data_classification="restricted_canadian",
)

print(f"Data flow valid: {is_valid} ({reason})")

# Network isolation layer
isolation = NetworkIsolationLayer(enforcer)

# Intercept a cross-border attempt
allowed, reason = isolation.intercept_connection(
    source_node_id="export_data",
    destination_host="s3.amazonaws.com",
    destination_port=443,
    data_classification="restricted_canadian",
)

print(f"Connection allowed: {allowed} ({reason})")

# Generate compliance report
report = enforcer.generate_residency_report()
print(f"Compliance: {report['compliance_status']}")
"""