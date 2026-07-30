"""Read projections rebuilt from event streams."""
from datetime import datetime
from typing import Dict, Tuple
from pydantic import BaseModel
from editorial_tres.domain.events import DomainEvent
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.work import Work
from editorial_tres.exceptions import WorkNotFoundError
class WorkReadModel(BaseModel):
    tenant_id: TenantId; editorial_id: EditorialId; work_id: WorkId; title: str; language: str; status: str; version: int; created_at: datetime; updated_at: datetime; stale_resource_ids: Tuple[str, ...] = ()
    model_config={"frozen":True}
class CurrentWorkProjection:
    def __init__(self): self._works: Dict[str,WorkReadModel]={}
    def _make_key(self, tenant_id, editorial_id, work_id, branch="main"): return f"{tenant_id.value}:{editorial_id.value}:{work_id.value}:{branch}"
    def apply(self,event: DomainEvent, branch="main"):
        key=self._make_key(event.tenant_id,event.editorial_id,event.work_id,branch); current=self._works.get(key)
        if current and event.aggregate_version <= current.version: return
        if event.event_type == "work.created":
            self._works[key]=WorkReadModel(tenant_id=event.tenant_id,editorial_id=event.editorial_id,work_id=event.work_id,title=event.payload["title"],language=event.payload["language"],status="conceived",version=1,created_at=event.occurred_at,updated_at=event.occurred_at); return
        if not current: raise WorkNotFoundError("La proyección debe recibir work.created primero.")
        self._works[key]=current.model_copy(update={"version":event.aggregate_version,"updated_at":event.occurred_at})
    def apply_work_created(self,event, branch="main"): self.apply(event, branch)
    def rebuild_work(self, events: list[DomainEvent], branch: str = "main"):
        work=Work.replay(events); key=self._make_key(work.tenant_id,work.editorial_id,work.work_id,branch)
        stale=tuple(sorted({item.dependent_resource_id for item in work.dependency_graph.dependencies if item.status == "stale"}))
        self._works[key]=WorkReadModel(tenant_id=work.tenant_id,editorial_id=work.editorial_id,work_id=work.work_id,title=work.title,language=work.language,status=work.status,version=work.version,created_at=work.created_at,updated_at=work.updated_at,stale_resource_ids=stale)
    def get_work(self,tenant_id,editorial_id,work_id,branch="main"):
        key=self._make_key(tenant_id,editorial_id,work_id,branch)
        if key not in self._works: raise WorkNotFoundError(f"La obra '{work_id.value}' no se encuentra en la proyección para la rama '{branch}'.")
        return self._works[key]
    def has_work(self,tenant_id,editorial_id,work_id,branch="main"): return self._make_key(tenant_id,editorial_id,work_id,branch) in self._works
    def list_works(self,tenant_id: TenantId,editorial_id: EditorialId,branch: str = "main"): return [work for key, work in self._works.items() if key.endswith(f":{branch}") and work.tenant_id==tenant_id and work.editorial_id==editorial_id]
