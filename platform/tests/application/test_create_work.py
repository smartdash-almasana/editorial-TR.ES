"""
Pruebas para el flujo de creación de obra (CreateWorkCommand).
"""

import pytest

from editorial_tres.application.commands import CreateWorkCommand
from editorial_tres.application.handlers import CreateWorkHandler
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.exceptions import (
    IdempotencyConflictError,
    WorkAlreadyExistsError,
)
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore


def _make_command(
    idempotency_key: str = "key-001",
    work_id_value: str = "work.yo-no-soy",
    title: str = "Yo no soy",
    editorial_id_value: str = "editorial.almasana",
    tenant_id_value: str = "tenant.almasana",
) -> CreateWorkCommand:
    return CreateWorkCommand(
        command_id=f"cmd-{idempotency_key}",
        idempotency_key=idempotency_key,
        tenant_id=TenantId(value=tenant_id_value),
        editorial_id=EditorialId(value=editorial_id_value),
        work_id=WorkId(value=work_id_value),
        title=title,
        language="es",
        actor_id=ActorId(value="actor.user-001"),
    )


def test_create_work_command():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    handler = CreateWorkHandler(event_store=store, work_projection=projection)

    command = _make_command()
    result = handler.handle(command)

    assert result.work_id == "work.yo-no-soy"
    assert result.version == 1
    assert result.status == "conceived"
    assert result.commit_id is not None
    assert result.event_id is not None


def test_work_created_event_emitted():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    handler = CreateWorkHandler(event_store=store, work_projection=projection)

    command = _make_command()
    handler.handle(command)

    events = store.get_events(
        command.tenant_id, command.editorial_id, command.work_id
    )
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "work.created"
    assert event.payload["title"] == "Yo no soy"
    assert event.aggregate_version == 1


def test_editorial_commit_created():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    handler = CreateWorkHandler(event_store=store, work_projection=projection)

    command = _make_command()
    handler.handle(command)

    commits = store.get_commits(
        command.tenant_id, command.editorial_id, command.work_id
    )
    assert len(commits) == 1
    commit = commits[0]
    assert commit.branch == "main"
    assert commit.parent_commit_id is None
    assert len(commit.events) == 1
    assert commit.message == "Creación de obra: Yo no soy"


def test_projection_updated():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    handler = CreateWorkHandler(event_store=store, work_projection=projection)

    command = _make_command()
    handler.handle(command)

    work_model = projection.get_work(
        command.tenant_id, command.editorial_id, command.work_id
    )
    assert work_model.title == "Yo no soy"
    assert work_model.status == "conceived"
    assert work_model.version == 1


def test_idempotency():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    handler = CreateWorkHandler(event_store=store, work_projection=projection)

    command = _make_command(idempotency_key="key-unique-001")
    result1 = handler.handle(command)
    result2 = handler.handle(command)

    assert result1.work_id == result2.work_id
    assert result1.commit_id == result2.commit_id
    assert result1.event_id == result2.event_id

    # Solo un commit debe existir
    commits = store.get_commits(
        command.tenant_id, command.editorial_id, command.work_id
    )
    assert len(commits) == 1


def test_reject_duplicate_work_id():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    handler = CreateWorkHandler(event_store=store, work_projection=projection)

    command1 = _make_command(idempotency_key="key-001")
    handler.handle(command1)

    command2 = _make_command(idempotency_key="key-002")
    with pytest.raises(WorkAlreadyExistsError):
        handler.handle(command2)


