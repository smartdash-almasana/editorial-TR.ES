"""Non-destructive editorial review findings and reviewer contracts."""

from abc import ABC, abstractmethod
import hashlib
import re
from typing import Literal, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.work import Work


FindingSeverity = Literal["info", "warning", "error"]


class ReviewFinding(BaseModel):
    """Immutable diagnostic result produced by a reviewer over one Work version."""

    finding_id: str
    reviewer_id: str
    finding_type: str
    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    branch: str = "main"
    source_version: int = Field(ge=1)
    target_id: str
    severity: FindingSeverity
    evidence: str
    description: str
    recommended_action: str | None = None

    model_config = {"frozen": True}

    @field_validator(
        "finding_id",
        "reviewer_id",
        "finding_type",
        "branch",
        "target_id",
        "evidence",
        "description",
    )
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El valor es obligatorio.")
        return value.strip()

    @field_validator("recommended_action")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class Reviewer(ABC):
    """Contract for a reviewer that diagnoses without mutating a Work."""

    reviewer_id: str

    @abstractmethod
    def review(self, work: Work, branch: str = "main") -> Tuple[ReviewFinding, ...]:
        """Return zero or more findings without mutating ``work``."""
        raise NotImplementedError


class RepeatedPhraseReviewer(BaseModel, Reviewer):
    """Minimal deterministic reviewer proving the Work -> ReviewFinding boundary."""

    reviewer_id: str
    phrase: str
    minimum_occurrences: int = Field(default=2, ge=2)
    severity: FindingSeverity = "warning"

    model_config = {"frozen": True}

    @field_validator("reviewer_id", "phrase")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El valor es obligatorio.")
        return value.strip()

    def review(self, work: Work, branch: str = "main") -> Tuple[ReviewFinding, ...]:
        if not branch or not branch.strip():
            raise ValueError("La rama no puede estar vacía.")
        normalized_branch = branch.strip()
        findings: list[ReviewFinding] = []

        for block in work.expression_graph.get_all_blocks():
            occurrences = block.content.count(self.phrase)
            if occurrences < self.minimum_occurrences:
                continue

            fingerprint = "|".join(
                (
                    self.reviewer_id,
                    work.tenant_id.value,
                    work.editorial_id.value,
                    work.work_id.value,
                    normalized_branch,
                    str(work.version),
                    block.id,
                    self.phrase,
                    str(occurrences),
                )
            )
            finding_id = f"finding-{hashlib.sha256(fingerprint.encode()).hexdigest()[:16]}"
            findings.append(
                ReviewFinding(
                    finding_id=finding_id,
                    reviewer_id=self.reviewer_id,
                    finding_type="expression.repeated_phrase",
                    tenant_id=work.tenant_id,
                    editorial_id=work.editorial_id,
                    work_id=work.work_id,
                    branch=normalized_branch,
                    source_version=work.version,
                    target_id=block.id,
                    severity=self.severity,
                    evidence=self.phrase,
                    description=(
                        f"La frase aparece {occurrences} veces en el bloque '{block.id}'."
                    ),
                    recommended_action="Revisar si la repetición es deliberada o mecánica.",
                )
            )

        return tuple(findings)


class ReviewEngine:
    """Executes independent reviewers and aggregates findings without mutation."""

    def __init__(self, reviewers: Tuple[Reviewer, ...]):
        if not reviewers:
            raise ValueError("ReviewEngine requiere al menos un reviewer.")
        reviewer_ids = [reviewer.reviewer_id for reviewer in reviewers]
        if len(reviewer_ids) != len(set(reviewer_ids)):
            raise ValueError("ReviewEngine no admite reviewer_id duplicados.")
        self._reviewers = reviewers

    @property
    def reviewer_ids(self) -> Tuple[str, ...]:
        """Expose the immutable execution order without leaking reviewer instances."""
        return tuple(reviewer.reviewer_id for reviewer in self._reviewers)

    def review(self, work: Work, branch: str = "main") -> Tuple[ReviewFinding, ...]:
        findings: list[ReviewFinding] = []
        for reviewer in self._reviewers:
            findings.extend(reviewer.review(work, branch=branch))
        return tuple(sorted(findings, key=lambda item: (item.target_id, item.reviewer_id, item.finding_id)))


