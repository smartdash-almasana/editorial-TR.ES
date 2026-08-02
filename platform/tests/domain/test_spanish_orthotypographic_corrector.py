"""PC-1 tests for the traceable Spanish orthotypographic corrector."""

import pytest
from pydantic import ValidationError

from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.proofreading import (
    BUILTIN_ORTHOTYPOGRAPHIC_RULES,
    LexicalCorrection,
    SpanishOrthotypographicCorrector,
)
from editorial_tres.domain.reviews import EditorialCriterion
from editorial_tres.domain.text_analysis import SpanishTextAnalyzer
from editorial_tres.domain.work import Work


TENANT = TenantId(value="tenant.tres")
EDITORIAL = EditorialId(value="editorial.tres")
WORK_ID = WorkId(value="work.pc1")


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
        title="Obra PC-1",
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


def _lexical(
    *,
    source: str = "Jesus",
    replacement: str = "Jesús",
    criterion_id: str = "oro.lexicon.jesus-accent",
) -> LexicalCorrection:
    return LexicalCorrection(
        source_token=source,
        replacement_text=replacement,
        rationale="El nombre propio lleva tilde en español.",
        criterion=EditorialCriterion(
            criterion_id=criterion_id,
            criterion_version="1.0.0",
        ),
    )


def _replacement(finding) -> str:
    return finding.replacement_proposals[0].replacement_text


def test_clean_text_produces_no_findings() -> None:
    snapshot = _snapshot("«La gracia llegó; después, permaneció.»")

    findings = SpanishOrthotypographicCorrector().analyze(snapshot)

    assert findings == ()


def test_repeated_horizontal_whitespace_is_bound_to_the_sentence() -> None:
    snapshot = _snapshot("La gracia  permanece.")

    finding = SpanishOrthotypographicCorrector().analyze(snapshot)[0]

    assert finding.finding_type == "orthotypography.repeated_horizontal_whitespace"
    assert finding.text_binding.span.kind == "sentence"
    assert finding.evidence == "La gracia  permanece."
    assert _replacement(finding) == "La gracia permanece."


def test_horizontal_tabs_are_normalized_without_touching_line_breaks() -> None:
    snapshot = _snapshot("Primera\t\tfrase.\nSegunda frase.")

    findings = SpanishOrthotypographicCorrector().analyze(snapshot)

    assert len(findings) == 1
    assert findings[0].evidence == "Primera\t\tfrase."
    assert _replacement(findings[0]) == "Primera frase."


def test_whitespace_before_closing_punctuation_is_removed() -> None:
    snapshot = _snapshot("La gracia llegó , y permaneció .")

    finding = SpanishOrthotypographicCorrector().analyze(snapshot)[0]

    assert finding.finding_type == "orthotypography.space_before_closing_punctuation"
    assert _replacement(finding) == "La gracia llegó, y permaneció."


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("Llegó,partió.", "Llegó, partió."),
        ("Llegó;partió.", "Llegó; partió."),
        ("Dijo:volveré.", "Dijo: volveré."),
    ),
)
def test_missing_space_after_medial_punctuation_is_added(
    source: str, expected: str
) -> None:
    snapshot = _snapshot(source)

    finding = SpanishOrthotypographicCorrector().analyze(snapshot)[0]

    assert (
        finding.finding_type
        == "orthotypography.missing_space_after_medial_punctuation"
    )
    assert _replacement(finding) == expected


def test_whitespace_inside_angle_quotes_is_removed_on_both_sides() -> None:
    snapshot = _snapshot("« La gracia permanece. »")

    finding = SpanishOrthotypographicCorrector().analyze(snapshot)[0]

    assert finding.finding_type == "orthotypography.angle_quote_inner_whitespace"
    assert finding.text_binding.span.kind == "paragraph"
    assert finding.evidence == "« La gracia permanece. »"
    assert _replacement(finding) == "«La gracia permanece.»"


