"""Expression graph and immutable content blocks."""
from typing import Any, Mapping, Optional, List
from pydantic import field_serializer, BaseModel, Field, field_validator
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.immutable_values import deep_freeze, deep_to_jsonable
from editorial_tres.exceptions import DuplicateNodeError, GraphCycleError, MissingParentNodeError

ALLOWED_BLOCK_TYPES = {"paragraph", "heading", "dialogue", "quote", "poem", "note"}
ALLOWED_BLOCK_STATUSES = {"draft", "revised", "approved"}

class ContentBlock(BaseModel):
    id: str
    block_type: str
    content: str = ""
    parent_id: Optional[str] = None
    position: int = Field(default=0, ge=0)
    language: str = "es"
    status: str = "draft"
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    model_config = {"frozen": True}

    @field_validator("metadata")
    @classmethod
    def _freeze_metadata(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return deep_freeze(value)

    @field_serializer("metadata", when_used="json")
    def _serialize_metadata(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return deep_to_jsonable(value)

    @field_validator("block_type")
    @classmethod
    def _validate_block_type(cls, value: str) -> str:
        if value not in ALLOWED_BLOCK_TYPES:
            raise ValueError(f"Tipo de bloque '{value}' no permitido.")
        return value

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        if value not in ALLOWED_BLOCK_STATUSES:
            raise ValueError(f"Estado '{value}' no permitido.")
        return value

class ExpressionGraph(BaseModel):
    work_id: WorkId
    tenant_id: Optional[TenantId] = None
    editorial_id: Optional[EditorialId] = None
    blocks: Mapping[str, ContentBlock] = Field(default_factory=dict)
    model_config = {"frozen": True}

    @field_validator("blocks")
    @classmethod
    def _freeze_blocks(cls, value: Mapping[str, ContentBlock]) -> Mapping[str, ContentBlock]:
        return deep_freeze(value)

    @field_serializer("blocks")
    def _serialize_blocks(self, value): return deep_to_jsonable(value)
    def add_block(self, block: ContentBlock) -> "ExpressionGraph":
        if block.id in self.blocks:
            raise DuplicateNodeError(f"El bloque con ID '{block.id}' ya existe en el grafo de expresión.")
        if block.parent_id and block.parent_id not in self.blocks:
            raise MissingParentNodeError(f"El bloque padre '{block.parent_id}' no existe en el grafo de expresión.")
        if block.block_type != "heading" and not block.content.strip():
            raise ValueError(f"El contenido del bloque '{block.id}' no puede estar vacío.")
        return ExpressionGraph(work_id=self.work_id, tenant_id=self.tenant_id, editorial_id=self.editorial_id, blocks={**self.blocks, block.id: block})

    def edit_block(self, block: ContentBlock) -> "ExpressionGraph":
        if block.id not in self.blocks:
            raise MissingParentNodeError(f"El bloque '{block.id}' no existe en el grafo de expresión.")
        if block.parent_id and block.parent_id not in self.blocks:
            raise MissingParentNodeError(f"El bloque padre '{block.parent_id}' no existe en el grafo de expresión.")
        if block.block_type != "heading" and not block.content.strip():
            raise ValueError(f"El contenido del bloque '{block.id}' no puede estar vacío.")
        return ExpressionGraph(work_id=self.work_id, tenant_id=self.tenant_id, editorial_id=self.editorial_id, blocks={**self.blocks, block.id: block})

    def delete_block(self, block_id: str) -> "ExpressionGraph":
        if block_id not in self.blocks:
            raise MissingParentNodeError(f"El bloque '{block_id}' no existe en el grafo de expresión.")
        if self.get_children(block_id):
            raise ValueError(f"El bloque '{block_id}' no puede eliminarse mientras tenga hijos.")
        remaining = dict(self.blocks)
        del remaining[block_id]
        return ExpressionGraph(
            work_id=self.work_id,
            tenant_id=self.tenant_id,
            editorial_id=self.editorial_id,
            blocks=remaining,
        )

    def move_block(
        self,
        block_id: str,
        *,
        parent_id: Optional[str],
        position: int,
    ) -> "ExpressionGraph":
        block = self.get_block(block_id)
        if block is None:
            raise MissingParentNodeError(f"El bloque '{block_id}' no existe en el grafo de expresión.")
        if position < 0:
            raise ValueError("La posición del bloque no puede ser negativa.")
        if parent_id == block_id:
            raise GraphCycleError(f"El bloque '{block_id}' no puede ser su propio padre.")
        if parent_id is not None and parent_id not in self.blocks:
            raise MissingParentNodeError(f"El bloque padre '{parent_id}' no existe en el grafo de expresión.")

        current_parent_id = parent_id
        visited = set()
        while current_parent_id is not None:
            if current_parent_id == block_id:
                raise GraphCycleError(
                    f"Mover '{block_id}' bajo '{parent_id}' produciría un ciclo."
                )
            if current_parent_id in visited:
                raise GraphCycleError("El grafo de expresión ya contiene un ciclo parental.")
            visited.add(current_parent_id)
            current_parent = self.get_block(current_parent_id)
            current_parent_id = current_parent.parent_id if current_parent else None

        moved_block = block.model_copy(
            update={"parent_id": parent_id, "position": position}
        )
        return self.edit_block(moved_block)

    def get_block(self, block_id: str) -> Optional[ContentBlock]: return self.blocks.get(block_id)
    def has_block(self, block_id: str) -> bool: return block_id in self.blocks
    def get_all_blocks(self) -> List[ContentBlock]: return sorted(self.blocks.values(), key=lambda b: (b.position, b.id))
    def get_children(self, parent_id: str) -> List[ContentBlock]: return sorted((b for b in self.blocks.values() if b.parent_id == parent_id), key=lambda b: (b.position, b.id))
    def get_roots(self) -> List[ContentBlock]: return sorted((b for b in self.blocks.values() if b.parent_id is None), key=lambda b: (b.position, b.id))
    def get_blocks_by_type(self, block_type: str) -> List[ContentBlock]: return [b for b in self.blocks.values() if b.block_type == block_type]


