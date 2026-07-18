"""
Capability Geometry Invariant (CGI) Evaluator.
Enforces the Multi-Builder Convergence Geometry bounding ratios:
I_C / G_C <= alpha
E_C / I_C >= beta
"""
import logging
from typing import Dict, Any
from backend.apps.api.routers.protocol import _CAPABILITY_GEOMETRY

logger = logging.getLogger(__name__)

class GeometryViolationException(Exception):
    def __init__(self, message: str, metrics: Dict[str, Any]):
        super().__init__(message)
        self.metrics = metrics

class GeometryEvaluator:
    def __init__(self):
        self.geometry_config = _CAPABILITY_GEOMETRY
        self.alpha = self.geometry_config["invariant_bounds"]["alpha"]
        self.beta = self.geometry_config["invariant_bounds"]["beta"]

    def extract_ic_gc_ec(self, pipeline_plan: Dict[str, Any]) -> Dict[str, float]:
        """
        Dynamically calculates Ic, Gc, Ec for a given pipeline plan based on the protocol manifest bounds
        and the specific plan's characteristics.
        """
        # I_C: Implementation Degrees of Freedom
        # Number of unique agents + tool calls + parallel branches
        agents_count = len(pipeline_plan.get("agents", []))
        tools_count = len(pipeline_plan.get("tools", []))
        branches = pipeline_plan.get("parallel_branches", 1)
        ic = agents_count + tools_count + branches

        # G_C: Governance Constraint Density
        # Base constraints from manifest + applied policies
        base_gc = self.geometry_config["ratios"]["governance_constraint_density"]["enforced_rbac_policies"]
        gc = base_gc + len(pipeline_plan.get("applied_policies", []))

        # E_C: Evidence Strength
        # Base evidence requirements + verifiable steps
        base_ec = self.geometry_config["ratios"]["evidence_strength"]["min_test_suites"]
        ec = base_ec + len(pipeline_plan.get("verifiable_checkpoints", []))

        return {"I_C": float(ic), "G_C": float(gc), "E_C": float(ec)}

    def evaluate_geometry(self, pipeline_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates if the pipeline plan satisfies the CGI inequalities.
        Raises GeometryViolationException if it fails.
        """
        metrics = self.extract_ic_gc_ec(pipeline_plan)
        ic = metrics["I_C"]
        gc = metrics["G_C"]
        ec = metrics["E_C"]

        # To prevent division by zero
        gc_safe = max(gc, 1.0)
        ic_safe = max(ic, 1.0)

        ratio_autonomy = ic / gc_safe
        ratio_evidence = ec / ic_safe

        is_valid_autonomy = ratio_autonomy <= self.alpha
        is_valid_evidence = ratio_evidence >= self.beta

        result = {
            "I_C": ic,
            "G_C": gc,
            "E_C": ec,
            "ratio_autonomy": ratio_autonomy,
            "ratio_evidence": ratio_evidence,
            "alpha": self.alpha,
            "beta": self.beta,
            "passed": is_valid_autonomy and is_valid_evidence,
            "violations": []
        }

        if not is_valid_autonomy:
            result["violations"].append(
                f"Autonomy bounds exceeded: I_C/G_C ({ratio_autonomy:.2f}) > alpha ({self.alpha})"
            )
            
        if not is_valid_evidence:
            result["violations"].append(
                f"Observability deficit: E_C/I_C ({ratio_evidence:.2f}) < beta ({self.beta})"
            )

        if not result["passed"]:
            logger.warning(f"Geometry Violation detected: {result['violations']}")
            raise GeometryViolationException(
                message="Workflow violates Capability Geometry Invariant (CGI). Execution halted to prevent agent drift.",
                metrics=result
            )

        return result
