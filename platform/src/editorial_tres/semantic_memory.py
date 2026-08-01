"""Semantic memory, retrieval and context-bound editorial execution.

Canonical state remains in Work/WorkGraph. Memory objects are projections or
approved reference material; retrieval is advisory; PassMemory is ephemeral.
"""

from __future__ import annotations

import re
from typing import List, Literal, Sequence, Tuple

from pydantic import BaseModel, Field, field_validator

from editorial_tres.domain.editorial_passes import EditorialPass
from editorial_tres.domain.graphs.expression import ContentBlock
from editorial_tres.domain.graphs.knowledge import KnowledgeNode
from editorial_tres.domain.graphs.narrative import NarrativeNode
from editorial_tres.domain.identifiers import EditorialId, TenantId, WorkId
from editorial_tres.domain.patches import Patch
from editorial_tres.domain.reviews import ReviewFinding, Reviewer
from editorial_tres.domain.work import Work


MemoryRefKind = Literal["expression_block", "knowledge_node", "narrative_node"]


def _required_text(value: str, message: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(message)
    return normalized


class MemoryRef(BaseModel):
    """Versioned reference to canonical semantic state."""

    kind: MemoryRefKind
    target_id: str

    model_config = {"frozen": True}

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, value: str) -> str:
        return _required_text(value, "La referencia de memoria requiere target_id.")


class WorkMemoryProjection(BaseModel):
    """Non-authoritative semantic projection over one exact Work version."""

    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    source_version: int = Field(ge=1)
    refs: List[MemoryRef] = Field(default_factory=list)

    model_config = {"frozen": True}

    @classmethod
    def from_work(cls, work: Work) -> "WorkMemoryProjection":
        refs: list[MemoryRef] = []
        refs.extend(MemoryRef(kind="expression_block", target_id=block.id) for block in work.expression_graph.get_all_blocks())
        refs.extend(MemoryRef(kind="knowledge_node", target_id=node.id) for node in work.knowledge_graph.get_all_nodes())
        refs.extend(MemoryRef(kind="narrative_node", target_id=node.id) for node in work.narrative_graph.get_all_nodes())
        return cls(
            tenant_id=work.tenant_id,
            editorial_id=work.editorial_id,
            work_id=work.work_id,
            source_version=work.version,
            refs=refs,
        )


class EditorialMemory(BaseModel):
    """Approved institutional memory; it constrains but does not impersonate an author."""

    editorial_id: EditorialId
    constitution: List[str] = Field(default_factory=list)
    policies: List[str] = Field(default_factory=list)
    terminology: List[str] = Field(default_factory=list)
    approval_criteria: List[str] = Field(default_factory=list)

    model_config = {"frozen": True}


class AuthorMemory(BaseModel):
    """Approved author memory preserving identity without reducing it to mimicry."""

    author_id: str
    invariants: List[str] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    occasional_resources: List[str] = Field(default_factory=list)
    anti_patterns: List[str] = Field(default_factory=list)
    approved_examples: List[str] = Field(default_factory=list)
    rejected_examples: List[str] = Field(default_factory=list)

    model_config = {"frozen": True}

    @field_validator("author_id")
    @classmethod
    def validate_author_id(cls, value: str) -> str:
        return _required_text(value, "AuthorMemory requiere author_id.")


