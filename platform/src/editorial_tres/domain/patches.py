"""Immutable editorial change proposals."""

from types import MappingProxyType
from typing import Annotated, Any, Literal, Mapping, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

from editorial_tres.domain.graphs.expression import ContentBlock
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId


class PatchOperation(BaseModel):
    """Backward-compatible replace-content operation."""

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


ReplaceContentOperation = PatchOperation


class InsertBlockOperation(BaseModel):
    """Propose one new immutable content block for the expression graph."""

    operation: Literal["insert_block"] = "insert_block"
    block_id: str
    block_type: str
    content: str = ""
    parent_id: Optional[str] = None
    position: int = Field(default=0, ge=0)
    language: str = "es"
    status: str = "draft"
    metadata: Mapping[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}

    @field_validator("block_id")
    @classmethod
    def _required_block_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El block_id del patch es obligatorio.")
        return value.strip()

    @field_validator("parent_id")
    @classmethod
    def _normalize_parent_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("parent_id no puede estar vacío.")
        return normalized

    @field_validator("metadata")
    @classmethod
    def _freeze_metadata(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return MappingProxyType(dict(value))

    @field_serializer("metadata")
    def _serialize_metadata(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return dict(value)

    @model_validator(mode="after")
    def _valid_content_block(self) -> "InsertBlockOperation":
        self.to_content_block()
        return self

    def to_content_block(self) -> ContentBlock:
        return ContentBlock(
            id=self.block_id,
            block_type=self.block_type,
            content=self.content,
            parent_id=self.parent_id,
            position=self.position,
            language=self.language,
            status=self.status,
            metadata=dict(self.metadata),
        )


class DeleteBlockOperation(BaseModel):
    """Propose deletion of one exact content-block state."""

    operation: Literal["delete_block"] = "delete_block"
    block_id: str
    before_block: ContentBlock
    dependent_policy: Literal["reject"] = "reject"

    model_config = {"frozen": True}

    @field_validator("block_id")
    @classmethod
    def _required_block_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El block_id del patch es obligatorio.")
        return value.strip()

    @model_validator(mode="after")
    def _matching_before_state(self) -> "DeleteBlockOperation":
        if self.before_block.id != self.block_id:
            raise ValueError("before_block debe corresponder al block_id eliminado.")
        return self


class MoveBlockOperation(BaseModel):
    """Propose moving one existing block to a new parent and/or position."""

    operation: Literal["move_block"] = "move_block"
    block_id: str
    before_parent_id: Optional[str] = None
    before_position: int = Field(ge=0)
    after_parent_id: Optional[str] = None
    after_position: int = Field(ge=0)

    model_config = {"frozen": True}

    @field_validator("block_id")
    @classmethod
    def _required_block_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El block_id del patch es obligatorio.")
        return value.strip()

    @field_validator("before_parent_id", "after_parent_id")
    @classmethod
    def _normalize_parent_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("El parent_id no puede estar vacío.")
        return normalized

    @model_validator(mode="after")
    def _must_move(self) -> "MoveBlockOperation":
        if self.after_parent_id == self.block_id:
            raise ValueError("Un bloque no puede ser su propio padre.")
        if (
            self.before_parent_id == self.after_parent_id
            and self.before_position == self.after_position
        ):
            raise ValueError("MoveBlockOperation debe proponer un cambio real.")
        return self


PatchOperationVariant = Annotated[
    Union[
        PatchOperation,
        InsertBlockOperation,
        DeleteBlockOperation,
        MoveBlockOperation,
    ],
    Field(discriminator="operation"),
]


class Patch(BaseModel):
    """Immutable proposal produced by one editorial pass over one Work version."""

    patch_id: str
    pass_id: str
    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    branch: str = "main"
    source_version: int = Field(ge=1)
    operations: Tuple[PatchOperationVariant, ...]

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
        cls, value: Tuple[PatchOperationVariant, ...]
    ) -> Tuple[PatchOperationVariant, ...]:
        if not value:
            raise ValueError("Un Patch debe contener al menos una operación.")
        block_ids = [operation.block_id for operation in value]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("Un Patch no puede proponer dos operaciones sobre el mismo bloque.")
        return value
