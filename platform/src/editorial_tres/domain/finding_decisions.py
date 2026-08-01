"""Explicit editorial decisions over non-destructive review findings."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import ReviewFinding


FindingDecisionStatus = Literal["pending", "accepted", "rejected", "escalated"]


class FindingDecision(BaseModel):
    """Immutable decision boundary between diagnosis and transformation."""

    decision_id: str
    finding_id: str
    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    branch: str = "main"
    source_version: int
    status: FindingDecisionStatus = "pending"
    decided_by: ActorId | None = None
    reason: str | None = None
    decided_at: datetime | None = None

    model_config = {"frozen": True}

    @field_validator("decision_id", "finding_id", "branch")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El valor es obligatorio.")
        return value.strip()

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def _decision_consistency(self) -> "FindingDecision":
        if self.status == "pending":
            if self.decided_by is not None or self.decided_at is not None:
                raise ValueError("Una decisión pendiente no puede registrar actor ni fecha.")
        elif self.decided_by is None or self.decided_at is None:
            raise ValueError("Una decisión resuelta debe registrar actor y fecha.")
        return self

    @classmethod
    def for_finding(cls, finding: ReviewFinding, *, decision_id: str) -> "FindingDecision":
        return cls(
            decision_id=decision_id,
            finding_id=finding.finding_id,
            tenant_id=finding.tenant_id,
            editorial_id=finding.editorial_id,
            work_id=finding.work_id,
            branch=finding.branch,
            source_version=finding.source_version,
        )

    def accept(self, *, actor_id: ActorId, reason: str | None = None, decided_at: datetime | None = None) -> "FindingDecision":
        return self._resolve("accepted", actor_id, reason, decided_at)

    def reject(self, *, actor_id: ActorId, reason: str | None = None, decided_at: datetime | None = None) -> "FindingDecision":
        return self._resolve("rejected", actor_id, reason, decided_at)

    def escalate(self, *, actor_id: ActorId, reason: str | None = None, decided_at: datetime | None = None) -> "FindingDecision":
        return self._resolve("escalated", actor_id, reason, decided_at)

    def _resolve(
        self,
        status: Literal["accepted", "rejected", "escalated"],
        actor_id: ActorId,
        reason: str | None,
        decided_at: datetime | None,
    ) -> "FindingDecision":
        if self.status != "pending":
            raise ValueError("Una decisión ya resuelta no puede volver a decidirse.")
        normalized_reason = reason.strip() if reason and reason.strip() else None
        return self.model_copy(
            update={
                "status": status,
                "decided_by": actor_id,
                "reason": normalized_reason,
                "decided_at": decided_at or datetime.now(timezone.utc),
            }
        )
