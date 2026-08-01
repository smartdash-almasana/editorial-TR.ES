from pathlib import Path

import pytest

from editorial_tres.domain.reviews import (
    ContinuityReviewer,
    RepeatedPhraseReviewer,
    ReviewEngine,
    RhythmReviewer,
    StructuralReviewer,
)
from editorial_tres.exceptions import InvalidManifestError, PluginNotFoundError
from editorial_tres.plugin_contract import PluginManifest
from editorial_tres.plugin_runtime import (
    AuthorVoiceBehavior,
    EditorialBehavior,
    GenreBehavior,
    NarratorBehavior,
    PluginRuntime,
    ReviewerBehavior,
    StyleBehavior,
)


def _editorial_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins" / "editorials" / "tres" / "plugin.yaml"


def _novel_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins" / "genres" / "novel" / "plugin.yaml"


def _literary_style_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins" / "styles" / "literary" / "plugin.yaml"


def _default_voice_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins" / "voices" / "default" / "plugin.yaml"


def _reflective_narrator_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins" / "narrators" / "reflective" / "plugin.yaml"


def _repetition_reviewer_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins" / "reviewers" / "repetition" / "plugin.yaml"


def _structural_reviewer_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins" / "reviewers" / "structural" / "plugin.yaml"


def _continuity_reviewer_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins" / "reviewers" / "continuity" / "plugin.yaml"


def _rhythm_reviewer_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "plugins" / "reviewers" / "rhythm" / "plugin.yaml"


def test_editorial_plugin_activates_with_executable_editorial_behavior():
    manifest = PluginManifest.from_yaml(_editorial_manifest_path())
    runtime = PluginRuntime()

    activated = runtime.activate(manifest)

    assert activated.id == "editorial.tres"
    assert activated.type == "editorial"
    assert isinstance(activated.editorial, EditorialBehavior)
    assert "preservar la identidad autoral y la originalidad de cada obra" in activated.editorial.constitution
    assert "preservación de la identidad autoral" in activated.editorial.approval_criteria
    assert "editorial_governance" in activated.capabilities
    assert "institutional_homogenization" in activated.risks


def test_editorial_plugin_without_valid_behavior_cannot_activate():
    manifest = PluginManifest(
        id="editorial.invalid",
        version="0.1.0",
        type="editorial",
        name="Inválida",
        description="Sin constitución editorial ejecutable.",
        entrypoint="SKILL.md",
    )

    with pytest.raises(InvalidManifestError):
        PluginRuntime().activate(manifest)


def test_novel_plugin_activates_with_executable_genre_behavior():
    manifest = PluginManifest.from_yaml(_novel_manifest_path())
    runtime = PluginRuntime()

    activated = runtime.activate(manifest)

    assert activated.id == "genre.novel"
    assert activated.type == "genre"
    assert isinstance(activated.genre, GenreBehavior)
    assert activated.genre.unit_types == ["part", "chapter", "scene"]
    assert activated.genre.compilation_strategy == "narrative_sequence"
    assert activated.genre.required_reviewers == [
        "reviewer.structural",
        "reviewer.continuity",
        "reviewer.rhythm",
    ]
    assert "characters" in activated.capabilities
    assert "flattening_author_voice" in activated.risks


def test_genre_plugin_without_valid_behavior_cannot_activate():
    manifest = PluginManifest(
        id="genre.invalid",
        version="0.1.0",
        type="genre",
        name="Inválido",
        description="Sin gramática ejecutable.",
        entrypoint="SKILL.md",
    )

    with pytest.raises(InvalidManifestError):
        PluginRuntime().activate(manifest)


def test_runtime_can_deactivate_plugin():
    manifest = PluginManifest.from_yaml(_novel_manifest_path())
    runtime = PluginRuntime()
    runtime.activate(manifest)

    runtime.deactivate("genre.novel")

    with pytest.raises(PluginNotFoundError):
        runtime.get("genre.novel")


def test_literary_style_plugin_activates_with_executable_style_behavior():
    manifest = PluginManifest.from_yaml(_literary_style_manifest_path())
    runtime = PluginRuntime()

    activated = runtime.activate(manifest)

    assert activated.id == "style.literary"
    assert activated.type == "style"
    assert isinstance(activated.style, StyleBehavior)
    assert "preservar la identidad autoral" in activated.style.principles
    assert "clichés de prosa generativa" in activated.style.avoid
    assert "rhythm_modulation" in activated.capabilities
    assert "voice_erasure" in activated.risks


