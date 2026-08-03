import hashlib
import json
import re
from pathlib import Path

from editorial_tres.application.private_factory import PrivateEditorialFactory
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId


PROJECT = Path(__file__).parents[3] / "projects" / "una-luz-extrana-en-buenos-aires"
SOURCE = PROJECT / "manuscript.txt"
OUTPUT = PROJECT.parents[1] / "exports" / "una-luz-extrana-en-buenos-aires"


def test_complete_real_manuscript_reaches_master_edition_and_pdf_without_rewrite():
    source = SOURCE.read_text(encoding="utf-8")
    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    factory = PrivateEditorialFactory()
    scope = {
        "tenant_id": TenantId(value="tenant.tres-private"),
        "editorial_id": EditorialId(value="editorial.tres"),
        "work_id": WorkId(value="work.una-luz-extrana-en-buenos-aires"),
        "actor_id": ActorId(value="actor.editorial-tres"),
    }

    review = factory.review(source, **scope)
    assert review.manuscript.word_count == 9000
    assert len(review.manuscript.chapters) == 9
    assert review.manuscript.source_sha256 == source_sha256
    assert review.findings == ()

    result = factory.process(
        source,
        author="Editorial TR.ES",
        **scope,
    )

    assert result.final_work.expression_graph.get_block("chapter-01-body").content == (
        review.manuscript.chapters[0].body
    )
    assert result.final_work.expression_graph.get_block("chapter-09-body").content == (
        review.manuscript.chapters[8].body
    )
    assert len(result.master_edition.blocks) == 18
    assert result.master_edition.reading_order[0] == "chapter-01"
    assert result.master_edition.reading_order[-1] == "chapter-09-body"
    assert result.master_edition.public_metadata["source_sha256"] == source_sha256
    assert result.master_edition.public_metadata["chapter_count"] == 9
    assert result.master_edition.public_metadata["word_count"] == 9000
    assert result.pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in result.pdf_bytes[-1024:]
    page_count = len(re.findall(rb"/Type\s*/Page\b", result.pdf_bytes))
    assert page_count >= 60

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pdf_path = OUTPUT / "una-luz-extrana-en-buenos-aires.pdf"
    edition_path = OUTPUT / "edition-master.json"
    report_path = OUTPUT / "factory-report.json"
    pdf_path.write_bytes(result.pdf_bytes)
    edition_path.write_text(
        result.master_edition.model_dump_json(indent=2),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(
            {
                "accepted": result.accepted_count,
                "chapter_count": 9,
                "edition_sha256": result.master_edition.digest(),
                "findings": len(result.findings),
                "page_count": page_count,
                "pdf_bytes": len(result.pdf_bytes),
                "rejected": result.rejected_count,
                "source_sha256": source_sha256,
                "word_count": 9000,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    assert pdf_path.read_bytes() == result.pdf_bytes
    assert json.loads(report_path.read_text(encoding="utf-8"))["findings"] == 0
