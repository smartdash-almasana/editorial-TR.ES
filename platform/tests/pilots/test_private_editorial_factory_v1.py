from datetime import datetime, timezone

import pytest

from editorial_tres.application.app_book_compiler import AppBookCompiler
from editorial_tres.application.commands import (
    AddContentBlockCommand,
    ApplyApprovedPatchCommand,
    CreateWorkCommand,
    DecideReviewFindingCommand,
    RecordReviewFindingCommand,
)
from editorial_tres.application.edition_projector import EditionProjector
from editorial_tres.application.handlers import (
    AddContentBlockHandler,
    ApplyApprovedPatchHandler,
    CreateWorkHandler,
    DecideReviewFindingHandler,
    RecordReviewFindingHandler,
    get_review_history,
)
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.domain.approvals import ApprovalGate
from editorial_tres.domain.editorial_passes import FindingDrivenBlockEditPass
from editorial_tres.domain.finding_decisions import FindingDecision
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import (
    RepeatedPhraseReviewer,
    ReviewEngine,
)
from editorial_tres.domain.work import Work
from editorial_tres.infrastructure.html_edition_renderer import HtmlEditionRenderer
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore


TENANT = TenantId(value="tenant.tres-private-factory")
EDITORIAL = EditorialId(value="editorial.tres")
WORK = WorkId(value="work.la-aguja-quieta")
EDITOR = ActorId(value="actor.editor")
DECIDED_AT = datetime(2026, 8, 1, 18, 0, tzinfo=timezone.utc)

OPENING_BEFORE = (
    "La aguja estaba quieta, quieta, sobre la mesa. "
    "Afuera, el reloj del taller seguía andando."
)
OPENING_AFTER = (
    "La aguja estaba quieta sobre la mesa. "
    "Afuera, el reloj del taller seguía andando."
)
CLOSING = (
    "El silencio era una pausa, no una falla. "
    "El silencio guardaba el último movimiento."
)


def _seed_original_work():
    store = MemoryEventStore()
    projection = CurrentWorkProjection()
    create_result = CreateWorkHandler(store, projection).handle(
        CreateWorkCommand(
            command_id="pf0-create",
            idempotency_key="pf0-create",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=EDITOR,
            title="La aguja quieta",
            language="es",
        )
    )

    blocks = (
        {
            "block_id": "chapter-1",
            "block_type": "heading",
            "content": "La aguja quieta",
            "parent_id": None,
            "position": 0,
        },
        {
            "block_id": "opening",
            "block_type": "paragraph",
            "content": OPENING_BEFORE,
            "parent_id": "chapter-1",
            "position": 0,
        },
        {
            "block_id": "closing",
            "block_type": "paragraph",
            "content": CLOSING,
            "parent_id": "chapter-1",
            "position": 1,
        },
    )

    version = create_result.version
    add_handler = AddContentBlockHandler(store, projection)
    for block in blocks:
        result = add_handler.handle(
            AddContentBlockCommand(
                command_id=f"pf0-add-{block['block_id']}",
                idempotency_key=f"pf0-add-{block['block_id']}",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=EDITOR,
                expected_version=version,
                language="es",
                status="approved",
                **block,
            )
        )
        version = result.version

    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    return store, projection, work


def _record_findings(store, projection, findings, *, expected_version):
    handler = RecordReviewFindingHandler(store, projection)
    version = expected_version
    for finding in findings:
        result = handler.handle(
            RecordReviewFindingCommand(
                command_id=f"pf0-record-{finding.finding_id}",
                idempotency_key=f"pf0-record-{finding.finding_id}",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=EDITOR,
                expected_version=version,
                finding=finding,
            )
        )
        version = result.version
    return version


def _persist_decision(store, projection, decision, *, expected_version):
    return DecideReviewFindingHandler(store, projection).handle(
        DecideReviewFindingCommand(
            command_id=f"pf0-decide-{decision.decision_id}",
            idempotency_key=f"pf0-decide-{decision.decision_id}",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=EDITOR,
            expected_version=expected_version,
            decision=decision,
        )
    )


