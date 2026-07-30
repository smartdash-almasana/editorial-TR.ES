"""
Pruebas para el contrato y validación del manifiesto de plugins (PluginManifest).
"""

from pathlib import Path
import pytest

from editorial_tres.exceptions import (
    InvalidManifestError,
    InvalidPluginTypeError,
    UnsafePathError,
)
from editorial_tres.plugin_contract import PluginManifest


def test_valid_plugin_manifest():
    manifest = PluginManifest(
        id="genre.essay",
        version="0.1.0",
        type="genre",
        name="Ensayo",
        description="Estructura para ensayos.",
        entrypoint="SKILL.md",
        language=["es"],
        compatible_with=[],
        requires=[],
    )
    assert manifest.id == "genre.essay"
    assert manifest.type == "genre"
    assert manifest.version == "0.1.0"
    assert manifest.entrypoint == "SKILL.md"


def test_invalid_plugin_type():
    with pytest.raises(InvalidPluginTypeError) as excinfo:
        PluginManifest(
            id="custom.unknown",
            version="1.0.0",
            type="magic_type",
            name="Tipo invalido",
            description="Test",
            entrypoint="SKILL.md",
        )
    assert "magic_type" in str(excinfo.value)


def test_invalid_semver():
    with pytest.raises(InvalidManifestError):
        PluginManifest(
            id="genre.essay",
            version="1.0",  # No es semver valido (requiere x.y.z)
            type="genre",
            name="Ensayo",
            description="Test",
            entrypoint="SKILL.md",
        )


def test_unsafe_path_rejection_parent_traversal():
    with pytest.raises(UnsafePathError) as excinfo:
        PluginManifest(
            id="genre.essay",
            version="0.1.0",
            type="genre",
            name="Ensayo",
            description="Test",
            entrypoint="../../etc/passwd",
        )
    assert "insegura" in str(excinfo.value)


def test_unsafe_path_rejection_absolute():
    with pytest.raises(UnsafePathError) as excinfo:
        PluginManifest(
            id="genre.essay",
            version="0.1.0",
            type="genre",
            name="Ensayo",
            description="Test",
            entrypoint="/abs/path/SKILL.md",
        )
    assert "insegura" in str(excinfo.value)


def test_load_manifest_from_yaml_valid(tmp_path: Path):
    yaml_file = tmp_path / "plugin.yaml"
    yaml_file.write_text(
        """
id: style.literary
version: 1.2.3
type: style
name: Estilo Literario
description: Reglas de estilo.
entrypoint: prompts/style.md
language: ["es"]
compatible_with: []
requires: []
""",
        encoding="utf-8",
    )

    manifest = PluginManifest.from_yaml(yaml_file)
    assert manifest.id == "style.literary"
    assert manifest.type == "style"
    assert manifest.version == "1.2.3"
    assert manifest.entrypoint == "prompts/style.md"
