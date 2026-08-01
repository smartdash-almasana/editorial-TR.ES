"""CapabilityFactoryRegistry — implementation_id → constructor validado de Reviewer.

ADR-004 §3: evita que PluginRuntime crezca como un switch central de
implementaciones.  Los plugins declaran comportamiento; no obtienen acceso
directo a Work ni a mecanismos de mutación.

Cada fábrica recibe (plugin_id, ReviewerBehavior) y retorna un Reviewer
construido y validado.  La validación de configuración es fail-fast:
parámetros ausentes o inválidos lanzan InvalidManifestError antes de
construir el objeto.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Callable, Dict, Tuple

from pydantic import ValidationError

from editorial_tres.domain.llm_repetition import LLMGlobalRepetitionReviewer
from editorial_tres.domain.reviews import (
    ContinuityReviewer,
    ContinuityRule,
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

if TYPE_CHECKING:
    from editorial_tres.plugin_runtime import ReviewerBehavior


# ---------------------------------------------------------------------------
# Tipo de fábrica
# ---------------------------------------------------------------------------

ReviewerFactory = Callable[["str", "ReviewerBehavior"], Reviewer]


# ---------------------------------------------------------------------------
# Fábricas concretas (una por implementation_id)
# ---------------------------------------------------------------------------


def build_repeated_phrase(plugin_id: str, behavior: ReviewerBehavior) -> Reviewer:
    """Construye un RepeatedPhraseReviewer desde parameters.phrase."""
    phrase = str(behavior.parameters.get("phrase", "")).strip()
    if not phrase:
        raise InvalidManifestError(
            f"El reviewer '{plugin_id}' requiere parameters.phrase para repeated_phrase."
        )
    try:
        minimum_occurrences = int(
            behavior.parameters.get("minimum_occurrences", 2)
        )
        return RepeatedPhraseReviewer(
            reviewer_id=plugin_id,
            phrase=phrase,
            minimum_occurrences=minimum_occurrences,
            severity=behavior.severity,
        )
    except (ValidationError, TypeError, ValueError) as exc:
        raise InvalidManifestError(
            f"El reviewer '{plugin_id}' declara parámetros inválidos para repeated_phrase: {exc}"
        ) from exc


def build_structural(plugin_id: str, behavior: ReviewerBehavior) -> Reviewer:
    """Construye un StructuralReviewer desde parameters.thematic_phrases."""
    raw_phrases = behavior.parameters.get("thematic_phrases", [])
    if not isinstance(raw_phrases, (list, tuple)):
        raise InvalidManifestError(
            f"El reviewer '{plugin_id}' requiere parameters.thematic_phrases como lista."
        )
    thematic_phrases = tuple(
        str(phrase).strip() for phrase in raw_phrases if str(phrase).strip()
    )
    try:
        minimum_occurrences = int(
            behavior.parameters.get("minimum_thematic_occurrences", 3)
        )
        return StructuralReviewer(
            reviewer_id=plugin_id,
            thematic_phrases=thematic_phrases,
            minimum_thematic_occurrences=minimum_occurrences,
            severity=behavior.severity,
        )
    except (ValidationError, TypeError, ValueError) as exc:
        raise InvalidManifestError(
            f"El reviewer '{plugin_id}' declara parámetros estructurales inválidos: {exc}"
        ) from exc


def build_configured_continuity(plugin_id: str, behavior: ReviewerBehavior) -> Reviewer:
    """Construye un ContinuityReviewer desde parameters.rules."""
    raw_rules = behavior.parameters.get("rules", [])
    if not isinstance(raw_rules, list) or not raw_rules:
        raise InvalidManifestError(
            f"El reviewer '{plugin_id}' requiere parameters.rules como lista no vacía."
        )
    try:
        rules = tuple(ContinuityRule.model_validate(rule) for rule in raw_rules)
        return ContinuityReviewer(
            reviewer_id=plugin_id,
            rules=rules,
            severity=behavior.severity,
        )
    except (ValidationError, TypeError, ValueError) as exc:
        raise InvalidManifestError(
            f"El reviewer '{plugin_id}' declara reglas de continuidad inválidas: {exc}"
        ) from exc


def build_rhythm(plugin_id: str, behavior: ReviewerBehavior) -> Reviewer:
    """Construye un RhythmReviewer desde umbrales en parameters."""
    try:
        return RhythmReviewer(
            reviewer_id=plugin_id,
            short_sentence_max_words=int(
                behavior.parameters.get("short_sentence_max_words", 3)
            ),
            long_sentence_min_words=int(
                behavior.parameters.get("long_sentence_min_words", 35)
            ),
            minimum_short_run=int(
                behavior.parameters.get("minimum_short_run", 4)
            ),
            minimum_long_run=int(
                behavior.parameters.get("minimum_long_run", 3)
            ),
            uniformity_min_sentences=int(
                behavior.parameters.get("uniformity_min_sentences", 6)
            ),
            uniformity_max_word_range=int(
                behavior.parameters.get("uniformity_max_word_range", 2)
            ),
            opening_word_count=int(
                behavior.parameters.get("opening_word_count", 2)
            ),
            minimum_repeated_openings=int(
                behavior.parameters.get("minimum_repeated_openings", 4)
            ),
            severity=behavior.severity,
        )
    except (ValidationError, TypeError, ValueError) as exc:
        raise InvalidManifestError(
            f"El reviewer '{plugin_id}' declara umbrales rítmicos inválidos: {exc}"
        ) from exc


def build_llm_global_repetition(plugin_id: str, behavior: ReviewerBehavior) -> Reviewer:
    """Construye revisión semántica global mediante Gemini con salida estructurada."""
    from editorial_tres.infrastructure.gemini_structured_llm import (
        GeminiStructuredLLMAdapter,
    )

    api_key_env = str(
        behavior.parameters.get("api_key_env", "GEMINI_API_KEY")
    ).strip()
    api_key = os.environ.get(api_key_env, "")
    if not api_key:
        raise InvalidManifestError(
            f"El reviewer '{plugin_id}' requiere la variable de entorno '{api_key_env}'."
        )
    try:
        adapter = GeminiStructuredLLMAdapter(
            api_key=api_key,
            model=str(
                behavior.parameters.get("model", "gemini-3.6-flash")
            ).strip(),
            timeout_seconds=float(
                behavior.parameters.get("timeout_seconds", 90)
            ),
        )
        return LLMGlobalRepetitionReviewer(
            reviewer_id=plugin_id,
            llm=adapter,
            minimum_confidence=float(
                behavior.parameters.get("minimum_confidence", 0.55)
            ),
            severity=behavior.severity,
            max_blocks=int(behavior.parameters.get("max_blocks", 250)),
            max_characters=int(
                behavior.parameters.get("max_characters", 300_000)
            ),
        )
    except (TypeError, ValueError) as exc:
        raise InvalidManifestError(
            f"El reviewer '{plugin_id}' declara parámetros LLM inválidos: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class CapabilityFactoryRegistry:
    """Registro explícito implementation_id → ReviewerFactory.

    Fail-fast ante:
    - registro duplicado de un implementation_id;
    - construcción con implementation_id inexistente;
    - configuración inválida (delegada a cada fábrica).
    """

    def __init__(self) -> None:
        self._factories: Dict[str, ReviewerFactory] = {}
        self._frozen = False

    @property
    def is_frozen(self) -> bool:
        """Indica si el registry bloquea nuevos registros."""
        return self._frozen

    def freeze(self) -> None:
        """Congela el registry sin impedir la construcción de capacidades."""
        self._frozen = True

    def register(self, implementation_id: str, factory: ReviewerFactory) -> None:
        """Registra una fábrica en una instancia extensible del registry."""
        normalized = implementation_id.strip() if implementation_id else ""
        if self._frozen:
            raise RegistryFrozenError(
                f"El registry está congelado; no puede registrar '{normalized or implementation_id}'."
            )
        if not normalized:
            raise ValueError("implementation_id no puede estar vacío.")
        if normalized in self._factories:
            raise ValueError(
                f"implementation_id '{normalized}' ya está registrado. "
                "No se permite sobrescribir una fábrica existente."
            )
        self._factories[normalized] = factory

    def build(
        self, implementation_id: str, plugin_id: str, behavior: ReviewerBehavior
    ) -> Reviewer:
        """Construye un Reviewer. Lanza UnknownImplementationError si no existe."""
        normalized = implementation_id.strip() if implementation_id else ""
        if normalized not in self._factories:
            raise UnknownImplementationError(
                f"El reviewer '{plugin_id}' declara una implementación no registrada: "
                f"'{normalized}'. Implementaciones disponibles: "
                f"{', '.join(sorted(self._factories)) or '(ninguna)'}."
            )
        reviewer = self._factories[normalized](plugin_id, behavior)
        if not isinstance(reviewer, Reviewer):
            raise InvalidManifestError(
                f"La fábrica registrada para '{normalized}' retornó "
                f"'{type(reviewer).__name__}' en lugar de un Reviewer."
            )
        return reviewer

    def has(self, implementation_id: str) -> bool:
        """Indica si un implementation_id está registrado."""
        return implementation_id.strip() in self._factories

    def registered_implementations(self) -> Tuple[str, ...]:
        """Retorna los implementation_ids registrados en orden determinista."""
        return tuple(sorted(self._factories))


# ---------------------------------------------------------------------------
# Registry por defecto (singleton perezoso)
# ---------------------------------------------------------------------------

_default_registry: CapabilityFactoryRegistry | None = None


def default_reviewer_registry() -> CapabilityFactoryRegistry:
    """Retorna el registry singleton con las implementaciones canónicas."""
    global _default_registry
    if _default_registry is None:
        registry = CapabilityFactoryRegistry()
        registry.register("repeated_phrase", build_repeated_phrase)
        registry.register("structural", build_structural)
        registry.register("configured_continuity", build_configured_continuity)
        registry.register("rhythm", build_rhythm)
        registry.register("llm_global_repetition", build_llm_global_repetition)
        registry.freeze()
        _default_registry = registry
    return _default_registry