def test_private_editorial_factory_reaches_integrity_checked_appbook_and_html():
    store, projection, diagnosed_work = _seed_original_work()
    manuscript_before_review = diagnosed_work.expression_graph.model_dump(mode="json")

    findings = ReviewEngine(
        reviewers=(
            RepeatedPhraseReviewer(
                reviewer_id="reviewer.mechanical-repetition",
                phrase="quieta",
            ),
            RepeatedPhraseReviewer(
                reviewer_id="reviewer.deliberate-motif",
                phrase="El silencio",
            ),
        )
    ).review(diagnosed_work)

    assert len(findings) == 2
    assert diagnosed_work.expression_graph.model_dump(mode="json") == manuscript_before_review
    assert {finding.source_version for finding in findings} == {
        diagnosed_work.manuscript_version
    }

    finding_by_reviewer = {finding.reviewer_id: finding for finding in findings}
    accepted_finding = finding_by_reviewer["reviewer.mechanical-repetition"]
    rejected_finding = finding_by_reviewer["reviewer.deliberate-motif"]

    version = _record_findings(
        store,
        projection,
        findings,
        expected_version=diagnosed_work.version,
    )
    accepted_decision = FindingDecision.for_finding(
        accepted_finding,
        decision_id="decision.accept-mechanical-repetition",
    ).accept(
        actor_id=EDITOR,
        reason="La repetición inmediata no aporta sentido y se corrige.",
        decided_at=DECIDED_AT,
    )
    accepted_result = _persist_decision(
        store,
        projection,
        accepted_decision,
        expected_version=version,
    )
    rejected_decision = FindingDecision.for_finding(
        rejected_finding,
        decision_id="decision.keep-deliberate-motif",
    ).reject(
        actor_id=EDITOR,
        reason="La repetición sostiene deliberadamente el motivo del silencio.",
        decided_at=DECIDED_AT,
    )
    _persist_decision(
        store,
        projection,
        rejected_decision,
        expected_version=accepted_result.version,
    )

    decided_work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    history = get_review_history(store, TENANT, EDITORIAL, WORK)
    assert decided_work.manuscript_version == diagnosed_work.manuscript_version
    assert decided_work.expression_graph.model_dump(mode="json") == manuscript_before_review
    assert history.get_decision(accepted_finding.finding_id).status == "accepted"
    assert history.get_decision(rejected_finding.finding_id).status == "rejected"
    assert history.unresolved_findings() == ()

    patch = FindingDrivenBlockEditPass(
        pass_id="pass.remove-mechanical-repetition",
        finding=accepted_finding,
        decision=accepted_decision,
        replacement_content=OPENING_AFTER,
    ).propose(decided_work)
    approval = ApprovalGate.for_patch(
        patch,
        gate_id="gate.pf0-editorial-change",
        required_role="editor",
    ).approve(
        actor_id=EDITOR,
        reason="Cambio editorial revisado y aprobado.",
        decided_at=DECIDED_AT,
    )

    assert patch.source_version == decided_work.version
    assert approval.patch_digest == patch.digest()
    assert tuple(operation.block_id for operation in patch.operations) == ("opening",)

    apply_result = ApplyApprovedPatchHandler(store, projection).handle(
        ApplyApprovedPatchCommand(
            command_id="pf0-apply-approved-patch",
            idempotency_key="pf0-apply-approved-patch",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=EDITOR,
            expected_version=patch.source_version,
            patch=patch,
            approval=approval,
        )
    )

    final_work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    final_history = get_review_history(store, TENANT, EDITORIAL, WORK)
    assert final_work.version == apply_result.version
    assert final_work.manuscript_version == diagnosed_work.manuscript_version + 1
    assert final_work.expression_graph.get_block("opening").content == OPENING_AFTER
    assert final_work.expression_graph.get_block("closing").content == CLOSING
    assert final_history.get_decision(rejected_finding.finding_id) == rejected_decision

    projector = EditionProjector()
    with pytest.raises(ValueError, match="Work aprobada"):
        projector.project(final_work)

    # PF-0 validates publication from an explicitly approved immutable fixture.
    # Persisting the global Work status is a separate production capability.
    approved_work = final_work.model_copy(update={"status": "approved"})
    snapshot = projector.project(
        approved_work,
        edition_id="edition.la-aguja-quieta.v1",
        edition_version=1,
        public_metadata={"author": "Editorial TR.ES", "pilot": "PF-0"},
    )
    package = AppBookCompiler().compile(snapshot)
    html = HtmlEditionRenderer().render(snapshot)

    assert snapshot.source_work_version == final_work.version
    assert snapshot.source_manuscript_version == final_work.manuscript_version
    assert snapshot.reading_order == ("chapter-1", "opening", "closing")
    assert package.manifest.snapshot_sha256 == snapshot.digest()
    assert package.manifest.source_manuscript_version == final_work.manuscript_version
    assert package.verify_integrity() is True
    assert OPENING_AFTER in package.to_json()
    assert CLOSING in package.to_json()
    assert OPENING_AFTER in html
    assert CLOSING in html

    public_artifacts = package.to_json() + html
    for internal_id in (
        accepted_finding.finding_id,
        rejected_finding.finding_id,
        accepted_decision.decision_id,
        rejected_decision.decision_id,
        patch.patch_id,
        approval.gate_id,
    ):
        assert internal_id not in public_artifacts
