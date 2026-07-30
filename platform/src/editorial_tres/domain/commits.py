"""Editorial commits: immutable, stream-scoped event batches."""
from datetime import datetime, timezone
from typing import Optional, Tuple
from pydantic import BaseModel, Field, field_validator
from editorial_tres.domain.events import DomainEvent
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId

class EditorialCommit(BaseModel):
    commit_id: str
    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    branch: str = "main"
    parent_commit_id: Optional[str] = None
    parent_branch: Optional[str] = None
    parent_branch_version: Optional[int] = None
    events: Tuple[DomainEvent, ...] = Field(default_factory=tuple)
    message: str = ""
    actor_id: ActorId
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"frozen": True}

    @field_validator("events")
    @classmethod
    def _validate_events_not_empty(cls, value: Tuple[DomainEvent, ...]) -> Tuple[DomainEvent, ...]:
        if not value:
            raise ValueError("Un commit debe contener al menos un evento.")
        return value

    @field_validator("branch")
    @classmethod
    def _validate_branch(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El nombre de la rama no puede estar vacío.")
        return value.strip()
