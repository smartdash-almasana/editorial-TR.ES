"""Application handlers."""
import hashlib, json, uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from editorial_tres.application.commands import AddContentBlockCommand, ApplyApprovedPatchCommand, CreateWorkCommand, EditContentBlockCommand, RegisterDependencyCommand, CreateBranchCommand, RecordReviewFindingCommand, DecideReviewFindingCommand
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.domain.commits import EditorialCommit
from editorial_tres.domain.events import create_content_block_added_event, create_content_block_deleted_event, create_content_block_edited_event, create_content_block_moved_event, create_dependency_registered_event, create_derived_resource_invalidated_event, create_review_finding_decided_event, create_review_finding_recorded_event, create_work_created_event
from editorial_tres.domain.patches import DeleteBlockOperation, InsertBlockOperation, MoveBlockOperation
from editorial_tres.domain.review_history import ReviewHistory
from editorial_tres.domain.work import Work
from editorial_tres.exceptions import ConcurrencyError, WorkAlreadyExistsError, BranchAlreadyExistsError, BranchNotFoundError
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
        self._event_store.append_commit(commit,command.idempotency_key,type(command).__name__,_hash(command)); self._work_projection.rebuild_work(self._event_store.get_events(command.tenant_id,command.editorial_id,command.work_id,command.branch), branch=command.branch); return _result(commit)
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

class CreateBranchHandler(_Handler):
    def handle(self, command: CreateBranchCommand):
        existing = self._idempotent(command)
        if existing:
            return _result(existing)
        if not self._event_store.branch_exists(command.tenant_id, command.editorial_id, command.work_id, command.source_branch):
            raise BranchNotFoundError(f"La rama origen '{command.source_branch}' no existe.")
        if self._event_store.branch_exists(command.tenant_id, command.editorial_id, command.work_id, command.target_branch):
            raise BranchAlreadyExistsError(f"La rama destino '{command.target_branch}' ya existe.")
        source_events = self._event_store.get_events(command.tenant_id, command.editorial_id, command.work_id, command.source_branch)
        max_source_version = max(e.aggregate_version for e in source_events)
        if command.source_version is not None:
            if command.source_version < 1 or command.source_version > max_source_version:
                raise ConcurrencyError(f"La versión solicitada {command.source_version} no existe en la rama origen (máxima versión: {max_source_version}).")
            cutoff_version = command.source_version
        else:
            cutoff_version = max_source_version
        events_to_copy = [e for e in source_events if e.aggregate_version <= cutoff_version]
        copied_events = []
        for e in events_to_copy:
            copied_events.append(e.model_copy(update={
                "event_id": f"evt-{uuid.uuid4().hex[:16]}",
                "origin_event_id": e.event_id,
            }))
        commit = EditorialCommit(
            commit_id=f"commit-{uuid.uuid4().hex[:16]}",
            tenant_id=command.tenant_id,
            editorial_id=command.editorial_id,
            work_id=command.work_id,
            branch=command.target_branch,
            parent_commit_id=None,
            parent_branch=command.source_branch,
            parent_branch_version=cutoff_version,
            events=tuple(copied_events),
            message=f"Fork de la rama {command.source_branch} en la versión {cutoff_version}",
            actor_id=command.actor_id,
            created_at=copied_events[0].occurred_at if copied_events else datetime.now(timezone.utc)
        )
        self._event_store.append_commit(commit, command.idempotency_key, type(command).__name__, _hash(command))
        self._work_projection.rebuild_work(self._event_store.get_events(command.tenant_id, command.editorial_id, command.work_id, command.target_branch), branch=command.target_branch)
        return _result(commit)


