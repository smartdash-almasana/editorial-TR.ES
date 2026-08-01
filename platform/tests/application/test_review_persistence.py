from datetime import datetime, timezone

import pytest

from editorial_tres.application.commands import (
    AddContentBlockCommand,
    ApplyApprovedPatchCommand,
    CreateWorkCommand,
    DecideReviewFindingCommand,
    EditContentBlockCommand,
    RecordReviewFindingCommand,
)
from editorial_tres.application.handlers import (
    AddContentBlockHandler,
    ApplyApprovedPatchHandler,
    CreateWorkHandler,
    DecideReviewFindingHandler,
    EditContentBlockHandler,
    RecordReviewFindingHandler,
    get_review_history,
)
from editorial_tres.application.projections import CurrentWorkProjection
from editorial_tres.composition import compose_application
from editorial_tres.domain.approvals import ApprovalGate
from editorial_tres.domain.editorial_passes import FindingDrivenBlockEditPass
from editorial_tres.domain.finding_decisions import FindingDecision
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import RepeatedPhraseReviewer
from editorial_tres.domain.work import Work
from editorial_tres.exceptions import ConcurrencyError
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore

TENANT = TenantId(value="tenant.tres")
EDITORIAL = EditorialId(value="editorial.tres")
WORK = WorkId(value="work.review-history")
EDITOR = ActorId(value="actor.editor")


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
            actor_id=EDITOR,
            title="Review history",
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
            actor_id=EDITOR,
            expected_version=1,
            block_id="block-1",
            block_type="paragraph",
            content="eco eco final",
        )
    )
    work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    finding = RepeatedPhraseReviewer(reviewer_id="reviewer.repeat", phrase="eco").review(work)[0]
    return store, projection, finding


def record_command(finding, *, key="record"):
    return RecordReviewFindingCommand(
        command_id=f"cmd-{key}",
        idempotency_key=key,
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        actor_id=EDITOR,
        branch="main",
        expected_version=2,
        finding=finding,
    )


def accepted_decision(finding):
    return FindingDecision.for_finding(finding, decision_id="decision-1").accept(
        actor_id=EDITOR,
        reason="Corregir repetición.",
        decided_at=datetime(2026, 7, 30, 21, 0, tzinfo=timezone.utc),
    )


def decision_command(decision, *, expected_version=3, key="decide"):
    return DecideReviewFindingCommand(
        command_id=f"cmd-{key}",
        idempotency_key=key,
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        actor_id=EDITOR,
        branch="main",
        expected_version=expected_version,
        decision=decision,
    )


def test_recorded_finding_replays_without_mutating_manuscript():
    store, projection, finding = setup_work()
    before = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))

    result = RecordReviewFindingHandler(store, projection).handle(record_command(finding))

    after = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    history = get_review_history(store, TENANT, EDITORIAL, WORK)
    assert result.version == 3
    assert after.version == 3
    assert after.manuscript_version == before.manuscript_version == 2
    assert after.expression_graph == before.expression_graph
    assert history.get_finding(finding.finding_id) == finding
    assert history.unresolved_findings() == (finding,)


def test_decision_is_persisted_and_replayed_against_existing_finding():
    store, projection, finding = setup_work()
    RecordReviewFindingHandler(store, projection).handle(record_command(finding))
    decision = accepted_decision(finding)

    result = DecideReviewFindingHandler(store, projection).handle(decision_command(decision))

    current_work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    history = get_review_history(store, TENANT, EDITORIAL, WORK)
    assert result.version == 4
    assert current_work.version == 4
    assert current_work.manuscript_version == 2
    assert history.get_decision(finding.finding_id) == decision
    assert history.unresolved_findings() == ()


def test_decision_rejects_finding_stale_after_manuscript_edit():
    store, projection, finding = setup_work()
    RecordReviewFindingHandler(store, projection).handle(record_command(finding))
    EditContentBlockHandler(store, projection).handle(
        EditContentBlockCommand(
            command_id="edit",
            idempotency_key="edit",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=EDITOR,
            expected_version=3,
            block_id="block-1",
            block_type="paragraph",
            content="eco final",
        )
    )

    with pytest.raises(ConcurrencyError, match="stale"):
        DecideReviewFindingHandler(store, projection).handle(
            decision_command(accepted_decision(finding), expected_version=4)
        )

    assert get_review_history(store, TENANT, EDITORIAL, WORK).get_decision(finding.finding_id) is None


