from datetime import datetime, timezone

import pytest

from editorial_tres.application.commands import (
    AddContentBlockCommand,
    ApplyApprovedPatchCommand,
    CreateWorkCommand,
    RegisterDependencyCommand,
)
from editorial_tres.application.handlers import (
    AddContentBlockHandler,
    ApplyApprovedPatchHandler,
    CreateWorkHandler,
    RegisterDependencyHandler,
)
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.domain.approvals import ApprovalGate
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.patches import DeleteBlockOperation, InsertBlockOperation, MoveBlockOperation, Patch, PatchOperation
from editorial_tres.domain.work import Work
from editorial_tres.exceptions import ConcurrencyError, GraphCycleError, MissingParentNodeError
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore

TENANT = TenantId(value="tenant.tres")
EDITORIAL = EditorialId(value="editorial.tres")
WORK = WorkId(value="work.patch")
ACTOR = ActorId(value="actor.editor")


def setup_work():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(
            command_id="create",
            idempotency_key="create",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=ACTOR,
            title="Patch work",
            language="es",
        )
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(
            command_id="add",
            idempotency_key="add",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=ACTOR,
            expected_version=1,
            block_id="block-1",
            block_type="paragraph",
            content="Antes",
        )
    )
    return store, projection


def approved_patch(source_version: int = 2):
    patch = Patch(
        patch_id="patch-1",
        pass_id="pass-1",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=source_version,
        operations=(
            PatchOperation(
                block_id="block-1",
                before_content="Antes",
                after_content="Después",
            ),
        ),
    )
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-1",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Aprobado",
        decided_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
    )
    return patch, gate


def command(patch, gate, *, key="apply"):
    return ApplyApprovedPatchCommand(
        command_id=f"cmd-{key}",
        idempotency_key=key,
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        actor_id=ACTOR,
        branch="main",
        expected_version=patch.source_version,
        patch=patch,
        approval=gate,
    )


def test_approved_patch_updates_content_and_creates_new_version():
    store, projection = setup_work()
    patch, gate = approved_patch()

    result = ApplyApprovedPatchHandler(store, projection).handle(command(patch, gate))

    rebuilt = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    assert result.version == 3
    assert rebuilt.version == 3
    assert rebuilt.expression_graph.get_block("block-1").content == "Después"


def test_approved_patch_invalidates_transitive_dependents():
    store, projection = setup_work()
    RegisterDependencyHandler(store, projection).handle(
        RegisterDependencyCommand(
            command_id="dependency",
            idempotency_key="dependency",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=ACTOR,
            expected_version=2,
            source_resource_id="block-1",
            dependent_resource_id="visual-1",
            source_resource_type="content_block",
            dependent_resource_type="visual_asset",
            source_version=2,
        )
    )
    patch, gate = approved_patch(source_version=3)

    result = ApplyApprovedPatchHandler(store, projection).handle(command(patch, gate))

    rebuilt = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    assert result.version == 5
    assert rebuilt.dependency_graph.is_stale("visual-1")


def test_stale_approved_patch_is_rejected_before_mutation():
    store, projection = setup_work()
    patch, gate = approved_patch()
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(
            command_id="add-2",
            idempotency_key="add-2",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=ACTOR,
            expected_version=2,
            block_id="block-2",
            block_type="paragraph",
            content="Otro",
        )
    )

    with pytest.raises(ConcurrencyError):
        ApplyApprovedPatchHandler(store, projection).handle(command(patch, gate))

    rebuilt = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    assert rebuilt.version == 3
    assert rebuilt.expression_graph.get_block("block-1").content == "Antes"


def test_patch_application_is_idempotent():
    store, projection = setup_work()
    patch, gate = approved_patch()
    handler = ApplyApprovedPatchHandler(store, projection)
    apply_command = command(patch, gate)

    first = handler.handle(apply_command)
    second = handler.handle(apply_command)

    assert second.commit_id == first.commit_id
    assert len(store.get_events(TENANT, EDITORIAL, WORK)) == 3


