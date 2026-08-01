from inspect import signature
from pathlib import Path

import pytest

from editorial_tres.composition import (
    activate_project_composition,
    compose_project,
)
from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.graphs.expression import ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.reviews import ReviewEngine
from editorial_tres.domain.work import Work
from editorial_tres.exceptions import (
    InvalidManifestError,
    RequiredReviewerNotFoundError,
    UnknownImplementationError,
)
from editorial_tres.plugin_registry import PluginRegistry


def _plugins_root() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins"


def _catalog(root: Path) -> PluginRegistry:
    catalog = PluginRegistry()
    catalog.discover_plugins(root)
    return catalog


def _write_plugin(root: Path, name: str, content: str) -> None:
    plugin_dir = root / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(content, encoding="utf-8")


def _write_project(tmp_path: Path, plugins: str) -> Path:
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        f"""
id: activated-composition-test
title: Composición activada
plugins:
{plugins}
""",
        encoding="utf-8",
    )
    return project_path


def _genre_manifest(required_reviewer: str) -> str:
    return f"""
id: genre.test
version: 0.1.0
type: genre
name: Género de prueba
description: Género mínimo para activación.
entrypoint: SKILL.md
behavior:
  unit_types: [chapter]
  required_reviewers:
    - {required_reviewer}
  compilation_strategy: linear
"""


def _reviewer_manifest(implementation: str, parameters: str = "{}") -> str:
    return f"""
id: reviewer.test
version: 0.1.0
type: reviewer
name: Reviewer de prueba
description: Reviewer mínimo para materialización.
entrypoint: SKILL.md
behavior:
  finding_type: test.finding
  scope: [expression_block]
  severity: warning
  evidence_format: text
  nature: deterministic
  recommendation_policy: revisar
  implementation: {implementation}
  parameters: {parameters}
"""


def _work() -> Work:
    tenant_id = TenantId(value="tenant.test")
    editorial_id = EditorialId(value="editorial.test")
    work_id = WorkId(value="work.test")
    return Work(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="Obra intacta",
        language="es",
        knowledge_graph=KnowledgeGraph(
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
        ),
        narrative_graph=NarrativeGraph(
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
        ),
        expression_graph=ExpressionGraph(
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
        ),
        dependency_graph=DependencyGraph(
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
        ),
    )


def test_novel_activation_materializes_its_three_required_reviewers(tmp_path: Path):
    project_path = _write_project(tmp_path, "  genre: genre.novel")
    plugins_root = _plugins_root()
    composition = compose_project(project_path, plugins_root)

    activated = activate_project_composition(
        composition,
        _catalog(plugins_root),
    )

    assert composition.composition_order == ["genre.novel"]
    assert [plugin.id for plugin in activated.activated_plugins] == [
        "genre.novel",
        "reviewer.structural",
        "reviewer.continuity",
        "reviewer.rhythm",
    ]
    assert activated.required_reviewer_ids == (
        "reviewer.structural",
        "reviewer.continuity",
        "reviewer.rhythm",
    )


def test_composed_plugins_activate_first_in_static_composition_order(tmp_path: Path):
    project_path = _write_project(
        tmp_path,
        """  genre: genre.novel
  workflow: workflow.standard
  reviewers:
    - reviewer.structural""",
    )
    plugins_root = _plugins_root()
    composition = compose_project(project_path, plugins_root)

    activated = activate_project_composition(
        composition,
        _catalog(plugins_root),
    )

    activated_ids = [plugin.id for plugin in activated.activated_plugins]
    assert activated_ids[: len(composition.composition_order)] == composition.composition_order
    assert activated_ids == [
        "genre.novel",
        "workflow.standard",
        "reviewer.structural",
        "reviewer.continuity",
        "reviewer.rhythm",
    ]


