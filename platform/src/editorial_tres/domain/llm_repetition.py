"""LLM-assisted discovery of cross-block literary repetition.

The LLM proposes semantic clusters. TR.ES validates every quoted occurrence against
an exact manuscript block before turning it into a ReviewFinding. The model never
mutates the Work and never decides authorial intent.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal, Mapping, Protocol, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from editorial_tres.domain.reviews import FindingSeverity, ReviewFinding, Reviewer
from editorial_tres.domain.work import Work


RepetitionCandidateType = Literal[
    "literal_repetition",
    "near_duplicate",
    "semantic_echo",
    "recurring_image",
    "narrative_motif",
    "character_catchphrase",
    "possible_redundancy",
    "requires_context",
]


class StructuredLLMPort(Protocol):
    """Provider-neutral port for schema-constrained JSON generation."""

    provider_id: str
    model_id: str

    def generate_json(
        self,
        *,
        prompt: str,
        schema: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Return one JSON object that conforms to ``schema``."""


class LLMRepetitionOccurrence(BaseModel):
    block_id: str
    quote: str
    local_reason: str

    model_config = {"frozen": True}

    @field_validator("block_id", "quote", "local_reason")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Cada aparición requiere bloque, cita y explicación.")
        return normalized


class LLMRepetitionCluster(BaseModel):
    cluster_id: str
    candidate_type: RepetitionCandidateType
    canonical_label: str
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)
    occurrences: Tuple[LLMRepetitionOccurrence, ...] = Field(min_length=2)

    model_config = {"frozen": True}

    @field_validator("cluster_id", "canonical_label", "explanation")
    @classmethod
    def _cluster_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("El cluster requiere identidad, etiqueta y explicación.")
        return normalized

    @model_validator(mode="after")
    def _distinct_blocks(self) -> "LLMRepetitionCluster":
        block_ids = tuple(item.block_id for item in self.occurrences)
        if len(set(block_ids)) < 2:
            raise ValueError("Una reiteración global debe abarcar al menos dos bloques.")
        occurrence_keys = tuple((item.block_id, item.quote) for item in self.occurrences)
        if len(occurrence_keys) != len(set(occurrence_keys)):
            raise ValueError("El cluster no puede duplicar la misma aparición.")
        return self


class LLMRepetitionAnalysis(BaseModel):
    clusters: Tuple[LLMRepetitionCluster, ...] = ()

    model_config = {"frozen": True}

    @field_validator("clusters")
    @classmethod
    def _unique_cluster_ids(
        cls, values: Tuple[LLMRepetitionCluster, ...]
    ) -> Tuple[LLMRepetitionCluster, ...]:
        ids = tuple(item.cluster_id for item in values)
        if len(ids) != len(set(ids)):
            raise ValueError("El análisis no puede duplicar cluster_id.")
        return values


