"""Domain events for the neoliterary kernel."""
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Literal, Mapping, Optional
from pydantic import BaseModel, Field, field_serializer, field_validator
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
class DomainEvent(BaseModel):
    event_id: str; event_type: str; tenant_id: TenantId; editorial_id: EditorialId; work_id: WorkId
    origin_event_id: Optional[str] = None
    aggregate_version: int = Field(..., ge=1); occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)); actor_id: ActorId
    payload: Mapping[str, Any] = Field(default_factory=dict); model_config = {"frozen": True}
    @field_validator("payload")
    @classmethod
    def _freeze_payload(cls, value): return MappingProxyType(dict(value))
    @field_serializer("payload")
    def _serialize_payload(self, value): return dict(value)
class ContentBlockAdded(DomainEvent): event_type: Literal["content_block.added"] = "content_block.added"
class ContentBlockEdited(DomainEvent): event_type: Literal["content_block.edited"] = "content_block.edited"
class DependencyRegistered(DomainEvent): event_type: Literal["dependency.registered"] = "dependency.registered"
class DerivedResourceInvalidated(DomainEvent): event_type: Literal["derived_resource.invalidated"] = "derived_resource.invalidated"
def create_work_created_event(**kwargs: Any) -> DomainEvent:
    return DomainEvent(event_type="work.created", aggregate_version=1, payload={"title": kwargs.pop("title"), "language": kwargs.pop("language"), "status": "conceived"}, **kwargs)
def create_content_block_added_event(*, block: Mapping[str, Any], **kwargs: Any) -> ContentBlockAdded: return ContentBlockAdded(payload={"block": dict(block)}, **kwargs)
def create_content_block_edited_event(*, block: Mapping[str, Any], **kwargs: Any) -> ContentBlockEdited: return ContentBlockEdited(payload={"block": dict(block)}, **kwargs)
def create_dependency_registered_event(*, dependency: Mapping[str, Any], **kwargs: Any) -> DependencyRegistered: return DependencyRegistered(payload={"dependency": dict(dependency)}, **kwargs)
def create_derived_resource_invalidated_event(*, source_resource_id: str, dependent_resource_id: str, source_version: int, **kwargs: Any) -> DerivedResourceInvalidated: return DerivedResourceInvalidated(payload={"source_resource_id": source_resource_id, "dependent_resource_id": dependent_resource_id, "source_version": source_version}, **kwargs)

