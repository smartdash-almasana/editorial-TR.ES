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
from editorial_tres.domain.patches import Patch, PatchOperation
from editorial_tres.domain.work import Work
from editorial_tres.exceptions import ConcurrencyError
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
