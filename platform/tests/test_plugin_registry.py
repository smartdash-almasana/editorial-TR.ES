"""
Pruebas para el registro y descubrimiento de plugins (PluginRegistry).
"""

from pathlib import Path
import pytest

from editorial_tres.exceptions import (
    DuplicatePluginError,
    PluginNotFoundError,
)
from editorial_tres.plugin_contract import PluginManifest
from editorial_tres.plugin_registry import PluginRegistry


def test_register_and_get_plugin():
    registry = PluginRegistry()
    manifest = PluginManifest(
        id="genre.essay",
        version="0.1.0",
        type="genre",
        name="Ensayo",
        description="Test",
        entrypoint="SKILL.md",
    )
    registry.register(manifest)
    assert registry.contains("genre.essay")
    retrieved = registry.get("genre.essay")
    assert retrieved.id == "genre.essay"


def test_plugin_not_found():
    registry = PluginRegistry()
    with pytest.raises(PluginNotFoundError) as excinfo:
        registry.get("nonexistent.plugin")
    assert "nonexistent.plugin" in str(excinfo.value)


def test_duplicate_plugin_registration():
    registry = PluginRegistry()
    m1 = PluginManifest(
        id="voice.default",
        version="0.1.0",
        type="voice",
        name="Voz 1",
        description="Test",
        entrypoint="SKILL.md",
    )
    m2 = PluginManifest(
        id="voice.default",
        version="0.2.0",
        type="voice",
        name="Voz 2",
        description="Test",
        entrypoint="SKILL.md",
    )
    registry.register(m1)
    with pytest.raises(DuplicatePluginError) as excinfo:
        registry.register(m2)
    assert "voice.default" in str(excinfo.value)


def test_discover_plugins(tmp_path: Path):
    p1 = tmp_path / "g1"
    p1.mkdir()
    (p1 / "plugin.yaml").write_text(
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

    p2 = tmp_path / "v1"
    p2.mkdir()
    (p2 / "plugin.yaml").write_text(
        """
id: voice.default
version: 0.1.0
type: voice
name: Voz
description: Test
entrypoint: SKILL.md
""",
        encoding="utf-8",
    )

    registry = PluginRegistry()
    count = registry.discover_plugins(tmp_path)
    assert count == 2
    assert registry.contains("genre.essay")
    assert registry.contains("voice.default")
