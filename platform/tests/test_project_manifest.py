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
  editorial: editorial.tres
  genre: genre.essay
  styles:
    - style.literary
""",
        encoding="utf-8",
    )

    manifest = ProjectManifest.from_yaml(proj_yaml)
    assert manifest.id == "sample_proj"
    assert manifest.title == "Proyecto Test"
    assert manifest.plugins.editorial == "editorial.tres"
    assert manifest.plugins.genre == "genre.essay"
    assert manifest.plugins.styles == ["style.literary"]
    assert "editorial.tres" in manifest.plugins.get_all_plugin_ids()
    assert "genre.essay" in manifest.plugins.get_all_plugin_ids()
    assert "style.literary" in manifest.plugins.get_all_plugin_ids()


def test_invalid_project_manifest(tmp_path: Path):
    proj_yaml = tmp_path / "project.yaml"
    proj_yaml.write_text("invalid_yaml: [missing_required_fields", encoding="utf-8")

    with pytest.raises(InvalidManifestError):
        ProjectManifest.from_yaml(proj_yaml)


def test_private_factory_manifest_accepts_project_id_and_resolves_source(tmp_path: Path):
    project = tmp_path / "book"
    project.mkdir()
    source = project / "manuscript.txt"
    source.write_text("OBRA", encoding="utf-8")
    (project / "project.yaml").write_text(
        """
project_id: book-one
title: Obra privada
language: es
source_file: manuscript.txt
source_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
expected_word_count: 1
expected_chapter_count: 1
workflow: private-editorial-factory-v1
""",
        encoding="utf-8",
    )

    manifest = ProjectManifest.from_yaml(project)

    assert manifest.id == "book-one"
    assert manifest.project_id == "book-one"
    assert manifest.work_id == "work.book-one"
    assert manifest.output_slug == "book-one"
    assert manifest.resolve_source_path() == source
