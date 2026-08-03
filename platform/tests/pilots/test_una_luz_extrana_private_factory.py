import hashlib
from datetime import datetime, timezone
from pathlib import Path

from editorial_tres.application.private_factory import (
    EditionApprovalInput,
    PrivateEditorialFactory,
)
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.infrastructure.memory.event_store import MemoryEventStore


PROJECT = Path(__file__).parents[3] / "projects" / "una-luz-extrana-en-buenos-aires"
SOURCE = PROJECT / "manuscript.txt"


def test_complete_real_manuscript_reaches_persistent_master_and_all_derivatives():
    source = SOURCE.read_text(encoding="utf-8")
    source_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    store = MemoryEventStore()
    factory = PrivateEditorialFactory(event_store=store)
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

    prepared = factory.prepare(source, decisions=(), **scope)
    pending = prepared.pending_approval
    result = factory.publish(
        source,
        author="Editorial TR.ES",
        approval=EditionApprovalInput(
            approval_id=pending.approval_id,
            work_id=pending.work_id.value,
            source_work_version=pending.source_work_version,
            source_manuscript_version=pending.source_manuscript_version,
            status="approved",
            actor_id="actor.directora-editorial",
            reason="La edición exacta fue revisada y autorizada.",
            decided_at=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
        ),
        **scope,
    )

    first_chapter_paragraphs = tuple(
        block.content
        for block in result.master_edition.blocks
        if block.parent_id == "chapter-01"
    )
    last_chapter_paragraphs = tuple(
        block.content
        for block in result.master_edition.blocks
        if block.parent_id == "chapter-09"
    )
    assert first_chapter_paragraphs == review.manuscript.chapters[0].paragraphs
    assert last_chapter_paragraphs == review.manuscript.chapters[8].paragraphs
    assert len(result.master_edition.blocks) > 18
    assert result.master_edition.reading_order[0] == "chapter-01"
    assert result.master_edition.reading_order[-1].startswith(
        "chapter-09-paragraph-"
    )
    assert result.master_edition.public_metadata["source_sha256"] == source_sha256
    assert result.master_edition.public_metadata["chapter_count"] == 9
    assert result.master_edition.public_metadata["word_count"] == 9000
    assert result.app_book.verify_integrity() is True
    assert result.app_book.manifest.reading_order == result.master_edition.reading_order
    assert result.html.startswith("<!doctype html>")
    assert result.pdf_bytes.startswith(b"%PDF-")
    assert len(result.pdf_bytes) > 100_000
    assert store.get_edition_approval(pending.approval_id) == result.edition_approval