def test_decision_rejects_unknown_finding():
    store, projection, finding = setup_work()
    decision = accepted_decision(finding)

    with pytest.raises(ValueError, match="no existe"):
        DecideReviewFindingHandler(store, projection).handle(
            decision_command(decision, expected_version=2)
        )


def test_record_and_decision_are_idempotent():
    store, projection, finding = setup_work()
    record_handler = RecordReviewFindingHandler(store, projection)
    record = record_command(finding)
    first_record = record_handler.handle(record)
    second_record = record_handler.handle(record)
    assert second_record.commit_id == first_record.commit_id

    decision_handler = DecideReviewFindingHandler(store, projection)
    decide = decision_command(accepted_decision(finding))
    first_decision = decision_handler.handle(decide)
    second_decision = decision_handler.handle(decide)
    assert second_decision.commit_id == first_decision.commit_id
    assert len(store.get_events(TENANT, EDITORIAL, WORK)) == 4


def test_sqlite_composition_preserves_review_history_after_restart(tmp_path):
    database_path = tmp_path / "editorial.sqlite"
    with compose_application(database_path) as app:
        app.create_work.handle(
            CreateWorkCommand(
                command_id="create",
                idempotency_key="create",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=EDITOR,
                title="Persisted review",
                language="es",
            )
        )
        app.add_content_block.handle(
            AddContentBlockCommand(
                command_id="add",
                idempotency_key="add",
                tenant_id=TENANT,
                editorial_id=EDITORIAL,
                work_id=WORK,
                actor_id=EDITOR,
                expected_version=1,
                block_id="block-1",
                block_type="paragraph",
                content="eco eco final",
            )
        )
        work = Work.replay(app.event_store.get_events(TENANT, EDITORIAL, WORK))
        finding = RepeatedPhraseReviewer(reviewer_id="reviewer.repeat", phrase="eco").review(work)[0]
        app.record_review_finding.handle(record_command(finding))
        app.decide_review_finding.handle(decision_command(accepted_decision(finding)))

    with compose_application(database_path) as restarted:
        history = restarted.review_history(TENANT, EDITORIAL, WORK)
        assert history.get_finding(finding.finding_id) == finding
        assert history.get_decision(finding.finding_id).status == "accepted"


def test_persisted_accepted_finding_can_still_produce_patch_on_current_work():
    store, projection, finding = setup_work()
    RecordReviewFindingHandler(store, projection).handle(record_command(finding))
    decision = accepted_decision(finding)
    DecideReviewFindingHandler(store, projection).handle(decision_command(decision))

    current_work = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    editorial_pass = FindingDrivenBlockEditPass(
        pass_id="pass.fix-repetition",
        finding=finding,
        decision=decision,
        replacement_content="eco final",
    )

    patch = editorial_pass.propose(current_work)

    assert current_work.version == 4
    assert current_work.manuscript_version == 2
    assert finding.source_version == current_work.manuscript_version
    assert decision.source_version == current_work.manuscript_version
    assert patch.source_version == current_work.version
    assert patch.operations[0].block_id == "block-1"
    assert patch.operations[0].before_content == "eco eco final"
    assert patch.operations[0].after_content == "eco final"

    approval = ApprovalGate.for_patch(
        patch,
        gate_id="gate-finding-1",
        required_role="editor",
    ).approve(
        actor_id=EDITOR,
        reason="Aplicar corrección aceptada.",
        decided_at=datetime(2026, 8, 1, 13, 0, tzinfo=timezone.utc),
    )
    result = ApplyApprovedPatchHandler(store, projection).handle(
        ApplyApprovedPatchCommand(
            command_id="apply-finding-patch",
            idempotency_key="apply-finding-patch",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK,
            actor_id=EDITOR,
            branch="main",
            expected_version=patch.source_version,
            patch=patch,
            approval=approval,
        )
    )

    rebuilt = Work.replay(store.get_events(TENANT, EDITORIAL, WORK))
    assert result.version == 5
    assert rebuilt.version == 5
    assert rebuilt.manuscript_version == 3
    assert rebuilt.expression_graph.get_block("block-1").content == "eco final"
