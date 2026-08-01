"""Runtime mínimo para activar plugins validados y exponer comportamiento ejecutable."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from pydantic import BaseModel, Field, ValidationError, field_validator

from editorial_tres.exceptions import InvalidManifestError, PluginNotFoundError
from editorial_tres.domain.reviews import FindingSeverity, Reviewer
from editorial_tres.plugin_contract import PluginManifest


class EditorialBehavior(BaseModel):
    """Comportamiento ejecutable declarado por un plugin editorial."""

    constitution: List[str] = Field(min_length=1)
    policies: List[str] = Field(default_factory=list)
    terminology: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    approval_criteria: List[str] = Field(default_factory=list)
    source_standards: List[str] = Field(default_factory=list)
    institutional_identity: List[str] = Field(default_factory=list)
    branding: List[str] = Field(default_factory=list)

    @field_validator(
        "constitution",
        "policies",
        "terminology",
        "roles",
        "approval_criteria",
        "source_standards",
        "institutional_identity",
        "branding",
    )
    @classmethod
    def validate_unique_nonempty_items(cls, values: List[str]) -> List[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Las declaraciones editoriales no pueden repetirse dentro de la misma categoría.")
        return cleaned


class GenreBehavior(BaseModel):
    """Comportamiento ejecutable declarado por un plugin de género."""

    unit_types: List[str] = Field(min_length=1)
    structures: List[str] = Field(default_factory=list)
    default_passes: List[str] = Field(default_factory=list)
    required_reviewers: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    compilation_strategy: str

    @field_validator("unit_types")
    @classmethod
    def validate_unit_types(cls, values: List[str]) -> List[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if not cleaned:
            raise ValueError("Un plugin de género debe declarar al menos un tipo de unidad.")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Los tipos de unidad de un género no pueden repetirse.")
        return cleaned

    @field_validator("compilation_strategy")
    @classmethod
    def validate_compilation_strategy(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La estrategia de compilación del género es obligatoria.")
        return value


class StyleBehavior(BaseModel):
    """Comportamiento ejecutable declarado por un plugin de estilo."""

    principles: List[str] = Field(min_length=1)
    rhythm: List[str] = Field(default_factory=list)
    sentence_profile: List[str] = Field(default_factory=list)
    lexical_preferences: List[str] = Field(default_factory=list)
    rhetorical_devices: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)
    positive_examples: List[str] = Field(default_factory=list)
    negative_examples: List[str] = Field(default_factory=list)

    @field_validator("principles", "rhythm", "sentence_profile", "lexical_preferences", "rhetorical_devices", "avoid")
    @classmethod
    def validate_unique_nonempty_items(cls, values: List[str]) -> List[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Las declaraciones de estilo no pueden repetirse dentro de la misma categoría.")
        return cleaned


class AuthorVoiceBehavior(BaseModel):
    """Comportamiento ejecutable declarado por un plugin de voz autoral."""

    profile: List[str] = Field(min_length=1)
    patterns: List[str] = Field(default_factory=list)
    anti_patterns: List[str] = Field(default_factory=list)
    approved_examples: List[str] = Field(default_factory=list)
    rejected_examples: List[str] = Field(default_factory=list)
    drift_signals: List[str] = Field(default_factory=list)
    variation_rules: List[str] = Field(default_factory=list)

    @field_validator("profile", "patterns", "anti_patterns", "approved_examples", "rejected_examples", "drift_signals", "variation_rules")
    @classmethod
    def validate_unique_nonempty_items(cls, values: List[str]) -> List[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Las declaraciones de voz no pueden repetirse dentro de la misma categoría.")
        return cleaned


class NarratorBehavior(BaseModel):
    """Comportamiento ejecutable declarado por un plugin de narrador."""

    persona: str
    distance: str
    focalization: str
    reliability: str
    temporality: str
    reader_relation: List[str] = Field(default_factory=list)
    interiority_access: List[str] = Field(default_factory=list)
    knowledge_restrictions: List[str] = Field(default_factory=list)

    @field_validator("persona", "distance", "focalization", "reliability", "temporality")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Las propiedades nucleares del narrador no pueden estar vacías.")
        return value

    @field_validator("reader_relation", "interiority_access", "knowledge_restrictions")
    @classmethod
    def validate_unique_nonempty_items(cls, values: List[str]) -> List[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Las declaraciones del narrador no pueden repetirse dentro de la misma categoría.")
        return cleaned


class ReviewerBehavior(BaseModel):
    """Comportamiento ejecutable declarado por un plugin reviewer."""

    finding_type: str
    scope: List[str] = Field(min_length=1)
    severity: FindingSeverity
    evidence_format: str
    nature: str
    recommendation_policy: str
    implementation: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "finding_type",
        "severity",
        "evidence_format",
        "nature",
        "recommendation_policy",
        "implementation",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La declaración del reviewer es obligatoria.")
        return normalized

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, values: List[str]) -> List[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if not cleaned:
            raise ValueError("Un reviewer debe declarar al menos un scope.")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Los scopes de un reviewer no pueden repetirse.")
        return cleaned


class ResearchMethodBehavior(BaseModel):
    """Comportamiento ejecutable declarado por un método de investigación."""

    source_discovery: List[str] = Field(min_length=1)
    evidence_hierarchy: List[str] = Field(default_factory=list)
    credibility_checks: List[str] = Field(default_factory=list)
    extraction_rules: List[str] = Field(default_factory=list)
    contradiction_handling: List[str] = Field(default_factory=list)
    citation_policy: List[str] = Field(default_factory=list)
    update_policy: List[str] = Field(default_factory=list)


class VisualTypeBehavior(BaseModel):
    """Gramática ejecutable de un tipo de activo visual."""

    asset_kind: str
    semantic_inputs: List[str] = Field(min_length=1)
    constraints: List[str] = Field(default_factory=list)
    output_kind: str
    deterministic_composition: bool = True

    @field_validator("asset_kind", "output_kind")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El tipo visual debe declarar asset_kind y output_kind.")
        return normalized


class VisualStyleBehavior(BaseModel):
    """Tratamiento visual enchufable sin decidir el contenido semántico."""

    palette: List[str] = Field(default_factory=list)
    textures: List[str] = Field(default_factory=list)
    lighting: List[str] = Field(default_factory=list)
    iconography: List[str] = Field(default_factory=list)
    shape_language: List[str] = Field(default_factory=list)
    composition: List[str] = Field(min_length=1)
    character_treatment: List[str] = Field(default_factory=list)
    series_consistency: List[str] = Field(default_factory=list)
    prohibitions: List[str] = Field(default_factory=list)


class WorkflowBehavior(BaseModel):
    """Secuencia editorial ejecutable declarada por un workflow plugin."""

    stages: List[str] = Field(min_length=1)
    required_reviewers: List[str] = Field(default_factory=list)
    gates: List[str] = Field(default_factory=list)
    retry_policy: List[str] = Field(default_factory=list)
    human_escalation: List[str] = Field(default_factory=list)
    completion_criteria: List[str] = Field(min_length=1)


class OutputBehavior(BaseModel):
    """Contrato ejecutable de compilación hacia una salida concreta."""

    format: str
    required_inputs: List[str] = Field(min_length=1)
    artifacts: List[str] = Field(min_length=1)
    validation_rules: List[str] = Field(default_factory=list)
    preserves_canonical_work: bool = True

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Un output plugin debe declarar su formato.")
        return normalized


class ActivatedPlugin(BaseModel):
    """Vista runtime de un plugin activado."""

    id: str
    version: str
    type: str
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)
    schemas: List[str] = Field(default_factory=list)
    prompts: List[str] = Field(default_factory=list)
    reviewers: List[str] = Field(default_factory=list)
    passes: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    deterministic: bool | None = None
    risks: List[str] = Field(default_factory=list)
    genre: GenreBehavior | None = None
    style: StyleBehavior | None = None
    voice: AuthorVoiceBehavior | None = None
    narrator: NarratorBehavior | None = None
    reviewer: ReviewerBehavior | None = None
    editorial: EditorialBehavior | None = None
    research_method: ResearchMethodBehavior | None = None
    visual_type: VisualTypeBehavior | None = None
    visual_style: VisualStyleBehavior | None = None
    workflow: WorkflowBehavior | None = None
    output: OutputBehavior | None = None


class PluginRuntime:
    """Activa y desactiva plugins sin permitir que el manifiesto sustituya al kernel."""

    def __init__(self) -> None:
        self._active: Dict[str, ActivatedPlugin] = {}

    def activate(self, manifest: PluginManifest) -> ActivatedPlugin:
        if manifest.type == "editorial":
            try:
                editorial_behavior = EditorialBehavior.model_validate(manifest.behavior)
            except ValidationError as exc:
                raise InvalidManifestError(
                    f"El plugin editorial '{manifest.id}' no declara un behavior ejecutable válido: {exc}"
                ) from exc
        else:
            editorial_behavior = None

        if manifest.type == "genre":
            try:
                genre_behavior = GenreBehavior.model_validate(manifest.behavior)
            except ValidationError as exc:
                raise InvalidManifestError(
                    f"El plugin de género '{manifest.id}' no declara un behavior ejecutable válido: {exc}"
                ) from exc
        else:
            genre_behavior = None

        if manifest.type == "style":
            try:
                style_behavior = StyleBehavior.model_validate(manifest.behavior)
            except ValidationError as exc:
                raise InvalidManifestError(
                    f"El plugin de estilo '{manifest.id}' no declara un behavior ejecutable válido: {exc}"
                ) from exc
        else:
            style_behavior = None

        if manifest.type == "voice":
            try:
                voice_behavior = AuthorVoiceBehavior.model_validate(manifest.behavior)
            except ValidationError as exc:
                raise InvalidManifestError(
                    f"El plugin de voz '{manifest.id}' no declara un behavior ejecutable válido: {exc}"
                ) from exc
        else:
            voice_behavior = None

        if manifest.type == "narrator":
            try:
                narrator_behavior = NarratorBehavior.model_validate(manifest.behavior)
            except ValidationError as exc:
                raise InvalidManifestError(
                    f"El plugin de narrador '{manifest.id}' no declara un behavior ejecutable válido: {exc}"
                ) from exc
        else:
            narrator_behavior = None

        if manifest.type == "reviewer":
            try:
                reviewer_behavior = ReviewerBehavior.model_validate(manifest.behavior)
            except ValidationError as exc:
                raise InvalidManifestError(
                    f"El plugin reviewer '{manifest.id}' no declara un behavior ejecutable válido: {exc}"
                ) from exc
        else:
            reviewer_behavior = None

        if manifest.type == "research_method":
            try:
                research_method_behavior = ResearchMethodBehavior.model_validate(manifest.behavior)
            except ValidationError as exc:
                raise InvalidManifestError(
                    f"El método de investigación '{manifest.id}' no declara un behavior ejecutable válido: {exc}"
                ) from exc
        else:
            research_method_behavior = None

        if manifest.type == "visual_type":
            try:
                visual_type_behavior = VisualTypeBehavior.model_validate(manifest.behavior)
            except ValidationError as exc:
                raise InvalidManifestError(
                    f"El tipo visual '{manifest.id}' no declara un behavior ejecutable válido: {exc}"
                ) from exc
        else:
            visual_type_behavior = None

        if manifest.type == "visual_style":
            try:
                visual_style_behavior = VisualStyleBehavior.model_validate(manifest.behavior)
            except ValidationError as exc:
                raise InvalidManifestError(
                    f"El estilo visual '{manifest.id}' no declara un behavior ejecutable válido: {exc}"
                ) from exc
        else:
            visual_style_behavior = None

        if manifest.type == "workflow":
            try:
                workflow_behavior = WorkflowBehavior.model_validate(manifest.behavior)
            except ValidationError as exc:
                raise InvalidManifestError(
                    f"El workflow '{manifest.id}' no declara un behavior ejecutable válido: {exc}"
                ) from exc
        else:
            workflow_behavior = None

        if manifest.type == "output":
            try:
                output_behavior = OutputBehavior.model_validate(manifest.behavior)
            except ValidationError as exc:
                raise InvalidManifestError(
                    f"El output '{manifest.id}' no declara un behavior ejecutable válido: {exc}"
                ) from exc
        else:
            output_behavior = None

        activated = ActivatedPlugin(
            id=manifest.id,
            version=manifest.version,
            type=manifest.type,
            inputs=manifest.inputs,
            outputs=manifest.outputs,
            rules=manifest.rules,
            schemas=manifest.schemas,
            prompts=manifest.prompts,
            reviewers=manifest.reviewers,
            passes=manifest.passes,
            tools=manifest.tools,
            models=manifest.models,
            capabilities=manifest.capabilities,
            deterministic=manifest.deterministic,
            risks=manifest.risks,
            genre=genre_behavior,
            style=style_behavior,
            voice=voice_behavior,
            narrator=narrator_behavior,
            reviewer=reviewer_behavior,
            editorial=editorial_behavior,
            research_method=research_method_behavior,
            visual_type=visual_type_behavior,
            visual_style=visual_style_behavior,
            workflow=workflow_behavior,
            output=output_behavior,
        )
        self._active[manifest.id] = activated
        return activated

    def activate_all(self, manifests: Iterable[PluginManifest]) -> List[ActivatedPlugin]:
        return [self.activate(manifest) for manifest in manifests]

    def deactivate(self, plugin_id: str) -> None:
        if plugin_id not in self._active:
            raise PluginNotFoundError(f"El plugin activo '{plugin_id}' no fue encontrado.")
        del self._active[plugin_id]

    def get(self, plugin_id: str) -> ActivatedPlugin:
        if plugin_id not in self._active:
            raise PluginNotFoundError(f"El plugin activo '{plugin_id}' no fue encontrado.")
        return self._active[plugin_id]

    def build_reviewer(self, plugin_id: str) -> Reviewer:
        activated = self.get(plugin_id)
        if activated.type != "reviewer" or activated.reviewer is None:
            raise InvalidManifestError(f"El plugin '{plugin_id}' no es un reviewer ejecutable.")

        from editorial_tres.capability_factory import default_reviewer_registry

        return default_reviewer_registry().build(
            activated.reviewer.implementation, plugin_id, activated.reviewer
        )

    def list_active(self) -> List[ActivatedPlugin]:
        return [self._active[plugin_id] for plugin_id in sorted(self._active)]
