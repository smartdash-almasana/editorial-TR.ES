from editorial_tres.domain.edition import EditionBlock, EditionSnapshot
from editorial_tres.infrastructure.html_edition_renderer import (
    HtmlEditionRenderer,
)


def _snapshot():
    blocks = (
        EditionBlock(
            id="chapter",
            block_type="heading",
            content="Río <script>alert(1)</script>",
            position=0,
            language="es",
        ),
        EditionBlock(
            id="poem",
            block_type="poem",
            content="Agua primera\nagua final",
            parent_id="chapter",
            position=0,
            language="es",
        ),
        EditionBlock(
            id="closing",
            block_type="paragraph",
            content="La casa quedó en silencio.",
            position=1,
            language="es",
        ),
    )
    return EditionSnapshot(
        edition_id="edition.casa-del-rio.v1",
        edition_version=1,
        tenant_id="tenant.almasana",
        editorial_id="editorial.tres",
        work_id="work.casa-del-rio",
        source_work_version=5,
        source_manuscript_version=4,
        title="La casa del río",
        language="es",
        blocks=blocks,
        reading_order=("chapter", "poem", "closing"),
    )


def test_renders_a_complete_readable_static_document():
    html = HtmlEditionRenderer().render(_snapshot())
    assert html.startswith("<!doctype html>")
    assert '<html lang="es">' in html
    assert "<title>La casa del río</title>" in html
    assert '<meta name="edition-id" content="edition.casa-del-rio.v1">' in html
    assert "<h1>La casa del río</h1>" in html


def test_renders_exact_snapshot_order_and_parent_relationship():
    html = HtmlEditionRenderer().render(_snapshot())
    assert html.index('id="chapter"') < html.index('id="poem"')
    assert html.index('id="poem"') < html.index('id="closing"')
    assert 'data-parent-id="chapter"' in html


def test_escapes_content_and_preserves_poem_lines():
    html = HtmlEditionRenderer().render(_snapshot())
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "Agua primera\nagua final" in html


def test_render_is_deterministic_for_the_same_snapshot():
    renderer = HtmlEditionRenderer()
    snapshot = _snapshot()
    assert renderer.render(snapshot) == renderer.render(snapshot)
