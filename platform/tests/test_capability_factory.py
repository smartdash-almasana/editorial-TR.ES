"""Tests focales de CapabilityFactoryRegistry (ADR-004 §3).

Cubren el registry como unidad aislada: registro, resolución, fail-fast y
extensibilidad.  La construcción vía PluginRuntime.build_reviewer está cubierta
en test_plugin_runtime.py; aquí se prueba el contrato propio del registry sin
pasar por PluginRuntime.
"""

import pytest

from editorial_tres.capability_factory import (
    CapabilityFactoryRegistry,
    default_reviewer_registry,
)
from editorial_tres.domain.llm_repetition import LLMGlobalRepetitionReviewer
from editorial_tres.domain.reviews import (
    ContinuityReviewer,
    RepeatedPhraseReviewer,
    Reviewer,
    RhythmReviewer,
    StructuralReviewer,
)
from editorial_tres.exceptions import (
    InvalidManifestError,
    RegistryFrozenError,
    UnknownImplementationError,
)
from editorial_tres.plugin_runtime import ReviewerBehavior


def _behavior(implementation: str, **parameters) -> ReviewerBehavior:
    """Construye un ReviewerBehavior sintético con configuración mínima válida."""
    return ReviewerBehavior(
        finding_type="test.finding",
        scope=["expression_block"],
        severity="warning",
        evidence_format="test_evidence",
        nature="deterministic",
        recommendation_policy="revisar",
        implementation=implementation,
        parameters=dict(parameters),
    )


_VALID_CONTINUITY_RULE = {
    "rule_id": "regresion_temporal_explicita",
    "entity": "momento del día",
    "established_markers": ["había caído la noche"],
    "conflicting_markers": ["el sol de la tarde"],
}


# ---------------------------------------------------------------------------
# Registro por defecto
# ---------------------------------------------------------------------------


def test_default_registry_registers_the_canonical_implementations():
    registry = default_reviewer_registry()

    assert registry.registered_implementations() == (
        "configured_continuity",
        "llm_global_repetition",
        "repeated_phrase",
        "rhythm",
        "structural",
    )


def test_default_registry_is_a_singleton():
    assert default_reviewer_registry() is default_reviewer_registry()


def test_default_registry_reports_membership_via_has():
    registry = default_reviewer_registry()

    assert registry.has("repeated_phrase") is True
    assert registry.has("structural") is True
    assert registry.has("configured_continuity") is True
    assert registry.has("rhythm") is True
    assert registry.has("llm_global_repetition") is True
    assert registry.has("no_registrada") is False


# ---------------------------------------------------------------------------
# Construcción de cada implementación canónica
# ---------------------------------------------------------------------------


def test_build_repeated_phrase_from_behavior():
    behavior = _behavior("repeated_phrase", phrase="muy", minimum_occurrences=3)

    reviewer = default_reviewer_registry().build("repeated_phrase", "reviewer.repetition", behavior)

    assert isinstance(reviewer, RepeatedPhraseReviewer)
    assert reviewer.reviewer_id == "reviewer.repetition"
    assert reviewer.phrase == "muy"
    assert reviewer.minimum_occurrences == 3
    assert reviewer.severity == "warning"


def test_build_repeated_phrase_requires_phrase():
    behavior = _behavior("repeated_phrase", minimum_occurrences=2)

    with pytest.raises(InvalidManifestError, match="parameters.phrase"):
        default_reviewer_registry().build("repeated_phrase", "reviewer.repetition", behavior)


def test_build_structural_from_behavior():
    behavior = _behavior(
        "structural",
        thematic_phrases=["la casa", "el río"],
        minimum_thematic_occurrences=4,
    )

    reviewer = default_reviewer_registry().build("structural", "reviewer.structural", behavior)

    assert isinstance(reviewer, StructuralReviewer)
    assert reviewer.reviewer_id == "reviewer.structural"
    assert reviewer.thematic_phrases == ("la casa", "el río")
    assert reviewer.minimum_thematic_occurrences == 4