class RetrievalRequest(BaseModel):
    """Purpose-specific retrieval request over one WorkMemoryProjection."""

    query: str
    kinds: List[MemoryRefKind] = Field(default_factory=list)
    target_ids: List[str] = Field(default_factory=list)
    max_results: int = Field(default=8, ge=1, le=100)

    model_config = {"frozen": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        return _required_text(value, "MemoryRetriever requiere una consulta explícita.")


class MemoryRetriever:
    """Deterministic lexical/metadata retriever over canonical Work references.

    This is intentionally not a truth source. It ranks references already
    authorized by WorkMemoryProjection and resolves text from canonical Work.
    """

    def retrieve(self, work: Work, memory: WorkMemoryProjection, request: RetrievalRequest) -> List[MemoryRef]:
        self._validate_scope(work, memory)
        allowed = {(ref.kind, ref.target_id): ref for ref in memory.refs}
        kind_filter = set(request.kinds)
        explicit_targets = set(request.target_ids)
        tokens = tuple(sorted(set(re.findall(r"\w+", request.query.casefold()))))
        scored: list[tuple[int, int, str, MemoryRef]] = []

        for key, ref in allowed.items():
            if kind_filter and ref.kind not in kind_filter:
                continue
            searchable = self._searchable_text(work, ref).casefold()
            lexical_score = sum(1 for token in tokens if token in searchable)
            explicit_score = 1 if ref.target_id in explicit_targets else 0
            if lexical_score == 0 and explicit_score == 0:
                continue
            scored.append((explicit_score, lexical_score, f"{ref.kind}:{ref.target_id}", ref))

        scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
        return [item[3] for item in scored[: request.max_results]]

    @staticmethod
    def _validate_scope(work: Work, memory: WorkMemoryProjection) -> None:
        if (memory.tenant_id, memory.editorial_id, memory.work_id) != (work.tenant_id, work.editorial_id, work.work_id):
            raise ValueError("La memoria no pertenece al mismo ámbito que Work.")
        if memory.source_version != work.version:
            raise ValueError("La memoria está obsoleta respecto de la versión canónica de Work.")

    @staticmethod
    def _searchable_text(work: Work, ref: MemoryRef) -> str:
        if ref.kind == "expression_block":
            block = work.expression_graph.get_block(ref.target_id)
            if block is None:
                raise ValueError(f"Bloque canónico no encontrado: {ref.target_id}")
            return " ".join((block.id, block.block_type, block.content, str(dict(block.metadata))))
        if ref.kind == "knowledge_node":
            node = work.knowledge_graph.get_node(ref.target_id)
            if node is None:
                raise ValueError(f"Nodo de conocimiento no encontrado: {ref.target_id}")
            return " ".join((node.id, node.node_type, node.title, str(dict(node.metadata))))
        node = work.narrative_graph.get_node(ref.target_id)
        if node is None:
            raise ValueError(f"Nodo narrativo no encontrado: {ref.target_id}")
        return " ".join((node.id, node.node_type, node.title, str(dict(node.metadata))))


class PassMemory(BaseModel):
    """Ephemeral minimum context for one editorial operation."""

    tenant_id: TenantId
    editorial_id: EditorialId
    work_id: WorkId
    source_version: int = Field(ge=1)
    purpose: str
    editorial_context: List[str] = Field(default_factory=list)
    author_context: List[str] = Field(default_factory=list)
    expression_blocks: List[ContentBlock] = Field(default_factory=list)
    knowledge_nodes: List[KnowledgeNode] = Field(default_factory=list)
    narrative_nodes: List[NarrativeNode] = Field(default_factory=list)

    model_config = {"frozen": True}

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, value: str) -> str:
        return _required_text(value, "PassMemory requiere un propósito explícito.")


