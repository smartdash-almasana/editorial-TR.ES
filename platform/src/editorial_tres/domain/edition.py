"""Neutral, immutable publication snapshot for one approved editorial edition."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Literal, TYPE_CHECKING

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from editorial_tres.domain.graphs.expression import ALLOWED_BLOCK_TYPES
from editorial_tres.domain.identifiers import ActorId, EditorialId, TenantId, WorkId
from editorial_tres.domain.immutable_values import canonical_json, deep_freeze, deep_to_jsonable

if TYPE_CHECKING:
    from editorial_tres.domain.work import Work


EDITION_SNAPSHOT_SCHEMA_VERSION = "editorial.tres/edition-snapshot-v1"


class EditionBlock(BaseModel):
    """Public, addressable content copied out of the mutable production graph."""

    id: str
    block_type: str
    content: str
    parent_id: str | None = None
    position: int = Field(ge=0)
    language: str
    metadata: Mapping[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}

    @field_validator("id", "language")
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Los identificadores y el idioma de edición son obligatorios.")
        return normalized

    @field_validator("block_type")
    @classmethod
    def _supported_block_type(cls, value: str) -> str:
        if value not in ALLOWED_BLOCK_TYPES:
            raise ValueError(f"Tipo de bloque editorial '{value}' no permitido.")
        return value

    @field_validator("content")
    @classmethod
    def _publishable_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Un bloque de edición no puede tener contenido vacío.")
        return value

    @field_validator("metadata")
    @classmethod
    def _portable_metadata(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        canonical_json(value)
        return deep_freeze(value)

    @field_serializer("metadata", when_used="json")
    def _serialize_metadata(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return deep_to_jsonable(value)


class EditionSnapshot(BaseModel):
    """Format-neutral master edition from which every public derivative is built."""

    schema_version: str = EDITION_SNAPSHOT_SCHEMA_VERSION
    edition_id: str
    edition_version: int = Field(ge=1)
    tenant_id: str
    editorial_id: str
    work_id: str
    source_work_version: int = Field(ge=1)
    source_manuscript_version: int = Field(ge=1)
    title: str
    language: str
    blocks: tuple[EditionBlock, ...]
    reading_order: tuple[str, ...]
    public_metadata: Mapping[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}

    @field_validator(
        "schema_version",
        "edition_id",
        "tenant_id",
        "editorial_id",
        "work_id",
        "title",
        "language",
    )
    @classmethod
    def _required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Los datos de identidad de una edición son obligatorios.")
        return normalized

    @field_validator("public_metadata")
    @classmethod
    def _portable_public_metadata(
        cls, value: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        canonical_json(value)
        return deep_freeze(value)

    @field_serializer("public_metadata", when_used="json")
    def _serialize_public_metadata(
        self, value: Mapping[str, Any]
    ) -> dict[str, Any]:
        return deep_to_jsonable(value)

    @model_validator(mode="after")
    def _consistent_structure(self) -> "EditionSnapshot":
        if self.schema_version != EDITION_SNAPSHOT_SCHEMA_VERSION:
            raise ValueError(
                f"Versión de EditionSnapshot no soportada: {self.schema_version}."
            )
        if not self.blocks:
            raise ValueError("La edición debe contener al menos un bloque publicable.")

        block_ids = tuple(block.id for block in self.blocks)
        if len(set(block_ids)) != len(block_ids):
            raise ValueError("Una edición no puede contener IDs de bloque duplicados.")
        if self.reading_order != block_ids:
            raise ValueError(
                "El orden de lectura debe coincidir exactamente con el orden de los bloques."
            )

        available: set[str] = set()
        for block in self.blocks:
            if block.parent_id is not None and block.parent_id not in available:
                raise ValueError(
                    f"El padre '{block.parent_id}' del bloque '{block.id}' "
                    "debe aparecer antes en la edición."
                )
            available.add(block.id)
        return self

    def digest(self) -> str:
        """Stable checksum for the complete neutral edition."""

        payload = deep_to_jsonable(self)
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()

    def is_stale_for(self, work: "Work") -> bool:
        """Detect material divergence without invalidating on review-only events."""

        return (
            self.tenant_id != work.tenant_id.value
            or self.editorial_id != work.editorial_id.value
            or self.work_id != work.work_id.value
            or self.source_manuscript_version != work.manuscript_version
        )


EditionApprovalStatus = Literal["pending", "approved", "rejected"]


class EditionApproval(BaseModel):
    """Explicit authorization for publishing one exact material Work snapshot."""

    approval_id: str
    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    branch: str = "main"
    source_work_version: int = Field(ge=1)
    source_manuscript_version: int = Field(ge=1)
    status: EditionApprovalStatus = "pending"
    decided_by: ActorId | None = None
    reason: str | None = None
    decided_at: datetime | None = None

    model_config = {"frozen": True}

    @field_validator("approval_id", "branch")
    @classmethod
    def _required_approval_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("La aprobación de edición requiere identidad y rama.")
        return normalized

    @model_validator(mode="after")
    def _consistent_decision(self) -> "EditionApproval":
        if self.status == "pending":
            if self.decided_by is not None or self.decided_at is not None:
                raise ValueError("Una aprobación pendiente no puede registrar decisión.")
        elif self.decided_by is None or self.decided_at is None:
            raise ValueError("Una aprobación resuelta requiere actor y fecha.")
        return self

    @classmethod
    def for_work(
        cls,
        work: "Work",
        *,
        approval_id: str,
        branch: str = "main",
    ) -> "EditionApproval":
        return cls(
            approval_id=approval_id,
            tenant_id=work.tenant_id,
            editorial_id=work.editorial_id,
            work_id=work.work_id,
            branch=branch,
            source_work_version=work.version,
            source_manuscript_version=work.manuscript_version,
        )

    def approve(
        self,
        *,
        actor_id: ActorId,
        reason: str,
        decided_at: datetime | None = None,
    ) -> "EditionApproval":
        if self.status != "pending":
            raise ValueError("Una aprobación de edición ya resuelta no puede decidirse otra vez.")
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ValueError("La aprobación de edición debe conservar su fundamento.")
        return self.model_copy(
            update={
                "status": "approved",
                "decided_by": actor_id,
                "reason": normalized_reason,
                "decided_at": decided_at or datetime.now(timezone.utc),
            }
        )

    def authorizes(self, work: "Work", *, branch: str = "main") -> bool:
        return (
            self.status == "approved"
            and self.tenant_id == work.tenant_id
            and self.editorial_id == work.editorial_id
            and self.work_id == work.work_id
            and self.branch == branch
            and self.source_work_version == work.version
            and self.source_manuscript_version == work.manuscript_version
        )