def test_style_plugin_without_valid_behavior_cannot_activate():
    manifest = PluginManifest(
        id="style.invalid",
        version="0.1.0",
        type="style",
        name="Inválido",
        description="Sin comportamiento estilístico ejecutable.",
        entrypoint="SKILL.md",
    )

    with pytest.raises(InvalidManifestError):
        PluginRuntime().activate(manifest)


def test_default_voice_plugin_activates_with_executable_author_voice_behavior():
    manifest = PluginManifest.from_yaml(_default_voice_manifest_path())
    runtime = PluginRuntime()

    activated = runtime.activate(manifest)

    assert activated.id == "voice.default"
    assert activated.type == "voice"
    assert isinstance(activated.voice, AuthorVoiceBehavior)
    assert "claridad sin neutralizar singularidades expresivas" in activated.voice.profile
    assert "imitar superficialmente palabras o giros del corpus" in activated.voice.anti_patterns
    assert "voice_drift_detection" in activated.capabilities
    assert "mimicry" in activated.risks


def test_voice_plugin_without_valid_behavior_cannot_activate():
    manifest = PluginManifest(
        id="voice.invalid",
        version="0.1.0",
        type="voice",
        name="Inválida",
        description="Sin comportamiento de voz ejecutable.",
        entrypoint="SKILL.md",
    )

    with pytest.raises(InvalidManifestError):
        PluginRuntime().activate(manifest)


def test_reflective_narrator_plugin_activates_with_executable_narrator_behavior():
    manifest = PluginManifest.from_yaml(_reflective_narrator_manifest_path())
    runtime = PluginRuntime()

    activated = runtime.activate(manifest)

    assert activated.id == "narrator.reflective"
    assert activated.type == "narrator"
    assert isinstance(activated.narrator, NarratorBehavior)
    assert activated.narrator.persona == "tercera persona"
    assert activated.narrator.focalization == "interna variable controlada"
    assert "knowledge_scope_control" in activated.capabilities
    assert "unauthorized_omniscience" in activated.risks


def test_narrator_plugin_without_valid_behavior_cannot_activate():
    manifest = PluginManifest(
        id="narrator.invalid",
        version="0.1.0",
        type="narrator",
        name="Inválido",
        description="Sin comportamiento de narrador ejecutable.",
        entrypoint="SKILL.md",
    )

    with pytest.raises(InvalidManifestError):
        PluginRuntime().activate(manifest)


def test_repetition_reviewer_plugin_builds_review_engine_compatible_reviewer():
    manifest = PluginManifest.from_yaml(_repetition_reviewer_manifest_path())
    runtime = PluginRuntime()

    activated = runtime.activate(manifest)
    reviewer = runtime.build_reviewer("reviewer.repetition")
    engine = ReviewEngine((reviewer,))

    assert activated.id == "reviewer.repetition"
    assert activated.type == "reviewer"
    assert isinstance(activated.reviewer, ReviewerBehavior)
    assert isinstance(reviewer, RepeatedPhraseReviewer)
    assert reviewer.reviewer_id == "reviewer.repetition"
    assert reviewer.phrase == "muy"
    assert reviewer.minimum_occurrences == 2
    assert engine is not None


def test_structural_reviewer_plugin_builds_review_engine_compatible_reviewer():
    manifest = PluginManifest.from_yaml(_structural_reviewer_manifest_path())
    runtime = PluginRuntime()

    activated = runtime.activate(manifest)
    reviewer = runtime.build_reviewer("reviewer.structural")
    engine = ReviewEngine((reviewer,))

    assert activated.id == "reviewer.structural"
    assert activated.type == "reviewer"
    assert isinstance(activated.reviewer, ReviewerBehavior)
    assert isinstance(reviewer, StructuralReviewer)
    assert reviewer.reviewer_id == "reviewer.structural"
    assert reviewer.thematic_phrases == ()
    assert reviewer.minimum_thematic_occurrences == 3
    assert engine is not None


def test_continuity_reviewer_plugin_builds_review_engine_compatible_reviewer():
    manifest = PluginManifest.from_yaml(_continuity_reviewer_manifest_path())
    runtime = PluginRuntime()

    activated = runtime.activate(manifest)
    reviewer = runtime.build_reviewer("reviewer.continuity")
    engine = ReviewEngine((reviewer,))

    assert activated.id == "reviewer.continuity"
    assert activated.type == "reviewer"
    assert isinstance(activated.reviewer, ReviewerBehavior)
    assert isinstance(reviewer, ContinuityReviewer)
    assert reviewer.reviewer_id == "reviewer.continuity"
    assert reviewer.severity == "warning"
    assert [rule.rule_id for rule in reviewer.rules] == [
        "explicit_temporal_regression_after_nightfall"
    ]
    assert engine is not None


