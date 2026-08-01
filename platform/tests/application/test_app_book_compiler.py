import json

from editorial_tres.application.app_book_compiler import (
    APP_BOOK_FORMAT_VERSION,
    AppBookCompiler,
)
from editorial_tres.domain.edition import EditionBlock, EditionSnapshot


def _snapshot():
    blocks = (
        EditionBlock(
            id="chapter",
            block_type="heading",
            content="La casa del río",
            position=0,
            language="es",
        ),
        EditionBlock(
            id="paragraph",
            block_type="paragraph",
            content="La casa miraba el agua.",
            parent_id="chapter",
            position=0,
            language="es",
        ),
    )
    return EditionSnapshot(
        edition_id="edition.casa-del-rio.v1",
        edition_version=2,
        tenant_id="tenant.almasana",
        editorial_id="editorial.tres",
        work_id="work.casa-del-rio",
        source_work_version=8,
        source_manuscript_version=6,
        title="La casa del río",
        language="es",
        blocks=blocks,
        reading_order=("chapter", "paragraph"),
        public_metadata={"author": "Autora de prueba"},
    )


def test_compiles_deterministic_versioned_manifest_and_content():
    compiler = AppBookCompiler()
    first = compiler.compile(_snapshot())
    second = compiler.compile(_snapshot())

    assert first == second
    assert first.format_version == APP_BOOK_FORMAT_VERSION
    assert first.manifest.format_version == APP_BOOK_FORMAT_VERSION
    assert first.manifest.edition_version == 2
    assert first.manifest.reading_order == ("chapter", "paragraph")
    assert tuple(block.id for block in first.blocks) == (
        "chapter",
        "paragraph",
    )
    assert first.verify_integrity() is True


def test_package_has_all_sha256_integrity_entries():
    package = AppBookCompiler().compile(_snapshot())
    assert set(package.checksums) == {
        "snapshot",
        "manifest",
        "content",
        "package",
    }
    assert all(len(value) == 64 for value in package.checksums.values())


def test_package_json_is_portable_and_excludes_internal_production_state():
    package = AppBookCompiler().compile(_snapshot())
    payload = json.loads(package.to_json())
    assert payload["manifest"]["title"] == "La casa del río"
    assert payload["manifest"]["public_metadata"]["author"] == "Autora de prueba"
    serialized = package.to_json().lower()
    for internal_term in (
        "prompt",
        "finding",
        "patch",
        "approvalgate",
        "provider",
    ):
        assert internal_term not in serialized


def test_integrity_detects_tampered_checksum():
    package = AppBookCompiler().compile(_snapshot())
    tampered_checksums = dict(package.checksums)
    tampered_checksums["content"] = "0" * 64
    tampered = package.model_copy(update={"checksums": tampered_checksums})
    assert tampered.verify_integrity() is False