def test_missing_required_reviewer_fails_with_specific_error(tmp_path: Path):
    plugins_root = tmp_path / "plugins"
    _write_plugin(
        plugins_root,
        "genre",
        _genre_manifest("reviewer.missing"),
    )
    project_path = _write_project(tmp_path, "  genre: genre.test")
    composition = compose_project(project_path, plugins_root)

    with pytest.raises(RequiredReviewerNotFoundError, match="reviewer.missing"):
        activate_project_composition(composition, _catalog(plugins_root))


def test_required_reviewer_without_executable_behavior_fails_early(tmp_path: Path):
    plugins_root = tmp_path / "plugins"
    _write_plugin(
        plugins_root,
        "genre",
        _genre_manifest("reviewer.test"),
    )
    _write_plugin(
        plugins_root,
        "reviewer",
        """
id: reviewer.test
version: 0.1.0
type: reviewer
name: Reviewer sin behavior
description: Debe fallar durante activación.
entrypoint: SKILL.md
""",
    )
    project_path = _write_project(tmp_path, "  genre: genre.test")
    composition = compose_project(project_path, plugins_root)

    with pytest.raises(InvalidManifestError, match="behavior ejecutable válido"):
        activate_project_composition(composition, _catalog(plugins_root))


def test_required_reviewer_with_unknown_implementation_fails_early(tmp_path: Path):
    plugins_root = tmp_path / "plugins"
    _write_plugin(
        plugins_root,
        "genre",
        _genre_manifest("reviewer.test"),
    )
    _write_plugin(
        plugins_root,
        "reviewer",
        _reviewer_manifest("not_registered"),
    )
    project_path = _write_project(tmp_path, "  genre: genre.test")
    composition = compose_project(project_path, plugins_root)

    with pytest.raises(UnknownImplementationError, match="not_registered"):
        activate_project_composition(composition, _catalog(plugins_root))


def test_required_reviewer_whose_factory_cannot_build_fails_early(tmp_path: Path):
    plugins_root = tmp_path / "plugins"
    _write_plugin(
        plugins_root,
        "genre",
        _genre_manifest("reviewer.test"),
    )
    _write_plugin(
        plugins_root,
        "reviewer",
        _reviewer_manifest("repeated_phrase"),
    )
    project_path = _write_project(tmp_path, "  genre: genre.test")
    composition = compose_project(project_path, plugins_root)

    with pytest.raises(InvalidManifestError, match="parameters.phrase"):
        activate_project_composition(composition, _catalog(plugins_root))


def test_duplicate_requirements_across_project_genre_and_workflow_are_unambiguous(
    tmp_path: Path,
):
    plugins_root = tmp_path / "plugins"
    _write_plugin(
        plugins_root,
        "genre",
        _genre_manifest("reviewer.test"),
    )
    _write_plugin(
        plugins_root,
        "workflow",
        """
id: workflow.test
version: 0.1.0
type: workflow
name: Workflow de prueba
description: Workflow mínimo para deduplicación.
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
        _reviewer_manifest("structural"),
    )
    project_path = _write_project(
        tmp_path,
        """  genre: genre.test
  workflow: workflow.test
  reviewers:
    - reviewer.test""",
    )
    composition = compose_project(project_path, plugins_root)

    activated = activate_project_composition(
        composition,
        _catalog(plugins_root),
    )

    assert activated.required_reviewer_ids == ("reviewer.test",)
    assert [plugin.id for plugin in activated.activated_plugins].count("reviewer.test") == 1


def test_activation_does_not_create_review_engine_or_accept_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def _forbidden_engine_init(*args, **kwargs):
        raise AssertionError("ActivatedProjectComposition no debe crear ReviewEngine.")

    monkeypatch.setattr(ReviewEngine, "__init__", _forbidden_engine_init)
    work = _work()
    work_snapshot = work.model_dump(mode="python")
    project_path = _write_project(tmp_path, "  genre: genre.novel")
    plugins_root = _plugins_root()
    composition = compose_project(project_path, plugins_root)

    activate_project_composition(
        composition,
        _catalog(plugins_root),
    )

    parameters = signature(activate_project_composition).parameters
    assert "work" not in parameters
    assert "runtime" not in parameters
    assert work.model_dump(mode="python") == work_snapshot