def test_mixed_replace_and_insert_patch_applies_atomically_in_one_commit():
    store, projection = setup_work()
    patch = Patch(
        patch_id="patch-mixed",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=2,
        operations=(
            PatchOperation(
                block_id="block-1",
                before_content="Antes",
                after_content="Después",
            ),
            InsertBlockOperation(
                block_id="block-2",
                block_type="paragraph",
                content="Cierre nuevo",
                parent_id="block-1",
                position=1,
                language="es",
                status="revised",
                metadata={"role": "closing"},
            ),
        ),
    )
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-mixed",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Aprobar cambio estructural mixto.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    result = ApplyApprovedPatchHandler(store, projection).handle(command(patch, gate, key="mixed"))

    rebuilt = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    inserted = rebuilt.expression_graph.get_block("block-2")
    head = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")

    assert result.version == 4
    assert rebuilt.version == 4
    assert rebuilt.manuscript_version == 4
    assert rebuilt.expression_graph.get_block("block-1").content == "Después"
    assert inserted is not None
    assert inserted.block_type == "paragraph"
    assert inserted.content == "Cierre nuevo"
    assert inserted.parent_id == "block-1"
    assert inserted.position == 1
    assert inserted.language == "es"
    assert inserted.status == "revised"
    assert dict(inserted.metadata) == {"role": "closing"}
    assert tuple(event.event_type for event in head.events) == (
        "content_block.edited",
        "content_block.added",
    )


def test_invalid_insert_rejects_entire_mixed_patch_without_partial_commit():
    store, projection = setup_work()
    head_before = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")
    events_before = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    patch = Patch(
        patch_id="patch-invalid-insert",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=2,
        operations=(
            PatchOperation(
                block_id="block-1",
                before_content="Antes",
                after_content="Después",
            ),
            InsertBlockOperation(
                block_id="block-2",
                block_type="paragraph",
                content="No debe persistirse",
                parent_id="missing-parent",
                position=1,
            ),
        ),
    )
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-invalid-insert",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Aprobación que debe fallar por precondición estructural.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="snapshot fuente"):
        ApplyApprovedPatchHandler(store, projection).handle(
            command(patch, gate, key="invalid-insert")
        )

    events_after = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    head_after = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")
    rebuilt = Work.replay(events_after)

    assert events_after == events_before
    assert head_after.commit_id == head_before.commit_id
    assert rebuilt.version == 2
    assert rebuilt.expression_graph.get_block("block-1").content == "Antes"
    assert rebuilt.expression_graph.get_block("block-2") is None


def test_delete_block_patch_removes_exact_block_and_replays_event():
    store, projection = setup_work()
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    block = work.expression_graph.get_block("block-1")
    assert block is not None
    patch = Patch(
        patch_id="patch-delete",
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
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-delete",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Eliminar bloque aprobado.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    result = ApplyApprovedPatchHandler(store, projection).handle(
        command(patch, gate, key="delete")
    )

    rebuilt = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    head = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")
    assert result.version == 3
    assert rebuilt.version == 3
    assert rebuilt.manuscript_version == 3
    assert rebuilt.expression_graph.get_block("block-1") is None
    assert tuple(event.event_type for event in head.events) == ("content_block.deleted",)


def test_delete_block_rejects_parent_with_children_without_persisting():
    store, projection = setup_work()
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(
            command_id="add-child",
            idempotency_key="add-child",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=ACTOR,
            expected_version=2,
            block_id="block-2",
            block_type="paragraph",
            content="Hijo",
            parent_id="block-1",
            position=1,
        )
    )
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    block = work.expression_graph.get_block("block-1")
    assert block is not None
    patch = Patch(
        patch_id="patch-delete-parent",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=work.version,
        operations=(DeleteBlockOperation(block_id="block-1", before_block=block),),
    )
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-delete-parent",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Debe rechazarse por hijos.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    events_before = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    head_before = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")

    with pytest.raises(ValueError, match="tenga hijos"):
        ApplyApprovedPatchHandler(store, projection).handle(
            command(patch, gate, key="delete-parent")
        )

    assert tuple(store.get_events(TENANT, EDITORIAL, WORK)) == events_before
    assert store.get_head_commit(TENANT, EDITORIAL, WORK, "main").commit_id == head_before.commit_id


