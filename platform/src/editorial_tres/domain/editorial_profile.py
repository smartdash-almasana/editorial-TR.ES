"""
EditorialProfile — representa una editorial o sello editorial.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from editorial_tres.domain.identifiers import EditorialId, TenantId


class EditorialProfile(BaseModel):
    """Perfil inmutable de una editorial."""

    tenant_id: TenantId
    editorial_id: EditorialId
    name: str
    description: str = ""
    default_language: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"frozen": True}

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El nombre de la editorial es obligatorio.")
        return v.strip()

    @field_validator("default_language")
    @classmethod
    def _validate_language(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El idioma por defecto es obligatorio.")
        return v.strip()
