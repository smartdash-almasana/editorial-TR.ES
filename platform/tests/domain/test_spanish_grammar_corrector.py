"""PC-2 tests for the traceable Spanish grammar corrector."""

import pytest
from pydantic import ValidationError

from editorial_tres.domain.grammar import (
    BUILTIN_GRAMMAR_RULES,
    SimpleAgreementRule,
    SpanishGrammarCorrector,
)
from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import EditorialCriterion
from editorial_tres.domain.text_analysis import SpanishTextAnalyzer
from editorial_tres.domain.work import Work


TENANT = TenantId(value="tenant.tres")
EDITORIAL = EditorialId(value="editorial.tres")
WORK_ID = WorkId(value="work.pc2")


def _work(*contents: str) -> Work:
    expression = ExpressionGraph(
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK_ID,
    )
    for position, content in enumerate(contents):
        expression = expression.add_block(
            ContentBlock(
                id=f"block-{position + 1}",
                block_type="paragraph",
                content=content,
                position=position,
                language="es",
            )
        )
    return Work(
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=WORK_ID,
        title="Obra PC-2",
        language="es",
        knowledge_graph=KnowledgeGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK_ID,
        ),
        narrative_graph=NarrativeGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK_ID,
        ),
        expression_graph=expression,
        dependency_graph=DependencyGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=WORK_ID,
        ),
    )


def _snapshot(*contents: str):
    return SpanishTextAnalyzer().analyze(_work(*contents), branch_id="main")


def _agreement(
    *,
    criterion_id: str = "oro.grammar.palabra-transformar",
) -> SimpleAgreementRule:
    return SimpleAgreementRule(
        singular_subject="La palabra",
        plural_subject="Las palabras",
        singular_verb="transforma",
        plural_verb="transforman",
        rationale=(
            "Concordar el verbo «transformar» con el número del sujeto "
            "explícito."
        ),
        criterion=EditorialCriterion(
            criterion_id=criterion_id,
            criterion_version="1.0.0",
        ),
    )


def _replacement(finding) -> str:
    return finding.replacement_proposals[0].replacement_text


def test_clean_grammar_produces_no_findings() -> None:
    snapshot = _snapshot(
        "Se lo entregó a pesar de que había muchas razones."
    )

    assert SpanishGrammarCorrector().analyze(snapshot) == ()


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("Le lo entregó.", "Se lo entregó."),
        ("Le la entregó.", "Se la entregó."),
        ("Les los entregó.", "Se los entregó."),
        ("LES LAS entregó.", "SE LAS entregó."),
    ),
)
def test_incompatible_object_clitics_are_corrected(
    source: str,
    expected: str,
) -> None:
    finding = SpanishGrammarCorrector().analyze(_snapshot(source))[0]

    assert finding.finding_type == "grammar.incompatible_object_clitics"
    assert finding.editorial_classification == "verified_error"
    assert finding.certainty == 1.0
    assert _replacement(finding) == expected


def test_valid_clitic_sequences_are_not_generalized() -> None:
    snapshot = _snapshot("Se lo entregó y le entregó el libro.")

    assert SpanishGrammarCorrector().analyze(snapshot) == ()


def test_a_pesar_que_receives_the_governed_preposition() -> None:
    finding = SpanishGrammarCorrector().analyze(
        _snapshot("A pesar que llovía, salió.")
    )[0]

    assert finding.finding_type == "grammar.a_pesar_que_government"
    assert finding.editorial_classification == "verified_error"
    assert _replacement(finding) == "A pesar de que llovía, salió."


def test_complete_a_pesar_de_que_is_not_flagged() -> None:
    snapshot = _snapshot("A pesar de que llovía, salió.")

    assert SpanishGrammarCorrector().analyze(snapshot) == ()


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("Habían muchas razones.", "Había muchas razones."),
        ("Hubieron varios problemas.", "Hubo varios problemas."),
        ("Habrán tres encuentros.", "Habrá tres encuentros."),
    ),
)
def test_plural_impersonal_haber_is_a_probable_issue(
    source: str,
    expected: str,
) -> None:
    finding = SpanishGrammarCorrector().analyze(_snapshot(source))[0]

    assert finding.finding_type == "grammar.probable_plural_impersonal_haber"
    assert finding.editorial_classification == "probable_issue"
    assert finding.severity == "warning"
    assert finding.certainty == 0.92
    assert _replacement(finding) == expected


