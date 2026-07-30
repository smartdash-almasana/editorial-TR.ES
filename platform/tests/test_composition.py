"""
Pruebas para el motor de composición de proyectos (compose_project).
"""

from pathlib import Path
import pytest

from editorial_tres.composition import compose_project
from editorial_tres.exceptions import (
    IncompatibilityError,
    MissingDependencyError,
    PluginNotFoundError,
)


def test_full_project_composition():
    project_path = Path(__file__).parents[2] / "projects" / "example" / "project.yaml"
    plugins_root = Path(__file__).parents[2] / "plugins"

    composition = compose_project(project_path, plugins_root)

    assert composition.project.id == "example"
    assert len(composition.resolved_plugins) == 7
    assert "genre.essay" in composition.composition_order
    assert "voice.default" in composition.composition_order
    assert "narrator.reflective" in composition.composition_order
    assert "style.literary" in composition.composition_order
    assert "reviewer.structural" in composition.composition_order
    assert "visual.infographic" in composition.composition_order
    assert "output.manuscript" in composition.composition_order


def test_composition_missing_plugin(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    (plugins_dir / "genre").mkdir()
    (plugins_dir / "genre" / "plugin.yaml").write_text(
        """
id: genre.essay
version: 0.1.0
type: genre
name: Ensayo
description: Test
entrypoint: SKILL.md
""",
        encoding="utf-8",
    )

    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()
    (proj_dir / "project.yaml").write_text(
        """
id: p1
title: Test
plugins:
  genre: genre.essay
  voice: voice.missing
""",
        encoding="utf-8",
    )

    with pytest.raises(PluginNotFoundError) as excinfo:
        compose_project(proj_dir / "project.yaml", plugins_dir)
    assert "voice.missing" in str(excinfo.value)


def test_composition_missing_dependency(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    # Plugin A requires Plugin B
    (plugins_dir / "pluginA").mkdir()
    (plugins_dir / "pluginA" / "plugin.yaml").write_text(
        """
id: genre.essay
version: 0.1.0
type: genre
name: Ensayo
description: Test
entrypoint: SKILL.md
requires:
  - style.required_style
""",
        encoding="utf-8",
    )

    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()
    (proj_dir / "project.yaml").write_text(
        """
id: p1
title: Test
plugins:
  genre: genre.essay
""",
        encoding="utf-8",
    )

    with pytest.raises(MissingDependencyError) as excinfo:
        compose_project(proj_dir / "project.yaml", plugins_dir)
    assert "style.required_style" in str(excinfo.value)


def test_composition_incompatible_plugins(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    # Plugin A is only compatible with voice.allowed_voice
    (plugins_dir / "pluginA").mkdir()
    (plugins_dir / "pluginA" / "plugin.yaml").write_text(
        """
id: genre.essay
version: 0.1.0
type: genre
name: Ensayo
description: Test
entrypoint: SKILL.md
compatible_with:
  - voice.allowed_voice
""",
        encoding="utf-8",
    )

    (plugins_dir / "pluginB").mkdir()
    (plugins_dir / "pluginB" / "plugin.yaml").write_text(
        """
id: voice.forbidden_voice
version: 0.1.0
type: voice
name: Voz prohibida
description: Test
entrypoint: SKILL.md
""",
        encoding="utf-8",
    )

    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()
    (proj_dir / "project.yaml").write_text(
        """
id: p1
title: Test
plugins:
  genre: genre.essay
  voice: voice.forbidden_voice
""",
        encoding="utf-8",
    )

    with pytest.raises(IncompatibilityError) as excinfo:
        compose_project(proj_dir / "project.yaml", plugins_dir)
    assert "incompatible" in str(excinfo.value).lower()


def test_stable_composition_order_with_dependencies(tmp_path: Path):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    # Style depends on Reviewer (so Reviewer must come first)
    (plugins_dir / "style").mkdir()
    (plugins_dir / "style" / "plugin.yaml").write_text(
        """
id: style.literary
version: 0.1.0
type: style
name: Estilo
description: Test
entrypoint: SKILL.md
requires:
  - reviewer.structural
""",
        encoding="utf-8",
    )

    (plugins_dir / "reviewer").mkdir()
    (plugins_dir / "reviewer" / "plugin.yaml").write_text(
        """
id: reviewer.structural
version: 0.1.0
type: reviewer
name: Revisor
description: Test
entrypoint: SKILL.md
""",
        encoding="utf-8",
    )

    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()
    (proj_dir / "project.yaml").write_text(
        """
id: p1
title: Test
plugins:
  styles:
    - style.literary
  reviewers:
    - reviewer.structural
""",
        encoding="utf-8",
    )

    comp = compose_project(proj_dir / "project.yaml", plugins_dir)
    rev_index = comp.composition_order.index("reviewer.structural")
    style_index = comp.composition_order.index("style.literary")

    assert rev_index < style_index
