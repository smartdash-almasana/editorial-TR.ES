import pytest
from pydantic import ValidationError

from editorial_tres.domain.edition import EditionBlock, EditionSnapshot


def _blocks():
    return (
        EditionBlock(
            id="chapter-1",
            block_type="heading",
            content="El río",
            position=0,
            language="es",
            metadata={"level": 1},
        ),
        EditionBlock(
            id="paragraph-1",
            block_type="paragraph",
            content="La casa miraba el agua.",
            parent_id="chapter-1",
            position=0,
            language="es",
            metadata={"tags": ["opening", "river"]},
        ),
    )


def _snapshot(**changes):
    values = {
        "edition_id": "edition.casa-del-rio.v1",
        "edition_version": 1,
        "tenant_id": "tenant.almasana",
        "editorial_id": "editorial.tres",
        "work_id": "work.casa-del-rio",
        "source_work_version": 8,
        "source_manuscript_version": 6,
        "title": "La casa del río",
        "language": "es",
        "blocks": _blocks(),
        "reading_order": ("chapter-1", "paragraph-1"),
        "public_metadata": {"author": "Autora de prueba"},
    }
    values.update(changes)
    return EditionSnapshot(**values)


def test_snapshot_is_deeply_immutable_and_json_serializable():
    snapshot = _snapshot()
    with pytest.raises(TypeError):
        snapshot.public_metadata["author"] = "Otra autora"
    with pytest.raises(TypeError):
        snapshot.blocks[1].metadata["tags"] = []
    assert snapshot.model_dump(mode="json")["blocks"][1]["metadata"] == {
        "tags": ["opening", "river"]
    }


def test_snapshot_digest_is_deterministic_for_equivalent_metadata():
    first = _snapshot(public_metadata={"author": "A", "year": 2026})
    second = _snapshot(public_metadata={"year": 2026, "author": "A"})
    assert first.digest() == second.digest()
    assert len(first.digest()) == 64


def test_snapshot_rejects_reading_order_that_diverges_from_blocks():
    with pytest.raises(ValidationError, match="orden de lectura"):
        _snapshot(reading_order=("paragraph-1", "chapter-1"))


def test_snapshot_rejects_parent_that_is_not_already_resolved():
    reversed_blocks = tuple(reversed(_blocks()))
    with pytest.raises(ValidationError, match="debe aparecer antes"):
        _snapshot(
            blocks=reversed_blocks,
            reading_order=("paragraph-1", "chapter-1"),
        )


def test_snapshot_staleness_tracks_material_work_version_only():
    snapshot = _snapshot()

    class Id:
        def __init__(self, value):
            self.value = value

    class WorkStub:
        tenant_id = Id("tenant.almasana")
        editorial_id = Id("editorial.tres")
        work_id = Id("work.casa-del-rio")
        manuscript_version = 6

    work = WorkStub()
    assert snapshot.is_stale_for(work) is False
    work.manuscript_version = 7
    assert snapshot.is_stale_for(work) is True
