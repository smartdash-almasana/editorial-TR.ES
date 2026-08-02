"""Dependency-free, span-traceable Spanish grammar findings."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from editorial_tres.domain.reviews import (
    EditorialCriterion,
    ReplacementProposal,
    ReviewFinding,
    TextualFindingBinding,
)
from editorial_tres.domain.text_analysis import TextAnalysisSnapshot, TextSpan


GrammarRuleKey = Literal[
    "incompatible_object_clitics",
    "a_pesar_que_government",
    "plural_impersonal_haber_quienes",
    "plural_impersonal_haber",
]
GrammarClassification = Literal["verified_error", "probable_issue"]
GrammarSeverity = Literal["warning", "error"]


class GrammarRule(BaseModel):
    """Immutable metadata for one deterministic built-in grammar rule."""

    rule_key: GrammarRuleKey
    finding_type: str
    criterion: EditorialCriterion
    classification: GrammarClassification
    certainty: float = Field(ge=0.0, le=1.0)
    severity: GrammarSeverity
    description: str
    rationale: str

    model_config = {"frozen": True}

    @field_validator("finding_type", "description", "rationale")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La regla gramatical requiere metadatos completos.")
        return normalized


class SimpleAgreementRule(BaseModel):
    """One governed exact subject/verb-number pair from editorial evidence."""

    singular_subject: str
    plural_subject: str
    singular_verb: str
    plural_verb: str
    rationale: str
    criterion: EditorialCriterion
    certainty: float = Field(default=1.0, ge=0.0, le=1.0)

    model_config = {"frozen": True}

    @field_validator(
        "singular_subject",
        "plural_subject",
        "singular_verb",
        "plural_verb",
        "rationale",
    )
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(
                "La regla de concordancia requiere valores no vacíos."
            )
        return normalized

    @model_validator(mode="after")
    def _explicit_distinct_forms(self) -> "SimpleAgreementRule":
        if self.singular_subject.casefold() == self.plural_subject.casefold():
            raise ValueError(
                "Las formas de sujeto singular y plural deben ser distintas."
            )
        if self.singular_verb.casefold() == self.plural_verb.casefold():
            raise ValueError(
                "Las formas verbales singular y plural deben ser distintas."
            )
        if any(character.isspace() for character in self.singular_verb):
            raise ValueError("La forma verbal singular debe ser un token exacto.")
        if any(character.isspace() for character in self.plural_verb):
            raise ValueError("La forma verbal plural debe ser un token exacto.")
        return self


BUILTIN_GRAMMAR_RULES: tuple[GrammarRule, ...] = (
    GrammarRule(
        rule_key="incompatible_object_clitics",
        finding_type="grammar.incompatible_object_clitics",
        criterion=EditorialCriterion(
            criterion_id="es.grammar.indirect-before-direct-object-clitic",
            criterion_version="1.0.0",
        ),
        classification="verified_error",
        certainty=1.0,
        severity="error",
        description=(
            "Un clítico indirecto «le/les» precede a un clítico directo de "
            "tercera persona."
        ),
        rationale=(
            "Ante «lo/la/los/las», el clítico indirecto de tercera persona "
            "adopta la forma «se»."
        ),
    ),
    GrammarRule(
        rule_key="a_pesar_que_government",
        finding_type="grammar.a_pesar_que_government",
        criterion=EditorialCriterion(
            criterion_id="es.grammar.a-pesar-de-que-government",
            criterion_version="1.0.0",
        ),
        classification="verified_error",
        certainty=1.0,
        severity="error",
        description="La locución «a pesar que» omite la preposición regida «de».",
        rationale="Usar la locución conjuntiva completa «a pesar de que».",
    ),
    GrammarRule(
        rule_key="plural_impersonal_haber_quienes",
        finding_type="grammar.impersonal_haber_quienes_number",
        criterion=EditorialCriterion(
            criterion_id="es.grammar.impersonal-haber-quienes-number",
            criterion_version="1.0.0",
        ),
        classification="verified_error",
        certainty=1.0,
        severity="error",
        description=(
            "La forma plural «habían» se usa como verbo impersonal existencial "
            "ante «quienes»."
        ),
        rationale=(
            "En «había quienes», el verbo impersonal «haber» se mantiene en "
            "singular."
        ),
    ),
    GrammarRule(
        rule_key="plural_impersonal_haber",
        finding_type="grammar.probable_plural_impersonal_haber",
        criterion=EditorialCriterion(
            criterion_id="es.grammar.impersonal-haber-number",
            criterion_version="1.0.0",
        ),
        classification="probable_issue",
        certainty=0.92,
        severity="warning",
        description=(
            "Una forma plural de «haber» parece funcionar como verbo "
            "impersonal existencial."
        ),
        rationale=(
            "En la construcción impersonal existencial, «haber» se mantiene "
            "en singular; confirmar el contexto antes de aprobar el cambio."
        ),
    ),
)


_CLITIC_SEQUENCE = re.compile(
    r"(?<!\w)(le|les)(\s+)(lo|la|los|las)(?!\w)",
    flags=re.IGNORECASE | re.UNICODE,
)
_A_PESAR_QUE = re.compile(
    r"(?<!\w)(a\s+pesar\s+)(que)(?!\w)",
    flags=re.IGNORECASE | re.UNICODE,
)
_IMPERSONAL_HABER_QUIENES = re.compile(
    r"(?<!\w)(habían)(\s+)(quienes)(?!\w)",
    flags=re.IGNORECASE | re.UNICODE,
)
_EXISTENTIAL_QUANTIFIER = (
    r"(?:much(?:o|a|os|as)|poc(?:o|a|os|as)|"
    r"vari(?:o|a|os|as)|numeros(?:o|a|os|as)|"
    r"demasiad(?:o|a|os|as)|tant(?:o|a|os|as)|"
    r"algun(?:o|a|os|as)|un(?:o|a|os|as)|"
    r"los|las|ambos|ambas|tres|\d+)"
)
_PLURAL_IMPERSONAL_HABER = re.compile(
    rf"(?<!\w)(habían|hubieron|habrán|habrían|hayan|"
    rf"hubieran|hubiesen)(\s+)(?={_EXISTENTIAL_QUANTIFIER}(?!\w))",
    flags=re.IGNORECASE | re.UNICODE,
)
_HABER_SINGULAR = {
    "habían": "había",
    "hubieron": "hubo",
    "habrán": "habrá",
    "habrían": "habría",
    "hayan": "haya",
    "hubieran": "hubiera",
    "hubiesen": "hubiese",
}


def _match_case(source: str, replacement: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper() and source[1:].islower():
        return replacement.capitalize()
    return replacement


def _correct_builtin(rule_key: GrammarRuleKey, text: str) -> str:
    if rule_key == "incompatible_object_clitics":
        return _CLITIC_SEQUENCE.sub(
            lambda match: (
                _match_case(match.group(1), "se")
                + match.group(2)
                + match.group(3)
            ),
            text,
        )
    if rule_key == "a_pesar_que_government":
        return _A_PESAR_QUE.sub(
            lambda match: match.group(1) + "de " + match.group(2),
            text,
        )
    if rule_key == "plural_impersonal_haber_quienes":
        return _IMPERSONAL_HABER_QUIENES.sub(
            lambda match: (
                _match_case(match.group(1), "había")
                + match.group(2)
                + match.group(3)
            ),
            text,
        )
    if rule_key == "plural_impersonal_haber":
        return _PLURAL_IMPERSONAL_HABER.sub(
            lambda match: (
                _match_case(
                    match.group(1),
                    _HABER_SINGULAR[match.group(1).casefold()],
                )
                + match.group(2)
            ),
            text,
        )
    raise AssertionError(f"Regla gramatical desconocida: {rule_key}")


def _phrase_pattern(value: str) -> str:
    words = re.split(r"\s+", value.strip())
    return r"\s+".join(re.escape(word) for word in words)


def _agreement_pattern(subject: str, verb: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?<!\w)({_phrase_pattern(subject)})(\s+)({re.escape(verb)})(?!\w)",
        flags=re.IGNORECASE | re.UNICODE,
    )


def _correct_agreement(rule: SimpleAgreementRule, text: str) -> str:
    singular_mismatch = _agreement_pattern(
        rule.singular_subject,
        rule.plural_verb,
    )
    plural_mismatch = _agreement_pattern(
        rule.plural_subject,
        rule.singular_verb,
    )
    corrected = singular_mismatch.sub(
        lambda match: (
            match.group(1)
            + match.group(2)
            + _match_case(match.group(3), rule.singular_verb)
        ),
        text,
    )
    return plural_mismatch.sub(
        lambda match: (
            match.group(1)
            + match.group(2)
            + _match_case(match.group(3), rule.plural_verb)
        ),
        corrected,
    )


class SpanishGrammarCorrector(BaseModel):
    """Emit governed grammar proposals without mutating the manuscript."""

    agreement_rules: tuple[SimpleAgreementRule, ...] = ()

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def _unique_registry(self) -> "SpanishGrammarCorrector":
        criteria = tuple(
            rule.criterion for rule in BUILTIN_GRAMMAR_RULES
        ) + tuple(rule.criterion for rule in self.agreement_rules)
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

        forms = tuple(
            (
                rule.singular_subject.casefold(),
                rule.plural_subject.casefold(),
                rule.singular_verb.casefold(),
                rule.plural_verb.casefold(),
            )
            for rule in self.agreement_rules
        )
        if len(forms) != len(set(forms)):
            raise ValueError(
                "Las reglas de concordancia no pueden repetir el mismo par."
            )
        return self

    @property
    def rule_registry(self) -> tuple[EditorialCriterion, ...]:
        """Expose the immutable, ordered criterion registry."""

        return tuple(
            rule.criterion for rule in BUILTIN_GRAMMAR_RULES
        ) + tuple(rule.criterion for rule in self.agreement_rules)

    def analyze(
        self,
        snapshot: TextAnalysisSnapshot,
    ) -> tuple[ReviewFinding, ...]:
        """Analyze canonical PT-0 sentences in deterministic reading order."""

        ordered: list[tuple[int, int, str, ReviewFinding]] = []
        for block_ordinal, block in enumerate(snapshot.blocks):
            for sentence in block.sentences:
                for rule in BUILTIN_GRAMMAR_RULES:
                    replacement = _correct_builtin(
                        rule.rule_key,
                        sentence.evidence,
                    )
                    if replacement == sentence.evidence:
                        continue
                    finding = self._finding(
                        snapshot=snapshot,
                        span=sentence,
                        finding_type=rule.finding_type,
                        criterion=rule.criterion,
                        classification=rule.classification,
                        certainty=rule.certainty,
                        severity=rule.severity,
                        description=rule.description,
                        rationale=rule.rationale,
                        replacement_text=replacement,
                    )
                    ordered.append(
                        (
                            block_ordinal,
                            sentence.start,
                            rule.criterion.criterion_id,
                            finding,
                        )
                    )

                for rule in self.agreement_rules:
                    replacement = _correct_agreement(rule, sentence.evidence)
                    if replacement == sentence.evidence:
                        continue
                    finding = self._finding(
                        snapshot=snapshot,
                        span=sentence,
                        finding_type=(
                            "grammar.simple_subject_verb_number_agreement"
                        ),
                        criterion=rule.criterion,
                        classification="verified_error",
                        certainty=rule.certainty,
                        severity="error",
                        description=(
                            "El sujeto y el verbo no coinciden en número según "
                            "el par explícitamente gobernado."
                        ),
                        rationale=rule.rationale,
                        replacement_text=replacement,
                    )
                    ordered.append(
                        (
                            block_ordinal,
                            sentence.start,
                            rule.criterion.criterion_id,
                            finding,
                        )
                    )

        ordered.sort(key=lambda item: item[:3])
        return tuple(item[3] for item in ordered)

    @staticmethod
    def _finding(
        *,
        snapshot: TextAnalysisSnapshot,
        span: TextSpan,
        finding_type: str,
        criterion: EditorialCriterion,
        classification: GrammarClassification,
        certainty: float,
        severity: GrammarSeverity,
        description: str,
        rationale: str,
        replacement_text: str,
    ) -> ReviewFinding:
        binding = TextualFindingBinding(snapshot=snapshot, span=span)
        return ReviewFinding.diagnostic(
            reviewer_id="proofreader.spanish-grammar.v1",
            finding_type=finding_type,
            tenant_id=snapshot.tenant_id,
            editorial_id=snapshot.editorial_id,
            work_id=snapshot.work_id,
            branch=snapshot.branch_id,
            source_version=snapshot.source_manuscript_version,
            target_id=span.block_id,
            severity=severity,
            evidence=span.evidence,
            description=description,
            recommended_action=(
                "Evaluar la propuesta antes de convertirla en un cambio aprobado."
            ),
            diagnostic_axis="normative_correction",
            editorial_classification=classification,
            criterion=criterion,
            certainty=certainty,
            text_binding=binding,
            replacement_proposals=(
                ReplacementProposal(
                    replacement_text=replacement_text,
                    rationale=rationale,
                ),
            ),
        )
