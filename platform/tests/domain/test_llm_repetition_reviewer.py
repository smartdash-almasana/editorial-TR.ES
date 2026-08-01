import json

import pytest

from editorial_tres.domain.graphs.dependency import DependencyGraph
from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph
from editorial_tres.domain.graphs.narrative import NarrativeGraph
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.llm_repetition import LLMGlobalRepetitionReviewer
from editorial_tres.domain.work import Work


class FakeStructuredLLM:
    provider_id = "fake-llm"
    model_id = "fake-literary-1"

    def __init__(self, payload):
        self.payload = payload
        self.prompt = None
        self.schema = None

    def generate_json(self, *, prompt, schema):
        self.prompt = prompt
        self.schema = schema
        return self.payload


def _work() -> Work:
    tenant_id = TenantId(value="tenant.demo")
    editorial_id = EditorialId(value="editorial.tres")
    work_id = WorkId(value="work.llm_repetition")
    expression = ExpressionGraph(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
    )
    blocks = (
        ("chapter-1", "La casa respiraba cada noche como un animal dormido."),
        ("chapter-2", "Al volver, sintió otra vez que las paredes tomaban aire."),
        ("chapter-3", "La vivienda permanecía inmóvil bajo la lluvia."),
    )
    for position, (block_id, content) in enumerate(blocks, start=1):
        expression = expression.add_block(
            ContentBlock(
                id=block_id,
                block_type="paragraph",
                content=content,
                position=position,
            )
        )
    return Work(
        tenant_id=tenant_id,
        editorial_id=editorial_id,
        work_id=work_id,
        title="La casa que respira",
        language="es",
        knowledge_graph=KnowledgeGraph(
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
        ),
        narrative_graph=NarrativeGraph(
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
        ),
        expression_graph=expression,
        dependency_graph=DependencyGraph(
            tenant_id=tenant_id,
            editorial_id=editorial_id,
            work_id=work_id,
        ),
    )


def test_llm_reviewer_discovers_semantic_echo_and_preserves_evidence():
    llm = FakeStructuredLLM(
        {
            "clusters": [
                {
                    "cluster_id": "cluster-house-breath",
                    "candidate_type": "recurring_image",
                    "canonical_label": "la casa como organismo que respira",
                    "explanation": "Dos escenas personifican la casa mediante la respiración.",
                    "confidence": 0.91,
                    "occurrences": [
                        {
                            "block_id": "chapter-1",
                            "quote": "La casa respiraba cada noche como un animal dormido.",
                            "local_reason": "La casa respira de forma literal en la imagen.",
                        },
                        {
                            "block_id": "chapter-2",
                            "quote": "las paredes tomaban aire",
                            "local_reason": "La misma imagen reaparece con otra formulación.",
                        },
                    ],
                }
            ]
        }
    )
    reviewer = LLMGlobalRepetitionReviewer(
        reviewer_id="reviewer.llm-repetition",
        llm=llm,
        minimum_confidence=0.60,
    )

    findings = reviewer.review(_work())

    assert len(findings) == 1
    finding = findings[0]
    assert finding.finding_type == "structure.llm_cross_block_repetition"
    assert finding.target_id == "chapter-1"
    assert finding.related_target_ids == ("chapter-1", "chapter-2")
    evidence = json.loads(finding.evidence)
    assert evidence["provider"] == "fake-llm"
    assert evidence["model"] == "fake-literary-1"
    assert evidence["candidate_type"] == "recurring_image"
    assert len(evidence["occurrences"]) == 2
    assert "No aplicar cambios directamente" in finding.recommended_action
    assert "No corrijas ni reescribas" in llm.prompt
    assert llm.schema["properties"]["clusters"]


def test_llm_reviewer_rejects_unverifiable_quote():
    llm = FakeStructuredLLM(
        {
            "clusters": [
                {
                    "cluster_id": "hallucinated",
                    "candidate_type": "semantic_echo",
                    "canonical_label": "cita inventada",
                    "explanation": "El modelo inventó una evidencia.",
                    "confidence": 0.99,
                    "occurrences": [
                        {
                            "block_id": "chapter-1",
                            "quote": "La casa cantaba al amanecer.",
                            "local_reason": "No existe.",
                        },
                        {
                            "block_id": "chapter-2",
                            "quote": "las paredes tomaban aire",
                            "local_reason": "Sí existe.",
                        },
                    ],
                }
            ]
        }
    )
    reviewer = LLMGlobalRepetitionReviewer(
        reviewer_id="reviewer.llm-repetition",
        llm=llm,
    )

    with pytest.raises(ValueError, match="cita no verificable"):
        reviewer.review(_work())


def test_llm_reviewer_discards_low_confidence_cluster():
    llm = FakeStructuredLLM(
        {
            "clusters": [
                {
                    "cluster_id": "weak",
                    "candidate_type": "requires_context",
                    "canonical_label": "relación débil",
                    "explanation": "La relación no es suficientemente clara.",
                    "confidence": 0.20,
                    "occurrences": [
                        {
                            "block_id": "chapter-1",
                            "quote": "La casa respiraba",
                            "local_reason": "Primera imagen.",
                        },
                        {
                            "block_id": "chapter-2",
                            "quote": "las paredes tomaban aire",
                            "local_reason": "Segunda imagen.",
                        },
                    ],
                }
            ]
        }
    )
    reviewer = LLMGlobalRepetitionReviewer(
        reviewer_id="reviewer.llm-repetition",
        llm=llm,
        minimum_confidence=0.55,
    )

    assert reviewer.review(_work()) == ()
