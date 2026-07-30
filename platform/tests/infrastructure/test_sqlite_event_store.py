"""Integration tests for the SQLite-backed Event Store."""

import pytest

from editorial_tres.application.commands import (
    AddContentBlockCommand,
    CreateBranchCommand,
    CreateWorkCommand,
)
from editorial_tres.application.handlers import (
    AddContentBlockHandler,
    CreateBranchHandler,
    CreateWorkHandler,
)
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.domain.commits import EditorialCommit
from editorial_tres.domain.events import DomainEvent
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.work import Work
from editorial_tres.exceptions import ConcurrencyError, DuplicateEventError
from editorial_tres.infrastructure.sqlite.event_store import SQLiteEventStore


TENANT = TenantId(value="tenant.almasana")
EDITORIAL = EditorialId(value="editorial.almasana")
WORK = WorkId(value="work.yo-no-soy")
ACTOR = ActorId(value="actor.user-001")


def _create_work_command() -> CreateWorkCommand:
    return CreateWorkCommand(
        command_id="cmd-create",
        idempotency_key="idem-create",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        actor_id=ACTOR,
        title="Obra persistida",
        language="es",
    )


def _add_block_command(
    *, branch: str = "main", expected_version: int = 1, key: str = "idem-add", block_id: str = "block-1"
) -> AddContentBlockCommand:
    return AddContentBlockCommand(
        command_id=f"cmd-{key}",
        idempotency_key=key,
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        actor_id=ACTOR,
        branch=branch,
        expected_version=expected_version,
        block_id=block_id,
        block_type="paragraph",
        content=f"Contenido de {block_id}",
    )


def _create_work(store: SQLiteEventStore) -> None:
    CreateWorkHandler(store, CurrentWorkProjection()).handle(_create_work_command())


def test_persists_events_between_store_instances(tmp_path):
    database_path = tmp_path / "events.sqlite"
    with SQLiteEventStore(database_path) as first_store:
        _create_work(first_store)

    with SQLiteEventStore(database_path) as reopened_store:
        events = reopened_store.get_events(TENANT, EDITORIAL, WORK)
        branch_exists = reopened_store.branch_exists(TENANT, EDITORIAL, WORK, "main")

    assert [event.event_type for event in events] == ["work.created"]
    assert branch_exists is True


def test_append_and_replay_from_persisted_stream(tmp_path):
    database_path = tmp_path / "events.sqlite"
    with SQLiteEventStore(database_path) as store:
        projection = CurrentWorkProjection()
        CreateWorkHandler(store, projection).handle(_create_work_command())
        AddContentBlockHandler(store, projection).handle(_add_block_command())

    with SQLiteEventStore(database_path) as reopened_store:
        replayed = Work.replay(reopened_store.get_events(TENANT, EDITORIAL, WORK))

    assert replayed.version == 2
    assert replayed.expression_graph.blocks["block-1"].content == "Contenido de block-1"


def test_branches_remain_isolated_after_persistence(tmp_path):
    database_path = tmp_path / "events.sqlite"
    with SQLiteEventStore(database_path) as store:
        projection = CurrentWorkProjection()
        CreateWorkHandler(store, projection).handle(_create_work_command())
        CreateBranchHandler(store, projection).handle(
            CreateBranchCommand(
                command_id="cmd-fork",
                idempotency_key="idem-fork",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=ACTOR,
                source_branch="main",
                target_branch="draft",
            )
        )
        AddContentBlockHandler(store, projection).handle(
            _add_block_command(branch="main", key="idem-main", block_id="main-only")
        )
        AddContentBlockHandler(store, projection).handle(
            _add_block_command(branch="draft", key="idem-draft", block_id="draft-only")
        )

    with SQLiteEventStore(database_path) as reopened_store:
        main = Work.replay(reopened_store.get_events(TENANT, EDITORIAL, WORK, "main"))
        draft = Work.replay(reopened_store.get_events(TENANT, EDITORIAL, WORK, "draft"))

    assert "main-only" in main.expression_graph.blocks
    assert "draft-only" not in main.expression_graph.blocks
    assert "draft-only" in draft.expression_graph.blocks
    assert "main-only" not in draft.expression_graph.blocks


def test_persists_fork_genealogy_and_event_origins(tmp_path):
    database_path = tmp_path / "events.sqlite"
    with SQLiteEventStore(database_path) as store:
        projection = CurrentWorkProjection()
        CreateWorkHandler(store, projection).handle(_create_work_command())
        AddContentBlockHandler(store, projection).handle(_add_block_command())
        source_events = store.get_events(TENANT, EDITORIAL, WORK)
        CreateBranchHandler(store, projection).handle(
            CreateBranchCommand(
                command_id="cmd-fork",
                idempotency_key="idem-fork",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=ACTOR,
                source_branch="main",
                target_branch="draft",
            )
        )

    with SQLiteEventStore(database_path) as reopened_store:
        fork_commit = reopened_store.get_commits(TENANT, EDITORIAL, WORK, "draft")[0]
        copied_events = reopened_store.get_events(TENANT, EDITORIAL, WORK, "draft")

    assert fork_commit.parent_branch == "main"
    assert fork_commit.parent_branch_version == 2
    assert [event.origin_event_id for event in copied_events] == [
        event.event_id for event in source_events
    ]


def test_idempotency_survives_store_reopen(tmp_path):
    database_path = tmp_path / "events.sqlite"
    command = _create_work_command()
    with SQLiteEventStore(database_path) as store:
        first = CreateWorkHandler(store, CurrentWorkProjection()).handle(command)

    with SQLiteEventStore(database_path) as reopened_store:
        second = CreateWorkHandler(reopened_store, CurrentWorkProjection()).handle(command)
        events = reopened_store.get_events(TENANT, EDITORIAL, WORK)

    assert second.commit_id == first.commit_id
    assert len(events) == 1


def test_rejects_version_conflicts_after_reopen(tmp_path):
    database_path = tmp_path / "events.sqlite"
    with SQLiteEventStore(database_path) as store:
        _create_work(store)

    with SQLiteEventStore(database_path) as reopened_store:
        with pytest.raises(ConcurrencyError):
            AddContentBlockHandler(reopened_store, CurrentWorkProjection()).handle(
                _add_block_command(expected_version=2)
            )


def test_rejects_duplicate_event_ids(tmp_path):
    database_path = tmp_path / "events.sqlite"
    first_event = DomainEvent(
        event_id="evt-duplicate",
        event_type="work.created",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        aggregate_version=1,
        actor_id=ACTOR,
        payload={"title": "Obra", "language": "es"},
    )
    first_commit = EditorialCommit(
        commit_id="commit-first",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        events=(first_event,),
        actor_id=ACTOR,
    )
    duplicate_event = first_event.model_copy(update={"aggregate_version": 2})
    duplicate_commit = EditorialCommit(
        commit_id="commit-second",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        parent_commit_id=first_commit.commit_id,
        events=(duplicate_event,),
        actor_id=ACTOR,
    )

    with SQLiteEventStore(database_path) as store:
        store.append_commit(first_commit)
        with pytest.raises(DuplicateEventError):
            store.append_commit(duplicate_commit)