def test_build_structural_rejects_non_list_thematic_phrases():
    behavior = _behavior("structural", thematic_phrases="no-es-una-lista")

    with pytest.raises(InvalidManifestError, match="thematic_phrases"):
        default_reviewer_registry().build("structural", "reviewer.structural", behavior)


def test_build_configured_continuity_from_behavior():
    behavior = _behavior("configured_continuity", rules=[_VALID_CONTINUITY_RULE])

    reviewer = default_reviewer_registry().build(
        "configured_continuity", "reviewer.continuity", behavior
    )

    assert isinstance(reviewer, ContinuityReviewer)
    assert reviewer.reviewer_id == "reviewer.continuity"
    assert [rule.rule_id for rule in reviewer.rules] == ["regresion_temporal_explicita"]
    assert reviewer.rules[0].entity == "momento del día"


def test_build_configured_continuity_requires_non_empty_rules():
    behavior = _behavior("configured_continuity", rules=[])

    with pytest.raises(InvalidManifestError, match="parameters.rules"):
        default_reviewer_registry().build("configured_continuity", "reviewer.continuity", behavior)


def test_build_configured_continuity_rejects_invalid_rule_shape():
    behavior = _behavior("configured_continuity", rules=[{"rule_id": "incompleta"}])

    with pytest.raises(InvalidManifestError, match="reglas de continuidad inválidas"):
        default_reviewer_registry().build("configured_continuity", "reviewer.continuity", behavior)


def test_build_rhythm_from_behavior_with_defaults():
    behavior = _behavior("rhythm")

    reviewer = default_reviewer_registry().build("rhythm", "reviewer.rhythm", behavior)

    assert isinstance(reviewer, RhythmReviewer)
    assert reviewer.reviewer_id == "reviewer.rhythm"
    assert reviewer.short_sentence_max_words == 3
    assert reviewer.long_sentence_min_words == 35
    assert reviewer.minimum_repeated_openings == 4


def test_build_rhythm_rejects_invalid_threshold_order():
    behavior = _behavior("rhythm", short_sentence_max_words=10, long_sentence_min_words=10)

    with pytest.raises(InvalidManifestError, match="umbrales rítmicos inválidos"):
        default_reviewer_registry().build("rhythm", "reviewer.rhythm", behavior)


def test_build_llm_global_repetition_from_environment(monkeypatch):
    monkeypatch.setenv("TEST_GEMINI_KEY", "secret")
    behavior = _behavior(
        "llm_global_repetition",
        api_key_env="TEST_GEMINI_KEY",
        model="gemini-3.6-flash",
        minimum_confidence=0.7,
    )

    reviewer = default_reviewer_registry().build(
        "llm_global_repetition",
        "reviewer.llm-repetition",
        behavior,
    )

    assert isinstance(reviewer, LLMGlobalRepetitionReviewer)
    assert reviewer.reviewer_id == "reviewer.llm-repetition"
    assert reviewer.llm_provider_id == "google-gemini"
    assert reviewer.llm_model_id == "gemini-3.6-flash"
    assert reviewer.minimum_confidence == 0.7


def test_build_llm_global_repetition_requires_api_key(monkeypatch):
    monkeypatch.delenv("MISSING_GEMINI_KEY", raising=False)
    behavior = _behavior(
        "llm_global_repetition",
        api_key_env="MISSING_GEMINI_KEY",
    )

    with pytest.raises(InvalidManifestError, match="MISSING_GEMINI_KEY"):
        default_reviewer_registry().build(
            "llm_global_repetition",
            "reviewer.llm-repetition",
            behavior,
        )


# ---------------------------------------------------------------------------
# Fail-fast del registry
# ---------------------------------------------------------------------------


def test_build_unknown_implementation_raises_with_available_list():
    with pytest.raises(UnknownImplementationError) as excinfo:
        default_reviewer_registry().build("no_existe", "reviewer.x", _behavior("no_existe"))

    message = str(excinfo.value)
    assert "no_existe" in message
    assert "repeated_phrase" in message


def test_build_normalizes_implementation_whitespace():
    behavior = _behavior("repeated_phrase", phrase="muy")

    reviewer = default_reviewer_registry().build("  repeated_phrase  ", "reviewer.repetition", behavior)

    assert isinstance(reviewer, RepeatedPhraseReviewer)


