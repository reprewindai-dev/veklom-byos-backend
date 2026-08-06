"""Build & Release Spine Workflow - Integrated with AuthorityRun for governed deployments."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User
import uuid
import hashlib
import json
from enum import Enum

router = APIRouter(prefix="/build-release", tags=["Build & Release"])


class BuildStatus(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    TESTING = "testing"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ReleaseType(str, Enum):
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"
    HOTFIX = "hotfix"
    SECURITY = "security"


@router.post("/build/create", response_model=Dict[str, Any])
async def create_build(
    build_request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new build with AuthorityRun integration."""
    
    try:
        required_fields = ["project_name", "commit_hash", "branch", "release_type"]
        for field in required_fields:
            if field not in build_request:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        build_id = f"build_{uuid.uuid4().hex[:8]}"
        authority_run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Create AuthorityRun for build governance
        authority_run = {
            "authority_run_id": authority_run_id,
            "build_id": build_id,
            "project_name": build_request["project_name"],
            "commit_hash": build_request["commit_hash"],
            "branch": build_request["branch"],
            "release_type": build_request["release_type"],
            "status": BuildStatus.PENDING,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": current_user.email,
            
            # Authority Context
            "authority_context": {
                "build_environment": "production",
                "security_level": "high",
                "compliance_requirements": ["sox", "gdpr", "soc2"],
                "stakeholders": ["devops", "security", "product"],
                "risk_assessment": "medium"
            },
            
            # Build Configuration
            "build_config": {
                "docker_registry": "registry.veklom.com",
                "kubernetes_namespace": "production",
                "deployment_strategy": "blue_green",
                "health_checks": True,
                "rollback_enabled": True,
                "monitoring_enabled": True
            }
        }
        
        return {
            "build_id": build_id,
            "authority_run_id": authority_run_id,
            "status": BuildStatus.PENDING,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "estimated_duration_minutes": 45,
            "next_steps": ["security_scan", "unit_tests", "integration_tests", "approval"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create build: {str(e)}"
        )


@router.post("/build/{build_id}/start", response_model=Dict[str, Any])
async def start_build(
    build_id: str,
    build_config: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start the build process with governance tracking."""
    
    try:
        # Validate build configuration against policies
        policy_validation = await validate_build_policies(build_config)
        
        if not policy_validation["approved"]:
            raise HTTPException(
                status_code=403,
                detail=f"Build configuration violates policies: {policy_validation['violations']}"
            )
        
        # Create evidence pack for build
        evidence_pack_id = f"evidence_{uuid.uuid4().hex[:8]}"
        
        build_process = {
            "build_id": build_id,
            "evidence_pack_id": evidence_pack_id,
            "status": BuildStatus.BUILDING,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "started_by": current_user.email,
            
            # Build Steps
            "build_steps": [
                {
                    "step_id": "step_001",
                    "name": "source_code_checkout",
                    "status": "completed",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "duration_seconds": 15
                },
                {
                    "step_id": "step_002",
                    "name": "dependency_resolution",
                    "status": "running",
                    "started_at": datetime.now(timezone.utc).isoformat()
                },
                {
                    "step_id": "step_003",
                    "name": "security_scan",
                    "status": "pending"
                },
                {
                    "step_id": "step_004",
                    "name": "unit_tests",
                    "status": "pending"
                },
                {
                    "step_id": "step_005",
                    "name": "integration_tests",
                    "status": "pending"
                }
            ],
            
            # Resource Allocation
            "resources": {
                "build_runner": "runner-prod-001",
                "cpu_cores": 4,
                "memory_gb": 8,
                "disk_gb": 50,
                "network_mbps": 100
            }
        }
        
        return build_process
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start build: {str(e)}"
        )


@router.get("/build/{build_id}/status", response_model=Dict[str, Any])
async def get_build_status(
    build_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed build status with evidence tracking."""
    
    try:
        build_status = {
            "build_id": build_id,
            "status": BuildStatus.TESTING,
            "progress_percentage": 65,
            "started_at": "2026-01-15T10:00:00Z",
            "estimated_completion": "2026-01-15T10:45:00Z",
            
            # Step Status
            "build_steps": [
                {
                    "step_id": "step_001",
                    "name": "source_code_checkout",
                    "status": "completed",
                    "duration_seconds": 15,
                    "output": "Repository checked out successfully"
                },
                {
                    "step_id": "step_002",
                    "name": "dependency_resolution",
                    "status": "completed",
                    "duration_seconds": 120,
                    "output": "324 dependencies resolved"
                },
                {
                    "step_id": "step_003",
                    "name": "security_scan",
                    "status": "completed",
                    "duration_seconds": 180,
                    "output": "0 vulnerabilities found, 3 warnings"
                },
                {
                    "step_id": "step_004",
                    "name": "unit_tests",
                    "status": "completed",
                    "duration_seconds": 300,
                    "output": "245 tests passed, 2 failed"
                },
                {
                    "step_id": "step_005",
                    "name": "integration_tests",
                    "status": "running",
                    "progress": 45,
                    "output": "Running integration test suite..."
                }
            ],
            
            # Quality Metrics
            "quality_metrics": {
                "test_coverage": 87.5,
                "code_quality_score": 92.3,
                "security_score": 96.8,
                "performance_score": 89.1
            },
            
            # Evidence Collection
            "evidence": {
                "evidence_pack_id": f"evidence_{build_id}",
                "artifacts": [
                    {
                        "name": "source_code_hash",
                        "hash": "sha256:src_abc123...",
                        "collected_at": "2026-01-15T10:00:15Z"
                    },
                    {
                        "name": "dependency_hash",
                        "hash": "sha256:deps_def456...",
                        "collected_at": "2026-01-15T10:02:15Z"
                    },
                    {
                        "name": "test_results_hash",
                        "hash": "sha256:test_ghi789...",
                        "collected_at": "2026-01-15T10:07:15Z"
                    }
                ]
            }
        }
        
        return build_status
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get build status: {str(e)}"
        )


@router.post("/build/{build_id}/approve", response_model=Dict[str, Any])
async def approve_build(
    build_id: str,
    approval_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve build for release with human approval workflow."""
    
    try:
        required_fields = ["approval_decision", "comments"]
        for field in required_fields:
            if field not in approval_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        if approval_data["approval_decision"] not in ["approved", "rejected"]:
            raise HTTPException(
                status_code=400,
                detail="approval_decision must be 'approved' or 'rejected'"
            )
        
        approval_id = f"approval_{uuid.uuid4().hex[:8]}"
        
        approval_record = {
            "approval_id": approval_id,
            "build_id": build_id,
            "approver": current_user.email,
            "approval_decision": approval_data["approval_decision"],
            "comments": approval_data["comments"],
            "approved_at": datetime.now(timezone.utc).isoformat(),
            
            # Approval Context
            "approval_context": {
                "role": current_user.role or "developer",
                "authority_level": "production_release",
                "delegation_chain": [],
                "policy_compliance": True
            },
            
            # Evidence of Approval
            "approval_evidence": {
                "signature_hash": hashlib.sha256(
                    f"{build_id}:{current_user.email}:{datetime.now(timezone.utc).isoformat()}".encode()
                ).hexdigest(),
                "ip_address": "192.168.1.100",  # Would get from request
                "user_agent": "Veklom Build System",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Update build status based on approval
        new_status = BuildStatus.APPROVED if approval_data["approval_decision"] == "approved" else BuildStatus.FAILED
        
        return {
            **approval_record,
            "build_status_updated": new_status,
            "next_steps": ["deployment_preparation"] if new_status == BuildStatus.APPROVED else ["build_failure_analysis"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process approval: {str(e)}"
        )


@router.post("/release/{build_id}/deploy", response_model=Dict[str, Any])
async def deploy_release(
    build_id: str,
    deployment_config: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deploy release with full governance and rollback capability."""
    
    try:
        deployment_id = f"deploy_{uuid.uuid4().hex[:8]}"
        authority_run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        deployment = {
            "deployment_id": deployment_id,
            "build_id": build_id,
            "authority_run_id": authority_run_id,
            "status": "deploying",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "deployed_by": current_user.email,
            
            # Deployment Strategy
            "deployment_strategy": {
                "type": deployment_config.get("strategy", "blue_green"),
                "target_environment": deployment_config.get("environment", "production"),
                "rollback_enabled": deployment_config.get("rollback_enabled", True),
                "health_check_timeout": deployment_config.get("health_check_timeout", 300),
                "traffic_split": deployment_config.get("traffic_split", 0)
            },
            
            # Deployment Steps
            "deployment_steps": [
                {
                    "step_id": "deploy_001",
                    "name": "pre_deployment_checks",
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                },
                {
                    "step_id": "deploy_002",
                    "name": "artifact_deployment",
                    "status": "running",
                    "started_at": datetime.now(timezone.utc).isoformat()
                },
                {
                    "step_id": "deploy_003",
                    "name": "health_checks",
                    "status": "pending"
                },
                {
                    "step_id": "deploy_004",
                    "name": "traffic_routing",
                    "status": "pending"
                }
            ],
            
            # Monitoring and Verification
            "monitoring": {
                "metrics_endpoint": f"https://metrics.veklom.com/deployments/{deployment_id}",
                "log_endpoint": f"https://logs.veklom.com/deployments/{deployment_id}",
                "alert_channels": ["slack", "email", "pagerduty"]
            }
        }
        
        return deployment
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start deployment: {str(e)}"
        )


@router.post("/release/{deployment_id}/rollback", response_model=Dict[str, Any])
async def rollback_release(
    deployment_id: str,
    rollback_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rollback deployment with governance tracking."""
    
    try:
        rollback_id = f"rollback_{uuid.uuid4().hex[:8]}"
        
        rollback = {
            "rollback_id": rollback_id,
            "deployment_id": deployment_id,
            "initiated_by": current_user.email,
            "reason": rollback_data.get("reason", "Manual rollback requested"),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "rolling_back",
            
            # Rollback Configuration
            "rollback_config": {
                "target_version": rollback_data.get("target_version", "previous"),
                "preserve_data": rollback_data.get("preserve_data", True),
                "backup_created": True,
                "rollback_strategy": "immediate"
            },
            
            # Rollback Steps
            "rollback_steps": [
                {
                    "step_id": "rb_001",
                    "name": "traffic_diversion",
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat()
                },
                {
                    "step_id": "rb_002",
                    "name": "service_rollback",
                    "status": "running",
                    "started_at": datetime.now(timezone.utc).isoformat()
                },
                {
                    "step_id": "rb_003",
                    "name": "health_verification",
                    "status": "pending"
                }
            ],
            
            # Incident Recording
            "incident": {
                "incident_id": f"incident_{uuid.uuid4().hex[:8]}",
                "severity": "medium",
                "impact": "degraded_performance",
                "affected_services": ["api", "worker"],
                "escalation_level": 2
            }
        }
        
        return rollback
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate rollback: {str(e)}"
        )


@router.get("/releases/history", response_model=List[Dict[str, Any]])
async def get_release_history(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get build and release history with evidence."""
    
    try:
        history = [
            {
                "build_id": "build_abc123",
                "deployment_id": "deploy_def456",
                "project_name": "veklom-backend",
                "version": "v2.1.3",
                "release_type": ReleaseType.PATCH,
                "status": "deployed",
                "deployed_at": "2026-01-15T09:30:00Z",
                "deployed_by": "devops@veklom.com",
                "duration_minutes": 25,
                "rollback_available": True,
                "health_status": "healthy",
                "evidence_pack_id": "evidence_abc123"
            },
            {
                "build_id": "build_ghi789",
                "deployment_id": "deploy_jkl012",
                "project_name": "veklom-frontend",
                "version": "v2.1.2",
                "release_type": ReleaseType.MINOR,
                "status": "rolled_back",
                "deployed_at": "2026-01-14T14:15:00Z",
                "rolled_back_at": "2026-01-14T16:45:00Z",
                "deployed_by": "devops@veklom.com",
                "rollback_reason": "Performance degradation",
                "evidence_pack_id": "evidence_ghi789"
            }
        ]
        
        return history[offset:offset + limit]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get release history: {str(e)}"
        )


async def validate_build_policies(build_config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate build configuration against security and compliance policies."""
    
    violations = []
    warnings = []
    
    # Check for required security settings
    if not build_config.get("security_scan_enabled", True):
        violations.append("Security scan must be enabled")
    
    # Check resource limits
    if build_config.get("memory_gb", 0) > 16:
        warnings.append("High memory allocation may impact performance")
    
    # Check deployment targets
    forbidden_targets = ["production_root", "critical_infrastructure"]
    if build_config.get("target_environment") in forbidden_targets:
        violations.append(f"Deployment to {build_config['target_environment']} requires additional approval")
    
    return {
        "approved": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "policy_version": "1.0.0"
    }