class VoiceDriftReviewer(BaseModel, Reviewer):
    """Deterministic reviewer for configured signals of author-voice drift."""

    reviewer_id: str
    drift_markers: Tuple[str, ...]
    minimum_markers: int = Field(default=2, ge=1)
    severity: FindingSeverity = "warning"

    model_config = {"frozen": True}

    @field_validator("reviewer_id")
    @classmethod
    def _voice_required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El reviewer_id es obligatorio.")
        return value.strip()

    @field_validator("drift_markers")
    @classmethod
    def _voice_markers(cls, values: Tuple[str, ...]) -> Tuple[str, ...]:
        cleaned = tuple(value.strip() for value in values if value and value.strip())
        if not cleaned:
            raise ValueError("VoiceDriftReviewer requiere señales de deriva configuradas.")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Las señales de deriva no pueden repetirse.")
        return cleaned

    def review(self, work: Work, branch: str = "main") -> Tuple[ReviewFinding, ...]:
        normalized_branch = branch.strip() if branch else ""
        if not normalized_branch:
            raise ValueError("La rama no puede estar vacía.")
        findings: list[ReviewFinding] = []
        for block in work.expression_graph.get_all_blocks():
            matched = tuple(marker for marker in self.drift_markers if marker.casefold() in block.content.casefold())
            if len(matched) < self.minimum_markers:
                continue
            evidence = " | ".join(matched)
            fingerprint = "|".join((self.reviewer_id, work.work_id.value, normalized_branch, str(work.version), block.id, evidence))
            findings.append(ReviewFinding(
                finding_id=f"finding-{hashlib.sha256(fingerprint.encode()).hexdigest()[:16]}",
                reviewer_id=self.reviewer_id,
                finding_type="expression.voice_drift",
                tenant_id=work.tenant_id,
                editorial_id=work.editorial_id,
                work_id=work.work_id,
                branch=normalized_branch,
                source_version=work.version,
                target_id=block.id,
                severity=self.severity,
                evidence=evidence,
                description=f"El bloque reúne {len(matched)} señales configuradas de posible deriva de voz.",
                recommended_action="Comparar el pasaje con la memoria autoral aprobada antes de proponer cambios.",
            ))
        return tuple(findings)


class ContinuityRule(BaseModel):
    """Ordered incompatible states for one narrative entity."""

    rule_id: str
    entity: str
    established_markers: Tuple[str, ...]
    conflicting_markers: Tuple[str, ...]

    model_config = {"frozen": True}

    @field_validator("rule_id", "entity")
    @classmethod
    def _continuity_required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("La regla de continuidad requiere identidad y entidad.")
        return value.strip()

    @field_validator("established_markers", "conflicting_markers")
    @classmethod
    def _continuity_markers(cls, values: Tuple[str, ...]) -> Tuple[str, ...]:
        cleaned = tuple(value.strip() for value in values if value and value.strip())
        if not cleaned:
            raise ValueError("La regla de continuidad requiere marcadores de estado.")
        return cleaned


