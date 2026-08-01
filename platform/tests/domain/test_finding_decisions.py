"""Tests for explicit decisions over review findings and finding-driven passes."""

from datetime import datetime, timezone

import pytest

from editorial_tres.domain.editorial_passes import FindingDrivenBlockEditPass
from editorial_tres.domain.finding_decisions import FindingDecision
from editorial_tres.domain.graphs.expression import ContentBlock
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import ReviewFinding
from editorial_tres.domain.work import Work

TENANT = TenantId(value="tenant.tres")
EDITORIAL = EditorialId(value="editorial.tres")
WORK_ID = WorkId(value="work.finding")
ACTOR = ActorId(value="actor.editor")


def _work() -> Work:
    work = Work.create(
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK_ID,
        title="Obra",
        language="es",
        actor_id=ACTOR,
        event_id="evt-create",
    )
    graph = work.expression_graph.add_block(
        ContentBlock(
            id="block-1",
            block_type="paragraph",
            content="eco eco eco",
            position=0,
        )
    )
    return work.model_copy(update={"expression_graph": graph})


def _finding(work: Work) -> ReviewFinding:
    return ReviewFinding(
        finding_id="finding-1",
        reviewer_id="reviewer.repetition",
        finding_type="expression.repeated_phrase",
        tenant_id=work.tenant_id,
        editorial_id=work.editorial_id,
        work_id=work.work_id,
        branch="main",
        source_version=work.manuscript_version,
        target_id="block-1",
        severity="warning",
        evidence="eco",
        description="Repetición detectada.",
        recommended_action="Revisar repetición.",
    )


def test_finding_decision_starts_pending_and_preserves_snapshot_scope() -> None:
    work = _work()
    finding = _finding(work)

    decision = FindingDecision.for_finding(finding, decision_id="decision-1")

    assert decision.status == "pending"
    assert decision.finding_id == finding.finding_id
    assert decision.work_id == finding.work_id
    assert decision.source_version == finding.source_version
    assert decision.decided_by is None


def test_accept_reject_and_escalate_return_resolved_immutable_decisions() -> None:
    finding = _finding(_work())
    base = FindingDecision.for_finding(finding, decision_id="decision-1")
    decided_at = datetime(2026, 7, 30, 21, 0, tzinfo=timezone.utc)

    accepted = base.accept(actor_id=ACTOR, reason="Corregir.", decided_at=decided_at)
    rejected = FindingDecision.for_finding(finding, decision_id="decision-2").reject(actor_id=ACTOR)
    escalated = FindingDecision.for_finding(finding, decision_id="decision-3").escalate(actor_id=ACTOR, reason="Requiere autor.")

    assert base.status == "pending"
    assert accepted.status == "accepted"
    assert accepted.reason == "Corregir."
    assert accepted.decided_at == decided_at
    assert rejected.status == "rejected"
    assert escalated.status == "escalated"


def test_resolved_finding_decision_cannot_be_decided_twice() -> None:
    decision = FindingDecision.for_finding(_finding(_work()), decision_id="decision-1").accept(actor_id=ACTOR)

    with pytest.raises(ValueError, match="ya resuelta"):
        decision.reject(actor_id=ACTOR)


def test_finding_driven_pass_requires_accepted_matching_decision() -> None:
    work = _work()
    finding = _finding(work)
    pending = FindingDecision.for_finding(finding, decision_id="decision-1")

    with pytest.raises(ValueError, match="aceptado"):
        FindingDrivenBlockEditPass(
            pass_id="pass.fix-repetition",
            finding=finding,
            decision=pending,
            replacement_content="eco",
        ).propose(work)

    other_finding = finding.model_copy(update={"finding_id": "finding-other"})
    accepted = FindingDecision.for_finding(other_finding, decision_id="decision-2").accept(actor_id=ACTOR)
    with pytest.raises(ValueError, match="no corresponde"):
        FindingDrivenBlockEditPass(
            pass_id="pass.fix-repetition",
            finding=finding,
            decision=accepted,
            replacement_content="eco",
        ).propose(work)


def test_accepted_finding_can_produce_patch_without_mutating_work() -> None:
    work = _work()
    finding = _finding(work)
    decision = FindingDecision.for_finding(finding, decision_id="decision-1").accept(actor_id=ACTOR, reason="Aplicar corrección.")
    before = work.model_dump(mode="json")

    patch = FindingDrivenBlockEditPass(
        pass_id="pass.fix-repetition",
        finding=finding,
        decision=decision,
        replacement_content="eco",
    ).propose(work)

    assert work.model_dump(mode="json") == before
    assert patch.source_version == work.version
    assert patch.operations[0].block_id == finding.target_id
    assert patch.operations[0].before_content == "eco eco eco"
    assert patch.operations[0].after_content == "eco"


def test_finding_driven_pass_rejects_stale_snapshot() -> None:
    work = _work()
    finding = _finding(work)
    decision = FindingDecision.for_finding(finding, decision_id="decision-1").accept(actor_id=ACTOR)
    newer_work = work.model_copy(
        update={
            "version": work.version + 1,
            "manuscript_version": work.manuscript_version + 1,
        }
    )

    with pytest.raises(ValueError, match="manuscrito cambió"):
        FindingDrivenBlockEditPass(
            pass_id="pass.fix-repetition",
            finding=finding,
            decision=decision,
            replacement_content="eco",
        ).propose(newer_work)
