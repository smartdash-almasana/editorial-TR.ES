"""Professional print-oriented PDF projection for a neutral master edition."""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from editorial_tres.domain.edition import EditionSnapshot


class PdfEditionRenderer:
    """Render one EditionSnapshot without exposing production identifiers."""

    def render(self, snapshot: EditionSnapshot) -> bytes:
        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A5,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            title=snapshot.title,
            author=str(snapshot.public_metadata.get("author", "")),
            subject="Edición maestra de Editorial TR.ES",
            creator="Editorial TR.ES Private Factory",
            invariant=1,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TresTitle",
            parent=styles["Title"],
            fontName="Times-Bold",
            fontSize=24,
            leading=29,
            alignment=TA_CENTER,
            spaceAfter=12 * mm,
        )
        author_style = ParagraphStyle(
            "TresAuthor",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
        )
        chapter_label_style = ParagraphStyle(
            "TresChapterLabel",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            alignment=TA_CENTER,
            spaceBefore=20 * mm,
            spaceAfter=3 * mm,
        )
        chapter_style = ParagraphStyle(
            "TresChapter",
            parent=styles["Heading1"],
            fontName="Times-Bold",
            fontSize=17,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=13 * mm,
        )
        body_style = ParagraphStyle(
            "TresBody",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=10.5,
            leading=15.5,
            alignment=TA_JUSTIFY,
            firstLineIndent=6 * mm,
            spaceAfter=3.2 * mm,
            allowWidows=0,
            allowOrphans=0,
        )

        author = snapshot.public_metadata.get("author")
        story = [
            Spacer(1, 38 * mm),
            Paragraph(escape(snapshot.title), title_style),
        ]
        if author:
            story.append(Paragraph(escape(str(author)), author_style))
        story.append(PageBreak())
        for index, block in enumerate(snapshot.blocks):
            if block.block_type == "heading":
                if index and not isinstance(story[-1], PageBreak):
                    story.append(PageBreak())
                lines = [line for line in block.content.splitlines() if line.strip()]
                story.append(Paragraph(escape(lines[0]), chapter_label_style))
                title = "<br/>".join(escape(line) for line in lines[1:])
                if title:
                    story.append(Paragraph(title, chapter_style))
                continue
            paragraphs = [part.strip() for part in block.content.split("\n\n") if part.strip()]
            for paragraph in paragraphs:
                rendered = "<br/>".join(escape(line) for line in paragraph.splitlines())
                story.append(Paragraph(rendered, body_style))

        document.build(
            story,
            onFirstPage=self._first_page,
            onLaterPages=self._numbered_page,
        )
        pdf = output.getvalue()
        if not pdf.startswith(b"%PDF-") or b"%%EOF" not in pdf[-1024:]:
            raise ValueError("El renderer no produjo un PDF completo.")
        return pdf

    @staticmethod
    def _first_page(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(A5[0] / 2, 12 * mm, "EDITORIAL TR.ES")
        canvas.restoreState()

    @staticmethod
    def _numbered_page(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(A5[0] / 2, 10 * mm, str(document.page))
        canvas.restoreState()
