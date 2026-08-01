"""Base classes for specialized immutable graphs."""
from typing import Any, Mapping, List, Optional
from pydantic import BaseModel, Field, field_serializer, field_validator
from editorial_tres.domain.identifiers import WorkId
from editorial_tres.domain.immutable_values import deep_freeze, deep_to_jsonable
from editorial_tres.exceptions import DuplicateNodeError
class GraphNode(BaseModel):
    id: str
    node_type: str
    title: str = ""
    parent_id: Optional[str] = None
    position: int = Field(default=0, ge=0)
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    model_config = {"frozen": True}
    @field_validator("metadata")
    @classmethod
    def _freeze_metadata(cls, value): return deep_freeze(value)
    @field_serializer("metadata")
    def _serialize_metadata(self, value): return deep_to_jsonable(value)
class BaseGraph(BaseModel):
    work_id: WorkId
    nodes: Mapping[str, GraphNode] = Field(default_factory=dict)
    model_config = {"frozen": True}
    @field_validator("nodes")
    @classmethod
    def _freeze_nodes(cls, value): return deep_freeze(value)
    @field_serializer("nodes")
    def _serialize_nodes(self, value): return deep_to_jsonable(value)
    def get_node(self, node_id: str) -> Optional[GraphNode]: return self.nodes.get(node_id)
    def has_node(self, node_id: str) -> bool: return node_id in self.nodes
    def get_all_nodes(self) -> List[GraphNode]: return sorted(self.nodes.values(), key=lambda n: (n.position, n.id))
    def _check_duplicate(self, node_id: str) -> None:
        if node_id in self.nodes: raise DuplicateNodeError(f"El nodo con ID '{node_id}' ya existe en el grafo.")
