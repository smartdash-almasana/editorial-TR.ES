"""PC-0 contract tests for correction and literary-alignment findings."""

import pytest
from pydantic import ValidationError

from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import (
    EditorialCriterion,
    ReplacementProposal,
    ReviewFinding,
    TextualFindingBinding,
)
from editorial_tres.domain.text_analysis import SpanishTextAnalyzer
from editorial_tres.domain.work import Work


TENANT = TenantId(value="tenant.tres")
EDITORIAL = EditorialId(value="editorial.tres")
WORK_ID = WorkId(value="work.pc0")
CONTENT = "Las palabras de Jesús transforma al hombre."


def _work(
    *,
    work_id: WorkId = WORK_ID,
    content: str = CONTENT,
) -> Work:
    expression = ExpressionGraph(
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=work_id,
    ).add_block(
        ContentBlock(
            id="block-1",
            block_type="paragraph",
            content=content,
            position=0,
            language="es",
        )
    )
    return Work(
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=work_id,
        title="Obra PC-0",
        language="es",
        knowledge_graph=KnowledgeGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=work_id,
        ),
        narrative_graph=NarrativeGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=work_id,
        ),
        expression_graph=expression,
        dependency_graph=DependencyGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=work_id,
        ),
    )


def _bound_source(
    work: Work | None = None,
) -> tuple[Work, TextualFindingBinding]:
    source_work = work or _work()
    snapshot = SpanishTextAnalyzer().analyze(source_work, branch_id="main")
    span = snapshot.blocks[0].sentences[0]
    return source_work, TextualFindingBinding(snapshot=snapshot, span=span)


def _proposal(
    replacement_text: str = "Las palabras de Jesús transforman al hombre.",
) -> ReplacementProposal:
    return ReplacementProposal(
        replacement_text=replacement_text,
        rationale="Concordancia entre sujeto plural y verbo.",
    )


def _normative_finding(
    *,
    work: Work,
    binding: TextualFindingBinding,
    evidence: str | None = None,
    source_version: int | None = None,
    target_id: str = "block-1",
    work_id: WorkId | None = None,
    criterion_version: str = "1.0.0",
    proposals: tuple[ReplacementProposal, ...] | None = None,
) -> ReviewFinding:
    return ReviewFinding.diagnostic(
        reviewer_id="reviewer.grammar.concordance",
        finding_type="grammar.subject_verb_agreement",
        tenant_id=work.tenant_id,
        editorial_id=work.editorial_id,
        work_id=work_id or work.work_id,
        branch="main",
        source_version=source_version or work.manuscript_version,
        target_id=target_id,
        severity="error",
        evidence=evidence if evidence is not None else binding.span.evidence,
        description="El sujeto plural no concuerda con el verbo singular.",
        recommended_action="Revisar la concordancia.",
        diagnostic_axis="normative_correction",
        editorial_classification="verified_error",
        criterion=EditorialCriterion(
            criterion_id="es.grammar.subject-verb-agreement",
            criterion_version=criterion_version,
        ),
        certainty=0.99,
        text_binding=binding,
        replacement_proposals=proposals if proposals is not None else (_proposal(),),
    )


def test_legacy_finding_remains_backward_compatible() -> None:
    finding = ReviewFinding(
        finding_id="finding-legacy",
        reviewer_id="reviewer.repetition",
        finding_type="expression.repeated_phrase",
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK_ID,
        source_version=1,
        target_id="block-1",
        severity="warning",
        evidence="vida",
        description="Repetición detectada.",
    )

    assert finding.diagnostic_axis == "legacy"
    assert finding.editorial_classification is None
    assert finding.criterion is None
    assert finding.text_binding is None
    assert finding.replacement_proposals == ()


def test_normative_finding_binds_exact_pt0_evidence_and_proposals() -> None:
    work, binding = _bound_source()

    finding = _normative_finding(work=work, binding=binding)

    assert finding.diagnostic_axis == "normative_correction"
    assert finding.editorial_classification == "verified_error"
    assert finding.criterion.criterion_version == "1.0.0"
    assert finding.certainty == 0.99
    assert finding.text_binding.span == binding.span
    assert finding.evidence == binding.snapshot.evidence_for(binding.span.span_id)
    assert finding.replacement_proposals[0].replacement_text.endswith(
        "transforman al hombre."
    )


def test_literary_alignment_can_preserve_an_authorial_choice() -> None:
    work, binding = _bound_source(_work(content="Y entonces, silencio."))

    finding = ReviewFinding.diagnostic(
        reviewer_id="reviewer.voice",
        finding_type="style.elliptical_sentence",
        tenant_id=work.tenant_id,
        editorial_id=work.editorial_id,
        work_id=work.work_id,
        source_version=work.manuscript_version,
        target_id=binding.span.block_id,
        severity="info",
        evidence=binding.span.evidence,
        description="La elipsis sostiene la cadencia buscada.",
        diagnostic_axis="literary_alignment",
        editorial_classification="authorial_choice",
        criterion=EditorialCriterion(
            criterion_id="tres.voice.intent-preservation",
            criterion_version="1.0.0",
        ),
        certainty=0.94,
        text_binding=binding,
    )

    assert finding.diagnostic_axis == "literary_alignment"
    assert finding.editorial_classification == "authorial_choice"
    assert finding.replacement_proposals == ()


