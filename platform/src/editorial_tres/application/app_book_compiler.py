"""Deterministic App Book Format v1 compiler."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from editorial_tres.domain.edition import EditionBlock, EditionSnapshot
from editorial_tres.domain.immutable_values import canonical_json, deep_freeze, deep_to_jsonable


APP_BOOK_FORMAT_VERSION = "1.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class AppBookManifest(BaseModel):
    """Public identity and navigation contract consumed by a Reader."""

    format_version: str = APP_BOOK_FORMAT_VERSION
    edition_id: str
    edition_version: int = Field(ge=1)
    work_id: str
    title: str
    language: str
    reading_order: tuple[str, ...]
    assets: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ("text", "navigation")
    source_manuscript_version: int = Field(ge=1)
    snapshot_sha256: str
    public_metadata: Mapping[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}

    @field_validator("public_metadata")
    @classmethod
    def _freeze_public_metadata(
        cls, value: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        canonical_json(value)
        return deep_freeze(value)

    @field_serializer("public_metadata", when_used="json")
    def _serialize_public_metadata(
        self, value: Mapping[str, Any]
    ) -> dict[str, Any]:
        return deep_to_jsonable(value)

    @field_validator("snapshot_sha256")
    @classmethod
    def _valid_snapshot_checksum(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("El checksum del EditionSnapshot no es SHA-256 válido.")
        return value


class AppBookPackage(BaseModel):
    """Portable, integrity-verifiable App Book payload."""

    format_version: str = APP_BOOK_FORMAT_VERSION
    manifest: AppBookManifest
    blocks: tuple[EditionBlock, ...]
    checksums: Mapping[str, str]

    model_config = {"frozen": True}

    @field_validator("checksums")
    @classmethod
    def _freeze_checksums(cls, value: Mapping[str, str]) -> Mapping[str, str]:
        required = {"snapshot", "manifest", "content", "package"}
        if set(value) != required:
            raise ValueError(
                "El paquete requiere checksums de snapshot, manifest, content y package."
            )
        if any(not _SHA256.fullmatch(checksum) for checksum in value.values()):
            raise ValueError("Todos los checksums del paquete deben ser SHA-256 válidos.")
        return deep_freeze(value)

    @field_serializer("checksums", when_used="json")
    def _serialize_checksums(self, value: Mapping[str, str]) -> dict[str, str]:
        return dict(value)

    @model_validator(mode="after")
    def _consistent_reading_order(self) -> "AppBookPackage":
        if self.format_version != APP_BOOK_FORMAT_VERSION:
            raise ValueError(
                f"Versión de App Book Format no soportada: {self.format_version}."
            )
        if self.manifest.format_version != self.format_version:
            raise ValueError("Manifest y paquete declaran versiones incompatibles.")
        if self.manifest.reading_order != tuple(block.id for block in self.blocks):
            raise ValueError("El manifest no coincide con los bloques del paquete.")
        return self

    def verify_integrity(self) -> bool:
        content = _content_payload(self.blocks, self.manifest.reading_order)
        manifest_payload = deep_to_jsonable(self.manifest)
        base_checksums = {
            "snapshot": self.manifest.snapshot_sha256,
            "manifest": _sha256(manifest_payload),
            "content": _sha256(content),
        }
        expected_package = _package_checksum(
            self.format_version, manifest_payload, content, base_checksums
        )
        return dict(self.checksums) == {
            **base_checksums,
            "package": expected_package,
        }

    def to_json(self, *, indent: int | None = None) -> str:
        payload = self.model_dump(mode="json")
        if indent is None:
            return canonical_json(payload)
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=indent,
            allow_nan=False,
        )


def _content_payload(
    blocks: tuple[EditionBlock, ...], reading_order: tuple[str, ...]
) -> dict[str, Any]:
    return {
        "reading_order": list(reading_order),
        "blocks": [deep_to_jsonable(block) for block in blocks],
    }


def _package_checksum(
    format_version: str,
    manifest_payload: Mapping[str, Any],
    content_payload: Mapping[str, Any],
    checksums: Mapping[str, str],
) -> str:
    return _sha256(
        {
            "format_version": format_version,
            "manifest": manifest_payload,
            "content": content_payload,
            "checksums": dict(checksums),
        }
    )


class AppBookCompiler:
    """Compile one neutral snapshot into App Book Format v1."""

    def compile(self, snapshot: EditionSnapshot) -> AppBookPackage:
        snapshot_checksum = snapshot.digest()
        manifest = AppBookManifest(
            edition_id=snapshot.edition_id,
            edition_version=snapshot.edition_version,
            work_id=snapshot.work_id,
            title=snapshot.title,
            language=snapshot.language,
            reading_order=snapshot.reading_order,
            source_manuscript_version=snapshot.source_manuscript_version,
            snapshot_sha256=snapshot_checksum,
            public_metadata=snapshot.public_metadata,
        )
        content = _content_payload(snapshot.blocks, snapshot.reading_order)
        manifest_payload = deep_to_jsonable(manifest)
        checksums = {
            "snapshot": snapshot_checksum,
            "manifest": _sha256(manifest_payload),
            "content": _sha256(content),
        }
        checksums["package"] = _package_checksum(
            APP_BOOK_FORMAT_VERSION,
            manifest_payload,
            content,
            checksums,
        )
        return AppBookPackage(
            manifest=manifest,
            blocks=snapshot.blocks,
            checksums=checksums,
        )
