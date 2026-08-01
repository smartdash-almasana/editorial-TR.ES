from dataclasses import replace
from inspect import signature
import json
from pathlib import Path

import pytest

from editorial_tres.application.review_plan import ReviewPlanComposer
from editorial_tres.capability_factory import CapabilityFactoryRegistry
from editorial_tres.composition import (
    activate_project_composition,
    compose_project,
)
from editorial_tres.domain.reviews import (
    ContinuityReviewer,
    ReviewEngine,
    RhythmReviewer,
    StructuralReviewer,
)
from editorial_tres.exceptions import InvalidReviewPlanError
from editorial_tres.plugin_registry import PluginRegistry


def _plugins_root() -> Path:
    return Path(__file__).resolve().parents[3] / "plugins"


def _catalog(root: Path) -> PluginRegistry:
    catalog = PluginRegistry()
    catalog.discover_plugins(root)
    return catalog


def _write_project(tmp_path: Path, plugins: str) -> Path:
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        f"""
id: review-plan-test
title: Plan de revisión
plugins:
{plugins}
""",
        encoding="utf-8",
    )
    return project_path


def _write_plugin(root: Path, name: str, content: str) -> None:
    plugin_dir = root / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(content, encoding="utf-8")


def _activated(project_path: Path, plugins_root: Path):
    composition = compose_project(project_path, plugins_root)
    return activate_project_composition(composition, _catalog(plugins_root))


def test_novel_review_plan_is_ordered_traceable_and_buildable(tmp_path: Path):
    activated = _activated(
        _write_project(tmp_path, "  genre: genre.novel"),
        _plugins_root(),
    )

    plan = ReviewPlanComposer().compose(activated)

    assert plan.project_id == "review-plan-test"
    assert plan.reviewer_ids == (
        "reviewer.structural",
        "reviewer.continuity",
        "reviewer.rhythm",
    )
    assert [entry.order for entry in plan.entries] == [1, 2, 3]
    assert [entry.implementation_id for entry in plan.entries] == [
        "structural",
        "configured_continuity",
        "rhythm",
    ]
    assert [entry.nature for entry in plan.entries] == [
        "deterministic",
        "deterministic",
        "deterministic",
    ]
    assert [entry.origins[0].source_kind for entry in plan.entries] == [
        "genre",
        "genre",
        "genre",
    ]
    assert [entry.origins[0].source_id for entry in plan.entries] == [
        "genre.novel",
        "genre.novel",
        "genre.novel",
    ]
    assert [entry.origins[0].reason for entry in plan.entries] == [
        "genre_required_reviewer",
        "genre_required_reviewer",
        "genre_required_reviewer",
    ]
    assert isinstance(plan.entries[0].reviewer, StructuralReviewer)
    assert isinstance(plan.entries[1].reviewer, ContinuityReviewer)
    assert isinstance(plan.entries[2].reviewer, RhythmReviewer)
    assert isinstance(plan.build_engine(), ReviewEngine)


def test_project_reviewers_precede_genre_requirements_and_duplicates_merge_origins(
    tmp_path: Path,
):
    activated = _activated(
        _write_project(
            tmp_path,
            """  genre: genre.novel
  workflow: workflow.standard
  reviewers:
    - reviewer.repetition
    - reviewer.structural""",
        ),
        _plugins_root(),
    )

    plan = ReviewPlanComposer().compose(activated)

    assert plan.reviewer_ids == (
        "reviewer.repetition",
        "reviewer.structural",
        "reviewer.continuity",
        "reviewer.rhythm",
    )
    structural_origins = plan.entries[1].origins
    assert [origin.source_kind for origin in structural_origins] == [
        "project",
        "genre",
    ]
    assert [origin.source_id for origin in structural_origins] == [
        "review-plan-test",
        "genre.novel",
    ]
    assert [origin.reason for origin in structural_origins] == [
        "explicit_project_reviewer",
        "genre_required_reviewer",
    ]


def test_project_genre_and_workflow_origins_are_all_preserved_once(tmp_path: Path):
    plugins_root = tmp_path / "plugins"
    _write_plugin(
        plugins_root,
        "genre",
        """
id: genre.test
version: 0.1.0
type: genre
name: Género de prueba
description: Género para procedencia del plan.
entrypoint: SKILL.md
behavior:
  unit_types: [chapter]
  required_reviewers: [reviewer.test]
  compilation_strategy: linear
""",
    )
    _write_plugin(
        plugins_root,
        "workflow",
        """
id: workflow.test
version: 0.1.0
type: workflow
name: Workflow de prueba
description: Workflow para procedencia del plan.
entrypoint: SKILL.md
behavior:
  stages: [diagnose]
  required_reviewers: [reviewer.test]
  completion_criteria: [done]
""",
    )
    _write_plugin(
        plugins_root,
        "reviewer",
        """
id: reviewer.test
version: 0.1.0
type: reviewer
name: Reviewer de prueba
description: Reviewer estructural mínimo.
entrypoint: SKILL.md
behavior:
  finding_type: test.finding
  scope: [expression_block]
  severity: warning
  evidence_format: text
  nature: deterministic
  recommendation_policy: revisar
  implementation: structural
  parameters:
    thematic_phrases: []
    minimum_thematic_occurrences: 3
""",
    )
    activated = _activated(
        _write_project(
            tmp_path,
            """  genre: genre.test
  workflow: workflow.test
  reviewers:
    - reviewer.test
    - reviewer.test""",
        ),
        plugins_root,
    )

    plan = ReviewPlanComposer().compose(activated)

    assert plan.reviewer_ids == ("reviewer.test",)
    assert [origin.source_kind for origin in plan.entries[0].origins] == [
        "project",
        "genre",
        "workflow",
    ]
    assert [origin.source_id for origin in plan.entries[0].origins] == [
        "review-plan-test",
        "genre.test",
        "workflow.test",
    ]


