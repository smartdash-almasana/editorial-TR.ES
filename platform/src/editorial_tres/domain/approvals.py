"""Human approval gates for editorial change proposals."""

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator

from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.patches import Patch


ApprovalStatus = Literal["pending", "approved", "rejected"]


class ApprovalGate(BaseModel):
    """Immutable human decision boundary for one Patch proposal."""

    gate_id: str
    patch_id: str
    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    branch: str = "main"
    source_version: int
    required_role: str
    status: ApprovalStatus = "pending"
    decided_by: Optional[ActorId] = None
    decision_reason: Optional[str] = None
    decided_at: Optional[datetime] = None

    model_config = {"frozen": True}

    @field_validator("gate_id", "patch_id", "branch", "required_role")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El valor es obligatorio.")
        return value.strip()

    @model_validator(mode="after")
    def _decision_consistency(self) -> "ApprovalGate":
        if self.status == "pending":
            if self.decided_by is not None or self.decided_at is not None:
                raise ValueError("Una aprobación pendiente no puede tener decisión registrada.")
        elif self.decided_by is None or self.decided_at is None:
            raise ValueError("Una aprobación resuelta debe registrar actor y fecha.")
        return self

    @classmethod
    def for_patch(
        cls,
        patch: Patch,
        *,
        gate_id: str,
        required_role: str,
    ) -> "ApprovalGate":
        return cls(
            gate_id=gate_id,
            patch_id=patch.patch_id,
            tenant_id=patch.tenant_id,
            editorial_id=patch.editorial_id,
            work_id=patch.work_id,
            branch=patch.branch,
            source_version=patch.source_version,
            required_role=required_role,
        )

    def approve(
        self,
        *,
        actor_id: ActorId,
        reason: Optional[str] = None,
        decided_at: Optional[datetime] = None,
    ) -> "ApprovalGate":
        return self._decide("approved", actor_id, reason, decided_at)

    def reject(
        self,
        *,
        actor_id: ActorId,
        reason: Optional[str] = None,
        decided_at: Optional[datetime] = None,
    ) -> "ApprovalGate":
        return self._decide("rejected", actor_id, reason, decided_at)

    def _decide(
        self,
        status: Literal["approved", "rejected"],
        actor_id: ActorId,
        reason: Optional[str],
        decided_at: Optional[datetime],
    ) -> "ApprovalGate":
        if self.status != "pending":
            raise ValueError("Una compuerta ya resuelta no puede volver a decidirse.")
        normalized_reason = reason.strip() if reason and reason.strip() else None
        return self.model_copy(
            update={
                "status": status,
                "decided_by": actor_id,
                "decision_reason": normalized_reason,
                "decided_at": decided_at or datetime.now(timezone.utc),
            }
        )