def test_continuity_reviewer_requires_declared_rules():
    manifest = PluginManifest(
        id="reviewer.continuity-empty",
        version="0.1.0",
        type="reviewer",
        name="Continuidad sin reglas",
        description="Contrato inválido para construcción.",
        entrypoint="SKILL.md",
        behavior={
            "finding_type": "narrative.continuity_conflict",
            "scope": ["expression_block"],
            "severity": "warning",
            "evidence_format": "ordered_marker_pair",
            "nature": "deterministic",
            "recommendation_policy": "revisar",
            "implementation": "configured_continuity",
            "parameters": {"rules": []},
        },
    )
    runtime = PluginRuntime()
    runtime.activate(manifest)

    with pytest.raises(InvalidManifestError, match="parameters.rules"):
        runtime.build_reviewer(manifest.id)


def test_rhythm_reviewer_plugin_builds_review_engine_compatible_reviewer():
    manifest = PluginManifest.from_yaml(_rhythm_reviewer_manifest_path())
    runtime = PluginRuntime()

    activated = runtime.activate(manifest)
    reviewer = runtime.build_reviewer("reviewer.rhythm")
    engine = ReviewEngine((reviewer,))

    assert activated.id == "reviewer.rhythm"
    assert activated.type == "reviewer"
    assert isinstance(activated.reviewer, ReviewerBehavior)
    assert isinstance(reviewer, RhythmReviewer)
    assert reviewer.reviewer_id == "reviewer.rhythm"
    assert reviewer.short_sentence_max_words == 3
    assert reviewer.long_sentence_min_words == 35
    assert reviewer.minimum_repeated_openings == 4
    assert engine is not None


def test_rhythm_reviewer_rejects_invalid_threshold_order():
    manifest = PluginManifest(
        id="reviewer.rhythm-invalid",
        version="0.1.0",
        type="reviewer",
        name="Ritmo inválido",
        description="Contrato inválido para construcción.",
        entrypoint="SKILL.md",
        behavior={
            "finding_type": "expression.rhythm.signal",
            "scope": ["expression_block"],
            "severity": "warning",
            "evidence_format": "sentence_excerpt_or_word_counts",
            "nature": "deterministic",
            "recommendation_policy": "revisar",
            "implementation": "rhythm",
            "parameters": {
                "short_sentence_max_words": 10,
                "long_sentence_min_words": 10,
            },
        },
    )
    runtime = PluginRuntime()
    runtime.activate(manifest)

    with pytest.raises(InvalidManifestError, match="umbrales rítmicos inválidos"):
        runtime.build_reviewer(manifest.id)


def test_reviewer_plugin_without_valid_behavior_cannot_activate():
    manifest = PluginManifest(
        id="reviewer.invalid",
        version="0.1.0",
        type="reviewer",
        name="Inválido",
        description="Sin comportamiento reviewer ejecutable.",
        entrypoint="SKILL.md",
    )

    with pytest.raises(InvalidManifestError):
        PluginRuntime().activate(manifest)


def test_runtime_lists_active_plugins_deterministically():
    editorial = PluginManifest.from_yaml(_editorial_manifest_path())
    novel = PluginManifest.from_yaml(_novel_manifest_path())
    style = PluginManifest.from_yaml(_literary_style_manifest_path())
    voice = PluginManifest.from_yaml(_default_voice_manifest_path())
    narrator = PluginManifest.from_yaml(_reflective_narrator_manifest_path())
    runtime = PluginRuntime()

    runtime.activate_all([style, narrator, voice, novel, editorial])

    assert [plugin.id for plugin in runtime.list_active()] == [
        "editorial.tres",
        "genre.novel",
        "narrator.reflective",
        "style.literary",
        "voice.default",
    ]


def test_reviewer_with_invalid_severity_fails_during_activation():
    manifest = PluginManifest(
        id="reviewer.invalid-severity",
        version="0.1.0",
        type="reviewer",
        name="Reviewer con severidad inválida",
        description="Debe fallar antes de construir el reviewer.",
        entrypoint="SKILL.md",
        behavior={
            "finding_type": "test.invalid_severity",
            "scope": ["expression_block"],
            "severity": "critical",
            "evidence_format": "text",
            "nature": "deterministic",
            "recommendation_policy": "revisar",
            "implementation": "repeated_phrase",
            "parameters": {"phrase": "muy"},
        },
    )

    with pytest.raises(InvalidManifestError, match="behavior ejecutable válido"):
        PluginRuntime().activate(manifest)
