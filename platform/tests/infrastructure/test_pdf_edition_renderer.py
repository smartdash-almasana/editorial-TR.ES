import re

from editorial_tres.domain.edition import EditionBlock, EditionSnapshot
from editorial_tres.infrastructure.pdf_edition_renderer import PdfEditionRenderer


def _snapshot():
    return EditionSnapshot(
        edition_id="edition.pdf-test.v1",
        edition_version=1,
        tenant_id="tenant.pdf-test",
        editorial_id="editorial.tres",
        work_id="work.pdf-test",
        source_work_version=3,
        source_manuscript_version=3,
        title="Una edición con acentos",
        language="es",
        blocks=(
            EditionBlock(
                id="chapter-01",
                block_type="heading",
                content="CAPÍTULO I\nLA SEÑAL",
                position=0,
                language="es",
            ),
            EditionBlock(
                id="chapter-01-body",
                block_type="paragraph",
                content="Tomás miró el río.\n\n—¿Quién está ahí? —preguntó.",
                parent_id="chapter-01",
                position=0,
                language="es",
            ),
        ),
        reading_order=("chapter-01", "chapter-01-body"),
        public_metadata={"author": "Editorial TR.ES"},
    )


def test_pdf_renderer_is_deterministic_complete_and_multipage():
    renderer = PdfEditionRenderer()
    first = renderer.render(_snapshot())
    second = renderer.render(_snapshot())

    assert first == second
    assert first.startswith(b"%PDF-")
    assert b"%%EOF" in first[-1024:]
    assert len(re.findall(rb"/Type\s*/Page\b", first)) >= 2
    for private_identifier in (b"tenant.pdf-test", b"work.pdf-test", b"chapter-01"):
        assert private_identifier not in first
