"""Integration tests for the SQLite-backed Event Store."""

from datetime import datetime, timezone

import pytest

from editorial_tres.application.commands import (
    AddContentBlockCommand,
    ApplyApprovedPatchCommand,
    CreateBranchCommand,
    CreateWorkCommand,
)
from editorial_tres.application.handlers import (
    AddContentBlockHandler,
    ApplyApprovedPatchHandler,
    CreateBranchHandler,
    CreateWorkHandler,
)
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.domain.approvals import ApprovalGate
from editorial_tres.domain.commits import EditorialCommit
from editorial_tres.domain.edition import EditionApproval
from editorial_tres.domain.events import DomainEvent
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.patches import (
    DeleteBlockOperation,
    InsertBlockOperation,
    MoveBlockOperation,
    Patch,
    PatchOperation,
)
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


def test_delete_patch_replays_after_sqlite_store_reopen(tmp_path):
    database_path = tmp_path / "events.sqlite"
    with SQLiteEventStore(database_path) as store:
        projection = CurrentWorkProjection()
        CreateWorkHandler(store, projection).handle(_create_work_command())
        AddContentBlockHandler(store, projection).handle(_add_block_command())
        work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
        block = work.expression_graph.get_block("block-1")
        assert block is not None
        patch = Patch(
            patch_id="patch-delete-sqlite",
            pass_id="pass-structural",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            branch="main",
            source_version=work.version,
            operations=(
                DeleteBlockOperation(
                    block_id="block-1",
                    before_block=block,
                ),
            ),
        )
        approval = ApprovalGate.for_patch(
            patch,
            gate_id="gate-delete-sqlite",
            required_role="editor",
        ).approve(
            actor_id=ACTOR,
            reason="Persistir eliminación estructural.",
            decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        ApplyApprovedPatchHandler(store, projection).handle(
            ApplyApprovedPatchCommand(
                command_id="cmd-delete-sqlite",
                idempotency_key="idem-delete-sqlite",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=ACTOR,
                branch="main",
                expected_version=patch.source_version,
                patch=patch,
                approval=approval,
            )
        )

    with SQLiteEventStore(database_path) as reopened_store:
        events = reopened_store.get_events(TENANT, EDITORIAL, WORK)
        replayed = Work.replay(events)

    assert [event.event_type for event in events] == [
        "work.created",
        "content_block.added",
        "content_block.deleted",
    ]
    assert replayed.version == 3
    assert replayed.manuscript_version == 3
    assert replayed.expression_graph.get_block("block-1") is None



def test_move_patch_replays_after_sqlite_store_reopen(tmp_path):
    database_path = tmp_path / "events.sqlite"
    with SQLiteEventStore(database_path) as store:
        projection = CurrentWorkProjection()
        CreateWorkHandler(store, projection).handle(_create_work_command())
        AddContentBlockHandler(store, projection).handle(_add_block_command())
        AddContentBlockHandler(store, projection).handle(
            _add_block_command(
                expected_version=2,
                key="idem-add-parent-2",
                block_id="block-2",
            )
        )
        AddContentBlockHandler(store, projection).handle(
            AddContentBlockCommand(
                command_id="cmd-add-child-move",
                idempotency_key="idem-add-child-move",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=ACTOR,
                expected_version=3,
                block_id="block-3",
                block_type="paragraph",
                content="Bloque móvil persistido",
                parent_id="block-1",
                position=0,
            )
        )
        work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
        patch = Patch(
            patch_id="patch-move-sqlite",
            pass_id="pass-structural",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            branch="main",
            source_version=work.version,
            operations=(
                MoveBlockOperation(
                    block_id="block-3",
                    before_parent_id="block-1",
                    before_position=0,
                    after_parent_id="block-2",
                    after_position=4,
                ),
            ),
        )
        approval = ApprovalGate.for_patch(
            patch,
            gate_id="gate-move-sqlite",
            required_role="editor",
        ).approve(
            actor_id=ACTOR,
            reason="Persistir movimiento estructural.",
            decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        ApplyApprovedPatchHandler(store, projection).handle(
            ApplyApprovedPatchCommand(
                command_id="cmd-move-sqlite",
                idempotency_key="idem-move-sqlite",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=ACTOR,
                branch="main",
                expected_version=patch.source_version,
                patch=patch,
                approval=approval,
            )
        )

    with SQLiteEventStore(database_path) as reopened_store:
        events = reopened_store.get_events(TENANT, EDITORIAL, WORK)
        replayed = Work.replay(events)

    moved = replayed.expression_graph.get_block("block-3")
    assert [event.event_type for event in events] == [
        "work.created",
        "content_block.added",
        "content_block.added",
        "content_block.added",
        "content_block.moved",
    ]
    assert replayed.version == 5
    assert replayed.manuscript_version == 5
    assert moved.parent_id == "block-2"
    assert moved.position == 4
    assert moved.content == "Bloque móvil persistido"



def test_structural_patch_catalog_replays_exactly_after_sqlite_reopen(tmp_path):
    database_path = tmp_path / "events.sqlite"
    with SQLiteEventStore(database_path) as store:
        projection = CurrentWorkProjection()
        CreateWorkHandler(store, projection).handle(_create_work_command())
        AddContentBlockHandler(store, projection).handle(
            AddContentBlockCommand(
                command_id="cmd-catalog-block-1",
                idempotency_key="idem-catalog-block-1",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=ACTOR,
                expected_version=1,
                block_id="block-1",
                block_type="paragraph",
                content="Antes",
                position=0,
            )
        )
        AddContentBlockHandler(store, projection).handle(
            AddContentBlockCommand(
                command_id="cmd-catalog-block-2",
                idempotency_key="idem-catalog-block-2",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=ACTOR,
                expected_version=2,
                block_id="block-2",
                block_type="paragraph",
                content="Bloque eliminable",
                position=1,
            )
        )
        AddContentBlockHandler(store, projection).handle(
            AddContentBlockCommand(
                command_id="cmd-catalog-block-3",
                idempotency_key="idem-catalog-block-3",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=ACTOR,
                expected_version=3,
                block_id="block-3",
                block_type="heading",
                content="",
                position=2,
            )
        )
        AddContentBlockHandler(store, projection).handle(
            AddContentBlockCommand(
                command_id="cmd-catalog-block-4",
                idempotency_key="idem-catalog-block-4",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=ACTOR,
                expected_version=4,
                block_id="block-4",
                block_type="paragraph",
                content="Bloque móvil",
                parent_id="block-1",
                position=1,
            )
        )
        work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
        deletable = work.expression_graph.get_block("block-2")
        assert deletable is not None
        patch = Patch(
            patch_id="patch-catalog-sqlite",
            pass_id="pass-structural-certification",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            branch="main",
            source_version=work.version,
            operations=(
                PatchOperation(
                    block_id="block-1",
                    before_content="Antes",
                    after_content="Texto revisado",
                ),
                InsertBlockOperation(
                    block_id="block-5",
                    block_type="paragraph",
                    content="Bloque insertado",
                    parent_id="block-3",
                    position=1,
                    metadata={"origin": "sqlite-certification"},
                ),
                DeleteBlockOperation(
                    block_id="block-2",
                    before_block=deletable,
                ),
                MoveBlockOperation(
                    block_id="block-4",
                    before_parent_id="block-1",
                    before_position=1,
                    after_parent_id="block-3",
                    after_position=0,
                ),
            ),
        )
        approval = ApprovalGate.for_patch(
            patch,
            gate_id="gate-catalog-sqlite",
            required_role="editor",
        ).approve(
            actor_id=ACTOR,
            reason="Certificar catálogo estructural persistido.",
            decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        ApplyApprovedPatchHandler(store, projection).handle(
            ApplyApprovedPatchCommand(
                command_id="cmd-catalog-sqlite",
                idempotency_key="idem-catalog-sqlite",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=ACTOR,
                branch="main",
                expected_version=patch.source_version,
                patch=patch,
                approval=approval,
            )
        )

    with SQLiteEventStore(database_path) as reopened_store:
        events = reopened_store.get_events(TENANT, EDITORIAL, WORK)
        commits = reopened_store.get_commits(TENANT, EDITORIAL, WORK, "main")
        replayed = Work.replay(events)

    patch_commit = commits[-1]
    inserted = replayed.expression_graph.get_block("block-5")
    moved = replayed.expression_graph.get_block("block-4")
    assert tuple(event.event_type for event in patch_commit.events) == (
        "content_block.edited",
        "content_block.added",
        "content_block.deleted",
        "content_block.moved",
    )
    assert tuple(event.aggregate_version for event in patch_commit.events) == (6, 7, 8, 9)
    assert replayed.version == 9
    assert replayed.manuscript_version == 9
    assert replayed.expression_graph.get_block("block-1").content == "Texto revisado"
    assert replayed.expression_graph.get_block("block-2") is None
    assert inserted is not None
    assert inserted.parent_id == "block-3"
    assert dict(inserted.metadata) == {"origin": "sqlite-certification"}
    assert moved is not None
    assert moved.parent_id == "block-3"
    assert moved.position == 0
    assert moved.content == "Bloque móvil"



def test_nested_patch_metadata_round_trips_through_sqlite_exactly(tmp_path):
    database_path = tmp_path / "events.sqlite"
    with SQLiteEventStore(database_path) as store:
        projection = CurrentWorkProjection()
        CreateWorkHandler(store, projection).handle(_create_work_command())
        patch = Patch(
            patch_id="patch-nested-sqlite",
            pass_id="pass-integrity",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            branch="main",
            source_version=1,
            operations=(
                InsertBlockOperation(
                    block_id="block-nested",
                    block_type="paragraph",
                    content="Metadata profundamente inmutable.",
                    metadata={
                        "editorial": {
                            "labels": ["opening", "reviewed"],
                            "settings": {"visible": True},
                        }
                    },
                ),
            ),
        )
        approval = ApprovalGate.for_patch(
            patch,
            gate_id="gate-nested-sqlite",
            required_role="editor",
        ).approve(
            actor_id=ACTOR,
            reason="Aprobar metadata anidada.",
            decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        ApplyApprovedPatchHandler(store, projection).handle(
            ApplyApprovedPatchCommand(
                command_id="cmd-nested-sqlite",
                idempotency_key="idem-nested-sqlite",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=ACTOR,
                branch="main",
                expected_version=1,
                patch=patch,
                approval=approval,
            )
        )

    with SQLiteEventStore(database_path) as reopened_store:
        events = reopened_store.get_events(TENANT, EDITORIAL, WORK)
        replayed = Work.replay(events)

    block = replayed.expression_graph.get_block("block-nested")
    assert block is not None
    assert block.metadata["editorial"]["labels"] == ("opening", "reviewed")
    assert block.metadata["editorial"]["settings"]["visible"] is True
    assert events[-1].model_dump(mode="json")["payload"]["block"]["metadata"] == {
        "editorial": {
            "labels": ["opening", "reviewed"],
            "settings": {"visible": True},
        }
    }


def test_persists_exact_edition_approval_between_store_instances(tmp_path):
    database_path = tmp_path / "events.sqlite"
    with SQLiteEventStore(database_path) as store:
        projection = CurrentWorkProjection()
        CreateWorkHandler(store, projection).handle(_create_work_command())
        work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
        approval = EditionApproval.for_work(
            work,
            approval_id="edition-approval.work.yo-no-soy.v1",
        ).approve(
            actor_id=ACTOR,
            reason="Versión exacta autorizada para publicación.",
        )
        store.save_edition_approval(approval)

    with SQLiteEventStore(database_path) as reopened_store:
        persisted = reopened_store.get_edition_approval(approval.approval_id)

    assert persisted == approval
