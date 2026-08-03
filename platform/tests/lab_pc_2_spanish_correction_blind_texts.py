"""LAB-PC-2: blind complete-text evaluation of the frozen Spanish correctors.

The corpus and complete adjudication were frozen before the first execution.
This harness measures quality; it does not mutate source material, create
patches, or turn a low score into a test failure.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Callable, Hashable

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
FROZEN_PRODUCT_HEAD = "3adea17be6773c04e6de8ff798aaba144b9fca60"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _work(content: str, *, work_id: str, title: str) -> Work:
    identity = WorkId(value=work_id)
    expression = ExpressionGraph(
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=identity,
    ).add_block(
        ContentBlock(
            id="body",
            block_type="paragraph",
            content=content,
            position=0,
            language="es-AR",
        )
    )
    return Work(
        tenant_id=TENANT,
        editorial_id=EDITORIAL,
        work_id=identity,
        title=title,
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


def _configured_correctors(controlled_gold: dict[str, Any]):
    configurations = [
        case["configuration"]
        for case in controlled_gold["errors"]
        if case["support_status"] == "supported"
        and case["configuration"]["kind"] != "builtin"
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
    contextual = tuple(
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
            contextual_accent_corrections=contextual,
        ),
        SpanishGrammarCorrector(agreement_rules=agreement),
    )


def _profiles(tests_dir: Path):
    controlled_path = tests_dir / "fixtures" / "el_puerto_y_el_rio_gold.json"
    controlled_gold = json.loads(controlled_path.read_text(encoding="utf-8"))
    return {
        "builtin_default": (
            SpanishOrthotypographicCorrector(),
            SpanishGrammarCorrector(),
        ),
        "pc3_configured_profile": _configured_correctors(controlled_gold),
    }


def _analyze(snapshot, correctors):
    return tuple(
        finding
        for corrector in correctors
        for finding in corrector.analyze(snapshot)
    )


def _replacement(finding) -> str:
    assert len(finding.replacement_proposals) == 1
    return finding.replacement_proposals[0].replacement_text


def _truth_key(case: dict[str, Any]) -> tuple[int, int, str]:
    return (
        case["start"],
        case["end"],
        case["replacement_fragment"],
    )


def _governed_key(case: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        case["expected_criterion_id"],
        case["start"],
        case["end"],
        case["replacement_fragment"],
    )


def _finding_truth_key(finding) -> tuple[int, int, str]:
    binding = finding.text_binding
    assert binding is not None
    return (
        binding.span.start,
        binding.span.end,
        _replacement(finding),
    )


def _finding_governed_key(finding) -> tuple[str, int, int, str]:
    binding = finding.text_binding
    criterion = finding.criterion
    assert binding is not None
    assert criterion is not None
    return (
        criterion.criterion_id,
        binding.span.start,
        binding.span.end,
        _replacement(finding),
    )


def _match_one_to_one(
    cases: list[Any],
    findings: tuple[Any, ...],
    *,
    case_key: Callable[[Any], Hashable],
    finding_key: Callable[[Any], Hashable],
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Match each finding to at most one case without collapsing duplicates."""
    available_cases: dict[Hashable, deque[int]] = defaultdict(deque)
    for case_index, case in enumerate(cases):
        available_cases[case_key(case)].append(case_index)

    matches: list[tuple[int, int]] = []
    unmatched_finding_indexes: list[int] = []
    matched_case_indexes: set[int] = set()
    for finding_index, finding in enumerate(findings):
        candidates = available_cases.get(finding_key(finding))
        if not candidates:
            unmatched_finding_indexes.append(finding_index)
            continue
        case_index = candidates.popleft()
        matched_case_indexes.add(case_index)
        matches.append((case_index, finding_index))

    unmatched_case_indexes = [
        case_index
        for case_index in range(len(cases))
        if case_index not in matched_case_indexes
    ]
    return matches, unmatched_case_indexes, unmatched_finding_indexes


def _finding_record(finding) -> dict[str, Any]:
    binding = finding.text_binding
    criterion = finding.criterion
    assert binding is not None
    assert criterion is not None
    return {
        "finding_id": finding.finding_id,
        "criterion_id": criterion.criterion_id,
        "classification": finding.editorial_classification,
        "certainty": finding.certainty,
        "start": binding.span.start,
        "end": binding.span.end,
        "evidence": finding.evidence,
        "replacement": _replacement(finding),
    }


def _assert_binding(snapshot, finding) -> None:
    binding = finding.text_binding
    assert binding is not None
    assert binding.snapshot == snapshot
    assert binding.span == snapshot.span(binding.span.span_id)
    assert binding.span.block_id == "body"
    assert finding.target_id == "body"
    assert finding.evidence == binding.span.evidence
    assert finding.evidence == snapshot.evidence_for(binding.span.span_id)
    block = snapshot.blocks[0]
    assert block.content[binding.span.start : binding.span.end] == finding.evidence
    assert _replacement(finding) != finding.evidence
    assert finding.diagnostic_axis == "normative_correction"
    assert finding.criterion is not None
    assert not hasattr(finding, "operations")


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _alters_control(
    finding,
    controls: list[dict[str, Any]],
) -> list[str]:
    binding = finding.text_binding
    assert binding is not None
    replacement = _replacement(finding)
    altered: list[str] = []
    for control in controls:
        if (
            binding.span.start < control["end"]
            and control["start"] < binding.span.end
            and replacement != finding.evidence
        ):
            altered.append(control["control_id"])
    return altered


