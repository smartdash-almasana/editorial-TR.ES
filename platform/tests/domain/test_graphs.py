"""
Pruebas para grafos especializados.
"""

import pytest

from editorial_tres.domain.graphs.expression import ContentBlock, ExpressionGraph
from editorial_tres.domain.graphs.knowledge import KnowledgeGraph, KnowledgeNode
from editorial_tres.domain.graphs.narrative import NarrativeGraph, NarrativeNode
from editorial_tres.domain.identifiers import WorkId
from editorial_tres.exceptions import (
    DuplicateNodeError,
    GraphCycleError,
    MissingParentNodeError,
)


def test_knowledge_graph_empty():
    work_id = WorkId(value="work.test-001")
    kg = KnowledgeGraph(work_id=work_id, nodes={})
    assert len(kg.nodes) == 0


def test_knowledge_graph_add_node():
    work_id = WorkId(value="work.test-001")
    kg = KnowledgeGraph(work_id=work_id, nodes={})
    node = KnowledgeNode(id="concept-1", node_type="concept", title="Concepto 1")
    kg = kg.add_node(node)
    assert kg.has_node("concept-1")


def test_knowledge_graph_duplicate():
    work_id = WorkId(value="work.test-001")
    kg = KnowledgeGraph(work_id=work_id, nodes={})
    node = KnowledgeNode(id="concept-1", node_type="concept", title="Concepto 1")
    kg = kg.add_node(node)
    with pytest.raises(DuplicateNodeError):
        kg.add_node(node)


def test_knowledge_graph_missing_parent():
    work_id = WorkId(value="work.test-001")
    kg = KnowledgeGraph(work_id=work_id, nodes={})
    child = KnowledgeNode(
        id="child-1", node_type="claim", title="Claim", parent_id="nonexistent"
    )
    with pytest.raises(MissingParentNodeError):
        kg.add_node(child)


def test_knowledge_graph_serialization():
    work_id = WorkId(value="work.test-001")
    kg = KnowledgeGraph(work_id=work_id, nodes={})
    node = KnowledgeNode(id="concept-1", node_type="concept", title="Concepto 1")
    kg = kg.add_node(node)
    data = kg.model_dump()
    restored = KnowledgeGraph.model_validate(data)
    assert restored.has_node("concept-1")
    assert restored.work_id == work_id


def test_narrative_graph_add_nodes():
    work_id = WorkId(value="work.test-001")
    ng = NarrativeGraph(work_id=work_id, nodes={})
    part = NarrativeNode(id="part-1", node_type="part", title="Parte 1", position=0)
    ng = ng.add_node(part)
    chap = NarrativeNode(
        id="chap-1", node_type="chapter", title="Capítulo 1", parent_id="part-1", position=0
    )
    ng = ng.add_node(chap)
    assert ng.has_node("part-1")
    assert ng.has_node("chap-1")
    children = ng.get_children("part-1")
    assert len(children) == 1
    assert children[0].id == "chap-1"


def test_narrative_graph_roots():
    work_id = WorkId(value="work.test-001")
    ng = NarrativeGraph(work_id=work_id, nodes={})
    p1 = NarrativeNode(id="p1", node_type="part", title="P1", position=0)
    p2 = NarrativeNode(id="p2", node_type="part", title="P2", position=1)
    ng = ng.add_node(p1)
    ng = ng.add_node(p2)
    roots = ng.get_roots()
    assert len(roots) == 2
    assert roots[0].id == "p1"
    assert roots[1].id == "p2"


def test_expression_graph_add_block():
    work_id = WorkId(value="work.test-001")
    eg = ExpressionGraph(work_id=work_id, blocks={})
    block = ContentBlock(
        id="b1", block_type="paragraph", content="Contenido", language="es", status="draft"
    )
    eg = eg.add_block(block)
    assert eg.has_block("b1")


def test_expression_graph_heading_can_be_empty():
    work_id = WorkId(value="work.test-001")
    eg = ExpressionGraph(work_id=work_id, blocks={})
    heading = ContentBlock(
        id="h1", block_type="heading", content="", language="es", status="draft"
    )
    eg = eg.add_block(heading)
    assert eg.has_block("h1")


def test_expression_graph_empty_paragraph_rejected():
    work_id = WorkId(value="work.test-001")
    eg = ExpressionGraph(work_id=work_id, blocks={})
    block = ContentBlock(
        id="b1", block_type="paragraph", content="", language="es", status="draft"
    )
    with pytest.raises(ValueError):
        eg.add_block(block)


def test_expression_graph_duplicate_block():
    work_id = WorkId(value="work.test-001")
    eg = ExpressionGraph(work_id=work_id, blocks={})
    block = ContentBlock(
        id="b1", block_type="paragraph", content="Contenido", language="es", status="draft"
    )
    eg = eg.add_block(block)
    with pytest.raises(DuplicateNodeError):
        eg.add_block(block)


def test_expression_graph_missing_parent():
    work_id = WorkId(value="work.test-001")
    eg = ExpressionGraph(work_id=work_id, blocks={})
    child = ContentBlock(
        id="b1",
        block_type="paragraph",
        content="Contenido",
        parent_id="nonexistent",
        language="es",
        status="draft",
    )
    with pytest.raises(MissingParentNodeError):
        eg.add_block(child)