# ---------------------------------------------------------------------------
# Registro explícito y extensibilidad (registry fresco, sin tocar el singleton)
# ---------------------------------------------------------------------------


def test_register_duplicate_implementation_raises():
    registry = CapabilityFactoryRegistry()
    registry.register("custom", lambda plugin_id, behavior: None)

    with pytest.raises(ValueError, match="ya está registrado"):
        registry.register("custom", lambda plugin_id, behavior: None)


def test_register_empty_implementation_raises():
    registry = CapabilityFactoryRegistry()

    with pytest.raises(ValueError, match="no puede estar vacío"):
        registry.register("   ", lambda plugin_id, behavior: None)


def test_custom_factory_can_be_registered_and_used():
    def _factory(plugin_id: str, behavior: ReviewerBehavior) -> RepeatedPhraseReviewer:
        return RepeatedPhraseReviewer(
            reviewer_id=plugin_id,
            phrase=str(behavior.parameters["phrase"]),
        )

    registry = CapabilityFactoryRegistry()
    registry.register("mi_IMPLEMENTACION", _factory)

    # El registro normaliza espacios pero preserva mayúsculas/minúsculas.
    assert registry.has("mi_IMPLEMENTACION") is True
    assert registry.registered_implementations() == ("mi_IMPLEMENTACION",)

    reviewer = registry.build("mi_IMPLEMENTACION", "reviewer.custom", _behavior("mi_IMPLEMENTACION", phrase="x"))
    assert isinstance(reviewer, RepeatedPhraseReviewer)
    assert reviewer.reviewer_id == "reviewer.custom"
    assert reviewer.phrase == "x"


def test_fresh_registry_has_no_implementations_and_build_fails_fast():
    registry = CapabilityFactoryRegistry()

    assert registry.registered_implementations() == ()

    with pytest.raises(UnknownImplementationError, match="\\(ninguna\\)"):
        registry.build("repeated_phrase", "reviewer.x", _behavior("repeated_phrase", phrase="muy"))


# ---------------------------------------------------------------------------
# Endurecimiento del registry y normalización de errores
# ---------------------------------------------------------------------------


def test_factory_returning_non_reviewer_fails_fast():
    registry = CapabilityFactoryRegistry()
    registry.register("invalid_return", lambda plugin_id, behavior: "not-a-reviewer")

    with pytest.raises(InvalidManifestError, match="en lugar de un Reviewer"):
        registry.build(
            "invalid_return",
            "reviewer.invalid-return",
            _behavior("invalid_return"),
        )


def test_repeated_phrase_invalid_numeric_parameter_is_normalized():
    behavior = _behavior(
        "repeated_phrase",
        phrase="muy",
        minimum_occurrences="no-es-numero",
    )

    with pytest.raises(InvalidManifestError, match="repeated_phrase"):
        default_reviewer_registry().build(
            "repeated_phrase", "reviewer.repetition", behavior
        )


def test_structural_invalid_numeric_parameter_is_normalized():
    behavior = _behavior(
        "structural",
        thematic_phrases=[],
        minimum_thematic_occurrences="no-es-numero",
    )

    with pytest.raises(InvalidManifestError, match="estructurales inválidos"):
        default_reviewer_registry().build(
            "structural", "reviewer.structural", behavior
        )


def test_default_registry_is_frozen_against_external_registration():
    registry = default_reviewer_registry()

    assert registry.is_frozen is True
    with pytest.raises(RegistryFrozenError, match="congelado"):
        registry.register("external", lambda plugin_id, behavior: None)


def test_fresh_registry_remains_extensible_after_default_registry_is_frozen():
    registry = CapabilityFactoryRegistry()

    assert registry.is_frozen is False
    registry.register(
        "custom",
        lambda plugin_id, behavior: RepeatedPhraseReviewer(
            reviewer_id=plugin_id,
            phrase="x",
        ),
    )
    reviewer = registry.build("custom", "reviewer.custom", _behavior("custom"))

    assert isinstance(reviewer, Reviewer)
    assert default_reviewer_registry().has("custom") is False