def test_one_to_one_matcher_does_not_collapse_duplicates() -> None:
    cases = [{"key": "same"}, {"key": "missing"}]
    findings = ("same", "same")

    matches, omissions, unexpected = _match_one_to_one(
        cases,
        findings,
        case_key=lambda case: case["key"],
        finding_key=lambda finding: finding,
    )

    assert matches == [(0, 0)]
    assert omissions == [1]
    assert unexpected == [1]


def test_frozen_corrector_on_new_complete_held_out_texts() -> None:
    tests_dir = Path(__file__).resolve().parent
    lab_dir = tests_dir / "fixtures" / "lab_pc_2"
    manifest_path = lab_dir / "gold.json"
    manifest_before = manifest_path.read_bytes()
    manifest = json.loads(manifest_before.decode("utf-8"))

    assert manifest["laboratory_id"] == "LAB-PC-2"
    assert manifest["frozen_before_first_execution"] is True
    assert manifest["frozen_product_head"] == FROZEN_PRODUCT_HEAD
    assert manifest["adjudication"]["status"] == "complete_before_first_execution"
    assert len(manifest["sources"]) >= 3
    assert len(manifest["errors"]) == manifest["adjudication"]["expected_error_count"]
    assert len(manifest["controls"]) == manifest["adjudication"][
        "clean_and_voice_control_count"
    ]
    assert len({item["case_id"] for item in manifest["errors"]}) == len(
        manifest["errors"]
    )
    assert len({item["control_id"] for item in manifest["controls"]}) == len(
        manifest["controls"]
    )

    profiles = _profiles(tests_dir)
    assert set(profiles) == {
        item["profile_id"] for item in manifest["product_profiles"]
    }

    results: dict[str, Any] = {}
    for profile_id, correctors in profiles.items():
        profile_results: list[dict[str, Any]] = []
        all_finding_count = 0
        all_detected_count = 0
        all_expected_count = 0
        all_governed_expected = 0
        all_governed_detected = 0
        unexpected_records: list[dict[str, Any]] = []
        duplicate_records: list[dict[str, Any]] = []
        omission_records: list[dict[str, Any]] = []
        dangerous_records: list[dict[str, Any]] = []

        registry_ids = {
            criterion.criterion_id
            for corrector in correctors
            for criterion in corrector.rule_registry
        }

        for source in manifest["sources"]:
            source_path = tests_dir.parent / source["fixture_path"]
            source_before = source_path.read_bytes()
            assert _sha256(source_before) == source["fixture_sha256"]
            title, separator, body = source_before.decode("utf-8").partition(
                "\n\n"
            )
            assert separator == "\n\n"
            assert title == source["title"]
            assert len(body) == source["body_length"]
            assert _sha256(body.encode("utf-8")) == source["body_sha256"]

            cases = [
                item
                for item in manifest["errors"]
                if item["corpus_id"] == source["corpus_id"]
            ]
            controls = [
                item
                for item in manifest["controls"]
                if item["corpus_id"] == source["corpus_id"]
            ]
            for item in (*cases, *controls):
                assert body[item["start"] : item["end"]] == item[
                    "source_fragment"
                ]
            for case in cases:
                assert case["source_fragment"] != case["replacement_fragment"]
                if profile_id in case["expected_profiles"]:
                    assert case["expected_criterion_id"] in registry_ids

            clean_id = source['corpus_id'].replace('.', '-')
            work = _work(
                body,
                work_id=f"work.{clean_id}-{profile_id}",
                title=source["title"],
            )
            work_before = work.model_dump(mode="json")
            analyzer = SpanishTextAnalyzer()
            snapshot = analyzer.analyze(work, branch_id=f"lab-pc-2-{profile_id}")
            snapshot_rerun = analyzer.analyze(
                work,
                branch_id=f"lab-pc-2-{profile_id}",
            )
            findings = _analyze(snapshot, correctors)
            findings_rerun = _analyze(snapshot, correctors)

            assert snapshot == snapshot_rerun
            assert findings == findings_rerun
            assert tuple(item.finding_id for item in findings) == tuple(
                item.finding_id for item in findings_rerun
            )
            assert work.model_dump(mode="json") == work_before
            assert source_path.read_bytes() == source_before
            for finding in findings:
                _assert_binding(snapshot, finding)

            governed_cases = [
                case
                for case in cases
                if profile_id in case["expected_profiles"]
            ]
            truth_matches, omitted_case_indexes, unexpected_finding_indexes = (
                _match_one_to_one(
                    cases,
                    findings,
                    case_key=_truth_key,
                    finding_key=_finding_truth_key,
                )
            )
            governed_matches, _, _ = _match_one_to_one(
                governed_cases,
                findings,
                case_key=_governed_key,
                finding_key=_finding_governed_key,
            )
            for case_index, finding_index in governed_matches:
                assert (
                    findings[finding_index].editorial_classification
                    == governed_cases[case_index]["expected_classification"]
                )

            truth_case_ids: dict[Hashable, list[str]] = defaultdict(list)
            for case in cases:
                truth_case_ids[_truth_key(case)].append(case["case_id"])

            unexpected: list[dict[str, Any]] = []
            duplicates: list[dict[str, Any]] = []
            dangerous: list[dict[str, Any]] = []
            for finding_index in unexpected_finding_indexes:
                finding = findings[finding_index]
                key = _finding_truth_key(finding)
                record = _finding_record(finding)
                duplicate_of = truth_case_ids.get(key, [])
                record["false_positive_reason"] = (
                    "duplicate_excess" if duplicate_of else "no_exact_gold_match"
                )
                if duplicate_of:
                    record["duplicate_of_case_ids"] = duplicate_of
                    duplicates.append(record)
                unexpected.append(record)

                altered_controls = _alters_control(finding, controls)
                if altered_controls:
                    dangerous_record = dict(record)
                    dangerous_record["altered_controls"] = altered_controls
                    dangerous.append(dangerous_record)

            omissions = [
                {
                    "case_id": cases[case_index]["case_id"],
                    "category": cases[case_index]["category"],
                    "source_fragment": cases[case_index]["source_fragment"],
                    "replacement_fragment": cases[case_index][
                        "replacement_fragment"
                    ],
                }
                for case_index in omitted_case_indexes
            ]

            all_finding_count += len(findings)
            all_detected_count += len(truth_matches)
            all_expected_count += len(cases)
            all_governed_expected += len(governed_cases)
            all_governed_detected += len(governed_matches)
            unexpected_records.extend(
                {"corpus_id": source["corpus_id"], **item}
                for item in unexpected
            )
            duplicate_records.extend(
                {"corpus_id": source["corpus_id"], **item}
                for item in duplicates
            )
            omission_records.extend(
                {"corpus_id": source["corpus_id"], **item}
                for item in omissions
            )
            dangerous_records.extend(
                {"corpus_id": source["corpus_id"], **item}
                for item in dangerous
            )

            profile_results.append(
                {
                    "corpus_id": source["corpus_id"],
                    "characters": len(body),
                    "paragraphs": len(snapshot.blocks[0].paragraphs),
                    "sentences": len(snapshot.blocks[0].sentences),
                    "tokens": len(snapshot.blocks[0].tokens),
                    "gold_errors": len(cases),
                    "findings": len(findings),
                    "true_positives": len(truth_matches),
                    "false_positives": len(unexpected_finding_indexes),
                    "duplicate_findings": len(duplicates),
                    "omissions": len(omitted_case_indexes),
                    "governed_expected": len(governed_cases),
                    "governed_detected": len(governed_matches),
                    "dangerous_control_corrections": len(dangerous),
                    "source_unchanged": True,
                    "work_unchanged": True,
                }
            )

        assert all_finding_count == all_detected_count + len(unexpected_records)
        assert all_expected_count == all_detected_count + len(omission_records)
        precision = _ratio(
            all_detected_count,
            all_detected_count + len(unexpected_records),
        )
        recall = _ratio(
            all_detected_count,
            all_detected_count + len(omission_records),
        )
        results[profile_id] = {
            "texts": profile_results,
            "gold_errors": all_expected_count,
            "findings": all_finding_count,
            "true_positives": all_detected_count,
            "false_positives": len(unexpected_records),
            "duplicate_findings": len(duplicate_records),
            "omissions": len(omission_records),
            "dangerous_control_corrections": len(dangerous_records),
            "precision": precision,
            "recall": recall,
            "f1": _f1(precision, recall),
            "governed_expected": all_governed_expected,
            "governed_detected": all_governed_detected,
            "governed_catalog_recall": _ratio(
                all_governed_detected,
                all_governed_expected,
            ),
            "unexpected_findings": unexpected_records,
            "duplicate_finding_records": duplicate_records,
            "omitted_cases": omission_records,
            "dangerous_control_correction_records": dangerous_records,
        }

    assert manifest_path.read_bytes() == manifest_before
    print(
        "LAB_PC_2_RESULTS="
        + json.dumps(
            results,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    print("FROZEN_BEFORE_FIRST_EXECUTION=True")
    print("PATCH_CREATED=False")
    print("AUTOMATIC_CORRECTION=False")
    print("PRODUCT_CODE_CHANGED=False")
    print("PRODUCT_WIDE_ACCURACY_CLAIM=False")
    print(
        "CATALOG_INTEGRATION_OBSERVATION="
        "PC3_CONFIGURATIONS_ARE_LOADED_FROM_THE_CONTROLLED_TEST_CORPUS"
    )
