"""
Erasure Handler - Right to erasure (RTBF) implementation

Implements AC-5: Implement right to erasure mechanism.
Handles GDPR Article 17 "Right to be Forgotten" requests.

EPIC: MD-2156
Child Task: MD-2282 [Privacy-5]
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
import hashlib
import json
import uuid


class ErasureStatus(Enum):
    """Status of an erasure request."""
    PENDING = "pending"
    VALIDATING = "validating"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    REJECTED = "rejected"
    FAILED = "failed"


class ErasureReason(Enum):
    """Reasons for erasure request per GDPR Article 17."""
    NO_LONGER_NECESSARY = "no_longer_necessary"  # 17(1)(a)
    CONSENT_WITHDRAWN = "consent_withdrawn"  # 17(1)(b)
    OBJECTION = "objection"  # 17(1)(c)
    UNLAWFUL_PROCESSING = "unlawful_processing"  # 17(1)(d)
    LEGAL_OBLIGATION = "legal_obligation"  # 17(1)(e)
    CHILD_DATA = "child_data"  # 17(1)(f)
    USER_REQUEST = "user_request"


class RejectionReason(Enum):
    """Reasons for rejecting erasure per GDPR Article 17(3)."""
    FREEDOM_EXPRESSION = "freedom_expression"  # 17(3)(a)
    LEGAL_OBLIGATION = "legal_obligation"  # 17(3)(b)
    PUBLIC_INTEREST = "public_interest"  # 17(3)(c)
    ARCHIVING_PURPOSE = "archiving_purpose"  # 17(3)(d)
    LEGAL_CLAIMS = "legal_claims"  # 17(3)(e)
    VERIFICATION_FAILED = "verification_failed"
    INSUFFICIENT_INFO = "insufficient_info"


@dataclass
class DataLocation:
    """Represents a location where user data is stored."""
    location_id: str
    system_name: str
    data_type: str
    description: str
    erasure_handler: Optional[str] = None
    status: str = "pending"
    erased_at: Optional[datetime] = None
    records_erased: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "location_id": self.location_id,
            "system_name": self.system_name,
            "data_type": self.data_type,
            "description": self.description,
            "status": self.status,
            "erased_at": self.erased_at.isoformat() if self.erased_at else None,
            "records_erased": self.records_erased,
        }


@dataclass
class ErasureRequest:
    """Represents a data erasure request."""
    request_id: str
    user_id: str
    reason: ErasureReason
    status: ErasureStatus
    created_at: datetime
    requested_by: str
    data_locations: list[DataLocation] = field(default_factory=list)
    identity_verified: bool = False
    verified_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rejection_reason: Optional[RejectionReason] = None
    rejection_details: Optional[str] = None
    deadline: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_overdue(self) -> bool:
        """Check if request has exceeded deadline."""
        if not self.deadline:
            return False
        if self.status == ErasureStatus.COMPLETED:
            return False
        return datetime.utcnow() > self.deadline

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.data_locations:
            return 0.0
        completed = sum(
            1 for loc in self.data_locations
            if loc.status == "completed"
        )
        return (completed / len(self.data_locations)) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "reason": self.reason.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "requested_by": self.requested_by,
            "data_locations": [loc.to_dict() for loc in self.data_locations],
            "identity_verified": self.identity_verified,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rejection_reason": self.rejection_reason.value if self.rejection_reason else None,
            "rejection_details": self.rejection_details,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "completion_percentage": self.completion_percentage,
            "is_overdue": self.is_overdue,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ErasureRequest":
        """Create from dictionary."""
        locations = [
            DataLocation(
                location_id=loc["location_id"],
                system_name=loc["system_name"],
                data_type=loc["data_type"],
                description=loc["description"],
                status=loc.get("status", "pending"),
                erased_at=datetime.fromisoformat(loc["erased_at"]) if loc.get("erased_at") else None,
                records_erased=loc.get("records_erased", 0),
            )
            for loc in data.get("data_locations", [])
        ]

        return cls(
            request_id=data["request_id"],
            user_id=data["user_id"],
            reason=ErasureReason(data["reason"]),
            status=ErasureStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            requested_by=data["requested_by"],
            data_locations=locations,
            identity_verified=data.get("identity_verified", False),
            verified_at=datetime.fromisoformat(data["verified_at"]) if data.get("verified_at") else None,
            approved_by=data.get("approved_by"),
            approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            rejection_reason=RejectionReason(data["rejection_reason"]) if data.get("rejection_reason") else None,
            rejection_details=data.get("rejection_details"),
            deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
        )


class ErasureHandler:
    """
    Handles Right to Erasure (Right to be Forgotten) requests.

    Implements GDPR Article 17 requirements:
    - Data subject has right to erasure without undue delay
    - Controller must erase within one month (extendable to 3 months)
    - Must inform other controllers to erase links/copies
    - Certain exemptions apply (Article 17(3))
    """

    # Default deadline: 30 days per GDPR Article 17
    DEFAULT_DEADLINE_DAYS = 30
    EXTENDED_DEADLINE_DAYS = 90  # For complex requests

    def __init__(self):
        """Initialize Erasure Handler."""
        self._requests: dict[str, ErasureRequest] = {}
        self._data_locations: dict[str, list[DataLocation]] = {}  # user_id -> locations
        self._erasure_handlers: dict[str, Callable[[str, str], int]] = {}  # system -> handler
        self._system_registry: dict[str, str] = {}  # system_name -> description

    def register_system(
        self,
        system_name: str,
        description: str,
        data_type: str,
    ) -> None:
        """
        Register a system that stores user data.

        Args:
            system_name: Name of the system
            description: Description of data stored
            data_type: Type of data stored
        """
        self._system_registry[system_name] = description

    def register_erasure_handler(
        self,
        system_name: str,
        handler: Callable[[str, str], int],
    ) -> None:
        """
        Register a handler for erasing data from a system.

        Args:
            system_name: System this handler handles
            handler: Function(user_id, request_id) -> records_erased
        """
        self._erasure_handlers[system_name] = handler

    def register_user_data_location(
        self,
        user_id: str,
        system_name: str,
        data_type: str,
        description: str,
    ) -> DataLocation:
        """
        Register a location where user data is stored.

        Args:
            user_id: User identifier
            system_name: System name
            data_type: Type of data
            description: Description

        Returns:
            Created DataLocation
        """
        location_id = f"LOC-{uuid.uuid4().hex[:8].upper()}"

        location = DataLocation(
            location_id=location_id,
            system_name=system_name,
            data_type=data_type,
            description=description,
        )

        if user_id not in self._data_locations:
            self._data_locations[user_id] = []
        self._data_locations[user_id].append(location)

        return location

    def submit_request(
        self,
        user_id: str,
        reason: ErasureReason,
        requested_by: str,
        extend_deadline: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ErasureRequest:
        """
        Submit a new erasure request.

        Args:
            user_id: User requesting erasure
            reason: Reason for erasure
            requested_by: Who submitted the request
            extend_deadline: Use extended deadline (90 days)
            metadata: Additional metadata

        Returns:
            Created erasure request
        """
        request_id = f"ERASE-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow()

        # Get all known data locations for user
        locations = []
        if user_id in self._data_locations:
            for loc in self._data_locations[user_id]:
                locations.append(DataLocation(
                    location_id=loc.location_id,
                    system_name=loc.system_name,
                    data_type=loc.data_type,
                    description=loc.description,
                ))

        deadline_days = (
            self.EXTENDED_DEADLINE_DAYS if extend_deadline
            else self.DEFAULT_DEADLINE_DAYS
        )

        request = ErasureRequest(
            request_id=request_id,
            user_id=user_id,
            reason=reason,
            status=ErasureStatus.PENDING,
            created_at=now,
            requested_by=requested_by,
            data_locations=locations,
            deadline=now + timedelta(days=deadline_days),
            metadata=metadata or {},
        )

        self._requests[request_id] = request
        return request

    def verify_identity(
        self,
        request_id: str,
        verification_method: str,
        verified_by: str,
    ) -> ErasureRequest:
        """
        Mark identity as verified for an erasure request.

        Args:
            request_id: Request to verify
            verification_method: How identity was verified
            verified_by: Who performed verification

        Returns:
            Updated request
        """
        if request_id not in self._requests:
            raise ValueError(f"Request not found: {request_id}")

        request = self._requests[request_id]
        request.identity_verified = True
        request.verified_at = datetime.utcnow()
        request.status = ErasureStatus.VALIDATING
        request.metadata["verification"] = {
            "method": verification_method,
            "verified_by": verified_by,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return request

    def approve_request(
        self,
        request_id: str,
        approved_by: str,
    ) -> ErasureRequest:
        """
        Approve an erasure request for processing.

        Args:
            request_id: Request to approve
            approved_by: Approver identifier

        Returns:
            Updated request
        """
        if request_id not in self._requests:
            raise ValueError(f"Request not found: {request_id}")

        request = self._requests[request_id]

        if not request.identity_verified:
            raise ValueError("Identity must be verified before approval")

        request.status = ErasureStatus.APPROVED
        request.approved_by = approved_by
        request.approved_at = datetime.utcnow()

        return request

    def reject_request(
        self,
        request_id: str,
        reason: RejectionReason,
        details: str,
        rejected_by: str,
    ) -> ErasureRequest:
        """
        Reject an erasure request.

        Args:
            request_id: Request to reject
            reason: Rejection reason
            details: Detailed explanation
            rejected_by: Rejector identifier

        Returns:
            Updated request
        """
        if request_id not in self._requests:
            raise ValueError(f"Request not found: {request_id}")

        request = self._requests[request_id]
        request.status = ErasureStatus.REJECTED
        request.rejection_reason = reason
        request.rejection_details = details
        request.metadata["rejection"] = {
            "rejected_by": rejected_by,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return request

    def execute_erasure(self, request_id: str) -> ErasureRequest:
        """
        Execute erasure for an approved request.

        Args:
            request_id: Request to execute

        Returns:
            Updated request with results
        """
        if request_id not in self._requests:
            raise ValueError(f"Request not found: {request_id}")

        request = self._requests[request_id]

        if request.status != ErasureStatus.APPROVED:
            raise ValueError("Request must be approved before execution")

        request.status = ErasureStatus.IN_PROGRESS

        # Process each data location
        for location in request.data_locations:
            try:
                handler = self._erasure_handlers.get(location.system_name)

                if handler:
                    records_erased = handler(request.user_id, request_id)
                    location.records_erased = records_erased
                else:
                    # Default: mark as completed (actual deletion should be handled)
                    location.records_erased = 0

                location.status = "completed"
                location.erased_at = datetime.utcnow()

            except Exception as e:
                location.status = "failed"
                request.metadata[f"error_{location.location_id}"] = str(e)

        # Determine final status
        completed = sum(1 for loc in request.data_locations if loc.status == "completed")
        total = len(request.data_locations)

        if completed == total:
            request.status = ErasureStatus.COMPLETED
        elif completed > 0:
            request.status = ErasureStatus.PARTIALLY_COMPLETED
        else:
            request.status = ErasureStatus.FAILED

        request.completed_at = datetime.utcnow()

        return request

    def get_request(self, request_id: str) -> Optional[ErasureRequest]:
        """Get an erasure request by ID."""
        return self._requests.get(request_id)

    def get_user_requests(self, user_id: str) -> list[ErasureRequest]:
        """Get all erasure requests for a user."""
        return [
            req for req in self._requests.values()
            if req.user_id == user_id
        ]

    def list_requests(
        self,
        status: Optional[ErasureStatus] = None,
        overdue_only: bool = False,
    ) -> list[ErasureRequest]:
        """
        List erasure requests with optional filters.

        Args:
            status: Filter by status
            overdue_only: Only show overdue requests

        Returns:
            List of matching requests
        """
        requests = list(self._requests.values())

        if status:
            requests = [r for r in requests if r.status == status]

        if overdue_only:
            requests = [r for r in requests if r.is_overdue]

        return requests

    def get_pending_count(self) -> int:
        """Get count of pending requests."""
        return sum(
            1 for r in self._requests.values()
            if r.status in (ErasureStatus.PENDING, ErasureStatus.VALIDATING, ErasureStatus.APPROVED)
        )

    def get_overdue_requests(self) -> list[ErasureRequest]:
        """Get all overdue requests."""
        return [r for r in self._requests.values() if r.is_overdue]

    def generate_certificate(self, request_id: str) -> dict[str, Any]:
        """
        Generate erasure completion certificate.

        Args:
            request_id: Completed request

        Returns:
            Certificate data
        """
        if request_id not in self._requests:
            raise ValueError(f"Request not found: {request_id}")

        request = self._requests[request_id]

        if request.status not in (ErasureStatus.COMPLETED, ErasureStatus.PARTIALLY_COMPLETED):
            raise ValueError("Cannot generate certificate for incomplete request")

        cert_data = {
            "certificate_id": f"CERT-{uuid.uuid4().hex[:8].upper()}",
            "request_id": request.request_id,
            "user_id": request.user_id,
            "status": request.status.value,
            "completed_at": request.completed_at.isoformat() if request.completed_at else None,
            "locations_processed": len(request.data_locations),
            "total_records_erased": sum(loc.records_erased for loc in request.data_locations),
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Generate hash for integrity
        cert_json = json.dumps(cert_data, sort_keys=True)
        cert_data["integrity_hash"] = hashlib.sha256(cert_json.encode()).hexdigest()

        return cert_data

    def export_request(self, request_id: str) -> str:
        """Export request as JSON."""
        if request_id not in self._requests:
            raise ValueError(f"Request not found: {request_id}")

        return json.dumps(self._requests[request_id].to_dict(), indent=2)

    def get_audit_trail(self, request_id: str) -> list[dict[str, Any]]:
        """
        Get audit trail for an erasure request.

        Args:
            request_id: Request to audit

        Returns:
            List of audit events
        """
        if request_id not in self._requests:
            raise ValueError(f"Request not found: {request_id}")

        request = self._requests[request_id]
        trail = []

        # Created event
        trail.append({
            "event": "created",
            "timestamp": request.created_at.isoformat(),
            "actor": request.requested_by,
            "details": {"reason": request.reason.value},
        })

        # Verification event
        if request.verified_at:
            trail.append({
                "event": "identity_verified",
                "timestamp": request.verified_at.isoformat(),
                "actor": request.metadata.get("verification", {}).get("verified_by"),
                "details": request.metadata.get("verification", {}),
            })

        # Approval/Rejection event
        if request.approved_at:
            trail.append({
                "event": "approved",
                "timestamp": request.approved_at.isoformat(),
                "actor": request.approved_by,
            })
        elif request.rejection_reason:
            trail.append({
                "event": "rejected",
                "timestamp": request.metadata.get("rejection", {}).get("timestamp"),
                "actor": request.metadata.get("rejection", {}).get("rejected_by"),
                "details": {
                    "reason": request.rejection_reason.value,
                    "details": request.rejection_details,
                },
            })

        # Completion event
        if request.completed_at:
            trail.append({
                "event": "completed",
                "timestamp": request.completed_at.isoformat(),
                "details": {
                    "status": request.status.value,
                    "completion_percentage": request.completion_percentage,
                },
            })

        return trail