class ContinuityReviewer(BaseModel, Reviewer):
    """Deterministic reviewer for configured ordered continuity conflicts."""

    reviewer_id: str
    rules: Tuple[ContinuityRule, ...]
    severity: FindingSeverity = "error"

    model_config = {"frozen": True}

    @field_validator("reviewer_id")
    @classmethod
    def _continuity_reviewer_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El reviewer_id es obligatorio.")
        return value.strip()

    @field_validator("rules")
    @classmethod
    def _continuity_rules(cls, values: Tuple[ContinuityRule, ...]) -> Tuple[ContinuityRule, ...]:
        if not values:
            raise ValueError("ContinuityReviewer requiere al menos una regla.")
        ids = [rule.rule_id for rule in values]
        if len(ids) != len(set(ids)):
            raise ValueError("Las reglas de continuidad no pueden duplicar rule_id.")
        return values

    def review(self, work: Work, branch: str = "main") -> Tuple[ReviewFinding, ...]:
        normalized_branch = branch.strip() if branch else ""
        if not normalized_branch:
            raise ValueError("La rama no puede estar vacía.")
        findings: list[ReviewFinding] = []
        for block in work.expression_graph.get_all_blocks():
            text = block.content.casefold()
            for rule in self.rules:
                established = [(text.find(marker.casefold()), marker) for marker in rule.established_markers if text.find(marker.casefold()) >= 0]
                conflicts = [(text.find(marker.casefold()), marker) for marker in rule.conflicting_markers if text.find(marker.casefold()) >= 0]
                if not established or not conflicts:
                    continue
                first_established = min(established)
                first_conflict = min(conflicts)
                if first_established[0] >= first_conflict[0]:
                    continue
                evidence = f"{first_established[1]} → {first_conflict[1]}"
                fingerprint = "|".join((self.reviewer_id, rule.rule_id, work.work_id.value, normalized_branch, str(work.version), block.id, evidence))
                findings.append(ReviewFinding(
                    finding_id=f"finding-{hashlib.sha256(fingerprint.encode()).hexdigest()[:16]}",
                    reviewer_id=self.reviewer_id,
                    finding_type="narrative.continuity_conflict",
                    tenant_id=work.tenant_id,
                    editorial_id=work.editorial_id,
                    work_id=work.work_id,
                    branch=normalized_branch,
                    source_version=work.version,
                    target_id=block.id,
                    severity=self.severity,
                    evidence=evidence,
                    description=f"La entidad '{rule.entity}' presenta estados incompatibles sin transición explicada.",
                    recommended_action="Verificar si existe una transición omitida o corregir uno de los estados.",
                ))
        return tuple(findings)


class StructuralReviewer(BaseModel, Reviewer):
    """Deterministic reviewer for duplicated paragraphs and configured thematic reiteration."""

    reviewer_id: str
    thematic_phrases: Tuple[str, ...] = ()
    minimum_thematic_occurrences: int = Field(default=3, ge=2)
    severity: FindingSeverity = "warning"

    model_config = {"frozen": True}

    @field_validator("reviewer_id")
    @classmethod
    def _structural_reviewer_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El reviewer_id es obligatorio.")
        return value.strip()

    def review(self, work: Work, branch: str = "main") -> Tuple[ReviewFinding, ...]:
        normalized_branch = branch.strip() if branch else ""
        if not normalized_branch:
            raise ValueError("La rama no puede estar vacía.")
        findings: list[ReviewFinding] = []
        for block in work.expression_graph.get_all_blocks():
            paragraphs = [" ".join(part.split()) for part in block.content.splitlines() if part.strip()]
            counts: dict[str, int] = {}
            for paragraph in paragraphs:
                counts[paragraph] = counts.get(paragraph, 0) + 1
            for paragraph, occurrences in sorted(counts.items()):
                if occurrences < 2:
                    continue
                evidence = paragraph[:240]
                fingerprint = "|".join((self.reviewer_id, "duplicate", work.work_id.value, normalized_branch, str(work.version), block.id, evidence, str(occurrences)))
                findings.append(ReviewFinding(
                    finding_id=f"finding-{hashlib.sha256(fingerprint.encode()).hexdigest()[:16]}",
                    reviewer_id=self.reviewer_id,
                    finding_type="structure.duplicate_paragraph",
                    tenant_id=work.tenant_id,
                    editorial_id=work.editorial_id,
                    work_id=work.work_id,
                    branch=normalized_branch,
                    source_version=work.version,
                    target_id=block.id,
                    severity="error",
                    evidence=evidence,
                    description=f"El mismo párrafo aparece {occurrences} veces.",
                    recommended_action="Conservar sólo la repetición que cumpla una función estructural deliberada.",
                ))
            for phrase in self.thematic_phrases:
                occurrences = block.content.casefold().count(phrase.casefold())
                if occurrences < self.minimum_thematic_occurrences:
                    continue
                fingerprint = "|".join((self.reviewer_id, "theme", work.work_id.value, normalized_branch, str(work.version), block.id, phrase, str(occurrences)))
                findings.append(ReviewFinding(
                    finding_id=f"finding-{hashlib.sha256(fingerprint.encode()).hexdigest()[:16]}",
                    reviewer_id=self.reviewer_id,
                    finding_type="structure.thematic_reiteration",
                    tenant_id=work.tenant_id,
                    editorial_id=work.editorial_id,
                    work_id=work.work_id,
                    branch=normalized_branch,
                    source_version=work.version,
                    target_id=block.id,
                    severity=self.severity,
                    evidence=phrase,
                    description=f"La formulación temática aparece {occurrences} veces sin evaluación de aporte nuevo.",
                    recommended_action="Revisar si cada aparición desarrolla la idea o sólo la repite.",
                ))
        return tuple(findings)