class ApplyApprovedPatchHandler(_Handler):
    """Apply one approved Patch atomically through the canonical event stream."""

    @staticmethod
    def _block_payload(block):
        return {
            "id": block.id,
            "block_type": block.block_type,
            "content": block.content,
            "parent_id": block.parent_id,
            "position": block.position,
            "language": block.language,
            "status": block.status,
            "metadata": dict(block.metadata),
        }

    def handle(self, command: ApplyApprovedPatchCommand):
        command.assert_patch_integrity()
        existing = self._idempotent(command)
        if existing:
            return _result(existing)

        events = self._event_store.get_events(
            command.tenant_id,
            command.editorial_id,
            command.work_id,
            command.branch,
        )
        work = Work.replay(events)
        if command.expected_version != work.version:
            raise ConcurrencyError(
                f"El Patch fue aprobado sobre la versión {command.expected_version}, "
                f"pero la obra está en la versión {work.version}."
            )

        validated_graph = work.expression_graph
        planned_operations = []

        for operation in command.patch.operations:
            if isinstance(operation, InsertBlockOperation):
                if work.expression_graph.has_block(operation.block_id):
                    raise ValueError(
                        f"El bloque '{operation.block_id}' ya existe en la obra."
                    )
                if (
                    operation.parent_id is not None
                    and not work.expression_graph.has_block(operation.parent_id)
                ):
                    raise ValueError(
                        f"El bloque padre '{operation.parent_id}' no existe en el snapshot fuente."
                    )
                inserted_block = operation.to_content_block()
                validated_graph = validated_graph.add_block(inserted_block)
                planned_operations.append(("insert", operation, inserted_block))
                continue

            if isinstance(operation, DeleteBlockOperation):
                block = work.expression_graph.get_block(operation.block_id)
                if block is None:
                    raise ValueError(f"El bloque '{operation.block_id}' ya no existe en la obra.")
                if block.model_dump(mode="json") != operation.before_block.model_dump(mode="json"):
                    raise ConcurrencyError(
                        f"El bloque '{operation.block_id}' ya no coincide con el estado aprobado para eliminar."
                    )
                if work.expression_graph.get_children(operation.block_id):
                    raise ValueError(
                        f"El bloque '{operation.block_id}' no puede eliminarse mientras tenga hijos."
                    )
                dependents = work.dependency_graph.direct_dependents(operation.block_id)
                if dependents:
                    dependent_ids = ", ".join(item.dependent_resource_id for item in dependents)
                    raise ValueError(
                        f"El bloque '{operation.block_id}' no puede eliminarse mientras tenga dependientes registrados: {dependent_ids}."
                    )
                incoming_dependencies = work.dependency_graph.incoming_dependencies(
                    operation.block_id
                )
                if incoming_dependencies:
                    source_ids = ", ".join(
                        sorted(dependency.source_resource_id for dependency in incoming_dependencies)
                    )
                    raise ValueError(
                        f"El bloque '{operation.block_id}' no puede eliminarse mientras sea destino de dependencias registradas desde: {source_ids}."
                    )
                validated_graph = validated_graph.delete_block(operation.block_id)
                planned_operations.append(("delete", operation, block))
                continue

            if isinstance(operation, MoveBlockOperation):
                block = work.expression_graph.get_block(operation.block_id)
                if block is None:
                    raise ValueError(f"El bloque '{operation.block_id}' ya no existe en la obra.")
                if (
                    block.parent_id != operation.before_parent_id
                    or block.position != operation.before_position
                ):
                    raise ConcurrencyError(
                        f"El bloque '{operation.block_id}' ya no coincide con la ubicación aprobada."
                    )
                work.expression_graph.move_block(
                    operation.block_id,
                    parent_id=operation.after_parent_id,
                    position=operation.after_position,
                )
                validated_graph = validated_graph.move_block(
                    operation.block_id,
                    parent_id=operation.after_parent_id,
                    position=operation.after_position,
                )
                moved_block = validated_graph.get_block(operation.block_id)
                planned_operations.append(("move", operation, moved_block))
                continue

            block = work.expression_graph.get_block(operation.block_id)
            if block is None:
                raise ValueError(f"El bloque '{operation.block_id}' ya no existe en la obra.")
            if block.content != operation.before_content:
                raise ConcurrencyError(
                    f"El bloque '{operation.block_id}' ya no coincide con el contenido aprobado."
                )
            updated_block = block.model_copy(update={"content": operation.after_content})
            validated_graph = validated_graph.edit_block(updated_block)
            planned_operations.append(("replace", operation, updated_block))

        commit_events = []
        next_version = work.version
        invalidated = set()
        occurred_at = datetime.now(timezone.utc)

        for operation_type, operation, block in planned_operations:
            next_version += 1
            block_payload = self._block_payload(block)

            if operation_type == "insert":
                commit_events.append(
                    create_content_block_added_event(
                        event_id=f"evt-{uuid.uuid4().hex[:16]}",
                        tenant_id=command.tenant_id,
                        editorial_id=command.editorial_id,
                        work_id=command.work_id,
                        aggregate_version=next_version,
                        actor_id=command.actor_id,
                        occurred_at=occurred_at,
                        block=block_payload,
                    )
                )
                continue

            if operation_type == "delete":
                commit_events.append(
                    create_content_block_deleted_event(
                        event_id=f"evt-{uuid.uuid4().hex[:16]}",
                        tenant_id=command.tenant_id,
                        editorial_id=command.editorial_id,
                        work_id=command.work_id,
                        aggregate_version=next_version,
                        actor_id=command.actor_id,
                        occurred_at=occurred_at,
                        block_id=operation.block_id,
                        before_block=block_payload,
                    )
                )
                continue

            if operation_type == "move":
                move_event = create_content_block_moved_event(
                    event_id=f"evt-{uuid.uuid4().hex[:16]}",
                    tenant_id=command.tenant_id,
                    editorial_id=command.editorial_id,
                    work_id=command.work_id,
                    aggregate_version=next_version,
                    actor_id=command.actor_id,
                    occurred_at=occurred_at,
                    block_id=operation.block_id,
                    before_parent_id=operation.before_parent_id,
                    before_position=operation.before_position,
                    after_parent_id=operation.after_parent_id,
                    after_position=operation.after_position,
                )
                commit_events.append(move_event)

                for dependency in work.dependency_graph.transitive_dependents(operation.block_id):
                    key = (operation.block_id, dependency.dependent_resource_id)
                    if key in invalidated:
                        continue
                    invalidated.add(key)
                    next_version += 1
                    commit_events.append(
                        create_derived_resource_invalidated_event(
                            event_id=f"evt-{uuid.uuid4().hex[:16]}",
                            tenant_id=command.tenant_id,
                            editorial_id=command.editorial_id,
                            work_id=command.work_id,
                            aggregate_version=next_version,
                            actor_id=command.actor_id,
                            occurred_at=occurred_at,
                            source_resource_id=operation.block_id,
                            dependent_resource_id=dependency.dependent_resource_id,
                            source_version=move_event.aggregate_version,
                        )
                    )
                continue

            edit_event = create_content_block_edited_event(
                event_id=f"evt-{uuid.uuid4().hex[:16]}",
                tenant_id=command.tenant_id,
                editorial_id=command.editorial_id,
                work_id=command.work_id,
                aggregate_version=next_version,
                actor_id=command.actor_id,
                occurred_at=occurred_at,
                block=block_payload,
            )
            commit_events.append(edit_event)

            for dependency in work.dependency_graph.transitive_dependents(operation.block_id):
                key = (operation.block_id, dependency.dependent_resource_id)
                if key in invalidated:
                    continue
                invalidated.add(key)
                next_version += 1
                commit_events.append(
                    create_derived_resource_invalidated_event(
                        event_id=f"evt-{uuid.uuid4().hex[:16]}",
                        tenant_id=command.tenant_id,
                        editorial_id=command.editorial_id,
                        work_id=command.work_id,
                        aggregate_version=next_version,
                        actor_id=command.actor_id,
                        occurred_at=occurred_at,
                        source_resource_id=operation.block_id,
                        dependent_resource_id=dependency.dependent_resource_id,
                        source_version=edit_event.aggregate_version,
                    )
                )

        return self._persist(
            command,
            commit_events,
            f"patch.applied: {command.patch.patch_id}",
        )


