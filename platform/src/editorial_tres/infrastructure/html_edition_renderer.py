"""Readable static HTML projection of an EditionSnapshot."""

from __future__ import annotations

from html import escape

from editorial_tres.domain.edition import EditionBlock, EditionSnapshot


class HtmlEditionRenderer:
    """Render the same neutral edition used by every other public derivative."""

    def render(self, snapshot: EditionSnapshot) -> str:
        rendered_blocks = "\n".join(
            self._render_block(block) for block in snapshot.blocks
        )
        title = escape(snapshot.title)
        language = escape(snapshot.language, quote=True)
        edition_id = escape(snapshot.edition_id, quote=True)

        return f"""<!doctype html>
<html lang="{language}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="edition-id" content="{edition_id}">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ margin: 0; font-family: Georgia, serif; line-height: 1.65; }}
    main {{ max-width: 44rem; margin: 0 auto; padding: 3rem 1.5rem 5rem; }}
    header {{ margin-bottom: 3rem; border-bottom: 1px solid currentColor; }}
    h1 {{ line-height: 1.1; }}
    h2 {{ margin-top: 2.4rem; line-height: 1.2; }}
    .dialogue {{ margin-left: 1.5rem; }}
    blockquote {{ margin: 2rem 1.5rem; font-style: italic; }}
    .poem {{ white-space: pre-wrap; font: inherit; margin: 2rem 0; }}
    .note {{ border-left: .2rem solid currentColor; padding-left: 1rem; }}
  </style>
</head>
<body data-edition-version="{snapshot.edition_version}">
  <main>
    <header>
      <h1>{title}</h1>
    </header>
    <article>
{rendered_blocks}
    </article>
  </main>
</body>
</html>
"""

    @staticmethod
    def _render_block(block: EditionBlock) -> str:
        block_id = escape(block.id, quote=True)
        block_type = escape(block.block_type, quote=True)
        parent = (
            ""
            if block.parent_id is None
            else f' data-parent-id="{escape(block.parent_id, quote=True)}"'
        )
        content = escape(block.content)
        content_with_breaks = content.replace("\n", "<br>")

        if block.block_type == "heading":
            element = f"<h2>{content_with_breaks}</h2>"
        elif block.block_type == "quote":
            element = f"<blockquote>{content_with_breaks}</blockquote>"
        elif block.block_type == "poem":
            element = f'<pre class="poem">{content}</pre>'
        elif block.block_type == "note":
            element = f'<aside class="note">{content_with_breaks}</aside>'
        else:
            element = (
                f'<p class="{block_type}">{content_with_breaks}</p>'
            )
        return (
            f'      <section id="{block_id}" data-block-type="{block_type}"'
            f"{parent}>{element}</section>"
        )
