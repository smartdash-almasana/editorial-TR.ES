"""Composición trazable de reviewers ejecutables desde plugins activados.

ADR-004: esta capa reconcilia requisitos de proyecto, género y workflow y
produce un ReviewPlan. No revisa Work, no ejecuta transformaciones y no aplica
patches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Dict, List, Literal, Set, Tuple

from editorial_tres.capability_factory import (
    CapabilityFactoryRegistry,
    default_reviewer_registry,
)
from editorial_tres.composition import ActivatedProjectComposition
from editorial_tres.domain.reviews import ReviewEngine, Reviewer
from editorial_tres.exceptions import InvalidReviewPlanError, PluginNotFoundError
from editorial_tres.plugin_runtime import ActivatedPlugin, ReviewerBehavior

__all__ = [
    "ReviewRequirementOrigin",
    "ReviewPlanEntry",
    "ReviewPlan",
    "ReviewPlanComposer",
]

RequirementSourceKind = Literal["project", "genre", "workflow"]
RequirementReason = Literal[
    "explicit_project_reviewer",
    "genre_required_reviewer",
    "workflow_required_reviewer",
]

_REASON_BY_SOURCE: Dict[RequirementSourceKind, RequirementReason] = {
    "project": "explicit_project_reviewer",
    "genre": "genre_required_reviewer",
    "workflow": "workflow_required_reviewer",
}


@dataclass(frozen=True)
class ReviewRequirementOrigin:
    """Procedencia auditable de la inclusión de un reviewer."""

    source_kind: RequirementSourceKind
    source_id: str
    reason: RequirementReason

    def __post_init__(self) -> None:
        normalized_source_id = self.source_id.strip() if self.source_id else ""
        if not normalized_source_id:
            raise InvalidReviewPlanError(
                "El origen de un reviewer debe declarar un source_id no vacío."
            )
        if self.source_kind not in _REASON_BY_SOURCE:
            raise InvalidReviewPlanError(
                f"Tipo de origen de reviewer no soportado: '{self.source_kind}'."
            )
        if self.reason != _REASON_BY_SOURCE[self.source_kind]:
            raise InvalidReviewPlanError(
                f"El origen '{self.source_kind}' no admite la razón '{self.reason}'."
            )
        object.__setattr__(self, "source_id", normalized_source_id)


@dataclass(frozen=True)
class ReviewPlanEntry:
    """Reviewer construido junto con la metadata que explica su inclusión."""

    order: int
    reviewer_id: str
    implementation_id: str
    configuration_json: str
    nature: str
    origins: Tuple[ReviewRequirementOrigin, ...]
    reviewer: Reviewer = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.order < 1:
            raise InvalidReviewPlanError("El orden de un reviewer debe comenzar en 1.")
        reviewer_id = self.reviewer_id.strip() if self.reviewer_id else ""
        implementation_id = (
            self.implementation_id.strip() if self.implementation_id else ""
        )
        nature = self.nature.strip() if self.nature else ""
        if not reviewer_id or not implementation_id or not nature:
            raise InvalidReviewPlanError(
                "Cada entrada del plan requiere reviewer_id, implementation_id y nature."
            )
        if not self.origins:
            raise InvalidReviewPlanError(
                f"El reviewer '{reviewer_id}' debe conservar al menos un origen."
            )
        origin_keys = tuple(
            (origin.source_kind, origin.source_id, origin.reason)
            for origin in self.origins
        )
        if len(origin_keys) != len(set(origin_keys)):
            raise InvalidReviewPlanError(
                f"El reviewer '{reviewer_id}' no admite orígenes duplicados."
            )
        if not isinstance(self.reviewer, Reviewer):
            raise InvalidReviewPlanError(
                f"La entrada '{reviewer_id}' no conserva una instancia Reviewer válida."
            )
        if self.reviewer.reviewer_id != reviewer_id:
            raise InvalidReviewPlanError(
                f"La instancia construida '{self.reviewer.reviewer_id}' no coincide "
                f"con la entrada '{reviewer_id}'."
            )
        try:
            parsed_configuration = json.loads(self.configuration_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise InvalidReviewPlanError(
                f"El reviewer '{reviewer_id}' no conserva configuración JSON válida."
            ) from exc
        if not isinstance(parsed_configuration, dict):
            raise InvalidReviewPlanError(
                f"La configuración de '{reviewer_id}' debe ser un objeto JSON."
            )
        object.__setattr__(self, "reviewer_id", reviewer_id)
        object.__setattr__(self, "implementation_id", implementation_id)
        object.__setattr__(self, "nature", nature)


@dataclass(frozen=True)
class ReviewPlan:
    """Plan inmutable y trazable que puede construir un ReviewEngine."""

    project_id: str
    entries: Tuple[ReviewPlanEntry, ...]

    def __post_init__(self) -> None:
        normalized_project_id = self.project_id.strip() if self.project_id else ""
        if not normalized_project_id:
            raise InvalidReviewPlanError("ReviewPlan requiere un project_id no vacío.")
        if not self.entries:
            raise InvalidReviewPlanError(
                "ReviewPlan requiere al menos un reviewer ejecutable."
            )
        if any(not isinstance(entry, ReviewPlanEntry) for entry in self.entries):
            raise InvalidReviewPlanError(
                "ReviewPlan sólo admite entradas ReviewPlanEntry válidas."
            )
        reviewer_ids = tuple(entry.reviewer_id for entry in self.entries)
        if len(reviewer_ids) != len(set(reviewer_ids)):
            raise InvalidReviewPlanError(
                "ReviewPlan no admite reviewer_id duplicados."
            )
        expected_order = tuple(range(1, len(self.entries) + 1))
        actual_order = tuple(entry.order for entry in self.entries)
        if actual_order != expected_order:
            raise InvalidReviewPlanError(
                "ReviewPlan requiere orden continuo, determinista y basado en 1."
            )
        object.__setattr__(self, "project_id", normalized_project_id)

    @property
    def reviewer_ids(self) -> Tuple[str, ...]:
        return tuple(entry.reviewer_id for entry in self.entries)

    def build_engine(self) -> ReviewEngine:
        """Construye el engine sin ejecutar reviewers ni recibir Work."""
        return ReviewEngine(tuple(entry.reviewer for entry in self.entries))


@dataclass(frozen=True)
class ReviewPlanComposer:
    """Reconcilia requisitos activados y construye un ReviewPlan trazable."""

    reviewer_registry: CapabilityFactoryRegistry = field(
        default_factory=default_reviewer_registry,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.reviewer_registry, CapabilityFactoryRegistry):
            raise InvalidReviewPlanError(
                "ReviewPlanComposer requiere un CapabilityFactoryRegistry válido."
            )

    def compose(self, activated: ActivatedProjectComposition) -> ReviewPlan:
        if not isinstance(activated, ActivatedProjectComposition):
            raise InvalidReviewPlanError(
                "ReviewPlanComposer requiere una ActivatedProjectComposition válida."
            )
        ordered_ids: List[str] = []
        origins_by_reviewer: Dict[str, List[ReviewRequirementOrigin]] = {}
        seen_origins: Dict[str, Set[Tuple[str, str, str]]] = {}

        def add_requirement(
            reviewer_id: str,
            source_kind: RequirementSourceKind,
            source_id: str,
        ) -> None:
            normalized_reviewer_id = reviewer_id.strip() if reviewer_id else ""
            if not normalized_reviewer_id:
                raise InvalidReviewPlanError(
                    f"El origen '{source_id}' declaró un reviewer_id vacío."
                )
            if normalized_reviewer_id not in origins_by_reviewer:
                ordered_ids.append(normalized_reviewer_id)
                origins_by_reviewer[normalized_reviewer_id] = []
                seen_origins[normalized_reviewer_id] = set()
            origin = ReviewRequirementOrigin(
                source_kind=source_kind,
                source_id=source_id,
                reason=_REASON_BY_SOURCE[source_kind],
            )
            origin_key = (origin.source_kind, origin.source_id, origin.reason)
            if origin_key in seen_origins[normalized_reviewer_id]:
                return
            seen_origins[normalized_reviewer_id].add(origin_key)
            origins_by_reviewer[normalized_reviewer_id].append(origin)

        project = activated.project_composition.project
        for reviewer_id in project.plugins.reviewers:
            add_requirement(reviewer_id, "project", project.id)

        for plugin in activated.activated_plugins:
            if plugin.genre is None:
                continue
            for reviewer_id in plugin.genre.required_reviewers:
                add_requirement(reviewer_id, "genre", plugin.id)

        for plugin in activated.activated_plugins:
            if plugin.workflow is None:
                continue
            for reviewer_id in plugin.workflow.required_reviewers:
                add_requirement(reviewer_id, "workflow", plugin.id)

        reconciled_ids = tuple(ordered_ids)
        if reconciled_ids != activated.required_reviewer_ids:
            raise InvalidReviewPlanError(
                "ActivatedProjectComposition y ReviewPlanComposer discrepan sobre "
                "los reviewers requeridos o su orden."
            )
        if not reconciled_ids:
            raise InvalidReviewPlanError(
                f"El proyecto '{project.id}' no declara reviewers para componer un plan."
            )

        entries: List[ReviewPlanEntry] = []
        for order, reviewer_id in enumerate(reconciled_ids, start=1):
            activated_reviewer = self._required_activated_reviewer(
                activated, reviewer_id
            )
            behavior = activated_reviewer.reviewer
            if behavior is None:
                raise InvalidReviewPlanError(
                    f"El plugin '{reviewer_id}' no conserva ReviewerBehavior activado."
                )
            reviewer = self.reviewer_registry.build(
                behavior.implementation,
                reviewer_id,
                behavior,
            )
            entries.append(
                ReviewPlanEntry(
                    order=order,
                    reviewer_id=reviewer_id,
                    implementation_id=behavior.implementation,
                    configuration_json=self._configuration_json(behavior),
                    nature=behavior.nature,
                    origins=tuple(origins_by_reviewer[reviewer_id]),
                    reviewer=reviewer,
                )
            )

        return ReviewPlan(project_id=project.id, entries=tuple(entries))

    @staticmethod
    def _required_activated_reviewer(
        activated: ActivatedProjectComposition,
        reviewer_id: str,
    ) -> ActivatedPlugin:
        try:
            plugin = activated.get(reviewer_id)
        except PluginNotFoundError as exc:
            raise InvalidReviewPlanError(
                f"El reviewer requerido '{reviewer_id}' no está activado."
            ) from exc
        if plugin.type != "reviewer" or plugin.reviewer is None:
            raise InvalidReviewPlanError(
                f"El plugin activado '{reviewer_id}' no es un reviewer ejecutable."
            )
        return plugin

    @staticmethod
    def _configuration_json(behavior: ReviewerBehavior) -> str:
        configuration = behavior.model_dump(
            mode="json",
            exclude={"implementation", "nature"},
        )
        return json.dumps(
            configuration,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
