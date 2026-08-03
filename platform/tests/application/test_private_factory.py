from datetime import datetime, timezone

import pytest

from editorial_tres.application.private_factory import (
    EditorialDecisionInput,
    PlainTextManuscriptParser,
    PrivateEditorialFactory,
)
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId


SOURCE = """OBRA DE PRUEBA

CAPÍTULO I
EL COMIENZO

El taller tenía  dos puertas.

CAPÍTULO II
EL REGRESO

La editora volvió al amanecer.
"""

SCOPE = {
    "tenant_id": TenantId(value="tenant.factory-test"),
    "editorial_id": EditorialId(value="editorial.tres"),
    "work_id": WorkId(value="work.factory-test"),
    "actor_id": ActorId(value="actor.editor"),
}


def test_parser_preserves_complete_chapter_structure_and_source_identity():
    parsed = PlainTextManuscriptParser().parse(SOURCE)

    assert parsed.title == "OBRA DE PRUEBA"
    assert len(parsed.chapters) == 2
    assert parsed.chapters[0].label == "CAPÍTULO I"
    assert parsed.chapters[0].title == "EL COMIENZO"
    assert parsed.chapters[0].body == "El taller tenía  dos puertas."
    assert parsed.chapters[1].body == "La editora volvió al amanecer."


def test_factory_requires_one_explicit_decision_per_finding():
    factory = PrivateEditorialFactory()
    review = factory.review(SOURCE, **SCOPE)

    assert len(review.findings) == 1
    with pytest.raises(ValueError, match="Toda revisión debe quedar resuelta"):
        factory.process(SOURCE, author="Autora", **SCOPE)


def test_factory_applies_only_accepted_findings_and_builds_master_pdf():
    factory = PrivateEditorialFactory()
    review = factory.review(SOURCE, **SCOPE)
    finding = review.findings[0]
    result = factory.process(
        SOURCE,
        author="Autora",
        decisions=(
            EditorialDecisionInput(
                finding_id=finding.finding_id,
                status="accepted",
                reason="El espacio duplicado es un error mecánico verificado.",
            ),
        ),
        decided_at=datetime(2026, 8, 2, 20, 0, tzinfo=timezone.utc),
        **SCOPE,
    )

    assert result.accepted_count == 1
    assert result.rejected_count == 0
    assert result.final_work.expression_graph.get_block("chapter-01-body").content == (
        "El taller tenía dos puertas."
    )
    assert "El taller tenía dos puertas." in result.master_edition.model_dump_json()
    assert "El taller tenía  dos puertas." not in result.master_edition.model_dump_json()
    assert result.master_edition.public_metadata["author"] == "Autora"
    assert result.pdf_bytes.startswith(b"%PDF-")


def test_factory_rejected_finding_leaves_source_material_unchanged():
    factory = PrivateEditorialFactory()
    finding = factory.review(SOURCE, **SCOPE).findings[0]
    result = factory.process(
        SOURCE,
        author="Autora",
        decisions=(
            EditorialDecisionInput(
                finding_id=finding.finding_id,
                status="rejected",
                reason="La autora conserva el espaciado como marca experimental.",
            ),
        ),
        **SCOPE,
    )

    assert result.accepted_count == 0
    assert result.rejected_count == 1
    assert result.final_work.expression_graph.get_block("chapter-01-body").content == (
        "El taller tenía  dos puertas."
    )


@pytest.mark.parametrize(
    "source",
    (
        "",
        "SIN CAPÍTULOS\n\nTexto suelto.",
        "OBRA\n\nPrefacio suelto\n\nCAPÍTULO I\nTÍTULO\n\nCuerpo.",
    ),
)
def test_parser_rejects_unstructured_or_empty_input(source):
    with pytest.raises(ValueError):
        PlainTextManuscriptParser().parse(source)


def test_factory_merges_compatible_corrections_from_the_same_sentence():
    source = SOURCE.replace("tenía  dos puertas.", "tenía  dos puertas .")
    factory = PrivateEditorialFactory()
    review = factory.review(source, **SCOPE)

    assert len(review.findings) == 2
    result = factory.process(
        source,
        author="Autora",
        decisions=tuple(
            EditorialDecisionInput(
                finding_id=finding.finding_id,
                status="accepted",
                reason="Corrección mecánica verificada.",
            )
            for finding in review.findings
        ),
        **SCOPE,
    )

    assert result.accepted_count == 2
    assert result.final_work.expression_graph.get_block("chapter-01-body").content == (
        "El taller tenía dos puertas."
    )
