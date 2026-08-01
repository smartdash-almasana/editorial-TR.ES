"""Narrative graph."""
from typing import Mapping, Optional, List, Set
from pydantic import field_serializer, Field, field_validator
from editorial_tres.domain.graphs.base import BaseGraph, GraphNode
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.immutable_values import deep_freeze, deep_to_jsonable
from editorial_tres.exceptions import GraphCycleError, MissingParentNodeError

ALLOWED_NARRATIVE_TYPES = {"part", "chapter", "scene", "arc", "transition", "promise", "timeline"}
class NarrativeNode(GraphNode):
    node_type: str = Field(default="chapter")
    model_config = {"frozen": True}
    @field_validator("node_type")
    @classmethod
    def _allowed_type(cls, value):
        if value not in ALLOWED_NARRATIVE_TYPES: raise ValueError(f"Tipo narrativo no permitido: {value}")
        return value
class NarrativeGraph(BaseGraph):
    work_id: WorkId
    tenant_id: Optional[TenantId] = None
    editorial_id: Optional[EditorialId] = None
    nodes: Mapping[str, NarrativeNode] = Field(default_factory=dict)
    @field_validator("nodes")
    @classmethod
    def _freeze_nodes(cls, value): return deep_freeze(value)
    @field_serializer("nodes")
    def _serialize_nodes(self, value): return deep_to_jsonable(value)
    def add_node(self, node: NarrativeNode) -> "NarrativeGraph":
        self._check_duplicate(node.id)
        if node.parent_id == node.id: raise GraphCycleError(f"El nodo '{node.id}' no puede referenciarse a sí mismo.")
        if node.parent_id and not self.has_node(node.parent_id): raise MissingParentNodeError(f"El nodo padre '{node.parent_id}' no existe en el grafo narrativo.")
        return NarrativeGraph(work_id=self.work_id, tenant_id=self.tenant_id, editorial_id=self.editorial_id, nodes={**self.nodes, node.id: node})
    def get_children(self, parent_id: str) -> List[NarrativeNode]: return sorted((n for n in self.nodes.values() if n.parent_id == parent_id), key=lambda n: (n.position,n.id))
    def get_roots(self) -> List[NarrativeNode]: return sorted((n for n in self.nodes.values() if n.parent_id is None), key=lambda n: (n.position,n.id))
    def get_nodes_by_type(self, node_type: str) -> List[NarrativeNode]: return [n for n in self.nodes.values() if n.node_type == node_type]