def test_delete_block_rejects_registered_dependents_without_persisting():
    store, projection = setup_work()
    RegisterDependencyHandler(store, projection).handle(
        RegisterDependencyCommand(
            command_id="delete-dependency",
            idempotency_key="delete-dependency",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=ACTOR,
            expected_version=2,
            source_resource_id="block-1",
            dependent_resource_id="visual-delete",
            source_resource_type="content_block",
            dependent_resource_type="visual_asset",
            source_version=2,
        )
    )
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    block = work.expression_graph.get_block("block-1")
    assert block is not None
    patch = Patch(
        patch_id="patch-delete-dependent",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=work.version,
        operations=(DeleteBlockOperation(block_id="block-1", before_block=block),),
    )
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-delete-dependent",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Debe rechazarse por dependencias.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    events_before = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    head_before = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")

    with pytest.raises(ValueError, match="dependientes registrados"):
        ApplyApprovedPatchHandler(store, projection).handle(
            command(patch, gate, key="delete-dependent")
        )

    assert tuple(store.get_events(TENANT, EDITORIAL, WORK)) == events_before
    assert store.get_head_commit(TENANT, EDITORIAL, WORK, "main").commit_id == head_before.commit_id


def test_invalid_delete_rejects_entire_mixed_patch_without_partial_commit():
    store, projection = setup_work()
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(
            command_id="add-atomic-child",
            idempotency_key="add-atomic-child",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=ACTOR,
            expected_version=2,
            block_id="block-2",
            block_type="paragraph",
            content="Hijo original",
            parent_id="block-1",
            position=1,
        )
    )
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    parent = work.expression_graph.get_block("block-1")
    assert parent is not None
    patch = Patch(
        patch_id="patch-atomic-delete",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=work.version,
        operations=(
            PatchOperation(
                block_id="block-2",
                before_content="Hijo original",
                after_content="Hijo editado",
            ),
            DeleteBlockOperation(
                block_id="block-1",
                before_block=parent,
            ),
        ),
    )
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-atomic-delete",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="La eliminación inválida debe abortar todo el patch.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    events_before = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    head_before = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")

    with pytest.raises(ValueError, match="tenga hijos"):
        ApplyApprovedPatchHandler(store, projection).handle(
            command(patch, gate, key="atomic-delete")
        )

    events_after = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    rebuilt = Work.replay(events_after)
    assert events_after == events_before
    assert store.get_head_commit(TENANT, EDITORIAL, WORK, "main").commit_id == head_before.commit_id
    assert rebuilt.expression_graph.get_block("block-1") is not None
    assert rebuilt.expression_graph.get_block("block-2").content == "Hijo original"


