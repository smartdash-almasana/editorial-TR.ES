from pathlib import Path

from editorial_tres.composition import compose_project
from editorial_tres.domain.reviews import ContinuityReviewer, RhythmReviewer, StructuralReviewer
from editorial_tres.plugin_contract import PluginManifest
from editorial_tres.plugin_registry import PluginRegistry
from editorial_tres.plugin_runtime import PluginRuntime


def _plugins_root() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins"


def test_full_editorial_plugin_composition_is_executable(tmp_path: Path):
    project_yaml = tmp_path / "project.yaml"
    project_yaml.write_text(
        """
id: full_composition
title: Obra de integración
language: es-AR
plugins:
  editorial: editorial.tres
  genre: genre.novel
  voice: voice.default
  narrator: narrator.reflective
  research_method: research.documentary
  workflow: workflow.standard
  styles:
    - style.literary
  reviewers:
    - reviewer.repetition
    - reviewer.structural
    - reviewer.continuity
    - reviewer.rhythm
  visual_types:
    - visual_type.infographic
  visual_styles:
    - visual_style.editorial
  outputs:
    - output.manuscript
""",
        encoding="utf-8",
    )

    composition = compose_project(project_yaml, _plugins_root())
    runtime = PluginRuntime()
    activated = runtime.activate_all(composition.resolved_plugins)

    assert composition.composition_order == [
        "editorial.tres",
        "genre.novel",
        "voice.default",
        "narrator.reflective",
        "research.documentary",
        "workflow.standard",
        "style.literary",
        "reviewer.continuity",
        "reviewer.repetition",
        "reviewer.rhythm",
        "reviewer.structural",
        "visual_type.infographic",
        "visual_style.editorial",
        "output.manuscript",
    ]
    assert len(activated) == 14
    assert runtime.get("editorial.tres").editorial is not None
    assert runtime.get("genre.novel").genre is not None
    assert runtime.get("voice.default").voice is not None
    assert runtime.get("narrator.reflective").narrator is not None
    assert runtime.get("research.documentary").research_method is not None
    assert runtime.get("style.literary").style is not None
    assert runtime.get("reviewer.continuity").reviewer is not None
    assert runtime.get("reviewer.repetition").reviewer is not None
    assert runtime.get("reviewer.rhythm").reviewer is not None
    assert runtime.get("reviewer.structural").reviewer is not None
    assert runtime.get("visual_type.infographic").visual_type is not None
    assert runtime.get("visual_style.editorial").visual_style is not None
    assert runtime.get("workflow.standard").workflow is not None
    assert runtime.get("output.manuscript").output is not None


def test_continuity_reviewer_is_discovered_and_buildable_from_project_composition(tmp_path: Path):
    project_yaml = tmp_path / "project.yaml"
    project_yaml.write_text(
        """
id: continuity_composition
title: Obra con continuidad
language: es-AR
plugins:
  genre: genre.novel
  reviewers:
    - reviewer.continuity
""",
        encoding="utf-8",
    )

    composition = compose_project(project_yaml, _plugins_root())
    runtime = PluginRuntime()
    runtime.activate_all(composition.resolved_plugins)
    reviewer = runtime.build_reviewer("reviewer.continuity")

    assert composition.composition_order == [
        "genre.novel",
        "reviewer.continuity",
    ]
    assert isinstance(reviewer, ContinuityReviewer)
    assert reviewer.rules[0].rule_id == "explicit_temporal_regression_after_nightfall"


def test_all_novel_required_reviewers_are_discoverable_and_buildable():
    plugins_root = _plugins_root()
    genre_manifest = PluginManifest.from_yaml(
        plugins_root / "genres" / "novel" / "plugin.yaml"
    )
    registry = PluginRegistry()
    registry.discover_plugins(plugins_root)
    runtime = PluginRuntime()
    activated_genre = runtime.activate(genre_manifest)

    assert activated_genre.genre is not None
    required_ids = activated_genre.genre.required_reviewers
    built_reviewers = []
    for reviewer_id in required_ids:
        runtime.activate(registry.get(reviewer_id))
        built_reviewers.append(runtime.build_reviewer(reviewer_id))

    assert required_ids == [
        "reviewer.structural",
        "reviewer.continuity",
        "reviewer.rhythm",
    ]
    assert [type(reviewer) for reviewer in built_reviewers] == [
        StructuralReviewer,
        ContinuityReviewer,
        RhythmReviewer,
    ]
