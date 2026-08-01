import pytest

from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import (
    ContinuityReviewer,
    ContinuityRule,
    RhythmReviewer,
    StructuralReviewer,
    VoiceDriftReviewer,
)
from editorial_tres.domain.work import Work


def _work(content: str) -> Work:
    tenant_id = TenantId(value="tenant.demo")
    editorial_id = EditorialId(value="editorial.tres")
    work_id = WorkId(value="work.reviewers")
    expression = ExpressionGraph(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
    ).add_block(ContentBlock(id="block-1", block_type="paragraph", content=content))
    return Work(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Prueba",
        language="es",
        knowledge_graph=KnowledgeGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id),
        narrative_graph=NarrativeGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id),
        expression_graph=expression,
        dependency_graph=DependencyGraph(tenant_id=tenant_id, editorial_id=editorial_id, work_id=work_id),
    )


def test_voice_drift_reviewer_emits_finding_only_after_configured_threshold():
    reviewer = VoiceDriftReviewer(
        reviewer_id="reviewer.voice",
        drift_markers=("necesidad imperiosa", "tirón invisible"),
        minimum_markers=2,
    )

    findings = reviewer.review(_work("Sintió una necesidad imperiosa y un tirón invisible."))

    assert len(findings) == 1
    assert findings[0].finding_type == "expression.voice_drift"
    assert findings[0].source_version == 1


def test_continuity_reviewer_requires_established_state_before_conflict():
    reviewer = ContinuityReviewer(
        reviewer_id="reviewer.continuity",
        rules=(
            ContinuityRule(
                rule_id="clock",
                entity="reloj",
                established_markers=("dejé sobre la cómoda",),
                conflicting_markers=("reloj en mi bolsillo",),
            ),
        ),
    )

    findings = reviewer.review(_work("Lo dejé sobre la cómoda. Más tarde sentí el reloj en mi bolsillo."))

    assert len(findings) == 1
    assert findings[0].finding_type == "narrative.continuity_conflict"
    assert findings[0].severity == "error"


def test_structural_reviewer_detects_duplicate_paragraph_and_thematic_reiteration():
    paragraph = "El tiempo pasó. Los años se acumularon."
    work = _work(f"{paragraph}\n{paragraph}\n{paragraph}")
    reviewer = StructuralReviewer(
        reviewer_id="reviewer.structural",
        thematic_phrases=("El tiempo pasó.",),
        minimum_thematic_occurrences=3,
    )

    findings = reviewer.review(work)
    finding_types = {finding.finding_type for finding in findings}

    assert finding_types == {
        "structure.duplicate_paragraph",
        "structure.thematic_reiteration",
    }


def test_literary_reviewers_reject_empty_configuration():
    with pytest.raises(ValueError):
        VoiceDriftReviewer(reviewer_id="reviewer.voice", drift_markers=())
    with pytest.raises(ValueError):
        ContinuityReviewer(reviewer_id="reviewer.continuity", rules=())


def test_rhythm_reviewer_detects_short_sentence_run():
    reviewer = RhythmReviewer(
        reviewer_id="reviewer.rhythm",
        short_sentence_max_words=2,
        long_sentence_min_words=20,
        minimum_short_run=4,
        uniformity_min_sentences=10,
    )

    findings = reviewer.review(_work("Corre. Mira. Espera. Vuelve."))

    assert [finding.finding_type for finding in findings] == [
        "expression.rhythm.short_sentence_run"
    ]


def test_rhythm_reviewer_detects_long_sentence_run():
    reviewer = RhythmReviewer(
        reviewer_id="reviewer.rhythm",
        short_sentence_max_words=1,
        long_sentence_min_words=5,
        minimum_long_run=3,
        uniformity_min_sentences=10,
    )
    content = (
        "Uno dos tres cuatro cinco. "
        "Seis siete ocho nueve diez. "
        "Once doce trece catorce quince."
    )

    findings = reviewer.review(_work(content))

    assert [finding.finding_type for finding in findings] == [
        "expression.rhythm.long_sentence_run"
    ]


def test_rhythm_reviewer_detects_uniform_sentence_lengths():
    reviewer = RhythmReviewer(
        reviewer_id="reviewer.rhythm",
        short_sentence_max_words=1,
        long_sentence_min_words=20,
        uniformity_min_sentences=6,
        uniformity_max_word_range=0,
    )
    content = (
        "Uno dos tres. Cuatro cinco seis. Siete ocho nueve. "
        "Diez once doce. Trece catorce quince. Dieciséis diecisiete dieciocho."
    )

    findings = reviewer.review(_work(content))

    assert [finding.finding_type for finding in findings] == [
        "expression.rhythm.uniform_sentence_length"
    ]


def test_rhythm_reviewer_detects_repeated_sentence_opening():
    reviewer = RhythmReviewer(
        reviewer_id="reviewer.rhythm",
        short_sentence_max_words=1,
        long_sentence_min_words=20,
        uniformity_min_sentences=10,
        opening_word_count=2,
        minimum_repeated_openings=4,
    )
    content = (
        "La casa canta. La casa duerme. La casa espera. La casa tiembla."
    )

    findings = reviewer.review(_work(content))

    assert [finding.finding_type for finding in findings] == [
        "expression.rhythm.repeated_opening"
    ]


def test_rhythm_reviewer_rejects_overlapping_short_and_long_thresholds():
    with pytest.raises(ValueError):
        RhythmReviewer(
            reviewer_id="reviewer.rhythm",
            short_sentence_max_words=10,
            long_sentence_min_words=10,
        )