def test_apply_patch_command_serializes_insert_and_delete_metadata_to_json():
    store, _ = setup_work()
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    existing = work.expression_graph.get_block("block-1")
    assert existing is not None

    insert_patch = Patch(
        patch_id="patch-serialize-insert",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=work.version,
        operations=(
            InsertBlockOperation(
                block_id="block-json",
                block_type="paragraph",
                content="Serializable",
                metadata={"role": "test"},
            ),
        ),
    )
    insert_gate = ApprovalGate.for_patch(
        insert_patch,
        gate_id="gate-serialize-insert",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Validar serialización.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    delete_before = existing.__class__(
        id=existing.id,
        block_type=existing.block_type,
        content=existing.content,
        parent_id=existing.parent_id,
        position=existing.position,
        language=existing.language,
        status=existing.status,
        metadata={"role": "test"},
    )
    assert type(delete_before.metadata).__name__ == "mappingproxy"

    delete_patch = Patch(
        patch_id="patch-serialize-delete",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=work.version,
        operations=(
            DeleteBlockOperation(
                block_id=existing.id,
                before_block=delete_before,
            ),
        ),
    )
    delete_gate = ApprovalGate.for_patch(
        delete_patch,
        gate_id="gate-serialize-delete",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Validar serialización.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    insert_dump = command(insert_patch, insert_gate, key="serialize-insert").model_dump(mode="json")
    delete_dump = command(delete_patch, delete_gate, key="serialize-delete").model_dump(mode="json")

    assert insert_dump["patch"]["operations"][0]["metadata"] == {"role": "test"}
    assert delete_dump["patch"]["operations"][0]["before_block"]["metadata"] == {"role": "test"}



def _setup_move_work():
    store, projection = setup_work()
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(
            command_id="add-move-child",
            idempotency_key="add-move-child",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=ACTOR,
            expected_version=2,
            block_id="block-2",
            block_type="paragraph",
            content="Hijo móvil",
            parent_id="block-1",
            position=1,
        )
    )
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(
            command_id="add-move-parent",
            idempotency_key="add-move-parent",
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
    return store, projection


def _approve_move_patch(patch: Patch, suffix: str):
    return ApprovalGate.for_patch(
        patch,
        gate_id=f"gate-{suffix}",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Aprobar movimiento estructural.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


def test_move_block_patch_changes_parent_and_position_and_invalidates_dependents():
    store, projection = _setup_move_work()
    RegisterDependencyHandler(store, projection).handle(
        RegisterDependencyCommand(
            command_id="move-dependency",
            idempotency_key="move-dependency",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=ACTOR,
            expected_version=4,
            source_resource_id="block-2",
            dependent_resource_id="visual-move",
            source_resource_type="content_block",
            dependent_resource_type="visual_asset",
            source_version=4,
        )
    )
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    patch = Patch(
        patch_id="patch-move",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=work.version,
        operations=(
            MoveBlockOperation(
                block_id="block-2",
                before_parent_id="block-1",
                before_position=1,
                after_parent_id="block-3",
                after_position=0,
            ),
        ),
    )
    gate = _approve_move_patch(patch, "move")

    result = ApplyApprovedPatchHandler(store, projection).handle(
        command(patch, gate, key="move")
    )

    rebuilt = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    moved = rebuilt.expression_graph.get_block("block-2")
    head = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")
    assert result.version == 7
    assert rebuilt.version == 7
    assert rebuilt.manuscript_version == 5
    assert moved.parent_id == "block-3"
    assert moved.position == 0
    assert moved.content == "Hijo móvil"
    assert rebuilt.dependency_graph.is_stale("visual-move")
    assert tuple(event.event_type for event in head.events) == (
        "content_block.moved",
        "derived_resource.invalidated",
    )


def test_move_block_rejects_stale_location_without_persisting():
    store, projection = _setup_move_work()
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    patch = Patch(
        patch_id="patch-move-stale",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=work.version,
        operations=(
            MoveBlockOperation(
                block_id="block-2",
                before_parent_id="block-1",
                before_position=99,
                after_parent_id="block-3",
                after_position=0,
            ),
        ),
    )
    gate = _approve_move_patch(patch, "move-stale")
    events_before = tuple(store.get_events(TENANT, EDITORIAL, WORK))

    with pytest.raises(ConcurrencyError, match="ubicación aprobada"):
        ApplyApprovedPatchHandler(store, projection).handle(
            command(patch, gate, key="move-stale")
        )

    assert tuple(store.get_events(TENANT, EDITORIAL, WORK)) == events_before


def test_move_block_rejects_missing_destination_parent_without_persisting():
    store, projection = _setup_move_work()
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    patch = Patch(
        patch_id="patch-move-missing-parent",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=work.version,
        operations=(
            MoveBlockOperation(
                block_id="block-2",
                before_parent_id="block-1",
                before_position=1,
                after_parent_id="missing-parent",
                after_position=0,
            ),
        ),
    )
    gate = _approve_move_patch(patch, "move-missing-parent")
    events_before = tuple(store.get_events(TENANT, EDITORIAL, WORK))

    with pytest.raises(MissingParentNodeError, match="no existe"):
        ApplyApprovedPatchHandler(store, projection).handle(
            command(patch, gate, key="move-missing-parent")
        )

    assert tuple(store.get_events(TENANT, EDITORIAL, WORK)) == events_before


def test_move_block_rejects_cycle_without_persisting():
    store, projection = _setup_move_work()
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    patch = Patch(
        patch_id="patch-move-cycle",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=work.version,
        operations=(
            MoveBlockOperation(
                block_id="block-1",
                before_parent_id=None,
                before_position=0,
                after_parent_id="block-2",
                after_position=0,
            ),
        ),
    )
    gate = _approve_move_patch(patch, "move-cycle")
    events_before = tuple(store.get_events(TENANT, EDITORIAL, WORK))

    with pytest.raises(GraphCycleError, match="ciclo"):
        ApplyApprovedPatchHandler(store, projection).handle(
            command(patch, gate, key="move-cycle")
        )

    assert tuple(store.get_events(TENANT, EDITORIAL, WORK)) == events_before


def test_invalid_move_rejects_entire_mixed_patch_without_partial_commit():
    store, projection = _setup_move_work()
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    patch = Patch(
        patch_id="patch-atomic-move",
        pass_id="pass-structural",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        branch="main",
        source_version=work.version,
        operations=(
            PatchOperation(
                block_id="block-3",
                before_content="",
                after_content="Título propuesto",
            ),
            MoveBlockOperation(
                block_id="block-2",
                before_parent_id="block-1",
                before_position=1,
                after_parent_id="missing-parent",
                after_position=0,
            ),
        ),
    )
    gate = _approve_move_patch(patch, "atomic-move")
    events_before = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    head_before = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")

    with pytest.raises(MissingParentNodeError):
        ApplyApprovedPatchHandler(store, projection).handle(
            command(patch, gate, key="atomic-move")
        )

    events_after = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    rebuilt = Work.replay(events_after)
    assert events_after == events_before
    assert store.get_head_commit(TENANT, EDITORIAL, WORK, "main").commit_id == head_before.commit_id
    assert rebuilt.expression_graph.get_block("block-3").content == ""
    assert rebuilt.expression_graph.get_block("block-2").parent_id == "block-1"



def _setup_structural_catalog_work():
    store, projection = setup_work()
    AddContentBlockHandler(store, projection).handle(
        AddContentBlockCommand(
            command_id="add-catalog-delete",
            idempotency_key="add-catalog-delete",
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
            command_id="add-catalog-parent",
            idempotency_key="add-catalog-parent",
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
            command_id="add-catalog-move",
            idempotency_key="add-catalog-move",
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
    RegisterDependencyHandler(store, projection).handle(
        RegisterDependencyCommand(
            command_id="catalog-dependency",
            idempotency_key="catalog-dependency",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=ACTOR,
            expected_version=5,
            source_resource_id="block-4",
            dependent_resource_id="visual-catalog",
            source_resource_type="content_block",
            dependent_resource_type="visual_asset",
            source_version=5,
        )
    )
    return store, projection


def _structural_catalog_patch(work: Work, *, before_delete=None) -> Patch:
    deletable = work.expression_graph.get_block("block-2")
    assert deletable is not None
    return Patch(
        patch_id="patch-structural-catalog",
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
                metadata={"origin": "certification"},
            ),
            DeleteBlockOperation(
                block_id="block-2",
                before_block=before_delete or deletable,
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


def test_structural_patch_catalog_applies_as_one_deterministic_atomic_commit():
    store, projection = _setup_structural_catalog_work()
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    patch = _structural_catalog_patch(work)
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-structural-catalog",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Certificar catálogo estructural completo.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    commits_before = len(store.get_commits(TENANT, EDITORIAL, WORK, "main"))

    result = ApplyApprovedPatchHandler(store, projection).handle(
        command(patch, gate, key="structural-catalog")
    )

    commits_after = store.get_commits(TENANT, EDITORIAL, WORK, "main")
    rebuilt = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    head = commits_after[-1]
    inserted = rebuilt.expression_graph.get_block("block-5")
    moved = rebuilt.expression_graph.get_block("block-4")

    assert len(commits_after) == commits_before + 1
    assert head.commit_id == result.commit_id
    assert tuple(event.event_type for event in head.events) == (
        "content_block.edited",
        "content_block.added",
        "content_block.deleted",
        "content_block.moved",
        "derived_resource.invalidated",
    )
    assert tuple(event.aggregate_version for event in head.events) == (7, 8, 9, 10, 11)
    assert result.version == 11
    assert rebuilt.version == 11
    assert rebuilt.manuscript_version == 9
    assert rebuilt.expression_graph.get_block("block-1").content == "Texto revisado"
    assert rebuilt.expression_graph.get_block("block-2") is None
    assert inserted is not None
    assert inserted.parent_id == "block-3"
    assert inserted.position == 1
    assert dict(inserted.metadata) == {"origin": "certification"}
    assert moved is not None
    assert moved.parent_id == "block-3"
    assert moved.position == 0
    assert moved.content == "Bloque móvil"
    assert rebuilt.dependency_graph.is_stale("visual-catalog")


def test_structural_patch_catalog_invalid_before_state_persists_nothing():
    store, projection = _setup_structural_catalog_work()
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    deletable = work.expression_graph.get_block("block-2")
    assert deletable is not None
    stale_delete_state = deletable.model_copy(update={"content": "Estado incorrecto"})
    patch = _structural_catalog_patch(work, before_delete=stale_delete_state)
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-structural-catalog-invalid",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Debe abortarse por estado previo inválido.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    events_before = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    head_before = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")

    with pytest.raises(ConcurrencyError, match="estado aprobado"):
        ApplyApprovedPatchHandler(store, projection).handle(
            command(patch, gate, key="structural-catalog-invalid")
        )

    events_after = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    head_after = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")
    rebuilt = Work.replay(events_after)

    assert events_after == events_before
    assert head_after.commit_id == head_before.commit_id
    assert rebuilt.version == 6
    assert rebuilt.expression_graph.get_block("block-1").content == "Antes"
    assert rebuilt.expression_graph.get_block("block-2") is not None
    assert rebuilt.expression_graph.get_block("block-4").parent_id == "block-1"
    assert rebuilt.expression_graph.get_block("block-5") is None
    assert not rebuilt.dependency_graph.is_stale("visual-catalog")



def test_delete_block_rejects_incoming_dependency_without_persisting():
    store, projection = setup_work()
    RegisterDependencyHandler(store, projection).handle(
        RegisterDependencyCommand(
            command_id="delete-incoming-dependency",
            idempotency_key="delete-incoming-dependency",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=ACTOR,
            expected_version=2,
            source_resource_id="knowledge-source",
            dependent_resource_id="block-1",
            source_resource_type="knowledge_node",
            dependent_resource_type="content_block",
            source_version=2,
        )
    )
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    block = work.expression_graph.get_block("block-1")
    assert block is not None
    patch = Patch(
        patch_id="patch-delete-incoming-dependent",
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
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-delete-incoming-dependent",
        required_role="editor",
    ).approve(
        actor_id=ACTOR,
        reason="Debe rechazarse por dependencia entrante.",
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    events_before = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    head_before = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")

    with pytest.raises(ValueError, match="destino de dependencias registradas"):
        ApplyApprovedPatchHandler(store, projection).handle(
            command(patch, gate, key="delete-incoming-dependent")
        )

    events_after = tuple(store.get_events(TENANT, EDITORIAL, WORK))
    head_after = store.get_head_commit(TENANT, EDITORIAL, WORK, "main")
    rebuilt = Work.replay(events_after)

    assert events_after == events_before
    assert head_after.commit_id == head_before.commit_id
    assert rebuilt.expression_graph.get_block("block-1") == block
