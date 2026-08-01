"""Replayable review history derived from canonical work events."""

from types import MappingProxyType
from typing import Mapping, Tuple

from pydantic import BaseModel, Field, field_validator

from editorial_tres.domain.events import DomainEvent
from editorial_tres.domain.finding_decisions import FindingDecision
from editorial_tres.domain.reviews import ReviewFinding


class ReviewHistory(BaseModel):
    """Immutable read model for persisted findings and their decisions."""

    findings: Mapping[str, ReviewFinding] = Field(default_factory=dict)
    decisions: Mapping[str, FindingDecision] = Field(default_factory=dict)

    model_config = {"frozen": True, "arbitrary_types_allowed": True}

    @field_validator("findings", "decisions")
    @classmethod
    def _freeze_mapping(cls, value):
        return MappingProxyType(dict(value))

    @classmethod
    def replay(cls, events: list[DomainEvent]) -> "ReviewHistory":
        findings: dict[str, ReviewFinding] = {}
        decisions: dict[str, FindingDecision] = {}

        for event in events:
            if event.event_type == "review.finding_recorded":
                finding = ReviewFinding.model_validate(event.payload["finding"])
                if finding.finding_id in findings:
                    raise ValueError(f"Finding duplicado en historial: {finding.finding_id}")
                findings[finding.finding_id] = finding
            elif event.event_type == "review.finding_decided":
                decision = FindingDecision.model_validate(event.payload["decision"])
                if decision.finding_id not in findings:
                    raise ValueError(
                        f"La decisión referencia un finding inexistente: {decision.finding_id}"
                    )
                if decision.finding_id in decisions:
                    raise ValueError(
                        f"El finding ya posee una decisión persistida: {decision.finding_id}"
                    )
                decisions[decision.finding_id] = decision

        return cls(findings=findings, decisions=decisions)

    def get_finding(self, finding_id: str) -> ReviewFinding | None:
        return self.findings.get(finding_id)

    def get_decision(self, finding_id: str) -> FindingDecision | None:
        return self.decisions.get(finding_id)

    def unresolved_findings(self) -> Tuple[ReviewFinding, ...]:
        return tuple(
            finding
            for finding_id, finding in sorted(self.findings.items())
            if finding_id not in self.decisions
        )
