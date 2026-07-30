"""Application handlers."""
import hashlib, json, uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from editorial_tres.application.commands import AddContentBlockCommand, CreateWorkCommand, EditContentBlockCommand, RegisterDependencyCommand
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.domain.commits import EditorialCommit
from editorial_tres.domain.events import create_content_block_added_event, create_content_block_edited_event, create_dependency_registered_event, create_derived_resource_invalidated_event, create_work_created_event
from editorial_tres.domain.work import Work
from editorial_tres.exceptions import ConcurrencyError, WorkAlreadyExistsError
@dataclass(frozen=True)
class CommandResult: work_id:str; commit_id:str; event_id:str; version:int; status:str
CreateWorkResult=CommandResult
def _hash(command: Any) -> str: return hashlib.sha256(json.dumps(command.model_dump(mode="json"),sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
def _result(commit):
    event=commit.events[-1]; return CommandResult(work_id=commit.work_id.value,commit_id=commit.commit_id,event_id=event.event_id,version=event.aggregate_version,status="conceived")
class _Handler:
    def __init__(self,event_store,work_projection: CurrentWorkProjection): self._event_store=event_store; self._work_projection=work_projection
    def _idempotent(self, command): return self._event_store.get_idempotent_commit(command.tenant_id,command.editorial_id,command.work_id,command.branch,type(command).__name__,command.idempotency_key,_hash(command))
    def _persist(self,command,events: Iterable,message):
        events=tuple(events); head=self._event_store.get_head_commit(command.tenant_id,command.editorial_id,command.work_id,command.branch)
        commit=EditorialCommit(commit_id=f"commit-{uuid.uuid4().hex[:16]}",tenant_id=command.tenant_id,editorial_id=command.editorial_id,work_id=command.work_id,branch=command.branch,parent_commit_id=head.commit_id if head else None,events=events,message=message,actor_id=command.actor_id,created_at=events[0].occurred_at)
        self._event_store.append_commit(commit,command.idempotency_key,type(command).__name__,_hash(command)); self._work_projection.rebuild_work(self._event_store.get_events(command.tenant_id,command.editorial_id,command.work_id,command.branch)); return _result(commit)
class CreateWorkHandler(_Handler):
    def handle(self,command:CreateWorkCommand):
        existing=self._idempotent(command)
        if existing:return _result(existing)
        if self._event_store.get_events(command.tenant_id,command.editorial_id,command.work_id,command.branch): raise WorkAlreadyExistsError(f"La obra '{command.work_id.value}' ya existe.")
        now=datetime.now(timezone.utc); event=create_work_created_event(event_id=f"evt-{uuid.uuid4().hex[:16]}",tenant_id=command.tenant_id,editorial_id=command.editorial_id,work_id=command.work_id,title=command.title,language=command.language,actor_id=command.actor_id,occurred_at=now); return self._persist(command,(event,),f"Creación de obra: {command.title}")
class _ContentBlockHandler(_Handler):
    event_factory=None
    def handle(self,command):
        existing=self._idempotent(command)
        if existing:return _result(existing)
        events=self._event_store.get_events(command.tenant_id,command.editorial_id,command.work_id,command.branch); work=Work.replay(events)
        if command.expected_version != work.version: raise ConcurrencyError(f"Se esperaba versión {work.version}, se recibió {command.expected_version}.")
        block={"id":command.block_id,"block_type":command.block_type,"content":command.content,"parent_id":command.parent_id,"position":command.position,"language":command.language,"status":command.status,"metadata":dict(command.metadata)}
        now=datetime.now(timezone.utc); event=self.event_factory(event_id=f"evt-{uuid.uuid4().hex[:16]}",tenant_id=command.tenant_id,editorial_id=command.editorial_id,work_id=command.work_id,aggregate_version=work.version+1,actor_id=command.actor_id,occurred_at=now,block=block); commit_events=[event]
        if isinstance(command, EditContentBlockCommand):
            for offset, dependency in enumerate(work.dependency_graph.transitive_dependents(command.block_id), start=2):
                commit_events.append(create_derived_resource_invalidated_event(event_id=f"evt-{uuid.uuid4().hex[:16]}",tenant_id=command.tenant_id,editorial_id=command.editorial_id,work_id=command.work_id,aggregate_version=work.version+offset,actor_id=command.actor_id,occurred_at=now,source_resource_id=command.block_id,dependent_resource_id=dependency.dependent_resource_id,source_version=event.aggregate_version))
        return self._persist(command,commit_events,f"{event.event_type}: {command.block_id}")
class AddContentBlockHandler(_ContentBlockHandler): event_factory=staticmethod(create_content_block_added_event)
class EditContentBlockHandler(_ContentBlockHandler): event_factory=staticmethod(create_content_block_edited_event)
class RegisterDependencyHandler(_Handler):
    def handle(self,command:RegisterDependencyCommand):
        existing=self._idempotent(command)
        if existing:return _result(existing)
        events=self._event_store.get_events(command.tenant_id,command.editorial_id,command.work_id,command.branch); work=Work.replay(events)
        if command.expected_version != work.version: raise ConcurrencyError(f"Se esperaba versión {work.version}, se recibió {command.expected_version}.")
        dependency={"tenant_id":command.tenant_id,"editorial_id":command.editorial_id,"work_id":command.work_id,"source_resource_id":command.source_resource_id,"dependent_resource_id":command.dependent_resource_id,"source_resource_type":command.source_resource_type,"dependent_resource_type":command.dependent_resource_type,"source_version":command.source_version,"metadata":dict(command.metadata)}
        event=create_dependency_registered_event(event_id=f"evt-{uuid.uuid4().hex[:16]}",tenant_id=command.tenant_id,editorial_id=command.editorial_id,work_id=command.work_id,aggregate_version=work.version+1,actor_id=command.actor_id,occurred_at=datetime.now(timezone.utc),dependency=dependency)
        return self._persist(command,(event,),f"dependency.registered: {command.source_resource_id}->{command.dependent_resource_id}")