class RecordReviewFindingHandler(_Handler):
    """Persist one diagnostic finding without changing manuscript content."""

    def handle(self, command: RecordReviewFindingCommand):
        existing = self._idempotent(command)
        if existing:
            return _result(existing)

        events = self._event_store.get_events(
            command.tenant_id,
            command.editorial_id,
            command.work_id,
            command.branch,
        )
        work = Work.replay(events)
        if command.expected_version != work.version:
            raise ConcurrencyError(
                f"Se esperaba versión {work.version}, se recibió {command.expected_version}."
            )
        if command.finding.source_version != work.manuscript_version:
            raise ConcurrencyError(
                f"El finding fue producido sobre la revisión material {command.finding.source_version}, "
                f"pero el manuscrito está en la revisión {work.manuscript_version}."
            )

        history = ReviewHistory.replay(events)
        if history.get_finding(command.finding.finding_id) is not None:
            raise ValueError(f"El finding '{command.finding.finding_id}' ya está registrado.")

        event = create_review_finding_recorded_event(
            event_id=f"evt-{uuid.uuid4().hex[:16]}",
            tenant_id=command.tenant_id,
            editorial_id=command.editorial_id,
            work_id=command.work_id,
            aggregate_version=work.version + 1,
            actor_id=command.actor_id,
            occurred_at=datetime.now(timezone.utc),
            finding=command.finding.model_dump(mode="json"),
        )
        return self._persist(command, (event,), f"review.finding_recorded: {command.finding.finding_id}")