def test_reject_invalid_commit_parent():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    handler = CreateWorkHandler(event_store=store, work_projection=projection)

    # Crear primer commit
    command1 = _make_command(idempotency_key="key-001")
    handler.handle(command1)

    # Intentar crear un segundo commit manualmente con parent incorrecto
    from editorial_tres.domain.commits import EditorialCommit
    from editorial_tres.domain.events import DomainEvent

    head = store.get_head_commit(
        command1.tenant_id, command1.editorial_id, command1.work_id
    )

    bad_event = DomainEvent(
        event_id="evt-bad-001",
        event_type="work.updated",
        tenant_id=command1.tenant_id,
        editorial_id=command1.editorial_id,
        work_id=command1.work_id,
        aggregate_version=2,
        actor_id=command1.actor_id,
        payload={"title": "Updated"},
    )
    bad_commit = EditorialCommit(
        commit_id="commit-bad-001",
        tenant_id=command1.tenant_id,
        editorial_id=command1.editorial_id,
        work_id=command1.work_id,
        branch="main",
        parent_commit_id="nonexistent-parent",
        events=[bad_event],
        message="Bad commit",
        actor_id=command1.actor_id,
    )

    from editorial_tres.exceptions import InvalidCommitParentError

    with pytest.raises(InvalidCommitParentError):
        store.append_commit(bad_commit)


def test_reject_concurrent_version():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    handler = CreateWorkHandler(event_store=store, work_projection=projection)

    command1 = _make_command(idempotency_key="key-001")
    handler.handle(command1)

    from editorial_tres.domain.commits import EditorialCommit
    from editorial_tres.domain.events import DomainEvent
    from editorial_tres.exceptions import ConcurrencyError

    head = store.get_head_commit(
        command1.tenant_id, command1.editorial_id, command1.work_id
    )

    # Evento con versión incorrecta (debería ser 2, pero ponemos 5)
    bad_event = DomainEvent(
        event_id="evt-bad-002",
        event_type="work.updated",
        tenant_id=command1.tenant_id,
        editorial_id=command1.editorial_id,
        work_id=command1.work_id,
        aggregate_version=5,
        actor_id=command1.actor_id,
        payload={"title": "Updated"},
    )
    bad_commit = EditorialCommit(
        commit_id="commit-bad-002",
        tenant_id=command1.tenant_id,
        editorial_id=command1.editorial_id,
        work_id=command1.work_id,
        branch="main",
        parent_commit_id=head.commit_id,
        events=[bad_event],
        message="Bad version commit",
        actor_id=command1.actor_id,
    )

    with pytest.raises(ConcurrencyError):
        store.append_commit(bad_commit)


def test_tenant_isolation():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    handler = CreateWorkHandler(event_store=store, work_projection=projection)

    command1 = _make_command(
        idempotency_key="key-t1",
        work_id_value="work.shared-name",
        tenant_id_value="tenant.almasana",
        title="Obra en Tenant 1",
    )
    handler.handle(command1)

    command2 = _make_command(
        idempotency_key="key-t2",
        work_id_value="work.shared-name",
        tenant_id_value="tenant.otro",
        title="Obra en Tenant 2",
    )
    handler.handle(command2)

    # Ambos deben existir
    w1 = projection.get_work(command1.tenant_id, command1.editorial_id, command1.work_id)
    w2 = projection.get_work(command2.tenant_id, command2.editorial_id, command2.work_id)
    assert w1.title == "Obra en Tenant 1"
    assert w2.title == "Obra en Tenant 2"


def test_editorial_isolation():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    handler = CreateWorkHandler(event_store=store, work_projection=projection)

    command1 = _make_command(
        idempotency_key="key-e1",
        work_id_value="work.shared-name",
        editorial_id_value="editorial.almasana",
        title="Obra en Editorial 1",
    )
    handler.handle(command1)

    command2 = _make_command(
        idempotency_key="key-e2",
        work_id_value="work.shared-name",
        editorial_id_value="editorial.otra",
        title="Obra en Editorial 2",
    )
    handler.handle(command2)

    w1 = projection.get_work(command1.tenant_id, command1.editorial_id, command1.work_id)
    w2 = projection.get_work(command2.tenant_id, command2.editorial_id, command2.work_id)
    assert w1.title == "Obra en Editorial 1"
    assert w2.title == "Obra en Editorial 2"
