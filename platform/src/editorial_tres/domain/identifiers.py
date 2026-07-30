"""
Identificadores tipados e inmutables para el dominio de Editorial TR.ES.
"""

import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from editorial_tres.exceptions import InvalidIdentifierError

# Patrón común: prefijo.nombre (p. ej. tenant.almasana)
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_PREFIJOS = {
    "TenantId": "tenant",
    "EditorialId": "editorial",
    "WorkId": "work",
    "ActorId": "actor",
}


class _TypedId(BaseModel):
    """Identificador tipado, inmutable y validado."""

    value: str = Field(..., frozen=True)

    model_config = {"frozen": True}

    @field_validator("value")
    @classmethod
    def _validate_value(cls, v: str) -> str:
        if not v or not v.strip():
            raise InvalidIdentifierError("El identificador no puede estar vacío.")
        v = v.strip()
        parts = v.split(".", 1)
        expected_prefix = _PREFIJOS.get(cls.__name__)
        if expected_prefix and (len(parts) != 2 or parts[0] != expected_prefix):
            raise InvalidIdentifierError(
                f"El identificador '{v}' debe comenzar con el prefijo '{expected_prefix}.'."
            )
        if len(parts) == 2:
            suffix = parts[1]
        else:
            suffix = parts[0]
        if not suffix:
            raise InvalidIdentifierError(
                f"El identificador '{v}' no tiene un sufijo válido."
            )
        if not _ID_PATTERN.match(suffix):
            raise InvalidIdentifierError(
                f"El sufijo del identificador '{v}' no cumple el formato permitido."
            )
        return v

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"

    def __hash__(self) -> int:
        return hash(self.value)


class TenantId(_TypedId):
    """Identificador de tenant (inquilino organizacional)."""

    pass


class EditorialId(_TypedId):
    """Identificador de sello editorial."""

    pass


class WorkId(_TypedId):
    """Identificador de obra."""

    pass


class ActorId(_TypedId):
    """Identificador de actor (persona o sistema que ejecuta acciones)."""

    pass
