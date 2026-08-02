"""Dependency-free Spanish orthographic and orthotypographic findings."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from editorial_tres.domain.reviews import (
    EditorialCriterion,
    ReplacementProposal,
    ReviewFinding,
    TextualFindingBinding,
)
from editorial_tres.domain.text_analysis import TextAnalysisSnapshot, TextSpan


RuleKey = Literal[
    "repeated_horizontal_whitespace",
    "space_before_closing_punctuation",
    "missing_space_after_medial_punctuation",
    "angle_quote_inner_whitespace",
]


class OrthotypographicRule(BaseModel):
    """Immutable metadata and criterion for one deterministic rule."""

    rule_key: RuleKey
    finding_type: str
    criterion: EditorialCriterion
    description: str
    rationale: str

    model_config = {"frozen": True}

    @field_validator("finding_type", "description", "rationale")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La regla ortotipográfica requiere metadatos completos.")
        return normalized


class LexicalCorrection(BaseModel):
    """One governed exact-token correction, suitable for Archivo Oro."""

    source_token: str
    replacement_text: str
    rationale: str
    criterion: EditorialCriterion

    model_config = {"frozen": True}

    @field_validator("source_token", "replacement_text", "rationale")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La corrección léxica requiere valores no vacíos.")
        return normalized

    @model_validator(mode="after")
    def _exact_effective_token_replacement(self) -> "LexicalCorrection":
        if any(character.isspace() for character in self.source_token):
            raise ValueError(
                "La fuente de una corrección léxica debe ser un único token exacto."
            )
        if self.source_token == self.replacement_text:
            raise ValueError("La corrección léxica debe producir un cambio efectivo.")
        return self


class ContextualAccentCorrection(BaseModel):
    """One exact-token accent correction guarded by adjacent sentence tokens."""

    source_token: str
    replacement_text: str
    left_anchor_tokens: tuple[str, ...] = ()
    right_anchor_tokens: tuple[str, ...] = ()
    rationale: str
    criterion: EditorialCriterion

    model_config = {"frozen": True}

    @field_validator("source_token", "replacement_text", "rationale")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(
                "La corrección contextual requiere valores no vacíos."
            )
        return normalized

    @field_validator("left_anchor_tokens", "right_anchor_tokens")
    @classmethod
    def _exact_anchor_tokens(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(token.strip() for token in value)
        if any(
            not token or any(character.isspace() for character in token)
            for token in normalized
        ):
            raise ValueError(
                "Cada ancla contextual debe ser un token exacto no vacío."
            )
        return normalized

    @model_validator(mode="after")
    def _effective_bounded_context(self) -> "ContextualAccentCorrection":
        if any(character.isspace() for character in self.source_token):
            raise ValueError(
                "La fuente contextual debe ser un único token exacto."
            )
        if any(character.isspace() for character in self.replacement_text):
            raise ValueError(
                "El reemplazo contextual debe ser un único token exacto."
            )
        if self.source_token == self.replacement_text:
            raise ValueError(
                "La corrección contextual debe producir un cambio efectivo."
            )
        if not self.left_anchor_tokens and not self.right_anchor_tokens:
            raise ValueError(
                "La corrección contextual requiere al menos un ancla declarada."
            )
        return self


BUILTIN_ORTHOTYPOGRAPHIC_RULES: tuple[OrthotypographicRule, ...] = (
    OrthotypographicRule(
        rule_key="repeated_horizontal_whitespace",
        finding_type="orthotypography.repeated_horizontal_whitespace",
        criterion=EditorialCriterion(
            criterion_id="es.orthotypography.horizontal-whitespace",
            criterion_version="1.0.0",
        ),
        description="La oración contiene espacios horizontales repetidos.",
        rationale="Sustituir la secuencia horizontal repetida por un solo espacio.",
    ),
    OrthotypographicRule(
        rule_key="space_before_closing_punctuation",
        finding_type="orthotypography.space_before_closing_punctuation",
        criterion=EditorialCriterion(
            criterion_id="es.orthotypography.space-before-closing-punctuation",
            criterion_version="1.0.0",
        ),
        description="Hay un espacio impropio antes de un signo de puntuación.",
        rationale="Suprimir el espacio que precede al signo de cierre.",
    ),
    OrthotypographicRule(
        rule_key="missing_space_after_medial_punctuation",
        finding_type="orthotypography.missing_space_after_medial_punctuation",
        criterion=EditorialCriterion(
            criterion_id="es.orthotypography.missing-space-after-medial-punctuation",
            criterion_version="1.0.0",
        ),
        description="Falta un espacio después de un signo de puntuación interior.",
        rationale="Agregar un espacio entre el signo interior y la palabra siguiente.",
    ),
    OrthotypographicRule(
        rule_key="angle_quote_inner_whitespace",
        finding_type="orthotypography.angle_quote_inner_whitespace",
        criterion=EditorialCriterion(
            criterion_id="es.orthotypography.angle-quote-inner-whitespace",
            criterion_version="1.0.0",
        ),
        description="Las comillas angulares contienen un espacio interior impropio.",
        rationale="Suprimir el espacio contiguo al interior de las comillas angulares.",
    ),
)


def _correct_sentence(rule_key: RuleKey, text: str) -> str:
    if rule_key == "repeated_horizontal_whitespace":
        return re.sub(r"(?<=\S)[ \t]{2,}(?=\S)", " ", text)
    if rule_key == "space_before_closing_punctuation":
        return re.sub(r"[ \t]+(?=[,.;:!?…])", "", text)
    if rule_key == "missing_space_after_medial_punctuation":
        return re.sub(r"([,;:])(?=[^\W\d_])", r"\1 ", text)
    if rule_key == "angle_quote_inner_whitespace":
        without_opening_space = re.sub(r"«[ \t]+", "«", text)
        return re.sub(r"[ \t]+»", "»", without_opening_space)
    raise AssertionError(f"Regla ortotipográfica desconocida: {rule_key}")


def _matches_adjacent_context(
    *,
    tokens: tuple[TextSpan, ...],
    token_index: int,
    correction: ContextualAccentCorrection,
) -> bool:
    left_size = len(correction.left_anchor_tokens)
    right_size = len(correction.right_anchor_tokens)
    if token_index < left_size or token_index + right_size >= len(tokens):
        return False

    left = tuple(
        token.evidence for token in tokens[token_index - left_size : token_index]
    )
    right = tuple(
        token.evidence
        for token in tokens[token_index + 1 : token_index + right_size + 1]
    )
    return (
        left == correction.left_anchor_tokens
        and right == correction.right_anchor_tokens
    )


class SpanishOrthotypographicCorrector(BaseModel):
    """Emit traceable proposals without mutating or patching the manuscript."""

    lexical_corrections: tuple[LexicalCorrection, ...] = ()
    contextual_accent_corrections: tuple[ContextualAccentCorrection, ...] = ()

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def _unique_registry(self) -> "SpanishOrthotypographicCorrector":
        sources = tuple(item.source_token for item in self.lexical_corrections)
        if len(sources) != len(set(sources)):
            raise ValueError(
                "Las correcciones léxicas no pueden repetir el token fuente exacto."
            )

        contextual_signatures = tuple(
            (
                item.source_token,
                item.left_anchor_tokens,
                item.right_anchor_tokens,
            )
            for item in self.contextual_accent_corrections
        )
        if len(contextual_signatures) != len(set(contextual_signatures)):
            raise ValueError(
                "Las correcciones contextuales no pueden repetir fuente y anclas."
            )
        contextual_sources = {
            item.source_token for item in self.contextual_accent_corrections
        }
        if set(sources) & contextual_sources:
            raise ValueError(
                "Un token fuente no puede tener corrección léxica global y contextual."
            )

        criteria = (
            tuple(rule.criterion for rule in BUILTIN_ORTHOTYPOGRAPHIC_RULES)
            + tuple(item.criterion for item in self.lexical_corrections)
            + tuple(
                item.criterion for item in self.contextual_accent_corrections
            )
        )
        criterion_ids = tuple(item.criterion_id for item in criteria)
        if len(criterion_ids) != len(set(criterion_ids)):
            raise ValueError(
                "El registro no puede contener identidades de criterio duplicadas."
            )
        versioned_ids = tuple(
            (item.criterion_id, item.criterion_version) for item in criteria
        )
        if len(versioned_ids) != len(set(versioned_ids)):
            raise ValueError(
                "El registro no puede contener criterios versionados duplicados."
            )
        return self

    @property
    def rule_registry(self) -> tuple[EditorialCriterion, ...]:
        """Expose the immutable, ordered criterion registry."""

        return (
            tuple(rule.criterion for rule in BUILTIN_ORTHOTYPOGRAPHIC_RULES)
            + tuple(item.criterion for item in self.lexical_corrections)
            + tuple(
                item.criterion for item in self.contextual_accent_corrections
            )
        )

    def analyze(
        self, snapshot: TextAnalysisSnapshot
    ) -> tuple[ReviewFinding, ...]:
        """Analyze one immutable PT-0 snapshot in canonical reading order."""

        ordered_findings: list[tuple[int, int, str, ReviewFinding]] = []
        for block_ordinal, block in enumerate(snapshot.blocks):
            for sentence in block.sentences:
                for rule in BUILTIN_ORTHOTYPOGRAPHIC_RULES:
                    if rule.rule_key == "angle_quote_inner_whitespace":
                        continue
                    replacement = _correct_sentence(
                        rule.rule_key, sentence.evidence
                    )
                    if replacement == sentence.evidence:
                        continue
                    finding = self._finding(
                        snapshot=snapshot,
                        span=sentence,
                        reviewer_id="proofreader.spanish-orthotypographic.v1",
                        finding_type=rule.finding_type,
                        criterion=rule.criterion,
                        description=rule.description,
                        rationale=rule.rationale,
                        replacement_text=replacement,
                    )
                    ordered_findings.append(
                        (
                            block_ordinal,
                            sentence.start,
                            rule.criterion.criterion_id,
                            finding,
                        )
                    )

            angle_quote_rule = next(
                rule
                for rule in BUILTIN_ORTHOTYPOGRAPHIC_RULES
                if rule.rule_key == "angle_quote_inner_whitespace"
            )
            for paragraph in block.paragraphs:
                replacement = _correct_sentence(
                    angle_quote_rule.rule_key, paragraph.evidence
                )
                if replacement == paragraph.evidence:
                    continue
                finding = self._finding(
                    snapshot=snapshot,
                    span=paragraph,
                    reviewer_id="proofreader.spanish-orthotypographic.v1",
                    finding_type=angle_quote_rule.finding_type,
                    criterion=angle_quote_rule.criterion,
                    description=angle_quote_rule.description,
                    rationale=angle_quote_rule.rationale,
                    replacement_text=replacement,
                )
                ordered_findings.append(
                    (
                        block_ordinal,
                        paragraph.start,
                        angle_quote_rule.criterion.criterion_id,
                        finding,
                    )
                )

            for token in block.tokens:
                for correction in self.lexical_corrections:
                    if token.evidence != correction.source_token:
                        continue
                    finding = self._finding(
                        snapshot=snapshot,
                        span=token,
                        reviewer_id="proofreader.spanish-lexical.v1",
                        finding_type="orthography.exact_token_correction",
                        criterion=correction.criterion,
                        description=(
                            "El token coincide con una corrección léxica "
                            "gobernada."
                        ),
                        rationale=correction.rationale,
                        replacement_text=correction.replacement_text,
                    )
                    ordered_findings.append(
                        (
                            block_ordinal,
                            token.start,
                            correction.criterion.criterion_id,
                            finding,
                        )
                    )

            for sentence in block.sentences:
                sentence_tokens = tuple(
                    token
                    for token in block.tokens
                    if sentence.start <= token.start
                    and token.end <= sentence.end
                )
                for token_index, token in enumerate(sentence_tokens):
                    for correction in self.contextual_accent_corrections:
                        if token.evidence != correction.source_token:
                            continue
                        if not _matches_adjacent_context(
                            tokens=sentence_tokens,
                            token_index=token_index,
                            correction=correction,
                        ):
                            continue
                        finding = self._finding(
                            snapshot=snapshot,
                            span=token,
                            reviewer_id=(
                                "proofreader.spanish-contextual-accent.v1"
                            ),
                            finding_type=(
                                "orthography.contextual_accent_correction"
                            ),
                            criterion=correction.criterion,
                            description=(
                                "El token coincide con una corrección de tilde "
                                "y con sus anclas contextuales gobernadas."
                            ),
                            rationale=correction.rationale,
                            replacement_text=correction.replacement_text,
                        )
                        ordered_findings.append(
                            (
                                block_ordinal,
                                token.start,
                                correction.criterion.criterion_id,
                                finding,
                            )
                        )

        ordered_findings.sort(key=lambda item: item[:3])
        return tuple(item[3] for item in ordered_findings)

    @staticmethod
    def _finding(
        *,
        snapshot: TextAnalysisSnapshot,
        span: TextSpan,
        reviewer_id: str,
        finding_type: str,
        criterion: EditorialCriterion,
        description: str,
        rationale: str,
        replacement_text: str,
    ) -> ReviewFinding:
        binding = TextualFindingBinding(snapshot=snapshot, span=span)
        return ReviewFinding.diagnostic(
            reviewer_id=reviewer_id,
            finding_type=finding_type,
            tenant_id=snapshot.tenant_id,
            editorial_id=snapshot.editorial_id,
            work_id=snapshot.work_id,
            branch=snapshot.branch_id,
            source_version=snapshot.source_manuscript_version,
            target_id=span.block_id,
            severity="error",
            evidence=span.evidence,
            description=description,
            recommended_action=(
                "Evaluar la propuesta antes de convertirla en un cambio aprobado."
            ),
            diagnostic_axis="normative_correction",
            editorial_classification="verified_error",
            criterion=criterion,
            certainty=1.0,
            text_binding=binding,
            replacement_proposals=(
                ReplacementProposal(
                    replacement_text=replacement_text,
                    rationale=rationale,
                ),
            ),
        )