def test_same_diagnostic_material_produces_same_finding_id() -> None:
    work, binding = _bound_source()

    first = _normative_finding(work=work, binding=binding)
    second = _normative_finding(work=work, binding=binding)

    assert first.finding_id == second.finding_id
    assert first.finding_id.startswith("finding-")


def test_criterion_version_or_proposal_changes_finding_identity() -> None:
    work, binding = _bound_source()

    base = _normative_finding(work=work, binding=binding)
    new_criterion = _normative_finding(
        work=work,
        binding=binding,
        criterion_version="1.1.0",
    )
    new_proposal = _normative_finding(
        work=work,
        binding=binding,
        proposals=(
            _proposal("Las palabras que pronunció Jesús transforman al hombre."),
        ),
    )

    assert len({base.finding_id, new_criterion.finding_id, new_proposal.finding_id}) == 3


def test_new_diagnostic_rejects_an_arbitrary_finding_id() -> None:
    work, binding = _bound_source()
    finding = _normative_finding(work=work, binding=binding)
    payload = finding.model_dump(mode="python")
    payload["finding_id"] = "finding-arbitrary"

    with pytest.raises(ValidationError, match="finding_id no corresponde"):
        ReviewFinding.model_validate(payload)


def test_diagnostic_requires_classification_criterion_and_certainty() -> None:
    with pytest.raises(ValidationError, match="clasificación, criterio y certeza"):
        ReviewFinding(
            finding_id="finding-incomplete",
            reviewer_id="reviewer.grammar",
            finding_type="grammar.test",
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK_ID,
            source_version=1,
            target_id="block-1",
            severity="warning",
            evidence="texto",
            description="Diagnóstico incompleto.",
            diagnostic_axis="normative_correction",
        )


def test_textual_binding_rejects_partial_or_foreign_span() -> None:
    _, binding = _bound_source()

    with pytest.raises(ValidationError):
        TextualFindingBinding(snapshot=binding.snapshot)  # type: ignore[call-arg]

    foreign_work = _work(content="Una frase completamente diferente.")
    foreign_snapshot = SpanishTextAnalyzer().analyze(
        foreign_work,
        branch_id="main",
    )
    foreign_span = foreign_snapshot.blocks[0].sentences[0]

    with pytest.raises(ValidationError, match="no pertenece|no coincide"):
        TextualFindingBinding(
            snapshot=binding.snapshot,
            span=foreign_span,
        )


def test_finding_rejects_cross_scope_or_stale_textual_binding() -> None:
    work, binding = _bound_source()

    with pytest.raises(ValidationError, match="obsoleto|otro alcance"):
        _normative_finding(
            work=work,
            binding=binding,
            work_id=WorkId(value="work.other"),
        )

    with pytest.raises(ValidationError, match="obsoleto|otro alcance"):
        _normative_finding(
            work=work,
            binding=binding,
            source_version=work.manuscript_version + 1,
        )


def test_finding_rejects_target_or_evidence_outside_bound_span() -> None:
    work, binding = _bound_source()

    with pytest.raises(ValidationError, match="bloque objetivo"):
        _normative_finding(
            work=work,
            binding=binding,
            target_id="block-other",
        )

    with pytest.raises(ValidationError, match="coincidir exactamente"):
        _normative_finding(
            work=work,
            binding=binding,
            evidence="Las palabras de Jesús transforman.",
        )


def test_replacement_proposals_must_change_text_and_be_unique() -> None:
    work, binding = _bound_source()
    unchanged = ReplacementProposal(
        replacement_text=binding.span.evidence,
        rationale="No cambia el texto.",
    )

    with pytest.raises(ValidationError, match="cambio textual efectivo"):
        _normative_finding(
            work=work,
            binding=binding,
            proposals=(unchanged,),
        )

    duplicate = _proposal()
    with pytest.raises(ValidationError, match="repetir el mismo reemplazo"):
        _normative_finding(
            work=work,
            binding=binding,
            proposals=(duplicate, duplicate),
        )


def test_finding_and_proposals_are_immutable_and_do_not_mutate_work() -> None:
    work, binding = _bound_source()
    before = work.model_dump(mode="json")

    finding = _normative_finding(work=work, binding=binding)

    assert work.model_dump(mode="json") == before
    assert not hasattr(finding, "operations")
    with pytest.raises(ValidationError):
        finding.certainty = 0.5
    with pytest.raises(ValidationError):
        finding.replacement_proposals[0].replacement_text = "Otro texto."