class ContextBuilder:
    """Resolve selected references and approved memories into minimal PassMemory."""

    def build(
        self,
        work: Work,
        memory: WorkMemoryProjection,
        *,
        purpose: str,
        refs: List[MemoryRef],
        editorial_memory: EditorialMemory | None = None,
        author_memory: AuthorMemory | None = None,
        max_editorial_items: int = 4,
        max_author_items: int = 6,
    ) -> PassMemory:
        MemoryRetriever._validate_scope(work, memory)
        if editorial_memory is not None and editorial_memory.editorial_id != work.editorial_id:
            raise ValueError("EditorialMemory no pertenece a la editorial de Work.")
        if max_editorial_items < 0 or max_author_items < 0:
            raise ValueError("Los presupuestos de contexto no pueden ser negativos.")

        allowed = {(ref.kind, ref.target_id) for ref in memory.refs}
        requested = [(ref.kind, ref.target_id) for ref in refs]
        if len(requested) != len(set(requested)):
            raise ValueError("El contexto solicitado contiene referencias duplicadas.")

        expression_blocks: list[ContentBlock] = []
        knowledge_nodes: list[KnowledgeNode] = []
        narrative_nodes: list[NarrativeNode] = []
        for ref in refs:
            if (ref.kind, ref.target_id) not in allowed:
                raise ValueError(f"La referencia {ref.kind}:{ref.target_id} no pertenece a esta memoria.")
            if ref.kind == "expression_block":
                target = work.expression_graph.get_block(ref.target_id)
                if target is None:
                    raise ValueError(f"Bloque canónico no encontrado: {ref.target_id}")
                expression_blocks.append(target)
            elif ref.kind == "knowledge_node":
                target = work.knowledge_graph.get_node(ref.target_id)
                if target is None:
                    raise ValueError(f"Nodo de conocimiento no encontrado: {ref.target_id}")
                knowledge_nodes.append(target)
            else:
                target = work.narrative_graph.get_node(ref.target_id)
                if target is None:
                    raise ValueError(f"Nodo narrativo no encontrado: {ref.target_id}")
                narrative_nodes.append(target)

        editorial_context = self._select_editorial(editorial_memory, max_editorial_items)
        author_context = self._select_author(author_memory, max_author_items)
        return PassMemory(
            tenant_id=work.tenant_id,
            editorial_id=work.editorial_id,
            work_id=work.work_id,
            source_version=work.version,
            purpose=purpose,
            editorial_context=editorial_context,
            author_context=author_context,
            expression_blocks=expression_blocks,
            knowledge_nodes=knowledge_nodes,
            narrative_nodes=narrative_nodes,
        )

    @staticmethod
    def _select_editorial(memory: EditorialMemory | None, limit: int) -> List[str]:
        if memory is None or limit == 0:
            return []
        ordered = memory.constitution + memory.policies + memory.terminology + memory.approval_criteria
        return ordered[:limit]

    @staticmethod
    def _select_author(memory: AuthorMemory | None, limit: int) -> List[str]:
        if memory is None or limit == 0:
            return []
        ordered = (
            memory.invariants
            + memory.patterns
            + memory.occasional_resources
            + memory.anti_patterns
            + memory.approved_examples
            + memory.rejected_examples
        )
        return ordered[:limit]


class PreparedEditorialOperation(BaseModel):
    """Context-bound operation over one exact canonical Work snapshot."""

    context: PassMemory

    model_config = {"frozen": True}

    def _validate_work(self, work: Work) -> None:
        if (self.context.tenant_id, self.context.editorial_id, self.context.work_id, self.context.source_version) != (
            work.tenant_id,
            work.editorial_id,
            work.work_id,
            work.version,
        ):
            raise ValueError("PassMemory no corresponde al snapshot canónico actual de Work.")

    def review(self, reviewer: Reviewer, work: Work, branch: str = "main") -> Tuple[ReviewFinding, ...]:
        self._validate_work(work)
        return reviewer.review(work, branch=branch)

    def propose(self, editorial_pass: EditorialPass, work: Work, branch: str = "main") -> Patch:
        self._validate_work(work)
        return editorial_pass.propose(work, branch=branch)


class SemanticContextService:
    """Orchestrates retrieval -> PassMemory while preserving canonical authority."""

    def __init__(self, retriever: MemoryRetriever | None = None, builder: ContextBuilder | None = None) -> None:
        self._retriever = retriever or MemoryRetriever()
        self._builder = builder or ContextBuilder()

    def prepare(
        self,
        work: Work,
        work_memory: WorkMemoryProjection,
        *,
        purpose: str,
        retrieval: RetrievalRequest,
        editorial_memory: EditorialMemory | None = None,
        author_memory: AuthorMemory | None = None,
        max_editorial_items: int = 4,
        max_author_items: int = 6,
    ) -> PreparedEditorialOperation:
        refs = self._retriever.retrieve(work, work_memory, retrieval)
        context = self._builder.build(
            work,
            work_memory,
            purpose=purpose,
            refs=refs,
            editorial_memory=editorial_memory,
            author_memory=author_memory,
            max_editorial_items=max_editorial_items,
            max_author_items=max_author_items,
        )
        return PreparedEditorialOperation(context=context)
