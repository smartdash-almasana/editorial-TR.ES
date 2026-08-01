"""Domain events for the neoliterary kernel."""
from datetime import datetime, timezone
from typing import Any, Literal, Mapping, Optional
from pydantic import BaseModel, Field, field_serializer, field_validator
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.immutable_values import deep_freeze, deep_to_jsonable
class DomainEvent(BaseModel):
    event_id: str; event_type: str; tenant_id: TenantId; editorial_id: EditorialId; work_id: WorkId
    origin_event_id: Optional[str] = None
    aggregate_version: int = Field(..., ge=1); occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)); actor_id: ActorId
    payload: Mapping[str, Any] = Field(default_factory=dict); model_config = {"frozen": True}
    @field_validator("payload")
    @classmethod
    def _freeze_payload(cls, value): return deep_freeze(value)
    @field_serializer("payload", when_used="json")
    def _serialize_payload(self, value): return deep_to_jsonable(value)
class ContentBlockAdded(DomainEvent): event_type: Literal["content_block.added"] = "content_block.added"
class ContentBlockEdited(DomainEvent): event_type: Literal["content_block.edited"] = "content_block.edited"
class ContentBlockDeleted(DomainEvent): event_type: Literal["content_block.deleted"] = "content_block.deleted"
class ContentBlockMoved(DomainEvent): event_type: Literal["content_block.moved"] = "content_block.moved"
class DependencyRegistered(DomainEvent): event_type: Literal["dependency.registered"] = "dependency.registered"
class DerivedResourceInvalidated(DomainEvent): event_type: Literal["derived_resource.invalidated"] = "derived_resource.invalidated"
class ReviewFindingRecorded(DomainEvent): event_type: Literal["review.finding_recorded"] = "review.finding_recorded"
class ReviewFindingDecided(DomainEvent): event_type: Literal["review.finding_decided"] = "review.finding_decided"
def create_work_created_event(**kwargs: Any) -> DomainEvent:
    return DomainEvent(event_type="work.created", aggregate_version=1, payload={"title": kwargs.pop("title"), "language": kwargs.pop("language"), "status": "conceived"}, **kwargs)
def create_content_block_added_event(*, block: Mapping[str, Any], **kwargs: Any) -> ContentBlockAdded: return ContentBlockAdded(payload={"block": dict(block)}, **kwargs)
def create_content_block_edited_event(*, block: Mapping[str, Any], **kwargs: Any) -> ContentBlockEdited: return ContentBlockEdited(payload={"block": dict(block)}, **kwargs)
def create_content_block_deleted_event(*, block_id: str, before_block: Mapping[str, Any], **kwargs: Any) -> ContentBlockDeleted: return ContentBlockDeleted(payload={"block_id": block_id, "before_block": dict(before_block)}, **kwargs)
def create_content_block_moved_event(*, block_id: str, before_parent_id: Optional[str], before_position: int, after_parent_id: Optional[str], after_position: int, **kwargs: Any) -> ContentBlockMoved: return ContentBlockMoved(payload={"block_id": block_id, "before_parent_id": before_parent_id, "before_position": before_position, "after_parent_id": after_parent_id, "after_position": after_position}, **kwargs)
def create_dependency_registered_event(*, dependency: Mapping[str, Any], **kwargs: Any) -> DependencyRegistered: return DependencyRegistered(payload={"dependency": dict(dependency)}, **kwargs)
def create_derived_resource_invalidated_event(*, source_resource_id: str, dependent_resource_id: str, source_version: int, **kwargs: Any) -> DerivedResourceInvalidated: return DerivedResourceInvalidated(payload={"source_resource_id": source_resource_id, "dependent_resource_id": dependent_resource_id, "source_version": source_version}, **kwargs)

def create_review_finding_recorded_event(*, finding: Mapping[str, Any], **kwargs: Any) -> ReviewFindingRecorded: return ReviewFindingRecorded(payload={"finding": dict(finding)}, **kwargs)
def create_review_finding_decided_event(*, decision: Mapping[str, Any], **kwargs: Any) -> ReviewFindingDecided: return ReviewFindingDecided(payload={"decision": dict(decision)}, **kwargs)
