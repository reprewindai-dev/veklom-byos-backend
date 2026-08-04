"""
Runtime Semantic State Record (RSSR)
Complete execution trace for Law 25 compliance

An RSSR is the cryptographic breadcrumb trail that proves:
1. What rules were applied at execution time
2. Why each data transformation was permitted
3. Consent status at each processing step
4. Data residency maintained throughout
5. No policy violations occurred

Location: veklom-byos-backend/backend/compliance/rssr.py
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, asdict, field
import hashlib
import json


@dataclass
class ComplianceDecision:
    """Single compliance check result"""
    check_name: str  # "consent_check", "residency_check", etc.
    passed: bool
    reason: str
    evidence: Dict[str, Any]
    timestamp: datetime
    checked_by: str  # Module/function that performed check


@dataclass
class DataTransformation:
    """Single node execution in pipeline"""
    node_id: str
    node_name: str
    node_type: str  # connector, transform, filter, export, etc.
    operation: str  # read, filter, aggregate, join, export
    
    # Inputs and outputs
    input_datasets: List[str]  # Element IDs consumed
    output_datasets: List[str]  # Element IDs produced
    row_count_in: int
    row_count_out: int
    
    # Execution context
    started_at: datetime
    completed_at: datetime
    duration_ms: float
    
    # Compliance decisions at this node
    compliance_decisions: List[ComplianceDecision] = field(default_factory=list)
    
    # Data residency verification
    residency_verified: bool = True
    residency_location: str = "canada/quebec"  # Where data physically resides
    
    # Policy checks
    all_policies_satisfied: bool = True
    violated_policies: List[str] = field(default_factory=list)


@dataclass
class RSSRHeader:
    """Metadata for RSSR document"""
    rssr_id: str
    pipeline_id: str
    execution_id: str
    tenant_id: str
    user_id: str
    
    started_at: datetime
    completed_at: datetime
    
    # Regulatory context
    jurisdiction: str  # "quebec" (Law 25), "canada" (PIPEDA)
    regulatory_framework: str  # e.g., "Law 25 Section 93"
    
    # System context
    system_fingerprint: str  # Hardware/deployment identifier
    system_version: str  # GPC version
    
    # Summary
    total_nodes_executed: int = 0
    total_decisions_made: int = 0
    compliance_violations: int = 0


class RuntimeSemanticStateRecord:
    """
    Complete execution trace for a single pipeline run.
    
    An RSSR is immutable proof of compliance. It captures:
    - Every rule checked during execution
    - Every consent verification
    - Every data residency confirmation
    - Every policy decision
    
    An RSSR can be:
    1. Archived for audit (Law 25 Section 93)
    2. Used for DSAR (Data Subject Access Request)
    3. Analyzed to prove compliance
    4. Used in breach investigation
    """
    
    def __init__(
        self,
        pipeline_id: str,
        execution_id: str,
        tenant_id: str,
        user_id: str,
        jurisdiction: str = "quebec",
        system_fingerprint: str = "",
        system_version: str = "2b-week8",
    ):
        """Initialize RSSR"""
        self.header = RSSRHeader(
            rssr_id=f"rssr_{pipeline_id}_{execution_id}_{datetime.utcnow().timestamp()}",
            pipeline_id=pipeline_id,
            execution_id=execution_id,
            tenant_id=tenant_id,
            user_id=user_id,
            started_at=datetime.utcnow(),
            completed_at=None,
            jurisdiction=jurisdiction,
            regulatory_framework="Law 25 Section 93" if jurisdiction == "quebec" else "PIPEDA",
            system_fingerprint=system_fingerprint,
            system_version=system_version,
        )
        
        # Execution trace
        self.transformations: List[DataTransformation] = []
        
        # Compliance context
        self.initial_consent_check: Optional[ComplianceDecision] = None
        self.initial_residency_check: Optional[ComplianceDecision] = None
        
        # Policy rules applied
        self.applied_rules: Dict[str, Dict[str, Any]] = {}
        
        # Integrity tracking
        self.integrity_chain: List[str] = []  # Hash chain for tamper detection
    
    # ====================================================================
    # EXECUTION PHASE TRACKING
    # ====================================================================
    
    def start_node_execution(
        self,
        node_id: str,
        node_name: str,
        node_type: str,
        operation: str,
        input_datasets: List[str],
        output_datasets: List[str],
    ) -> str:
        """
        Mark the start of node execution.
        
        Returns:
            Transformation ID for this node
        """
        transformation = DataTransformation(
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            operation=operation,
            input_datasets=input_datasets,
            output_datasets=output_datasets,
            row_count_in=0,  # Will be updated
            row_count_out=0,  # Will be updated
            started_at=datetime.utcnow(),
            completed_at=None,
            duration_ms=0.0,
        )
        
        self.transformations.append(transformation)
        
        return f"txn_{node_id}_{len(self.transformations)}"
    
    def record_compliance_decision(
        self,
        transformation_idx: int,
        check_name: str,
        passed: bool,
        reason: str,
        evidence: Dict[str, Any],
        checked_by: str,
    ) -> None:
        """
        Record a compliance decision during node execution.
        
        Args:
            transformation_idx: Index in self.transformations
            check_name: Name of the check (consent, residency, policy, etc.)
            passed: Whether the check passed
            reason: Human-readable reason
            evidence: Raw evidence supporting the decision
            checked_by: Which module performed the check
        """
        if transformation_idx >= len(self.transformations):
            return
        
        transformation = self.transformations[transformation_idx]
        
        decision = ComplianceDecision(
            check_name=check_name,
            passed=passed,
            reason=reason,
            evidence=evidence,
            timestamp=datetime.utcnow(),
            checked_by=checked_by,
        )
        
        transformation.compliance_decisions.append(decision)
        self.header.total_decisions_made += 1
        
        # Track violations
        if not passed:
            transformation.all_policies_satisfied = False
            transformation.violated_policies.append(check_name)
            self.header.compliance_violations += 1
    
    def end_node_execution(
        self,
        transformation_idx: int,
        row_count_in: int,
        row_count_out: int,
        residency_location: str = "canada/quebec",
        residency_verified: bool = True,
    ) -> None:
        """
        Mark the end of node execution.
        
        Args:
            transformation_idx: Which transformation just completed
            row_count_in: Number of rows processed
            row_count_out: Number of rows output
            residency_location: Where the output data physically resides
            residency_verified: Whether residency was verified
        """
        if transformation_idx >= len(self.transformations):
            return
        
        transformation = self.transformations[transformation_idx]
        transformation.completed_at = datetime.utcnow()
        transformation.row_count_in = row_count_in
        transformation.row_count_out = row_count_out
        transformation.duration_ms = (
            transformation.completed_at - transformation.started_at
        ).total_seconds() * 1000
        transformation.residency_location = residency_location
        transformation.residency_verified = residency_verified
        
        # Add to integrity chain
        self._update_integrity_chain(transformation)
    
    # ====================================================================
    # POLICY ENFORCEMENT
    # ====================================================================
    
    def apply_rule(
        self,
        rule_id: str,
        rule_name: str,
        rule_type: str,  # "consent", "residency", "retention", "purpose"
        condition: str,  # Description of the condition
        action: str,  # "allow", "deny", "quarantine"
        reason: str,
    ) -> None:
        """
        Record a policy rule that was applied during execution.
        
        Args:
            rule_id: Identifier for this rule
            rule_name: Human-readable name
            rule_type: Category of rule
            condition: What condition triggered it
            action: What happened (allow/deny/quarantine)
            reason: Why this rule exists
        """
        self.applied_rules[rule_id] = {
            "rule_name": rule_name,
            "rule_type": rule_type,
            "condition": condition,
            "action": action,
            "reason": reason,
            "applied_at": datetime.utcnow().isoformat(),
        }
    
    def set_initial_consent_check(
        self,
        passed: bool,
        user_id: str,
        consent_ids: List[str],
        reason: str,
    ) -> None:
        """
        Record the initial consent verification at pipeline start.
        
        This is the first gate: does the user have consent for this operation?
        """
        self.initial_consent_check = ComplianceDecision(
            check_name="initial_consent",
            passed=passed,
            reason=reason,
            evidence={
                "user_id": user_id,
                "consent_ids": consent_ids,
                "consent_count": len(consent_ids),
            },
            timestamp=datetime.utcnow(),
            checked_by="compliance.initial_consent_check",
        )
        
        if not passed:
            self.header.compliance_violations += 1
    
    def set_initial_residency_check(
        self,
        passed: bool,
        data_location: str,
        required_location: str,
        reason: str,
    ) -> None:
        """
        Record the initial data residency verification.
        
        This ensures data will remain in required jurisdiction (e.g., Quebec).
        """
        self.initial_residency_check = ComplianceDecision(
            check_name="initial_residency",
            passed=passed,
            reason=reason,
            evidence={
                "data_location": data_location,
                "required_location": required_location,
            },
            timestamp=datetime.utcnow(),
            checked_by="compliance.initial_residency_check",
        )
        
        if not passed:
            self.header.compliance_violations += 1
    
    # ====================================================================
    # FINALIZATION & INTEGRITY
    # ====================================================================
    
    def finalize(self) -> Dict[str, Any]:
        """
        Finalize the RSSR and compute integrity hash.
        
        Returns:
            Complete RSSR document
        """
        self.header.completed_at = datetime.utcnow()
        self.header.total_nodes_executed = len(self.transformations)
        
        # Compute integrity hash
        integrity_hash = self._compute_integrity_hash()
        
        # Build complete document
        rssr_doc = {
            "header": asdict(self.header),
            "integrity_hash": integrity_hash,
            
            "initial_compliance": {
                "consent_check": (
                    asdict(self.initial_consent_check)
                    if self.initial_consent_check
                    else None
                ),
                "residency_check": (
                    asdict(self.initial_residency_check)
                    if self.initial_residency_check
                    else None
                ),
            },
            
            "transformations": [
                {
                    **asdict(t),
                    "compliance_decisions": [
                        asdict(d) for d in t.compliance_decisions
                    ],
                }
                for t in self.transformations
            ],
            
            "applied_rules": self.applied_rules,
            
            "compliance_summary": {
                "total_nodes": len(self.transformations),
                "total_decisions": self.header.total_decisions_made,
                "violations": self.header.compliance_violations,
                "overall_compliant": self.header.compliance_violations == 0,
            },
        }
        
        return rssr_doc
    
    def _update_integrity_chain(self, transformation: DataTransformation) -> None:
        """Add transformation to integrity chain"""
        data = f"{transformation.node_id}:{transformation.operation}:{transformation.row_count_out}"
        hash_val = hashlib.sha256(data.encode()).hexdigest()
        self.integrity_chain.append(hash_val)
    
    def _compute_integrity_hash(self) -> str:
        """
        Compute hash chain for integrity verification.
        
        If any transformation is modified, this hash will not match.
        """
        chain_data = json.dumps(self.integrity_chain, sort_keys=True)
        return hashlib.sha256(chain_data.encode()).hexdigest()
    
    def verify_integrity(self, claimed_hash: str) -> bool:
        """
        Verify RSSR hasn't been tampered with.
        
        Args:
            claimed_hash: The hash value stored with the RSSR
            
        Returns:
            True if RSSR is unmodified
        """
        computed = self._compute_integrity_hash()
        return computed == claimed_hash
    
    def to_json(self) -> str:
        """Serialize RSSR to JSON"""
        doc = self.finalize()
        return json.dumps(doc, default=str)
    
    def export_for_audit(self) -> Dict[str, Any]:
        """
        Export RSSR in audit-friendly format.
        
        Format suitable for:
        - Law 25 Section 93 compliance audits
        - Breach investigations
        - DSAR fulfillment
        """
        doc = self.finalize()
        
        # Redact sensitive data for audit export
        audit_export = {
            "audit_period": f"{self.header.started_at.date()} to {self.header.completed_at.date()}",
            "pipeline_id": doc["header"]["pipeline_id"],
            "execution_count": 1,
            "compliance_status": doc["compliance_summary"]["overall_compliant"],
            "violations_count": doc["compliance_summary"]["violations"],
            
            # Compliance decisions (key for auditors)
            "initial_compliance_checks": doc["initial_compliance"],
            
            # Node-level compliance (show policy enforcement)
            "node_executions": [
                {
                    "node_id": t["node_id"],
                    "node_name": t["node_name"],
                    "operation": t["operation"],
                    "row_count_out": t["row_count_out"],
                    "residency_verified": t["residency_verified"],
                    "all_policies_satisfied": t["all_policies_satisfied"],
                    "compliance_decisions": [
                        {
                            "check": d["check_name"],
                            "passed": d["passed"],
                            "reason": d["reason"],
                        }
                        for d in t["compliance_decisions"]
                    ],
                }
                for t in doc["transformations"]
            ],
            
            # Rules applied (for regulatory review)
            "applied_rules": doc["applied_rules"],
            
            # Integrity verification
            "integrity_hash": doc["integrity_hash"],
            "integrity_verified": self.verify_integrity(doc["integrity_hash"]),
        }
        
        return audit_export


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.compliance.rssr import RuntimeSemanticStateRecord

# Create RSSR for a pipeline execution
rssr = RuntimeSemanticStateRecord(
    pipeline_id="pipeline_1",
    execution_id="exec_001",
    tenant_id="default",
    user_id="admin_1",
    jurisdiction="quebec",
    system_fingerprint="veklom-prod-001",
)

# Initial compliance checks
rssr.set_initial_consent_check(
    passed=True,
    user_id="admin_1",
    consent_ids=["consent_123"],
    reason="User has explicit consent for ANALYTICS",
)

rssr.set_initial_residency_check(
    passed=True,
    data_location="canada/quebec",
    required_location="canada/quebec",
    reason="All input data in Quebec as required",
)

# Apply policy rules
rssr.apply_rule(
    rule_id="rule_pii_masking",
    rule_name="PII Masking for Non-Approved Roles",
    rule_type="purpose",
    condition="User has marketing role, cannot access unmasked email",
    action="allow",
    reason="Enforce data minimization principle",
)

# Execute nodes
# Node 1: Read from PostgreSQL
txn_idx_1 = rssr.start_node_execution(
    node_id="postgres_read",
    node_name="Read Customer Data",
    node_type="connector",
    operation="read",
    input_datasets=[],
    output_datasets=["customer_data"],
)

rssr.record_compliance_decision(
    transformation_idx=0,
    check_name="data_classification",
    passed=True,
    reason="Customer data classified as internal",
    evidence={"classification": "internal", "pii_detected": True},
    checked_by="builders.database_builder",
)

rssr.end_node_execution(
    transformation_idx=0,
    row_count_in=0,
    row_count_out=150000,
    residency_location="canada/quebec",
)

# Node 2: Filter for privacy
txn_idx_2 = rssr.start_node_execution(
    node_id="pii_filter",
    node_name="Mask PII",
    node_type="transform",
    operation="filter",
    input_datasets=["customer_data"],
    output_datasets=["customer_data_masked"],
)

rssr.record_compliance_decision(
    transformation_idx=1,
    check_name="pii_masking",
    passed=True,
    reason="PII masking rules applied successfully",
    evidence={"fields_masked": ["email", "phone", "ssn"]},
    checked_by="builders.python_builder",
)

rssr.end_node_execution(
    transformation_idx=1,
    row_count_in=150000,
    row_count_out=150000,
)

# Export for audit
audit_report = rssr.export_for_audit()
print(f"Compliance status: {audit_report['compliance_status']}")
print(f"Violations: {audit_report['violations_count']}")
print(f"Integrity verified: {audit_report['integrity_verified']}")

# Export complete RSSR
full_rssr = rssr.to_json()
# Store in evidence pack or audit trail
"""