def test_plural_haber_auxiliary_is_not_inferred_as_impersonal() -> None:
    snapshot = _snapshot("Habían llegado muchas personas.")

    assert SpanishGrammarCorrector().analyze(snapshot) == ()


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        (
            "Las palabras transforma al hombre.",
            "Las palabras transforman al hombre.",
        ),
        (
            "La palabra transforman al hombre.",
            "La palabra transforma al hombre.",
        ),
    ),
)
def test_explicit_simple_agreement_pairs_correct_both_directions(
    source: str,
    expected: str,
) -> None:
    corrector = SpanishGrammarCorrector(agreement_rules=(_agreement(),))

    finding = corrector.analyze(_snapshot(source))[0]

    assert (
        finding.finding_type
        == "grammar.simple_subject_verb_number_agreement"
    )
    assert finding.editorial_classification == "verified_error"
    assert finding.criterion == _agreement().criterion
    assert _replacement(finding) == expected


def test_agreement_does_not_infer_unconfigured_subjects_or_verbs() -> None:
    corrector = SpanishGrammarCorrector(agreement_rules=(_agreement(),))
    snapshot = _snapshot(
        "Esas palabras transforma al hombre. Las palabras cambian al hombre."
    )

    assert corrector.analyze(snapshot) == ()


def test_findings_bind_exact_canonical_sentence_evidence() -> None:
    snapshot = _snapshot("Le lo dijo. Habían muchas razones.")
    findings = SpanishGrammarCorrector().analyze(snapshot)

    assert len(findings) == 2
    assert all(item.diagnostic_axis == "normative_correction" for item in findings)
    assert all(item.text_binding.span.kind == "sentence" for item in findings)
    assert all(
        item.evidence
        == snapshot.evidence_for(item.text_binding.span.span_id)
        for item in findings
    )


def test_registry_is_explicit_unique_versioned_and_immutable() -> None:
    corrector = SpanishGrammarCorrector(agreement_rules=(_agreement(),))
    identities = tuple(
        (criterion.criterion_id, criterion.criterion_version)
        for criterion in corrector.rule_registry
    )

    assert len(BUILTIN_GRAMMAR_RULES) == 3
    assert len(identities) == 4
    assert len(identities) == len(set(identities))
    with pytest.raises(ValidationError):
        BUILTIN_GRAMMAR_RULES[0].description = "Alterada."
    with pytest.raises(ValidationError):
        corrector.agreement_rules[0].plural_verb = "cambian"


def test_registry_rejects_duplicate_criteria_and_agreement_pairs() -> None:
    duplicate_builtin = _agreement(
        criterion_id="es.grammar.impersonal-haber-number"
    )
    with pytest.raises(ValidationError, match="identidades de criterio"):
        SpanishGrammarCorrector(agreement_rules=(duplicate_builtin,))

    first = _agreement()
    repeated = _agreement(criterion_id="oro.grammar.repeated")
    with pytest.raises(ValidationError, match="mismo par"):
        SpanishGrammarCorrector(agreement_rules=(first, repeated))


def test_agreement_rule_rejects_implicit_or_indistinct_forms() -> None:
    with pytest.raises(ValidationError, match="token exacto"):
        SimpleAgreementRule(
            singular_subject="La palabra",
            plural_subject="Las palabras",
            singular_verb="ha transformado",
            plural_verb="transforman",
            rationale="Regla inválida.",
            criterion=EditorialCriterion(
                criterion_id="oro.grammar.invalid",
                criterion_version="1.0.0",
            ),
        )

    with pytest.raises(ValidationError, match="formas verbales"):
        SimpleAgreementRule(
            singular_subject="La palabra",
            plural_subject="Las palabras",
            singular_verb="transforma",
            plural_verb="transforma",
            rationale="Regla inválida.",
            criterion=EditorialCriterion(
                criterion_id="oro.grammar.invalid-2",
                criterion_version="1.0.0",
            ),
        )


def test_findings_are_ordered_by_reading_position_and_criterion() -> None:
    snapshot = _snapshot(
        "Habían muchas razones. Le lo dijo a pesar que dudaba.",
        "Habrán tres encuentros.",
    )
    findings = SpanishGrammarCorrector().analyze(snapshot)
    keys = tuple(
        (
            snapshot.reading_order.index(finding.target_id),
            finding.text_binding.span.start,
            finding.criterion.criterion_id,
        )
        for finding in findings
    )

    assert len(findings) == 4
    assert keys == tuple(sorted(keys))


def test_analysis_is_deterministic_and_does_not_mutate_or_patch() -> None:
    snapshot = _snapshot("Las palabras transforma. Le lo dijo.")
    corrector = SpanishGrammarCorrector(agreement_rules=(_agreement(),))
    before = snapshot.model_dump(mode="json")

    first = corrector.analyze(snapshot)
    second = corrector.analyze(snapshot)

    assert first == second
    assert tuple(item.finding_id for item in first) == tuple(
        item.finding_id for item in second
    )
    assert snapshot.model_dump(mode="json") == before
    assert all(not hasattr(item, "operations") for item in first)
