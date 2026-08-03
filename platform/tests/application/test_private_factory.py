from datetime import datetime, timezone

import pytest

from editorial_tres.application.private_factory import (
    EditionApprovalInput,
    EditorialDecisionInput,
    PlainTextManuscriptParser,
    PrivateEditorialFactory,
)
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore


SOURCE = """OBRA DE PRUEBA

CAPÍTULO I
EL COMIENZO

El taller tenía  dos puertas.

Otra habitación permanecía cerrada.

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


def _approval(prepared) -> EditionApprovalInput:
    pending = prepared.pending_approval
    return EditionApprovalInput(
        approval_id=pending.approval_id,
        work_id=pending.work_id.value,
        source_work_version=pending.source_work_version,
        source_manuscript_version=pending.source_manuscript_version,
        status="approved",
        actor_id="actor.directora-editorial",
        reason="La versión exacta fue revisada y autorizada para publicación.",
        decided_at=datetime(2026, 8, 2, 21, 0, tzinfo=timezone.utc),
    )


def test_parser_preserves_chapters_source_identity_and_paragraph_boundaries():
    parsed = PlainTextManuscriptParser().parse(SOURCE)

    assert parsed.title == "OBRA DE PRUEBA"
    assert len(parsed.chapters) == 2
    assert parsed.chapters[0].label == "CAPÍTULO I"
    assert parsed.chapters[0].title == "EL COMIENZO"
    assert parsed.chapters[0].paragraphs == (
        "El taller tenía  dos puertas.",
        "Otra habitación permanecía cerrada.",
    )
    assert parsed.chapters[1].body == "La editora volvió al amanecer."


def test_factory_requires_one_explicit_decision_per_finding():
    factory = PrivateEditorialFactory()
    review = factory.review(SOURCE, **SCOPE)

    assert len(review.findings) == 1
    with pytest.raises(ValueError, match="Toda revisión debe quedar resuelta"):
        factory.prepare(SOURCE, **SCOPE)


def test_factory_persists_review_applies_only_accepted_and_publishes_all_formats():
    store = MemoryEventStore()
    factory = PrivateEditorialFactory(event_store=store)
    review = factory.review(SOURCE, **SCOPE)
    finding = review.findings[0]
    prepared = factory.prepare(
        SOURCE,
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

    assert prepared.accepted_count == 1
    assert prepared.final_work.expression_graph.get_block(
        "chapter-01-paragraph-001"
    ).content == "El taller tenía dos puertas."
    assert prepared.approval_template()["status"] is None
    assert prepared.approval_template()["reason"] == ""

    result = factory.publish(
        SOURCE,
        approval=_approval(prepared),
        author="Autora",
        **SCOPE,
    )

    assert "El taller tenía dos puertas." in result.master_edition.model_dump_json()
    assert "El taller tenía  dos puertas." not in result.master_edition.model_dump_json()
    assert result.master_edition.public_metadata["author"] == "Autora"
    assert result.app_book.verify_integrity() is True
    assert result.html.startswith("<!doctype html>")
    assert result.pdf_bytes.startswith(b"%PDF-")
    assert store.get_edition_approval(result.edition_approval.approval_id) == (
        result.edition_approval
    )


def test_factory_rejected_finding_leaves_source_material_unchanged():
    factory = PrivateEditorialFactory()
    finding = factory.review(SOURCE, **SCOPE).findings[0]
    prepared = factory.prepare(
        SOURCE,
        decisions=(
            EditorialDecisionInput(
                finding_id=finding.finding_id,
                status="rejected",
                reason="La autora conserva el espaciado como marca experimental.",
            ),
        ),
        **SCOPE,
    )

    assert prepared.accepted_count == 0
    assert prepared.rejected_count == 1
    assert prepared.final_work.expression_graph.get_block(
        "chapter-01-paragraph-001"
    ).content == "El taller tenía  dos puertas."


def test_factory_rejects_approval_for_another_snapshot():
    factory = PrivateEditorialFactory()
    finding = factory.review(SOURCE, **SCOPE).findings[0]
    prepared = factory.prepare(
        SOURCE,
        decisions=(
            EditorialDecisionInput(
                finding_id=finding.finding_id,
                status="rejected",
                reason="Decisión editorial fundada.",
            ),
        ),
        **SCOPE,
    )
    stale = _approval(prepared).model_copy(
        update={"source_work_version": prepared.final_work.version + 1}
    )

    with pytest.raises(ValueError, match="snapshot editorial preparado"):
        factory.publish(SOURCE, approval=stale, **SCOPE)


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
    prepared = factory.prepare(
        source,
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

    assert prepared.accepted_count == 2
    assert prepared.final_work.expression_graph.get_block(
        "chapter-01-paragraph-001"
    ).content == "El taller tenía dos puertas."
