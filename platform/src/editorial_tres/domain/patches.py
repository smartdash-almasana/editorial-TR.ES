"""Immutable editorial change proposals."""

from typing import Literal, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId


class PatchOperation(BaseModel):
    """One atomic proposed change against the expression graph."""

    operation: Literal["replace_content"] = "replace_content"
    block_id: str
    before_content: str
    after_content: str

    model_config = {"frozen": True}

    @field_validator("block_id")
    @classmethod
    def _required_block_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El block_id del patch es obligatorio.")
        return value.strip()

    @model_validator(mode="after")
    def _must_change_content(self) -> "PatchOperation":
        if self.before_content == self.after_content:
            raise ValueError("Un PatchOperation debe proponer un cambio real.")
        return self


class Patch(BaseModel):
    """Immutable proposal produced by one editorial pass over one Work version."""

    patch_id: str
    pass_id: str
    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    branch: str = "main"
    source_version: int = Field(ge=1)
    operations: Tuple[PatchOperation, ...]

    model_config = {"frozen": True}

    @field_validator("patch_id", "pass_id", "branch")
    @classmethod
    def _required_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El valor es obligatorio.")
        return value.strip()

    @field_validator("operations")
    @classmethod
    def _operations_not_empty(
        cls, value: Tuple[PatchOperation, ...]
    ) -> Tuple[PatchOperation, ...]:
        if not value:
            raise ValueError("Un Patch debe contener al menos una operación.")
        block_ids = [operation.block_id for operation in value]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("Un Patch no puede proponer dos operaciones sobre el mismo bloque.")
        return value
