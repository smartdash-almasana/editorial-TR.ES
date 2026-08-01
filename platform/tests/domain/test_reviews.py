from editorial_tres.domain.events import create_content_block_added_event
from editorial_tres.domain.graphs.expression import ContentBlock
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import RepeatedPhraseReviewer, ReviewEngine
from editorial_tres.domain.work import Work


TENANT = TenantId(value="tenant.tres")
EDITORIAL = EditorialId(value="editorial.tres")
WORK = WorkId(value="work.review")
ACTOR = ActorId(value="actor.editor")


def make_work(content: str) -> Work:
    work = Work.create(
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        title="Obra",
        language="es",
        actor_id=ACTOR,
        event_id="evt-create",
    )
    block = ContentBlock(id="block-1", block_type="paragraph", content=content)
    event = create_content_block_added_event(
        event_id="evt-add",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK,
        aggregate_version=2,
        actor_id=ACTOR,
        block={
            "id": block.id,
            "block_type": block.block_type,
            "content": block.content,
            "parent_id": block.parent_id,
            "position": block.position,
            "language": block.language,
            "status": block.status,
            "metadata": dict(block.metadata),
        },
    )
    return work.apply(event)


def test_reviewer_returns_structured_finding_without_mutating_work():
    work = make_work("vida vida propósito")
    before = work.model_dump(mode="python")
    reviewer = RepeatedPhraseReviewer(reviewer_id="reviewer.repetition", phrase="vida")

    findings = reviewer.review(work)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.reviewer_id == "reviewer.repetition"
    assert finding.finding_type == "expression.repeated_phrase"
    assert finding.target_id == "block-1"
    assert finding.source_version == work.manuscript_version
    assert finding.evidence == "vida"
    assert work.model_dump(mode="python") == before


def test_reviewer_returns_no_finding_when_threshold_is_not_met():
    work = make_work("vida propósito")
    reviewer = RepeatedPhraseReviewer(
        reviewer_id="reviewer.repetition",
        phrase="vida",
        minimum_occurrences=2,
    )

    assert reviewer.review(work) == ()


def test_same_snapshot_produces_same_finding_id():
    work = make_work("vida vida")
    reviewer = RepeatedPhraseReviewer(reviewer_id="reviewer.repetition", phrase="vida")

    first = reviewer.review(work)
    second = reviewer.review(work)

    assert first[0].finding_id == second[0].finding_id


def test_review_engine_aggregates_reviewers_deterministically():
    work = make_work("vida vida verdad verdad")
    engine = ReviewEngine(
        (
            RepeatedPhraseReviewer(reviewer_id="reviewer.truth", phrase="verdad"),
            RepeatedPhraseReviewer(reviewer_id="reviewer.life", phrase="vida"),
        )
    )

    findings = engine.review(work)

    assert [finding.reviewer_id for finding in findings] == [
        "reviewer.life",
        "reviewer.truth",
    ]


def test_review_engine_rejects_duplicate_reviewer_ids():
    reviewer = RepeatedPhraseReviewer(reviewer_id="reviewer.dup", phrase="vida")

    try:
        ReviewEngine((reviewer, reviewer))
    except ValueError as exc:
        assert "duplicados" in str(exc)
    else:
        raise AssertionError("Se esperaba rechazo de reviewer_id duplicados")