class LLMGlobalRepetitionReviewer(Reviewer):
    """Discover semantically related recurrences across manuscript blocks with an LLM."""

    reviewer_id: str

    def __init__(
        self,
        *,
        reviewer_id: str,
        llm: StructuredLLMPort,
        minimum_confidence: float = 0.55,
        severity: FindingSeverity = "warning",
        max_blocks: int = 250,
        max_characters: int = 300_000,
    ) -> None:
        normalized_id = reviewer_id.strip() if reviewer_id else ""
        if not normalized_id:
            raise ValueError("El reviewer_id es obligatorio.")
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence debe estar entre 0 y 1.")
        if max_blocks < 2:
            raise ValueError("max_blocks debe admitir al menos dos bloques.")
        if max_characters < 1_000:
            raise ValueError("max_characters es demasiado bajo para revisión global.")
        self.reviewer_id = normalized_id
        self._llm = llm
        self.minimum_confidence = minimum_confidence
        self.severity = severity
        self.max_blocks = max_blocks
        self.max_characters = max_characters

    @property
    def llm_provider_id(self) -> str:
        return self._llm.provider_id

    @property
    def llm_model_id(self) -> str:
        return self._llm.model_id

    @staticmethod
    def output_schema() -> Mapping[str, Any]:
        return LLMRepetitionAnalysis.model_json_schema()

    def review(self, work: Work, branch: str = "main") -> Tuple[ReviewFinding, ...]:
        normalized_branch = branch.strip() if branch else ""
        if not normalized_branch:
            raise ValueError("La rama no puede estar vacía.")

        blocks = tuple(work.expression_graph.get_all_blocks())
        if len(blocks) < 2:
            return ()
        if len(blocks) > self.max_blocks:
            raise ValueError(
                f"La revisión LLM admite hasta {self.max_blocks} bloques por ejecución; "
                "se requiere fragmentación gobernada."
            )
        total_characters = sum(len(block.content) for block in blocks)
        if total_characters > self.max_characters:
            raise ValueError(
                f"La revisión LLM admite hasta {self.max_characters} caracteres por ejecución; "
                "se requiere fragmentación gobernada."
            )

        prompt = self._build_prompt(work, blocks)
        raw = self._llm.generate_json(prompt=prompt, schema=self.output_schema())
        analysis = LLMRepetitionAnalysis.model_validate(raw)
        block_by_id = {block.id: block for block in blocks}
        order = {block.id: index for index, block in enumerate(blocks)}

        findings: list[ReviewFinding] = []
        for cluster in analysis.clusters:
            if cluster.confidence < self.minimum_confidence:
                continue

            validated_occurrences: list[LLMRepetitionOccurrence] = []
            for occurrence in cluster.occurrences:
                block = block_by_id.get(occurrence.block_id)
                if block is None:
                    raise ValueError(
                        f"El LLM citó un bloque inexistente: '{occurrence.block_id}'."
                    )
                if occurrence.quote not in block.content:
                    raise ValueError(
                        f"El LLM produjo una cita no verificable en '{occurrence.block_id}'."
                    )
                validated_occurrences.append(occurrence)

            target_ids = tuple(
                sorted(
                    {item.block_id for item in validated_occurrences},
                    key=order.__getitem__,
                )
            )
            if len(target_ids) < 2:
                continue

            evidence_payload = {
                "provider": self._llm.provider_id,
                "model": self._llm.model_id,
                "candidate_type": cluster.candidate_type,
                "canonical_label": cluster.canonical_label,
                "confidence": cluster.confidence,
                "occurrences": [item.model_dump(mode="json") for item in validated_occurrences],
            }
            evidence = json.dumps(
                evidence_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            fingerprint = "|".join(
                (
                    self.reviewer_id,
                    self._llm.provider_id,
                    self._llm.model_id,
                    work.tenant_id.value,
                    work.editorial_id.value,
                    work.work_id.value,
                    normalized_branch,
                    str(work.manuscript_version),
                    cluster.candidate_type,
                    cluster.canonical_label,
                    evidence,
                )
            )
            findings.append(
                ReviewFinding(
                    finding_id=f"finding-{hashlib.sha256(fingerprint.encode()).hexdigest()[:16]}",
                    reviewer_id=self.reviewer_id,
                    finding_type="structure.llm_cross_block_repetition",
                    tenant_id=work.tenant_id,
                    editorial_id=work.editorial_id,
                    work_id=work.work_id,
                    branch=normalized_branch,
                    source_version=work.manuscript_version,
                    target_id=target_ids[0],
                    related_target_ids=target_ids,
                    severity=self.severity,
                    evidence=evidence,
                    description=(
                        f"El LLM agrupó {len(validated_occurrences)} apariciones en "
                        f"{len(target_ids)} bloques como '{cluster.candidate_type}': "
                        f"{cluster.explanation}"
                    ),
                    recommended_action=(
                        "Revisión humana obligatoria: clasificar si se trata de símbolo, motivo, "
                        "eco deliberado, latiguillo, redundancia o coincidencia irrelevante. "
                        "No aplicar cambios directamente desde este hallazgo."
                    ),
                )
            )

        return tuple(findings)

    def _build_prompt(self, work: Work, blocks: tuple[Any, ...]) -> str:
        serialized_blocks = "\n\n".join(
            f"<block id={json.dumps(block.id, ensure_ascii=False)}>\n"
            f"{block.content}\n"
            "</block>"
            for block in blocks
        )
        return (
            "Sos un revisor literario asistido. Analizá el manuscrito y descubrí reiteraciones "
            "relevantes distribuidas entre bloques distintos. Incluí repeticiones literales, "
            "casi duplicados, ecos semánticos, imágenes recurrentes, motivos narrativos, "
            "latiguillos de personaje y posibles redundancias.\n\n"
            "REGLAS OBLIGATORIAS:\n"
            "1. No corrijas ni reescribas el manuscrito.\n"
            "2. No afirmes intención autoral como un hecho.\n"
            "3. Cada cluster debe abarcar al menos dos block_id distintos.\n"
            "4. Cada quote debe copiarse literalmente del bloque indicado.\n"
            "5. Omití nombres propios repetidos y vocabulario funcional salvo que formen un "
            "patrón literario significativo.\n"
            "6. Priorizá pocos candidatos útiles antes que coincidencias triviales.\n"
            "7. Usá exclusivamente los candidate_type permitidos por el esquema.\n"
            "8. La salida debe respetar exactamente el JSON Schema recibido.\n\n"
            f"OBRA: {work.title}\nIDIOMA: {work.language}\n"
            f"VERSIÓN MATERIAL: {work.manuscript_version}\n\n"
            f"{serialized_blocks}"
        )
