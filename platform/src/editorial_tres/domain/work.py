"""Work aggregate: immutable state rebuilt only from domain events."""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from editorial_tres.domain.events import DomainEvent
from editorial_tres.domain.graphs.dependency import DependencyGraph, ResourceDependency
from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
ALLOWED_STATUSES = {"conceived", "structured", "drafting", "review", "approved", "published"}
class Work(BaseModel):
    tenant_id: TenantId; editorial_id: EditorialId; work_id: WorkId; title: str; language: str; status: str = "conceived"; version: int = Field(default=1, ge=1)
    knowledge_graph: KnowledgeGraph; narrative_graph: NarrativeGraph; expression_graph: ExpressionGraph; dependency_graph: DependencyGraph
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)); updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)); model_config = {"frozen": True}
    @field_validator("status")
    @classmethod
    def _status(cls, value):
        if value not in ALLOWED_STATUSES: raise ValueError(f"Estado '{value}' no permitido.")
        return value
    @field_validator("title", "language")
    @classmethod
    def _required(cls, value):
        if not value or not value.strip(): raise ValueError("El valor es obligatorio.")
        return value.strip()
    @model_validator(mode="after")
    def _same_owner(self):
        for graph in (self.knowledge_graph, self.narrative_graph, self.expression_graph, self.dependency_graph):
            if graph.work_id != self.work_id or graph.tenant_id != self.tenant_id or graph.editorial_id != self.editorial_id:
                raise ValueError("Los grafos deben pertenecer al mismo tenant, editorial y work que el agregado.")
        return self
    @classmethod
    def create(cls, tenant_id: TenantId, editorial_id: EditorialId, work_id: WorkId, title: str, language: str, actor_id: ActorId, event_id: str, occurred_at: Optional[datetime] = None) -> "Work":
        now = occurred_at or datetime.now(timezone.utc)
        return cls(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id, title=title, language=language,
                   knowledge_graph=KnowledgeGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id), narrative_graph=NarrativeGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id), expression_graph=ExpressionGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id), dependency_graph=DependencyGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id), created_at=now, updated_at=now)
    def apply(self, event: DomainEvent) -> "Work":
        if (event.tenant_id, event.editorial_id, event.work_id) != (self.tenant_id, self.editorial_id, self.work_id): raise ValueError("El evento no pertenece a esta obra.")
        if event.aggregate_version != self.version + 1: raise ValueError("La versión del evento no es consecutiva.")
        expression_graph, dependency_graph = self.expression_graph, self.dependency_graph
        if event.event_type == "content_block.added": expression_graph = expression_graph.add_block(ContentBlock.model_validate(event.payload["block"]))
        elif event.event_type == "content_block.edited": expression_graph = expression_graph.edit_block(ContentBlock.model_validate(event.payload["block"]))
        elif event.event_type == "dependency.registered": dependency_graph = dependency_graph.register(ResourceDependency.model_validate(event.payload["dependency"]))
        elif event.event_type == "derived_resource.invalidated": dependency_graph = dependency_graph.mark_stale(event.payload["dependent_resource_id"], event.payload["source_version"])
        elif event.event_type in {"review.finding_recorded", "review.finding_decided"}: pass
        else: raise ValueError(f"Evento no soportado: {event.event_type}")
        return Work(tenant_id=self.tenant_id, editorial_id=self.editorial_id, work_id=self.work_id, title=self.title, language=self.language, status=self.status, version=event.aggregate_version, knowledge_graph=self.knowledge_graph, narrative_graph=self.narrative_graph, expression_graph=expression_graph, dependency_graph=dependency_graph, created_at=self.created_at, updated_at=event.occurred_at)
    @classmethod
    def replay(cls, events: list[DomainEvent]) -> "Work":
        if not events or events[0].event_type != "work.created" or events[0].aggregate_version != 1: raise ValueError("El stream debe comenzar con work.created versión 1.")
        first = events[0]; work = cls.create(first.tenant_id, first.editorial_id, first.work_id, first.payload["title"], first.payload["language"], first.actor_id, first.event_id, first.occurred_at)
        for event in events[1:]: work = work.apply(event)
        return work

