"""Tests for explicit human approval gates over editorial patches."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from editorial_tres.domain.approvals import ApprovalGate
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.patches import InsertBlockOperation, Patch, PatchOperation


def _patch() -> Patch:
    return Patch(
        patch_id="patch-001",
        pass_id="pass.structural-001",
        tenant_id=TenantId(value="tenant.tres"),
        editorial_id=EditorialId(value="editorial.tres"),
        work_id=WorkId(value="work.zoe"),
        branch="main",
        source_version=7,
        operations=(
            PatchOperation(
                block_id="block.opening",
                before_content="Texto anterior.",
                after_content="Texto propuesto.",
            ),
        ),
    )


def test_gate_starts_pending_and_is_bound_to_patch_snapshot() -> None:
    patch = _patch()
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-001",
        required_role="author",
    )

    assert gate.status == "pending"
    assert gate.patch_id == patch.patch_id
    assert gate.work_id == patch.work_id
    assert gate.branch == patch.branch
    assert gate.source_version == patch.source_version
    assert gate.decided_by is None


def test_approve_returns_new_gate_without_mutating_pending_gate() -> None:
    gate = ApprovalGate.for_patch(_patch(), gate_id="gate-001", required_role="author")
    decided_at = datetime(2026, 7, 30, 20, 0, tzinfo=timezone.utc)

    approved = gate.approve(
        actor_id=ActorId(value="actor.author"),
        reason="Cambio aprobado.",
        decided_at=decided_at,
    )

    assert gate.status == "pending"
    assert approved.status == "approved"
    assert approved.decided_by == ActorId(value="actor.author")
    assert approved.decision_reason == "Cambio aprobado."
    assert approved.decided_at == decided_at


def test_reject_records_human_decision_without_changing_patch() -> None:
    patch = _patch()
    original = patch.model_dump()
    gate = ApprovalGate.for_patch(patch, gate_id="gate-001", required_role="editor")

    rejected = gate.reject(actor_id=ActorId(value="actor.editor"), reason="No conserva la voz.")

    assert rejected.status == "rejected"
    assert rejected.required_role == "editor"
    assert rejected.decision_reason == "No conserva la voz."
    assert patch.model_dump() == original


def test_resolved_gate_cannot_be_decided_twice() -> None:
    gate = ApprovalGate.for_patch(_patch(), gate_id="gate-001", required_role="author")
    approved = gate.approve(actor_id=ActorId(value="actor.author"))

    with pytest.raises(ValueError, match="ya resuelta"):
        approved.reject(actor_id=ActorId(value="actor.editor"))


def test_resolved_gate_requires_actor_and_timestamp() -> None:
    patch = _patch()

    with pytest.raises(ValueError, match="actor y fecha"):
        ApprovalGate(
            gate_id="gate-invalid",
            patch_id=patch.patch_id,
            tenant_id=patch.tenant_id,
            editorial_id=patch.editorial_id,
            work_id=patch.work_id,
            branch=patch.branch,
            source_version=patch.source_version,
            required_role="author",
            status="approved",
        )



def test_gate_binds_approval_to_exact_canonical_patch_digest() -> None:
    patch = _patch()

    gate = ApprovalGate.for_patch(patch, gate_id="gate-digest", required_role="author")

    assert gate.patch_digest == patch.digest()
    assert len(gate.patch_digest) == 64


def test_patch_digest_is_stable_after_json_round_trip() -> None:
    patch = Patch(
        patch_id="patch-nested",
        pass_id="pass.structural-nested",
        tenant_id=TenantId(value="tenant.tres"),
        editorial_id=EditorialId(value="editorial.tres"),
        work_id=WorkId(value="work.zoe"),
        branch="main",
        source_version=7,
        operations=(
            InsertBlockOperation(
                block_id="block.nested",
                block_type="paragraph",
                content="Texto propuesto.",
                metadata={
                    "editorial": {
                        "labels": ["opening", "reviewed"],
                        "settings": {"visible": True},
                    }
                },
            ),
        ),
    )

    rebuilt = Patch.model_validate(patch.model_dump(mode="json"))

    assert rebuilt.digest() == patch.digest()
    assert rebuilt.canonical_payload() == patch.canonical_payload()


def test_patch_digest_changes_when_material_content_or_metadata_changes() -> None:
    base = Patch(
        patch_id="patch-same-id",
        pass_id="pass.structural-001",
        tenant_id=TenantId(value="tenant.tres"),
        editorial_id=EditorialId(value="editorial.tres"),
        work_id=WorkId(value="work.zoe"),
        branch="main",
        source_version=7,
        operations=(
            InsertBlockOperation(
                block_id="block.insert",
                block_type="paragraph",
                content="Aprobado",
                metadata={"nested": {"priority": 1}},
            ),
        ),
    )
    changed_content = base.model_copy(
        update={
            "operations": (
                InsertBlockOperation(
                    block_id="block.insert",
                    block_type="paragraph",
                    content="No aprobado",
                    metadata={"nested": {"priority": 1}},
                ),
            )
        }
    )
    changed_metadata = base.model_copy(
        update={
            "operations": (
                InsertBlockOperation(
                    block_id="block.insert",
                    block_type="paragraph",
                    content="Aprobado",
                    metadata={"nested": {"priority": 2}},
                ),
            )
        }
    )

    assert changed_content.digest() != base.digest()
    assert changed_metadata.digest() != base.digest()


def test_legacy_approval_without_digest_requires_new_approval() -> None:
    patch = _patch()
    legacy_gate = ApprovalGate(
        gate_id="gate-legacy",
        patch_id=patch.patch_id,
        tenant_id=patch.tenant_id,
        editorial_id=patch.editorial_id,
        work_id=patch.work_id,
        branch=patch.branch,
        source_version=patch.source_version,
        required_role="author",
    ).approve(
        actor_id=ActorId(value="actor.author"),
        decided_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )

    assert legacy_gate.patch_digest is None



def test_nested_metadata_cannot_change_after_patch_approval() -> None:
    metadata = {
        "editorial": {
            "labels": ["opening"],
            "settings": {"visible": True},
        }
    }
    patch = Patch(
        patch_id="patch-deep-freeze",
        pass_id="pass.structural-deep-freeze",
        tenant_id=TenantId(value="tenant.tres"),
        editorial_id=EditorialId(value="editorial.tres"),
        work_id=WorkId(value="work.zoe"),
        branch="main",
        source_version=7,
        operations=(
            InsertBlockOperation(
                block_id="block.deep-freeze",
                block_type="paragraph",
                content="Texto aprobado.",
                metadata=metadata,
            ),
        ),
    )
    gate = ApprovalGate.for_patch(
        patch,
        gate_id="gate-deep-freeze",
        required_role="author",
    )
    approved_digest = gate.patch_digest

    metadata["editorial"]["labels"].append("mutated")
    metadata["editorial"]["settings"]["visible"] = False
    operation = patch.operations[0]

    assert operation.metadata["editorial"]["labels"] == ("opening",)
    assert operation.metadata["editorial"]["settings"]["visible"] is True
    assert patch.digest() == approved_digest
    with pytest.raises(ValidationError):
        operation.content = "No aprobado"
    with pytest.raises(TypeError):
        operation.metadata["editorial"]["settings"]["visible"] = False



def test_patch_digest_preserves_operation_order() -> None:
    first_operation = InsertBlockOperation(
        block_id="block.first",
        block_type="paragraph",
        content="Primero",
    )
    second_operation = InsertBlockOperation(
        block_id="block.second",
        block_type="paragraph",
        content="Segundo",
    )
    common = dict(
        patch_id="patch-order",
        pass_id="pass.structural-order",
        tenant_id=TenantId(value="tenant.tres"),
        editorial_id=EditorialId(value="editorial.tres"),
        work_id=WorkId(value="work.zoe"),
        branch="main",
        source_version=7,
    )

    forward = Patch(operations=(first_operation, second_operation), **common)
    reversed_patch = Patch(operations=(second_operation, first_operation), **common)

    assert forward.digest() != reversed_patch.digest()
    assert forward.canonical_payload()["patch_schema_version"] == 1