def test_lexical_correction_matches_only_the_exact_canonical_token() -> None:
    snapshot = _snapshot("Jesus, Jesusito y JESUS.")
    corrector = SpanishOrthotypographicCorrector(
        lexical_corrections=(_lexical(),)
    )

    findings = corrector.analyze(snapshot)

    assert len(findings) == 1
    assert findings[0].finding_type == "orthography.exact_token_correction"
    assert findings[0].text_binding.span.kind == "token"
    assert findings[0].evidence == "Jesus"
    assert _replacement(findings[0]) == "Jesús"


def test_lexical_correction_rejects_phrases_and_noop_replacements() -> None:
    with pytest.raises(ValidationError, match="único token exacto"):
        _lexical(source="a ver", replacement="haber")

    with pytest.raises(ValidationError, match="cambio efectivo"):
        _lexical(source="Cristo", replacement="Cristo")


def test_registry_is_explicit_unique_versioned_and_immutable() -> None:
    corrector = SpanishOrthotypographicCorrector(
        lexical_corrections=(_lexical(),)
    )
    identities = tuple(
        (criterion.criterion_id, criterion.criterion_version)
        for criterion in corrector.rule_registry
    )

    assert len(BUILTIN_ORTHOTYPOGRAPHIC_RULES) == 4
    assert len(identities) == 5
    assert len(identities) == len(set(identities))
    with pytest.raises(ValidationError):
        BUILTIN_ORTHOTYPOGRAPHIC_RULES[0].description = "Alterada."


def test_registry_rejects_duplicate_sources_and_criterion_identities() -> None:
    first = _lexical()
    duplicate_source = _lexical(criterion_id="oro.lexicon.other")

    with pytest.raises(ValidationError, match="token fuente"):
        SpanishOrthotypographicCorrector(
            lexical_corrections=(first, duplicate_source)
        )

    duplicate_builtin_criterion = _lexical(
        source="Cristo",
        replacement="cristo",
        criterion_id="es.orthotypography.horizontal-whitespace",
    )
    with pytest.raises(ValidationError, match="identidades de criterio"):
        SpanishOrthotypographicCorrector(
            lexical_corrections=(duplicate_builtin_criterion,)
        )


def test_findings_are_ordered_by_reading_order_position_and_criterion() -> None:
    snapshot = _snapshot(
        "Uno  dos,mal.",
        "« Tres. »",
    )
    findings = SpanishOrthotypographicCorrector().analyze(snapshot)
    keys = tuple(
        (
            snapshot.reading_order.index(finding.target_id),
            finding.text_binding.span.start,
            finding.criterion.criterion_id,
        )
        for finding in findings
    )

    assert len(findings) == 3
    assert keys == tuple(sorted(keys))


def test_multiple_rules_remain_independent_without_conflict_arbitration() -> None:
    snapshot = _snapshot("Hola  ,mundo.")

    findings = SpanishOrthotypographicCorrector().analyze(snapshot)

    assert {finding.finding_type for finding in findings} == {
        "orthotypography.repeated_horizontal_whitespace",
        "orthotypography.space_before_closing_punctuation",
        "orthotypography.missing_space_after_medial_punctuation",
    }
    assert {_replacement(finding) for finding in findings} == {
        "Hola ,mundo.",
        "Hola,mundo.",
        "Hola  , mundo.",
    }


def test_analysis_is_deterministic_and_does_not_mutate_or_patch_snapshot() -> None:
    snapshot = _snapshot("Jesus dijo:volveré  mañana.")
    corrector = SpanishOrthotypographicCorrector(
        lexical_corrections=(_lexical(),)
    )
    before = snapshot.model_dump(mode="json")

    first = corrector.analyze(snapshot)
    second = corrector.analyze(snapshot)

    assert first == second
    assert tuple(item.finding_id for item in first) == tuple(
        item.finding_id for item in second
    )
    assert snapshot.model_dump(mode="json") == before
    assert all(not hasattr(item, "operations") for item in first)


def test_pc1_does_not_infer_grammar_or_literary_alignment() -> None:
    snapshot = _snapshot("Las palabras de Jesús transforma al hombre.")

    findings = SpanishOrthotypographicCorrector().analyze(snapshot)

    assert findings == ()