class DecideReviewFindingHandler(_Handler):
    """Persist one explicit decision over an existing, non-stale finding."""

    def handle(self, command: DecideReviewFindingCommand):
        existing = self._idempotent(command)
        if existing:
            return _result(existing)

        events = self._event_store.get_events(
            command.tenant_id,
            command.editorial_id,
            command.work_id,
            command.branch,
        )
        work = Work.replay(events)
        if command.expected_version != work.version:
            raise ConcurrencyError(
                f"Se esperaba versión {work.version}, se recibió {command.expected_version}."
            )

        history = ReviewHistory.replay(events)
        finding = history.get_finding(command.decision.finding_id)
        if finding is None:
            raise ValueError(
                f"El finding '{command.decision.finding_id}' no existe en el historial de revisión."
            )
        if history.get_decision(finding.finding_id) is not None:
            raise ValueError(f"El finding '{finding.finding_id}' ya fue decidido.")
        if command.decision.source_version != finding.source_version:
            raise ValueError("La decisión no corresponde a la versión fuente del finding.")

        if work.manuscript_version != finding.source_version:
            raise ConcurrencyError(
                f"El finding '{finding.finding_id}' quedó stale por una mutación posterior del manuscrito."
            )

        event = create_review_finding_decided_event(
            event_id=f"evt-{uuid.uuid4().hex[:16]}",
            tenant_id=command.tenant_id,
            editorial_id=command.editorial_id,
            work_id=command.work_id,
            aggregate_version=work.version + 1,
            actor_id=command.actor_id,
            occurred_at=command.decision.decided_at or datetime.now(timezone.utc),
            decision=command.decision.model_dump(mode="json"),
        )
        return self._persist(command, (event,), f"review.finding_decided: {finding.finding_id}")


def get_review_history(event_store, tenant_id, editorial_id, work_id, branch: str = "main") -> ReviewHistory:
    """Return the current review history derived from the canonical event stream."""
    return ReviewHistory.replay(event_store.get_events(tenant_id, editorial_id, work_id, branch))
