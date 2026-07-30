"""
Pruebas para el manifiesto del proyecto (ProjectManifest).
"""

from pathlib import Path
import pytest

from editorial_tres.exceptions import InvalidManifestError
from editorial_tres.project_manifest import ProjectManifest


def test_valid_project_manifest(tmp_path: Path):
    proj_yaml = tmp_path / "project.yaml"
    proj_yaml.write_text(
        """
id: sample_proj
title: Proyecto Test
language: es-AR
plugins:
  genre: genre.essay
  styles:
    - style.literary
""",
        encoding="utf-8",
    )

    manifest = ProjectManifest.from_yaml(proj_yaml)
    assert manifest.id == "sample_proj"
    assert manifest.title == "Proyecto Test"
    assert manifest.plugins.genre == "genre.essay"
    assert manifest.plugins.styles == ["style.literary"]
    assert "genre.essay" in manifest.plugins.get_all_plugin_ids()
    assert "style.literary" in manifest.plugins.get_all_plugin_ids()


def test_invalid_project_manifest(tmp_path: Path):
    proj_yaml = tmp_path / "project.yaml"
    proj_yaml.write_text("invalid_yaml: [missing_required_fields", encoding="utf-8")

    with pytest.raises(InvalidManifestError):
        ProjectManifest.from_yaml(proj_yaml)