class RhythmReviewer(BaseModel, Reviewer):
    """Deterministic reviewer for configurable sentence-level rhythm signals."""

    reviewer_id: str
    short_sentence_max_words: int = Field(default=3, ge=1)
    long_sentence_min_words: int = Field(default=35, ge=2)
    minimum_short_run: int = Field(default=4, ge=2)
    minimum_long_run: int = Field(default=3, ge=2)
    uniformity_min_sentences: int = Field(default=6, ge=3)
    uniformity_max_word_range: int = Field(default=2, ge=0)
    opening_word_count: int = Field(default=2, ge=1)
    minimum_repeated_openings: int = Field(default=4, ge=2)
    severity: FindingSeverity = "warning"

    model_config = {"frozen": True}

    @field_validator("reviewer_id")
    @classmethod
    def _rhythm_reviewer_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El reviewer_id es obligatorio.")
        return value.strip()

    @model_validator(mode="after")
    def _validate_threshold_order(self) -> "RhythmReviewer":
        if self.short_sentence_max_words >= self.long_sentence_min_words:
            raise ValueError(
                "El umbral de oración corta debe ser menor que el de oración larga."
            )
        return self

    @staticmethod
    def _split_sentences(text: str) -> Tuple[str, ...]:
        normalized = " ".join(text.split())
        if not normalized:
            return ()
        return tuple(
            sentence.strip()
            for sentence in re.findall(r"[^.!?]+(?:[.!?]+|$)", normalized)
            if sentence.strip()
        )

    @staticmethod
    def _words(sentence: str) -> Tuple[str, ...]:
        return tuple(
            re.findall(r"[^\W\d_]+(?:[’'-][^\W\d_]+)*", sentence, flags=re.UNICODE)
        )

    @staticmethod
    def _longest_run(matches: Tuple[bool, ...]) -> tuple[int, int]:
        best_start = 0
        best_length = 0
        current_start = 0
        current_length = 0
        for index, matched in enumerate(matches):
            if matched:
                if current_length == 0:
                    current_start = index
                current_length += 1
                if current_length > best_length:
                    best_start = current_start
                    best_length = current_length
            else:
                current_length = 0
        return best_start, best_length

    def review(self, work: Work, branch: str = "main") -> Tuple[ReviewFinding, ...]:
        normalized_branch = branch.strip() if branch else ""
        if not normalized_branch:
            raise ValueError("La rama no puede estar vacía.")

        findings: list[ReviewFinding] = []
        for block in work.expression_graph.get_all_blocks():
            sentences = self._split_sentences(block.content)
            if not sentences:
                continue
            sentence_words = tuple(self._words(sentence) for sentence in sentences)
            word_counts = tuple(len(words) for words in sentence_words)

            def add_finding(
                finding_type: str,
                evidence: str,
                description: str,
                recommended_action: str,
            ) -> None:
                fingerprint = "|".join(
                    (
                        self.reviewer_id,
                        finding_type,
                        work.tenant_id.value,
                        work.editorial_id.value,
                        work.work_id.value,
                        normalized_branch,
                        str(work.version),
                        block.id,
                        evidence,
                    )
                )
                findings.append(
                    ReviewFinding(
                        finding_id=f"finding-{hashlib.sha256(fingerprint.encode()).hexdigest()[:16]}",
                        reviewer_id=self.reviewer_id,
                        finding_type=finding_type,
                        tenant_id=work.tenant_id,
                        editorial_id=work.editorial_id,
                        work_id=work.work_id,
                        branch=normalized_branch,
                        source_version=work.version,
                        target_id=block.id,
                        severity=self.severity,
                        evidence=evidence,
                        description=description,
                        recommended_action=recommended_action,
                    )
                )

            short_start, short_length = self._longest_run(
                tuple(0 < count <= self.short_sentence_max_words for count in word_counts)
            )
            if short_length >= self.minimum_short_run:
                evidence = " | ".join(
                    sentences[short_start : short_start + short_length]
                )[:500]
                add_finding(
                    "expression.rhythm.short_sentence_run",
                    evidence,
                    f"Se detectó una secuencia de {short_length} oraciones de hasta "
                    f"{self.short_sentence_max_words} palabras.",
                    "Revisar si la cadencia entrecortada es deliberada en este pasaje.",
                )

            long_start, long_length = self._longest_run(
                tuple(count >= self.long_sentence_min_words for count in word_counts)
            )
            if long_length >= self.minimum_long_run:
                evidence = " | ".join(
                    sentences[long_start : long_start + long_length]
                )[:500]
                add_finding(
                    "expression.rhythm.long_sentence_run",
                    evidence,
                    f"Se detectó una secuencia de {long_length} oraciones de al menos "
                    f"{self.long_sentence_min_words} palabras.",
                    "Revisar si la extensión sostenida sirve al efecto buscado o necesita variación.",
                )

            if len(word_counts) >= self.uniformity_min_sentences:
                word_range = max(word_counts) - min(word_counts)
                if word_range <= self.uniformity_max_word_range:
                    evidence = ", ".join(str(count) for count in word_counts)
                    add_finding(
                        "expression.rhythm.uniform_sentence_length",
                        evidence,
                        f"Las {len(word_counts)} oraciones presentan un rango de sólo "
                        f"{word_range} palabras entre la más corta y la más larga.",
                        "Revisar si la uniformidad métrica es deliberada o mecánica.",
                    )

            opening_counts: dict[str, int] = {}
            for words in sentence_words:
                if len(words) < self.opening_word_count:
                    continue
                opening = " ".join(words[: self.opening_word_count]).casefold()
                opening_counts[opening] = opening_counts.get(opening, 0) + 1
            repeated_openings = sorted(
                (
                    (opening, occurrences)
                    for opening, occurrences in opening_counts.items()
                    if occurrences >= self.minimum_repeated_openings
                ),
                key=lambda item: (-item[1], item[0]),
            )
            if repeated_openings:
                opening, occurrences = repeated_openings[0]
                add_finding(
                    "expression.rhythm.repeated_opening",
                    f"{opening} ({occurrences})",
                    f"La misma apertura de {self.opening_word_count} palabras aparece "
                    f"en {occurrences} oraciones.",
                    "Revisar si el paralelismo de apertura es deliberado o mecánico.",
                )

        return tuple(findings)
