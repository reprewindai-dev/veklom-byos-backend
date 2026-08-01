"""CCPA compliance framework used by the multi-jurisdiction enforcer.

This module intentionally implements only local, auditable state transitions.
It does not send notifications, mutate external systems, or fabricate completed
consumer-right fulfillment. Callers receive deadlines and explicit pending status
so workflow code can fail closed or route to the appropriate backend worker.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Tuple


class CCPARequestStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass
class CCPARequestRecord:
    request_id: str
    user_id: str
    request_type: str
    received_at: datetime
    response_deadline: datetime
    status: CCPARequestStatus


class CCPAFramework:
    """Minimal CCPA enforcement surface for imports and fail-closed rights flow."""

    def __init__(self, organization_id: str):
        self.organization_id = organization_id
        self.opted_out_users: set[str] = set()
        self.requests: Dict[str, CCPARequestRecord] = {}
        self.breach_log: List[Dict[str, object]] = []
        self.audit_log: List[Dict[str, object]] = []

    def has_opted_out(self, user_id: str) -> bool:
        return user_id in self.opted_out_users

    def process_opt_out(self, user_id: str) -> str:
        opt_out_id = f"ccpa_opt_out_{user_id}_{datetime.utcnow().timestamp()}"
        self.opted_out_users.add(user_id)
        self.audit_log.append({
            "event": "CCPA_OPT_OUT_RECORDED",
            "opt_out_id": opt_out_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return opt_out_id

    def process_dsar(self, user_id: str) -> Dict[str, object]:
        record = self._record_request(user_id, "dsar", days=45)
        return {
            "request_id": record.request_id,
            "user_id": user_id,
            "status": record.status.value,
            "response_deadline": record.response_deadline.isoformat(),
            "data": {},
        }

    def process_deletion_request(self, user_id: str) -> Dict[str, object]:
        record = self._record_request(user_id, "deletion", days=45)
        return {
            "request_id": record.request_id,
            "user_id": user_id,
            "status": record.status.value,
            "response_deadline": record.response_deadline.isoformat(),
            "message": "Deletion request accepted for governed backend processing; no deletion is simulated here.",
        }

    def report_breach(
        self,
        breach_description: str,
        affected_consumers: int,
        breach_date: datetime,
    ) -> Tuple[str, datetime]:
        breach_id = f"ccpa_breach_{datetime.utcnow().timestamp()}"
        deadline = breach_date + timedelta(hours=24)
        self.breach_log.append({
            "breach_id": breach_id,
            "description": breach_description,
            "affected_consumers": affected_consumers,
            "breach_date": breach_date.isoformat(),
            "notification_deadline": deadline.isoformat(),
            "status": "pending_notification",
        })
        return breach_id, deadline

    def _record_request(self, user_id: str, request_type: str, days: int) -> CCPARequestRecord:
        now = datetime.utcnow()
        request_id = f"ccpa_{request_type}_{user_id}_{now.timestamp()}"
        record = CCPARequestRecord(
            request_id=request_id,
            user_id=user_id,
            request_type=request_type,
            received_at=now,
            response_deadline=now + timedelta(days=days),
            status=CCPARequestStatus.PENDING,
        )
        self.requests[request_id] = record
        self.audit_log.append({
            "event": "CCPA_REQUEST_RECORDED",
            "record": asdict(record),
        })
        return record
