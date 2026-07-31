"""Non-destructive editorial review findings and reviewer contracts."""

from abc import ABC, abstractmethod
import hashlib
from typing import Literal, Tuple

from pydantic import BaseModel, Field, field_validator

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

    def review(self, work: Work, branch: str = "main") -> Tuple[ReviewFinding, ...]:
        findings: list[ReviewFinding] = []
        for reviewer in self._reviewers:
            findings.extend(reviewer.review(work, branch=branch))
        return tuple(sorted(findings, key=lambda item: (item.target_id, item.reviewer_id, item.finding_id)))