def test_plan_keeps_canonical_configuration_snapshot(tmp_path: Path):
    activated = _activated(
        _write_project(tmp_path, "  genre: genre.novel"),
        _plugins_root(),
    )

    plan = ReviewPlanComposer().compose(activated)

    structural_configuration = plan.entries[0].configuration_json
    rhythm_configuration = plan.entries[2].configuration_json
    structural_data = json.loads(structural_configuration)
    rhythm_data = json.loads(rhythm_configuration)

    assert structural_data["finding_type"] == "structure.integrity"
    assert structural_data["scope"] == ["expression_block"]
    assert structural_data["severity"] == "warning"
    assert structural_data["parameters"] == {
        "minimum_thematic_occurrences": 3,
        "thematic_phrases": [],
    }
    assert rhythm_data["parameters"]["minimum_short_run"] == 4
    assert rhythm_configuration == json.dumps(
        rhythm_data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def test_composer_uses_the_explicit_factory_registry_without_singleton_fallback(
    tmp_path: Path,
):
    plugins_root = tmp_path / "plugins"
    _write_plugin(
        plugins_root,
        "genre",
        """
id: genre.custom
version: 0.1.0
type: genre
name: Género custom
description: Género para registry explícito.
entrypoint: SKILL.md
behavior:
  unit_types: [chapter]
  required_reviewers: [reviewer.custom]
  compilation_strategy: linear
""",
    )
    _write_plugin(
        plugins_root,
        "reviewer",
        """
id: reviewer.custom
version: 0.1.0
type: reviewer
name: Reviewer custom
description: Reviewer construido por registry inyectado.
entrypoint: SKILL.md
behavior:
  finding_type: custom.finding
  scope: [expression_block]
  severity: warning
  evidence_format: text
  nature: deterministic
  recommendation_policy: revisar
  implementation: custom_structural
  parameters: {}
""",
    )
    project_path = _write_project(tmp_path, "  genre: genre.custom")
    composition = compose_project(project_path, plugins_root)
    catalog = _catalog(plugins_root)
    registry = CapabilityFactoryRegistry()

    def build_custom(plugin_id, behavior):
        return StructuralReviewer(
            reviewer_id=plugin_id,
            severity=behavior.severity,
        )

    registry.register("custom_structural", build_custom)
    activated = activate_project_composition(
        composition,
        catalog,
        reviewer_registry=registry,
    )

    plan = ReviewPlanComposer(reviewer_registry=registry).compose(activated)

    assert plan.reviewer_ids == ("reviewer.custom",)
    assert plan.entries[0].implementation_id == "custom_structural"
    assert isinstance(plan.entries[0].reviewer, StructuralReviewer)


def test_composer_rejects_drift_from_activated_requirement_order(tmp_path: Path):
    activated = _activated(
        _write_project(tmp_path, "  genre: genre.novel"),
        _plugins_root(),
    )
    inconsistent = replace(
        activated,
        required_reviewer_ids=(
            "reviewer.rhythm",
            "reviewer.continuity",
            "reviewer.structural",
        ),
    )

    with pytest.raises(InvalidReviewPlanError, match="discrepan"):
        ReviewPlanComposer().compose(inconsistent)


def test_composer_rejects_project_without_reviewers(tmp_path: Path):
    activated = _activated(
        _write_project(tmp_path, "  styles: []"),
        _plugins_root(),
    )

    with pytest.raises(InvalidReviewPlanError, match="no declara reviewers"):
        ReviewPlanComposer().compose(activated)


def test_composer_rejects_required_reviewer_missing_from_activated_view(
    tmp_path: Path,
):
    activated = _activated(
        _write_project(tmp_path, "  genre: genre.novel"),
        _plugins_root(),
    )
    incomplete = replace(
        activated,
        activated_plugins=tuple(
            plugin
            for plugin in activated.activated_plugins
            if plugin.id != "reviewer.continuity"
        ),
    )

    with pytest.raises(InvalidReviewPlanError, match="no está activado"):
        ReviewPlanComposer().compose(incomplete)


def test_composer_does_not_construct_engine_or_accept_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    activated = _activated(
        _write_project(tmp_path, "  genre: genre.novel"),
        _plugins_root(),
    )

    def _forbidden_engine_init(*args, **kwargs):
        raise AssertionError("ReviewPlanComposer no debe construir ReviewEngine.")

    monkeypatch.setattr(ReviewEngine, "__init__", _forbidden_engine_init)
    plan = ReviewPlanComposer().compose(activated)

    assert plan.reviewer_ids == activated.required_reviewer_ids
    parameters = signature(ReviewPlanComposer.compose).parameters
    assert "work" not in parameters


def test_plan_build_engine_uses_exact_plan_order(tmp_path: Path):
    activated = _activated(
        _write_project(
            tmp_path,
            """  genre: genre.novel
  reviewers:
    - reviewer.repetition""",
        ),
        _plugins_root(),
    )
    plan = ReviewPlanComposer().compose(activated)

    engine = plan.build_engine()

    assert isinstance(engine, ReviewEngine)
    assert engine.reviewer_ids == plan.reviewer_ids
