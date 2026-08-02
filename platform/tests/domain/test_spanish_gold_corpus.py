"""PC-3: governed Gold corpus measurement for integrated PC-1 and PC-2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from editorial_tres.domain.grammar import (
    SimpleAgreementRule,
    SpanishGrammarCorrector,
)
from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.proofreading import (
    ContextualAccentCorrection,
    LexicalCorrection,
    SpanishOrthotypographicCorrector,
)
from editorial_tres.domain.reviews import EditorialCriterion
from editorial_tres.domain.text_analysis import SpanishTextAnalyzer
from editorial_tres.domain.work import Work


TENANT = TenantId(value="tenant.tres")
EDITORIAL = EditorialId(value="editorial.tres")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _work(*contents: str, work_id: str) -> Work:
    identity = WorkId(value=work_id)
    expression = ExpressionGraph(
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=identity,
    )
    for position, content in enumerate(contents):
        expression = expression.add_block(
            ContentBlock(
                id="story-body" if len(contents) == 1 else f"control-{position + 1}",
                block_type="paragraph",
                content=content,
                position=position,
                language="es-AR",
            )
        )
    return Work(
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=identity,
        title="Corpus Oro PC-3",
        language="es-AR",
        knowledge_graph=KnowledgeGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=identity,
        ),
        narrative_graph=NarrativeGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=identity,
        ),
        expression_graph=expression,
        dependency_graph=DependencyGraph(
            tenant_id=TENANT,
            editorial_id=EDITORIAL,
            work_id=identity,
        ),
    )


def _criterion(configuration: dict[str, Any]) -> EditorialCriterion:
    return EditorialCriterion(
        criterion_id=configuration["criterion_id"],
        criterion_version=configuration["criterion_version"],
    )


def _correctors(gold: dict[str, Any]):
    configurations = [
        case["configuration"]
        for case in gold["errors"]
        if case["support_status"] == "supported"
    ]
    lexical = tuple(
        LexicalCorrection(
            source_token=item["source_token"],
            replacement_text=item["replacement_text"],
            rationale=item["rationale"],
            criterion=_criterion(item),
        )
        for item in configurations
        if item["kind"] == "lexical"
    )
    contextual_accent = tuple(
        ContextualAccentCorrection(
            source_token=item["source_token"],
            replacement_text=item["replacement_text"],
            left_anchor_tokens=tuple(item["left_anchor_tokens"]),
            right_anchor_tokens=tuple(item["right_anchor_tokens"]),
            rationale=item["rationale"],
            criterion=_criterion(item),
        )
        for item in configurations
        if item["kind"] == "contextual_accent"
    )
    agreement = tuple(
        SimpleAgreementRule(
            singular_subject=item["singular_subject"],
            plural_subject=item["plural_subject"],
            singular_verb=item["singular_verb"],
            plural_verb=item["plural_verb"],
            rationale=item["rationale"],
            criterion=_criterion(item),
        )
        for item in configurations
        if item["kind"] == "agreement"
    )
    return (
        SpanishOrthotypographicCorrector(
            lexical_corrections=lexical,
            contextual_accent_corrections=contextual_accent,
        ),
        SpanishGrammarCorrector(agreement_rules=agreement),
    )


def _analyze(snapshot, correctors):
    return tuple(
        finding
        for corrector in correctors
        for finding in corrector.analyze(snapshot)
    )


def test_pc3_gold_corpus_measures_supported_and_unsupported_cases() -> None:
    tests_dir = Path(__file__).resolve().parents[1]
    fixture_path = tests_dir / "fixtures" / "el_puerto_y_el_rio_con_errores.md"
    gold_path = tests_dir / "fixtures" / "el_puerto_y_el_rio_gold.json"

    fixture_before = fixture_path.read_bytes()
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    assert _sha256(fixture_before) == gold["source"]["fixture_sha256"]

    source_text = fixture_before.decode("utf-8")
    title, separator, body = source_text.partition("\n\n")
    assert separator == "\n\n"
    assert title == "# El puerto y el río"
    assert len(body) == gold["source"]["block_length"]
    assert _sha256(body.encode("utf-8")) == gold["source"]["body_sha256"]

    errors = gold["errors"]
    assert len(errors) == gold["adjudication"]["expected_error_count"] == 20
    assert len({case["case_id"] for case in errors}) == len(errors)
    assert [case["start"] for case in errors] == sorted(
        case["start"] for case in errors
    )
    for case in errors:
        assert case["adjudication"] == "verified_error"
        assert body[case["start"] : case["end"]] == case["source_fragment"]
        assert case["source_fragment"] != case["replacement_fragment"]
        assert ("configuration" in case) == (
            case["support_status"] == "supported"
        )

    work = _work(body, work_id="work.pc3-gold")
    work_before = work.model_dump(mode="json")
    analyzer = SpanishTextAnalyzer()
    snapshot = analyzer.analyze(work, branch_id="pc-3")
    snapshot_rerun = analyzer.analyze(work, branch_id="pc-3")
    correctors = _correctors(gold)
    findings = _analyze(snapshot, correctors)
    findings_rerun = _analyze(snapshot, correctors)

    assert snapshot == snapshot_rerun
    assert findings == findings_rerun
    assert tuple(item.finding_id for item in findings) == tuple(
        item.finding_id for item in findings_rerun
    )
    assert work.model_dump(mode="json") == work_before
    assert fixture_path.read_bytes() == fixture_before

    supported = [case for case in errors if case["support_status"] == "supported"]
    unsupported = [
        case for case in errors if case["support_status"] == "unsupported"
    ]
    assert (
        len(supported)
        == gold["adjudication"]["supported_by_existing_configuration_count"]
        == 17
    )
    assert (
        len(unsupported)
        == gold["adjudication"]["unsupported_or_uncovered_count"]
        == 3
    )

    supported_by_criterion = {
        case["configuration"]["criterion_id"]: case for case in supported
    }
    findings_by_criterion = {
        finding.criterion.criterion_id: finding for finding in findings
    }
    detected_ids = set(supported_by_criterion) & set(findings_by_criterion)
    unexpected_ids = set(findings_by_criterion) - set(supported_by_criterion)
    omitted_supported_ids = set(supported_by_criterion) - set(findings_by_criterion)

    assert detected_ids == set(supported_by_criterion)
    assert omitted_supported_ids == set()
    assert unexpected_ids == set()
    assert len(findings) == 17

    for criterion_id, case in supported_by_criterion.items():
        finding = findings_by_criterion[criterion_id]
        binding = finding.text_binding
        assert binding is not None
        assert binding.snapshot == snapshot
        assert finding.target_id == gold["source"]["block_id"]
        assert binding.span == snapshot.span(binding.span.span_id)
        assert binding.span.start <= case["start"] < case["end"] <= binding.span.end
        if case["configuration"]["kind"] in {"lexical", "contextual_accent"}:
            assert binding.span.start == case["start"]
            assert binding.span.end == case["end"]
            assert finding.evidence == case["source_fragment"]
            assert (
                finding.replacement_proposals[0].replacement_text
                == case["replacement_fragment"]
            )
        else:
            replacement = finding.replacement_proposals[0].replacement_text
            assert case["source_fragment"] in finding.evidence
            assert case["replacement_fragment"] in replacement
            if case["source_fragment"] in case["replacement_fragment"]:
                assert case["source_fragment"] != replacement
            else:
                assert case["source_fragment"] not in replacement
        assert finding.editorial_classification == "verified_error"
        assert finding.certainty == 1.0
        assert not hasattr(finding, "operations")

    controls = (*gold["negative_controls"], *gold["ambiguous_controls"])
    assert len({item["control_id"] for item in controls}) == len(controls)
    control_work = _work(
        *(item["text"] for item in controls),
        work_id="work.pc3-controls",
    )
    control_before = control_work.model_dump(mode="json")
    control_snapshot = analyzer.analyze(control_work, branch_id="pc-3-controls")
    control_findings = _analyze(control_snapshot, correctors)

    assert control_findings == ()
    assert control_work.model_dump(mode="json") == control_before

    metrics = {
        "corpus_id": gold["corpus_id"],
        "gold_errors": len(errors),
        "supported_errors": len(supported),
        "supported_detected": len(detected_ids),
        "supported_omitted": len(omitted_supported_ids),
        "unsupported_errors": len(unsupported),
        "unsupported_detected": 0,
        "unexpected_findings": len(unexpected_ids),
        "control_false_positives": len(control_findings),
        "supported_recall": len(detected_ids) / len(supported),
        "controlled_corpus_overall_recall": len(detected_ids) / len(errors),
        "controlled_corpus_precision": len(detected_ids) / len(findings),
        "source_unchanged": fixture_path.read_bytes() == fixture_before,
        "work_unchanged": control_work.model_dump(mode="json") == control_before,
    }
    print(
        "PC3_GOLD_RESULTS="
        + json.dumps(
            metrics,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print("PATCH_CREATED=False")
    print("AUTOMATIC_CORRECTION=False")
    print("PRODUCT_WIDE_ACCURACY_CLAIM=False")
    print("CHRISTIAN_EDITORIAL_ALIGNMENT_VALIDATED=False")
