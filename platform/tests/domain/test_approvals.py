"""Tests for explicit human approval gates over editorial patches."""

from datetime import datetime, timezone

import pytest

from editorial_tres.domain.approvals import ApprovalGate
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.patches import Patch, PatchOperation


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
